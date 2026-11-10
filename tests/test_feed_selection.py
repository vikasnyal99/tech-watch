from datetime import date
from types import SimpleNamespace

from backend.feed_selection import importance, personal_feed, trending_feed


TODAY = date(2026, 11, 4)


def item(technology, topic, title, kind='update', score=40):
    return {'id': technology + title, 'technology': technology, 'topic': topic,
            'title': title, 'summary': title + ' Official project details for engineers.',
            'type': kind, 'score': score, 'published_at': '2026-11-02'}


def preferences(**changes):
    return SimpleNamespace(**({'follows': [], 'topics': [], 'roles': [], 'signals': []} | changes))


def test_feed_follows_explicit_interests_not_global_importance():
    items = [item('PHP', 'Backend & APIs', 'PHP security release', 'security', 90),
             item('AWS', 'Cloud infrastructure', 'AWS service update'),
             item('React', 'Frontend & Web', 'React library update')]
    feed = personal_feed(items, preferences(follows=['React'], roles=['Software engineer']), TODAY)
    assert [x['technology'] for x in feed] == ['React']
    feed = personal_feed(items, preferences(topics=['Cloud infrastructure']), TODAY)
    assert [x['technology'] for x in feed] == ['AWS']
    assert len(personal_feed(items, preferences(), TODAY)) == 3


def test_trending_is_broad_but_requires_a_significant_change():
    items = [item('PHP', 'Backend & APIs', 'PHP security release', 'release', 65),
             item('GitHub', 'CI/CD & Developer tools', 'GitHub Actions blocked by default'),
             item('Kubernetes', 'Kubernetes & containers', 'Kubernetes major release', 'release', 75),
             item('AWS', 'Cloud infrastructure', 'AWS Continuum finds code vulnerabilities', 'security', 85),
             item('Redis', 'Data & databases', 'Redis weekly tutorial')]
    assert importance(items[3]) == 0  # A new security tool is not a security advisory.
    selected = trending_feed(items, today=TODAY)
    assert {x['technology'] for x in selected} == {'PHP', 'GitHub', 'Kubernetes'}
    assert selected[0]['technology'] == 'PHP'


def test_trending_drops_stale_news_but_keeps_active_incidents():
    old_news = item('Python', 'Backend & APIs', 'Python security release', 'security', 90)
    old_news['published_at'] = '2026-09-01'
    active_incident = item('Cloudflare', 'Reliability & observability', 'Regional service disruption', 'incident', 80)
    active_incident['published_at'] = '2026-09-01'
    active_incident['intelligence'] = {'rule_version': 'official-status-v1', 'severity': 'high'}
    assert trending_feed([old_news, active_incident], today=TODAY) == [active_incident]
