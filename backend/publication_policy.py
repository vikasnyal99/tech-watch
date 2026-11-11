"""Narrow automatic publication gate for routine official-source briefings."""
from datetime import date
import re

from backend.briefing_copy import validate_briefing_copy

RISK_WORDS = re.compile(
    r'\b(?:security|vulnerab\w*|cve-\d+|exploit\w*|breach|outage|incident|degrad\w*|'
    r'breaking|deprecat\w*|discontinu\w*|end.of.life|end.of.support|recall|critical|'
    r'urgent|emergency|remov\w*|no.longer|disabled.by.default)\b', re.I)
RISK_UNKNOWN = re.compile(r'\b(?:outage|incident|impact|expos\w*|mitigation|'
                          r'affected regions?|affected users?|affected services?|eligibility|availability)\b', re.I)
EDITORIAL_NOISE = re.compile(r'\b(?:gsoc|summer of code|hackathon|meetup|conference|webinar|'
                             r'podcast|newsletter|scholarship|giveaway|hiring|career|'
                             r'promotion|discount|free trial|anniversary)\b', re.I)


def routine_auto_publishable(analysis: dict, *, source_title: str, source_text: str,
                             release_type: str, published_at: str | None,
                             today: date | None = None) -> bool:
    """Fail closed unless a fresh, low-risk AI draft has exact source support."""
    if (release_type not in ('update', 'release') or EDITORIAL_NOISE.search(source_title)
            or RISK_WORDS.search(source_title + ' ' + source_text[:500])):
        return False
    if len(source_text.strip()) < 200 or analysis.get('rule_version') != 'ai-evidence-v2':
        return False
    try:
        age = ((today or date.today()) - date.fromisoformat((published_at or '')[:10])).days
    except ValueError:
        return False
    if not 0 <= age <= 7:
        return False
    if analysis.get('severity') not in ('low', 'medium') or analysis.get('confidence') != 'high':
        return False
    unknowns = analysis.get('unknowns') or []
    if len(unknowns) > 2 or any(RISK_UNKNOWN.search(str(item)) for item in unknowns):
        return False
    if analysis.get('affected_regions'):
        return False
    evidence = analysis.get('evidence_quote') or ''
    summary_evidence = analysis.get('summary_evidence_quote') or ''
    if (not 20 <= len(evidence) <= 350 or evidence not in source_text
            or not 45 <= len(summary_evidence) <= 350 or summary_evidence not in source_text):
        return False
    return not validate_briefing_copy(analysis)


def needs_second_check(analysis: dict, *, source_title: str, source_text: str,
                       release_type: str, published_at: str | None,
                       today: date | None = None) -> bool:
    """Only source-rich, recent consequential drafts qualify for an extra AI call."""
    if analysis.get('rule_version') != 'ai-evidence-v2' or analysis.get('confidence') != 'high':
        return False
    if not 200 <= len(source_text.strip()) <= 4000 or EDITORIAL_NOISE.search(source_title):
        return False
    try:
        age = ((today or date.today()) - date.fromisoformat((published_at or '')[:10])).days
    except ValueError:
        return False
    if not 0 <= age <= 7 or validate_briefing_copy(analysis):
        return False
    consequential = (release_type in ('security', 'deprecation')
                     or bool(RISK_WORDS.search(source_title + ' ' + source_text[:500])))
    if not consequential or analysis.get('severity') not in ('medium', 'high', 'critical'):
        return False
    if release_type == 'security' and analysis.get('severity') not in ('high', 'critical'):
        return False
    evidence = analysis.get('evidence_quote') or ''
    summary_evidence = analysis.get('summary_evidence_quote') or ''
    return (20 <= len(evidence) <= 350 and evidence in source_text
            and 45 <= len(summary_evidence) <= 350 and summary_evidence in source_text)


def verified_auto_publishable(analysis: dict, verdict: dict, *, source_text: str) -> bool:
    """Require a separate checker to agree on severity and cite each main claim."""
    if not verdict.get('supported') or verdict.get('severity') != analysis.get('severity'):
        return False
    if verdict.get('contradiction') or verdict.get('material_unknown'):
        return False
    for key in ('title_quote', 'summary_quote', 'action_quote'):
        quote = verdict.get(key) or ''
        if not 30 <= len(quote) <= 350 or quote not in source_text:
            return False
    return True
