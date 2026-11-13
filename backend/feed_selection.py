"""Deterministic selection for the four briefing sections.

Only reviewed, published items enter here. Importance is inferred from the
publisher-backed briefing copy, never from fabricated view or popularity counts.
"""

import re
from collections import Counter
from datetime import date


ROLE_TOPICS = {
    'Software engineer': {'Backend & APIs', 'Frontend & Web', 'CI/CD & Developer tools', 'Security'},
    'Platform engineer': {'Cloud infrastructure', 'Kubernetes & containers', 'CI/CD & Developer tools', 'Reliability & observability', 'Security'},
    'DevOps / cloud engineer': {'Cloud infrastructure', 'Kubernetes & containers', 'CI/CD & Developer tools', 'Reliability & observability', 'Security'},
    'SRE': {'Reliability & observability', 'Cloud infrastructure', 'Kubernetes & containers', 'Security'},
    'Product manager': {'AI models & APIs', 'Architecture & strategy', 'Security', 'Frontend & Web'},
    'Engineering leader': {'Architecture & strategy', 'Security', 'AI models & APIs', 'Cloud infrastructure', 'CI/CD & Developer tools'},
}

SECURITY = re.compile(r'\b(?:security (?:release|advisory|update|fix)|critical vulnerabilit(?:y|ies)|cve-\d+|remote code execution|compromis(?:e|ed)|out-of-band security)\b', re.I)
BREAKING = re.compile(r'\b(?:breaking change|deprecat\w*|discontinu\w*|end.of.support|end.of.life|blocked by default|remov(?:e|ed|al)\s+apis?)\b', re.I)
MAJOR_TITLE = re.compile(r'\b(?:general availability|generally available|major release|stable release|reaches? ga|launch(?:ed|es)?|now available)\b', re.I)
MAJOR_BODY = re.compile(r'\b(?:general availability|generally available|reaches? ga)\b', re.I)


def freshness(item: dict, today: date) -> int:
    try:
        age = max(0, (today - date.fromisoformat(item['published_at'][:10])).days)
    except (KeyError, TypeError, ValueError):
        return 0
    return 12 if age <= 2 else 8 if age <= 7 else 4 if age <= 14 else 0 if age <= 30 else -12


def recent_for_trending(item: dict, today: date) -> bool:
    if item.get('fictional'):
        return True  # Recorded offline examples do not represent live recency.
    if (item.get('intelligence') or {}).get('rule_version') == 'official-status-v1':
        return True  # Still-active incidents are withdrawn when the provider resolves them.
    try:
        return (today - date.fromisoformat(item['published_at'][:10])).days <= 30
    except (KeyError, TypeError, ValueError):
        return False


def diverse_order(items: list[dict], value) -> list[dict]:
    """Keep strong stories first while avoiding a run from one vendor or topic."""
    remaining = list(items)
    ordered = []
    technologies: Counter[str] = Counter()
    topics: Counter[str] = Counter()
    while remaining:
        best = max(range(len(remaining)), key=lambda index: (
            value(remaining[index]) - 9 * technologies[remaining[index]['technology']]
            - 3 * topics[remaining[index]['topic']],
            remaining[index].get('published_at') or '',
            -index,
        ))
        item = remaining.pop(best)
        ordered.append(item)
        technologies[item['technology']] += 1
        topics[item['topic']] += 1
    return ordered


def personal_feed(items: list[dict], preferences, today: date | None = None) -> list[dict]:
    today = today or date.today()
    follows = set(preferences.follows)
    topics = set(preferences.topics)
    if follows or topics:
        selected = [item for item in items if item['technology'] in follows or item['topic'] in topics
                    or ('AI models' in follows and item['topic'] == 'AI models & APIs')]
    else:
        role_topics = set().union(*(ROLE_TOPICS.get(role, set()) for role in preferences.roles))
        selected = [item for item in items if item['topic'] in role_topics] if role_topics else items

    def value(item):
        return ((item.get('score') or 0) // 3 + freshness(item, today)
                + (38 if item['technology'] in follows else 0)
                + (26 if item['topic'] in topics else 0))

    return diverse_order(selected, value)


def importance(item: dict) -> int:
    intelligence = item.get('intelligence') or {}
    if intelligence.get('rule_version') == 'official-status-v1':
        return {'critical': 100, 'high': 85}.get(intelligence.get('severity'), 0)
    if intelligence.get('rule_version') == 'editorial-evidence-v1':
        return {'critical': 100, 'high': 85, 'medium': 60}.get(intelligence.get('severity'), 0)
    if intelligence.get('rule_version') in ('ai-evidence-v1', 'ai-evidence-v2') and 'severity' in intelligence:
        if intelligence.get('confidence') == 'low':
            return 0
        return {'critical': 100, 'high': 85, 'medium': 60,
                'low': 0, 'unknown': 0}.get(intelligence['severity'], 0)
    text = f"{item['title']} {item['summary']}"
    if item.get('source_id') == 'github-advisories' or SECURITY.search(text):
        return 100
    if item['type'] == 'deprecation' or BREAKING.search(text):
        return 85
    if MAJOR_TITLE.search(item['title']) or MAJOR_BODY.search(item['summary']):
        return 70
    if item['type'] == 'release' and (item.get('score') or 0) >= 70:
        return 65
    return 0


def trending_feed(items: list[dict], signals: list[str] | None = None, today: date | None = None) -> list[dict]:
    today = today or date.today()
    signals = set(signals or [])
    candidates = [item for item in items if importance(item) >= 65 and recent_for_trending(item, today)]

    def value(item):
        tier = importance(item)
        bonus = (8 if 'Security' in signals and tier == 100 else 0)
        bonus += 8 if 'Breaking changes' in signals and tier == 85 else 0
        bonus += 5 if 'Major releases' in signals and tier in (65, 70) else 0
        return tier + (item.get('score') or 0) // 5 + freshness(item, today) + bonus

    # Diversity is useful within a severity tier, but must never bury a critical
    # advisory or confirmed major incident beneath a less consequential story.
    ordered = []
    for tier in (100, 85, 70, 65):
        ordered.extend(diverse_order([item for item in candidates if importance(item) == tier], value))
    return ordered[:20]
