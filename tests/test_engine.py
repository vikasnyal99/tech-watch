from pathlib import Path
from datetime import datetime, timedelta, timezone
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import backend.db as db
import backend.engine as pipeline
import backend.main as main
import backend.ai_budget as ai_budget
from backend.fetcher import check_url
from backend.python_source import discover_releases, parse_release
from backend.rss_source import parse_feed, score, canonical_url, SOURCES, DISABLED_BY_DEFAULT
from backend.special_sources import (parse_anthropic_news, article_excerpt,
                                     parse_github_advisories, parse_kernel_releases,
                                     parse_kafka_blog, parse_mysql_tags)
from backend.data import TECHNOLOGIES
from backend.feed_selection import importance
from backend.service_health import parse_status_page, parse_aws_events, parse_google_events, parse_azure_feed, PROVIDERS
from backend.intelligence import analyze, AnalysisError
from backend.intelligence import configured as ai_configured, eligible as ai_eligible
from backend.publication_policy import routine_auto_publishable


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    database = create_engine(f"sqlite:///{tmp_path / 'engine.db'}", connect_args={'check_same_thread': False})
    sessions = sessionmaker(bind=database)
    for module in (db, pipeline, ai_budget):
        monkeypatch.setattr(module, 'engine', database)
        monkeypatch.setattr(module, 'Session', sessions)
    monkeypatch.setattr(main, 'Session', sessions)
    db.migrate()
    yield sessions
    database.dispose()


def drain():
    for _ in range(20):
        if not pipeline.run_once():
            return
    raise AssertionError('job queue did not drain')


def count(sessions, table):
    with sessions() as session:
        return session.execute(text(f'SELECT count(*) FROM {table}')).scalar_one()


def test_recorded_python_release_reaches_personalized_feed(isolated_db):
    pipeline.seed_source('python-fixture', 'fixture_python', True)
    assert pipeline.schedule_due() == 1
    drain()
    assert count(isolated_db, 'technology_releases') == 1
    assert count(isolated_db, 'release_revisions') == 1
    assert count(isolated_db, 'release_facts') == 1
    assert count(isolated_db, 'tech_briefs') == 1
    assert len(pipeline.published_items()) == 1
    item = pipeline.published_items()[0]
    assert item['fictional'] is True and item['source_url'] is None
    assert pipeline.event_detail(item['id'])['facts'][0]['evidence_excerpt'].startswith('Python 3.99.0')
    with TestClient(main.app) as client:
        headers = {'X-Installation-ID': uuid.uuid4().hex}
        preferences = client.get('/v1/preferences', headers=headers).json()
        preferences['follows'] = ['Python']
        assert client.put('/v1/preferences', headers=headers, json=preferences).status_code == 200
        stack = client.get('/v1/feed?section=stack', headers=headers).json()['items']
        assert stack[0]['id'] == item['id']
        assert stack[0]['summary'] == item['summary']
    pipeline.manual_recheck('python-fixture')
    drain()
    assert count(isolated_db, 'release_revisions') == 1
    assert count(isolated_db, 'tech_briefs') == 1


def test_changed_release_creates_revision_not_duplicate(isolated_db, monkeypatch):
    pipeline.seed_source('python-fixture', 'fixture_python', True)
    pipeline.schedule_due(); drain()
    original = pipeline.get_html
    changed = (Path(__file__).parents[1] / 'fixtures/python_source/release.html').read_text().replace(
        'source-to-feed pipeline.', 'source-to-feed pipeline and revision handling.')
    monkeypatch.setattr(pipeline, 'get_html', lambda source, url, **kw: (changed, 200, None, None) if not kw.get('index') else original(source, url, **kw))
    pipeline.manual_recheck('python-fixture'); drain()
    assert count(isolated_db, 'technology_releases') == 1
    assert count(isolated_db, 'release_revisions') == 2
    assert count(isolated_db, 'tech_briefs') == 2
    assert len(pipeline.published_items()) == 1


def test_live_source_requires_admin_review(isolated_db, monkeypatch):
    pipeline.seed_source('python-live', 'python_downloads', True)
    index = (Path(__file__).parents[1] / 'fixtures/python_source/downloads.html').read_text()
    release = (Path(__file__).parents[1] / 'fixtures/python_source/release.html').read_text()
    monkeypatch.setattr(pipeline, 'get_html', lambda source, url, **kw: (index if kw.get('index') else release, 200, None, None))
    pipeline.schedule_due(); drain()
    assert not pipeline.published_items()
    queued = pipeline.review_queue()
    assert len(queued) == 1 and queued[0]['status'] == 'review_required'
    monkeypatch.setenv('ADMIN_TOKEN', 'local-test-token')
    with TestClient(main.app) as client:
        assert client.get('/admin/review-queue').status_code == 403
        headers = {'X-Admin-Token': 'local-test-token'}
        assert len(client.get('/admin/review-queue', headers=headers).json()['items']) == 1
        assert client.post(f"/admin/review/{queued[0]['id']}/publish", headers=headers).status_code == 200
    assert len(pipeline.published_items()) == 1
    assert pipeline.published_items()[0]['source_url'].startswith('https://www.python.org/')


def test_parser_failure_never_publishes(isolated_db, monkeypatch):
    pipeline.seed_source('python-fixture', 'fixture_python', True)
    monkeypatch.setattr(pipeline, 'get_html', lambda source, url, **kw: ('<html>changed structure</html>', 200, None, None))
    pipeline.schedule_due(); drain()
    assert count(isolated_db, 'technology_releases') == 0
    assert count(isolated_db, 'tech_briefs') == 0
    with isolated_db() as session:
        job = session.execute(text("SELECT status,last_error FROM processing_jobs WHERE kind='fetch-index'")).first()
    assert job[0] == 'pending' and 'no Python release links' in job[1]


def test_python_parser_and_url_guard():
    html = (Path(__file__).parents[1] / 'fixtures/python_source/downloads.html').read_text()
    links = discover_releases(html)
    assert [(x.version, x.url) for x in links] == [('3.99.0', 'https://www.python.org/downloads/release/python-3990/')]
    release_html = (Path(__file__).parents[1] / 'fixtures/python_source/release.html').read_text()
    release = parse_release(release_html, links[0].url, links[0].version)
    assert release.version == '3.99.0' and 'fictional' in release.evidence
    official_shape = '<article class="text"><header class="article-header"><h1>Python 3.15.2</h1></header><p>Release date: Oct. 25, 2026</p><h2>Maintenance release</h2><p>Python 3.15.2 is an expedited security release with verified changes documented on the official page.</p><h2>Security content in this release</h2><ul><li>CVE-2026-115557: Distrust compromised intermediate CA keys.</li></ul></article>'
    parsed = parse_release(official_shape, 'https://www.python.org/downloads/release/python-3152/', '3.15.2')
    assert parsed.release_type == 'security' and parsed.published_at == '2026-10-25'
    assert parsed.evidence.startswith('CVE-2026-115557')
    check_url(links[0].url, resolver=lambda host: True)
    with pytest.raises(ValueError):
        check_url('https://127.0.0.1/admin', resolver=lambda host: True)
    with pytest.raises(ValueError):
        check_url('https://www.python.org.evil.test/downloads/', resolver=lambda host: True)


def test_official_rss_deduplicates_ranks_and_requires_review(isolated_db, monkeypatch):
    xml = '''<rss version="2.0"><channel><title>GitHub Changelog</title>
    <item><title>Security release for Actions</title><link>https://github.blog/changelog/security-release/</link>
    <description>GitHub Actions changes the default event policy for public repositories. Workflows using pull_request_target will be blocked unless an applicable policy explicitly allows the event.</description>
    <pubDate>Mon, 02 Nov 2026 10:00:00 GMT</pubDate></item>
    <item><title>Security release for Actions</title><link>https://github.blog/changelog/security-release/</link>
    <description>GitHub Actions changes the default event policy for public repositories. Workflows using pull_request_target will be blocked unless an applicable policy explicitly allows the event.</description></item>
    <item><title>Fake external</title><link>https://evil.test/news</link><description>Do not use.</description></item>
    </channel></rss>'''
    assert len(parse_feed(xml, 'https://github.blog/changelog/feed/')) == 1
    assert score('Critical security advisory', 'security', '2026-11-02') > score('Weekly podcast', 'update', '2026-11-02')
    pipeline.seed_rss_sources()
    monkeypatch.setattr(pipeline, 'get_html', lambda source, url, **kw: (xml, 200, None, None))
    pipeline.manual_recheck('github-changelog'); drain()
    assert count(isolated_db, 'technology_releases') == 1
    assert count(isolated_db, 'release_facts') == 1
    assert not pipeline.published_items()
    queued = pipeline.review_queue()
    assert len(queued) == 1 and queued[0]['status'] == 'needs_edit'
    pipeline.manual_recheck('github-changelog'); drain()
    assert count(isolated_db, 'technology_releases') == 1
    assert count(isolated_db, 'release_revisions') == 1
    pipeline.edit_brief(queued[0]['id'], {
        'why_it_matters': 'Repositories relying on pull_request_target need an explicit policy before the change.',
        'next_action': 'Audit workflows and configure an applicable Actions event policy.',
    })
    pipeline.review_decision(queued[0]['id'], 'publish')
    item = pipeline.published_items()[0]
    assert item['technology'] == 'GitHub' and item['fictional'] is False
    original_id = item['id']
    pipeline.edit_brief(original_id, {'next_action': 'Audit affected workflows and set an explicit event policy.'})
    assert not pipeline.published_items()
    pipeline.review_decision(original_id, 'publish')
    assert pipeline.published_items()[0]['id'] == original_id
    assert pipeline.event_detail(item['id'])['facts'][0]['evidence_url'] == item['source_url']
    with TestClient(main.app) as client:
        headers = {'X-Installation-ID': uuid.uuid4().hex}
        live = client.get('/v1/feed', headers=headers).json()['items']
        demo = client.get('/v1/feed?demo=true', headers=headers).json()['items']
        assert len(live) == 1 and live[0]['fictional'] is False
        assert len(demo) == 4 and any(x['fictional'] for x in demo)


def test_cross_host_official_feed_and_fragment_identity():
    assert len(SOURCES) >= 29 and DISABLED_BY_DEFAULT == {'docker-blog'}
    cloud = '''<rss><channel><item><title>Google Cloud update</title>
    <link>https://cloud.google.com/blog/products/example</link>
    <description>Google Cloud added a documented feature for developers.</description>
    </item></channel></rss>'''
    feed = 'https://cloudblog.withgoogle.com/rss/'
    with pytest.raises(ValueError):
        parse_feed(cloud, feed, allowed_hosts={'cloudblog.withgoogle.com'})
    assert len(parse_feed(cloud, feed, allowed_hosts={'cloud.google.com'})) == 1
    assert canonical_url('https://www.php.net/index.php#release-a', 'https://www.php.net/feed.atom') != canonical_url(
        'https://www.php.net/index.php#release-b', 'https://www.php.net/feed.atom')
    assert main.ai_relevant({'title': 'Spring AI accepts embeddings', 'summary': 'Update', 'type': 'update', 'topic': 'Backend & APIs'})
    assert not main.ai_relevant({'title': 'PostgreSQL release', 'summary': 'Bug fixes', 'type': 'release', 'topic': 'Data & databases'})


def test_offline_mode_never_fetches_live_sources(monkeypatch):
    monkeypatch.setenv('OFFLINE_MODE', '1')
    with pytest.raises(RuntimeError, match='offline mode'):
        pipeline.get_html({'adapter': 'rss'}, 'https://go.dev/blog/feed.atom', index=True)


def test_new_sources_cover_catalog_and_ai_models_follow():
    monitored = {source[1] for source in SOURCES}
    assert set(TECHNOLOGIES) - monitored == {'AI models'}
    item = {'technology': 'Anthropic', 'topic': 'AI models & APIs', 'score': 70,
            'published_at': '2026-11-05', 'title': 'Claude release', 'summary': 'Official model update'}
    assert main.personal_feed([item], main.Preferences(follows=['AI models'])) == [item]


def test_article_only_node_feed_creates_source_backed_draft(isolated_db, monkeypatch):
    feed = '''<rss><channel><item><title>Node.js security release</title>
    <link>https://nodejs.org/en/blog/vulnerability/example</link>
    <pubDate>Thu, 05 Nov 2026 09:00:00 GMT</pubDate></item></channel></rss>'''
    article = '<main><h1>Node.js security release</h1><p>Node.js has published a security release for maintained branches. Applications should consult the release notes to identify the affected versions and fixes before upgrading their runtime.</p></main>'
    pipeline.seed_rss_sources()
    monkeypatch.setattr(pipeline, 'get_html', lambda source, url, **kw: (
        feed if kw.get('index') else article, 200, None, None))
    pipeline.manual_recheck('node-security'); drain()
    assert count(isolated_db, 'technology_releases') == 1
    assert count(isolated_db, 'release_facts') == 1
    assert not pipeline.published_items()
    assert pipeline.review_queue()[0]['technology'] == 'Node.js'


def test_anthropic_article_and_github_advisory_adapters(isolated_db, monkeypatch):
    listing = '<a href="/news/claude-model-update"><h3>Claude model update</h3></a>'
    article = '<article><p>Anthropic released a Claude model update with changes to the API and developer tooling. The official article explains availability, compatibility, and evaluation guidance for teams considering adoption.</p></article>'
    advisory = '''[{"ghsa_id":"GHSA-aaaa-bbbb-cccc","html_url":"https://github.com/advisories/GHSA-aaaa-bbbb-cccc","summary":"A Python package allows unsafe deserialization","description":"The official advisory documents the conditions that allow unsafe deserialization and recommends upgrading after checking the affected version range.","severity":"high","published_at":"2026-11-05T08:00:00Z","vulnerabilities":[{"package":{"ecosystem":"pip","name":"sample-package"},"vulnerable_version_range":"< 2.0.0","first_patched_version":"2.0.0"}]}]'''
    assert parse_anthropic_news(listing)[0].url.endswith('/news/claude-model-update')
    assert 'developer tooling' in article_excerpt(article, 'anthropic-news')[0]
    parsed = parse_github_advisories(advisory)
    assert parsed[0].technology == 'Python' and 'First patched version: 2.0.0' in parsed[0].excerpt
    assert importance({'title': parsed[0].title, 'summary': 'Unsafe deserialization',
                       'type': parsed[0].kind, 'source_id': 'github-advisories'}) == 100
    pipeline.seed_rss_sources()
    def source_body(source, url, **kw):
        if source['id'] == 'github-advisories':
            return advisory, 200, None, None
        return (listing if kw.get('index') else article), 200, None, None
    monkeypatch.setattr(pipeline, 'get_html', source_body)
    pipeline.manual_recheck('anthropic-news')
    pipeline.manual_recheck('github-advisories')
    drain()
    assert count(isolated_db, 'technology_releases') == 2
    assert not pipeline.published_items()
    assert {x['technology'] for x in pipeline.review_queue()} == {'Anthropic', 'Python'}


def test_kernel_feed_uses_unique_official_changelog_urls():
    xml = '''<rss><channel><item><title>7.3.1: stable</title>
    <link>https://www.kernel.org/</link><description><![CDATA[
    <table><tr><th>Released:</th><td>2026-11-05</td></tr>
    <tr><th>ChangeLog:</th><td><a href="https://cdn.kernel.org/pub/linux/kernel/v7.x/ChangeLog-7.3.1">ChangeLog-7.3.1</a></td></tr></table>]]></description></item>
    <item><title>7.2.15: stable</title><link>https://www.kernel.org/</link><description><![CDATA[
    <a href="https://cdn.kernel.org/pub/linux/kernel/v7.x/ChangeLog-7.2.15">ChangeLog-7.2.15</a>]]></description></item>
    </channel></rss>'''
    entries = parse_kernel_releases(xml)
    assert len(entries) == 2 and entries[0].url != entries[1].url


def test_urgent_source_cadence_and_incident_review_lifecycle(isolated_db):
    pipeline.seed_rss_sources()
    with isolated_db() as session:
        intervals = dict(session.execute(text("SELECT id,interval_seconds FROM technology_sources WHERE id IN ('aws-security','cloudflare-blog')")).all())
    assert intervals == {'aws-security': 600, 'cloudflare-blog': 1800}
    incident = {'id': 'cloudflare:cf-123', 'provider': 'Cloudflare',
                'title': 'Regional Cloudflare service disruption', 'status': 'investigating',
                'impact': 'major', 'summary': ('Cloudflare reports elevated errors for its edge service in one region. '
                'The provider is investigating and has not established whether other regions are affected. '
                'Customers using the named region should inspect the official status page.'),
                'updated_at': '2026-11-11T07:00:00+00:00',
                'url': 'https://www.cloudflarestatus.com/incidents/cf-123'}
    snapshot = {'offline': False, 'providers': [{'name': 'Cloudflare', 'available': True}], 'incidents': [incident]}
    assert pipeline.sync_service_incidents(snapshot) == 1
    assert pipeline.sync_service_incidents(snapshot) == 0
    assert not pipeline.published_items()
    queued = pipeline.review_queue()
    assert len(queued) == 1 and queued[0]['intelligence']['severity'] == 'high'
    pipeline.edit_brief(queued[0]['id'], {'next_action': 'Check the official incident page and the error rate in your affected region.'})
    assert pipeline.draft_detail(queued[0]['id'])['intelligence']['severity'] == 'high'
    pipeline.review_decision(queued[0]['id'], 'publish')
    published = pipeline.published_items()
    assert len(published) == 1 and published[0]['topic'] == 'Reliability & observability'
    assert importance(published[0]) == 85
    assert len(main.trending_feed(published)) == 1
    # The provider's confirmed resolution removes the briefing, but never on a failed status check.
    assert pipeline.sync_service_incidents({'offline': False, 'providers': [{'name': 'Cloudflare', 'available': False}], 'incidents': []}) == 0
    assert len(pipeline.published_items()) == 1
    assert pipeline.sync_service_incidents({'offline': False, 'providers': [{'name': 'Cloudflare', 'available': True}], 'incidents': []}) == 0
    assert not pipeline.published_items()


def test_ai_analysis_requires_source_evidence_and_keeps_review_gate(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.setenv('AI_ENABLED', '1')
    monkeypatch.delenv('OFFLINE_MODE', raising=False)
    source = ('Cloudflare reports a partial outage in one region. The edge service returns elevated errors. '
              'The provider is investigating the cause and has not confirmed impact in other regions.')
    result = {'title': 'Cloudflare edge errors in one region',
              'summary': ('Cloudflare reports elevated errors for its edge service in one region. '
                          'The provider is investigating the cause. It has not confirmed impact elsewhere, '
                          'so teams should check the official incident for their affected service and location.'),
              'why_it_matters': 'Applications using the affected edge region may see increased errors.',
              'next_action': 'Check the incident page and your regional error rates.',
              'severity': 'high', 'confidence': 'medium', 'affected_products': ['edge service'],
              'affected_regions': [], 'evidence_quote': 'The edge service returns elevated errors.',
              'summary_evidence_quote': 'Cloudflare reports a partial outage in one region. The edge service returns elevated errors.',
              'unknowns': ['Other regions']}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {'status': 'completed', 'usage': {'input_tokens': 900, 'output_tokens': 300},
                    'output': [{'content': [{'type': 'output_text', 'text': __import__('json').dumps(result)}]}]}

    calls = []
    monkeypatch.setattr('backend.intelligence.httpx.post', lambda *args, **kwargs: (calls.append(kwargs), Response())[1])
    output = analyze('Cloudflare outage', source, 'https://www.cloudflarestatus.com/incidents/example')
    assert output['severity'] == 'high' and output['rule_version'] == 'ai-evidence-v2'
    assert calls[0]['json']['model'] == 'gpt-6-luna'
    assert calls[0]['json']['reasoning'] == {'effort': 'none'}
    assert calls[0]['json']['max_output_tokens'] == 1000
    assert output['_usage']['input_tokens'] == 900
    result['severity'] = 'medium'
    result['evidence_quote'] = ''
    assert analyze('Cloudflare outage', source, 'https://www.cloudflarestatus.com/incidents/example')['evidence_quote'] == result['summary_evidence_quote']
    result['severity'] = 'high'
    result['evidence_quote'] = 'A worldwide outage is confirmed.'
    with pytest.raises(ValueError, match='absent from source'):
        analyze('Cloudflare outage', source, 'https://www.cloudflarestatus.com/incidents/example')


def test_ai_draft_is_reviewed_and_edit_clears_model_rank(isolated_db, monkeypatch):
    when = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
    xml = f'''<rss><channel><item><title>Cloudflare security update</title>
    <link>https://blog.cloudflare.com/example-update/</link>
    <description>Cloudflare published a security update for its edge service. The official release describes the issue and the mitigation for operators.</description>
    <pubDate>{when}</pubDate>
    </item></channel></rss>'''
    copy = {'title': 'Cloudflare security update', 'summary': ('Cloudflare published a security update for its edge service. '
            'The official release describes the issue and mitigation for operators. Teams should check the official '
            'article for the specific deployments covered before changing their configuration.'),
            'why_it_matters': 'Operators of the affected edge service may need to review their configuration.',
            'next_action': 'Read the official release and check the affected deployment scope.',
            'severity': 'high', 'confidence': 'medium', 'evidence_quote': 'Cloudflare published a security update',
            'summary_evidence_quote': 'Cloudflare published a security update for its edge service. The official release describes the issue and the mitigation for operators.',
            'rule_version': 'ai-evidence-v2', '_usage': {'input_tokens': 800, 'output_tokens': 300}}
    pipeline.seed_rss_sources()
    monkeypatch.setattr(pipeline, 'get_html', lambda source, url, **kw: (xml, 200, None, None))
    monkeypatch.setattr(pipeline, 'intelligence_configured', lambda: True)
    monkeypatch.setattr(pipeline, 'analyze', lambda *args: copy)
    pipeline.manual_recheck('cloudflare-blog'); drain()
    draft = pipeline.review_queue()[0]
    assert draft['status'] == 'review_required' and draft['intelligence']['severity'] == 'high'
    assert count(isolated_db, 'ai_requests') == 1
    assert ai_budget.usage_snapshot()['spent_usd'] == 0.00023
    assert not pipeline.published_items()
    pipeline.edit_brief(draft['id'], {'next_action': 'Check the official release and deployment scope before acting.'})
    assert pipeline.draft_detail(draft['id'])['intelligence'] is None


def test_editor_can_rank_unknown_impact_only_with_retained_evidence(isolated_db):
    quote = 'The service is returning elevated errors in multiple regions.'
    snapshot = {'offline': False, 'providers': [{'name': 'AWS', 'available': True}],
                'incidents': [{'id': 'aws:regional-event', 'provider': 'AWS', 'title': 'Cloud service errors',
                               'status': 'investigating', 'impact': 'unknown',
                               'summary': quote + ' Engineers are investigating the affected services and will publish a further update. '
                               'Customers should check the official status page for their account and region.',
                               'updated_at': '2026-11-11T08:00:00+00:00',
                               'url': 'https://health.aws.amazon.com/health/status'}]}
    pipeline.sync_service_incidents(snapshot)
    draft = pipeline.review_queue()[0]
    assert draft['intelligence']['severity'] == 'unknown'
    with pytest.raises(ValueError, match='exact'):
        pipeline.edit_brief(draft['id'], {'severity': 'high', 'evidence_quote': 'All AWS services are down worldwide.'})
    pipeline.edit_brief(draft['id'], {'severity': 'high', 'evidence_quote': quote})
    assert pipeline.draft_detail(draft['id'])['intelligence']['rule_version'] == 'editorial-evidence-v1'
    pipeline.review_decision(draft['id'], 'publish')
    assert importance(pipeline.published_items()[0]) == 85


def test_ai_requires_explicit_switch_and_significant_recent_source(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key')
    monkeypatch.delenv('AI_ENABLED', raising=False)
    assert not ai_configured()
    monkeypatch.setenv('AI_ENABLED', '1')
    assert ai_configured()
    text_body = 'The vendor confirms a serious update with documented scope and mitigation. ' * 3
    assert ai_eligible('security', 'Security release', 'node-security', text_body, '2026-11-12',
                       today=datetime(2026, 11, 12, tzinfo=timezone.utc).date())
    assert ai_eligible('update', 'Routine developer update', 'cloudflare-blog', text_body, '2026-11-12',
                       today=datetime(2026, 11, 12, tzinfo=timezone.utc).date())
    assert not ai_eligible('update', 'Rust Summer of Code results', 'rust-blog', text_body, '2026-11-12',
                           today=datetime(2026, 11, 12, tzinfo=timezone.utc).date())
    assert not ai_eligible('security', 'Old security release', 'node-security', text_body, '2026-09-01',
                           today=datetime(2026, 11, 12, tzinfo=timezone.utc).date())


def test_routine_publication_policy_requires_source_evidence_and_no_risk():
    source = ('Kubernetes 1.32 adds a new scheduling option for workloads using dedicated nodes. '
              'Operators can enable the option in the scheduler configuration after reviewing the release notes. '
              'The previous scheduling behaviour remains the default for existing clusters.')
    analysis = {
        'title': 'Kubernetes adds a scheduling option',
        'summary': ('Kubernetes 1.32 adds a scheduling option for workloads using dedicated nodes. '
                    'Operators can enable it through scheduler configuration after reviewing the release notes. '
                    'Existing clusters keep the previous scheduling behaviour by default.'),
        'why_it_matters': 'Teams with dedicated nodes can evaluate the new scheduler option.',
        'next_action': 'Review the release notes and scheduler configuration before enabling it.',
        'severity': 'medium', 'confidence': 'high', 'affected_regions': [], 'unknowns': [],
        'evidence_quote': 'Kubernetes 1.32 adds a new scheduling option for workloads using dedicated nodes.',
        'summary_evidence_quote': 'Operators can enable the option in the scheduler configuration after reviewing the release notes.',
        'rule_version': 'ai-evidence-v2',
    }
    today = datetime(2026, 11, 12, tzinfo=timezone.utc).date()
    kw = {'source_title': 'Kubernetes scheduling option', 'source_text': source,
          'release_type': 'update', 'published_at': '2026-11-12', 'today': today}
    assert routine_auto_publishable(analysis, **kw)
    assert not routine_auto_publishable(analysis, **{**kw, 'source_title': 'Security update for Kubernetes'})
    assert not routine_auto_publishable(analysis, **{**kw, 'source_title': 'Kubernetes Summer of Code results'})
    assert not routine_auto_publishable(analysis, **{**kw, 'published_at': '2026-11-01'})
    assert not routine_auto_publishable({**analysis, 'unknowns': ['Impact not confirmed']}, **kw)
    assert routine_auto_publishable({**analysis, 'unknowns': ['Future timeline not stated']}, **kw)
    assert not routine_auto_publishable({**analysis, 'summary_evidence_quote': 'Unsupported claim'}, **kw)


def test_routine_ai_publishes_without_review_but_records_audit(isolated_db, monkeypatch):
    when = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
    source = ('Kubernetes adds a scheduling option for workloads using dedicated nodes. '
              'Operators can enable the option in the scheduler configuration after reviewing the release notes. '
              'The previous scheduling behaviour remains the default for existing clusters.')
    xml = f'''<rss><channel><item><title>Kubernetes scheduling option</title>
    <link>https://kubernetes.io/blog/scheduling-option/</link>
    <description>{source}</description><pubDate>{when}</pubDate></item></channel></rss>'''
    analysis = {'title': 'Kubernetes adds a scheduling option',
                'summary': ('Kubernetes adds a scheduling option for workloads using dedicated nodes. '
                            'Operators can enable it after reviewing the release notes. Existing clusters keep '
                            'the previous scheduling behaviour by default.'),
                'why_it_matters': 'Teams with dedicated nodes can evaluate the new scheduler option.',
                'next_action': 'Review the release notes and scheduler configuration before enabling it.',
                'severity': 'medium', 'confidence': 'high', 'affected_regions': [], 'unknowns': [],
                'evidence_quote': 'Kubernetes adds a scheduling option for workloads using dedicated nodes.',
                'summary_evidence_quote': 'Operators can enable the option in the scheduler configuration after reviewing the release notes.',
                'rule_version': 'ai-evidence-v2', '_usage': {'input_tokens': 700, 'output_tokens': 250}}
    monkeypatch.setenv('AUTO_PUBLISH_ROUTINE', '1')
    pipeline.seed_rss_sources()
    monkeypatch.setattr(pipeline, 'get_html', lambda source, url, **kw: (xml, 200, None, None))
    monkeypatch.setattr(pipeline, 'intelligence_configured', lambda: True)
    monkeypatch.setattr(pipeline, 'analyze', lambda *args: dict(analysis))
    pipeline.manual_recheck('kubernetes-blog'); drain()
    assert not pipeline.review_queue()
    assert len(pipeline.published_items()) == 1
    with isolated_db() as session:
        assert session.execute(text("SELECT action FROM review_audit WHERE actor='routine-policy-v1'")).scalar_one() == 'auto_publish'
    published_id = pipeline.published_items()[0]['id']
    assert pipeline.review_decision(published_id, 'withdraw')['status'] == 'withdrawn'
    assert not pipeline.published_items()


def test_recent_untouched_draft_can_enter_bounded_ai_backfill(isolated_db, monkeypatch):
    when = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
    xml = f'''<rss><channel><item><title>Kubernetes scheduler update</title>
    <link>https://kubernetes.io/blog/scheduler-update/</link>
    <description>Kubernetes adds a scheduler configuration option for dedicated nodes. Operators can review the release documentation before enabling it. Existing clusters keep their previous scheduler configuration until an operator changes it.</description>
    <pubDate>{when}</pubDate></item></channel></rss>'''
    pipeline.seed_rss_sources()
    monkeypatch.setattr(pipeline, 'get_html', lambda source, url, **kw: (xml, 200, None, None))
    monkeypatch.setattr(pipeline, 'intelligence_configured', lambda: False)
    pipeline.manual_recheck('kubernetes-blog'); drain()
    assert pipeline.review_queue()
    monkeypatch.setattr(pipeline, 'intelligence_configured', lambda: True)
    assert pipeline.schedule_ai_backfill(limit=1) == 1
    assert pipeline.schedule_ai_backfill(limit=1) == 0
    with isolated_db() as session:
        assert session.execute(text("SELECT count(*) FROM processing_jobs WHERE kind='analyze-brief'")).scalar_one() == 1


def test_existing_valid_ai_draft_promotes_without_another_model_call(isolated_db, monkeypatch):
    when = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
    source = ('Kubernetes adds a scheduling option for workloads using dedicated nodes. '
              'Operators can enable the option in the scheduler configuration after reviewing the release notes. '
              'The previous scheduling behaviour remains the default for existing clusters.')
    xml = f'''<rss><channel><item><title>Kubernetes scheduling option</title>
    <link>https://kubernetes.io/blog/scheduling-option/</link><description>{source}</description>
    <pubDate>{when}</pubDate></item></channel></rss>'''
    analysis = {'title': 'Kubernetes adds a scheduling option',
                'summary': ('Kubernetes adds a scheduling option for workloads using dedicated nodes. '
                            'Operators can enable it after reviewing the release notes. Existing clusters keep '
                            'the previous scheduling behaviour by default.'),
                'why_it_matters': 'Teams with dedicated nodes can evaluate the new scheduler option.',
                'next_action': 'Review the release notes and scheduler configuration before enabling it.',
                'severity': 'medium', 'confidence': 'high', 'affected_regions': [],
                'unknowns': ['Future rollout timeline is not stated'],
                'evidence_quote': 'Kubernetes adds a scheduling option for workloads using dedicated nodes.',
                'summary_evidence_quote': 'Operators can enable the option in the scheduler configuration after reviewing the release notes.',
                'rule_version': 'ai-evidence-v2', '_usage': {'input_tokens': 700, 'output_tokens': 250}}
    monkeypatch.delenv('AUTO_PUBLISH_ROUTINE', raising=False)
    pipeline.seed_rss_sources()
    monkeypatch.setattr(pipeline, 'get_html', lambda source, url, **kw: (xml, 200, None, None))
    monkeypatch.setattr(pipeline, 'intelligence_configured', lambda: True)
    monkeypatch.setattr(pipeline, 'analyze', lambda *args: dict(analysis))
    pipeline.manual_recheck('kubernetes-blog'); drain()
    assert not pipeline.published_items()
    calls = ai_budget.usage_snapshot()['calls']
    monkeypatch.setenv('AUTO_PUBLISH_ROUTINE', '1')
    assert pipeline.publish_existing_routine_ai() == 1
    assert pipeline.publish_existing_routine_ai() == 0
    assert len(pipeline.published_items()) == 1
    assert ai_budget.usage_snapshot()['calls'] == calls


def test_ai_budget_is_idempotent_and_preserves_urgent_capacity(isolated_db, monkeypatch):
    pipeline.seed_source('python-fixture', 'fixture_python', True)
    pipeline.schedule_due(); drain()
    with isolated_db.begin() as db_session:
        release_id = db_session.execute(text('SELECT id FROM technology_releases LIMIT 1')).scalar_one()
        first = db_session.execute(text('SELECT id FROM release_revisions LIMIT 1')).scalar_one()
        second = uuid.uuid4().hex
        db_session.execute(text('INSERT INTO release_revisions (id,release_id,content_hash,raw_text,created_at) '
                                'VALUES (:id,:release,:hash,:raw,:stamp)'),
                           {'id': second, 'release': release_id, 'hash': 'second-test-hash',
                            'raw': 'Second recorded revision', 'stamp': datetime.now(timezone.utc).isoformat()})
    monkeypatch.setattr(ai_budget, 'monthly_cap', lambda: ai_budget.RESERVATION_MICROUSD - 1)
    assert ai_budget.reserve(first) is None
    with isolated_db.begin() as db_session:
        db_session.execute(text('UPDATE ai_budget_months SET cap_microusd=5000000'))
    monkeypatch.setattr(ai_budget, 'DEFAULT_DAILY_ROUTINE_CAP', 1)
    reservation = ai_budget.reserve(first)
    assert reservation
    assert ai_budget.reserve(first) is None
    assert ai_budget.reserve(second) is None
    assert ai_budget.reserve(second, urgent=True)
    assert ai_budget.settle(reservation, input_tokens=1000, output_tokens=400) == 300
    assert ai_budget.usage_snapshot()['spent_usd'] == 0.0003
    monkeypatch.setenv('ADMIN_TOKEN', 'local-test-token')
    with TestClient(main.app) as client:
        assert client.get('/admin/ai-usage').status_code == 403
        usage = client.get('/admin/ai-usage', headers={'X-Admin-Token': 'local-test-token'}).json()
        assert usage['calls'] == 2 and usage['input_tokens'] == 1000


def test_failed_ai_keeps_source_draft_and_records_token_usage(isolated_db, monkeypatch):
    when = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
    xml = f'''<rss><channel><item><title>GitHub security release</title>
    <link>https://github.blog/changelog/security-release/</link>
    <description>GitHub reports a security release for Actions with documented workflow policy changes and guidance for engineers reviewing their affected repositories.</description>
    <pubDate>{when}</pubDate></item></channel></rss>'''
    pipeline.seed_rss_sources()
    monkeypatch.setattr(pipeline, 'get_html', lambda source, url, **kw: (xml, 200, None, None))
    monkeypatch.setattr(pipeline, 'intelligence_configured', lambda: True)

    def bad_analysis(*args):
        raise AnalysisError('Unsupported scope', {'input_tokens': 700, 'output_tokens': 250})

    monkeypatch.setattr(pipeline, 'analyze', bad_analysis)
    pipeline.manual_recheck('github-changelog'); drain()
    assert pipeline.review_queue()[0]['status'] == 'needs_edit'
    assert len(pipeline.attention_queue()) == 1
    monkeypatch.setenv('ADMIN_TOKEN', 'local-test-token')
    with TestClient(main.app) as client:
        assert client.get('/admin/attention').status_code == 403
        assert len(client.get('/admin/attention', headers={'X-Admin-Token': 'local-test-token'}).json()['items']) == 1
    assert not pipeline.published_items()
    assert ai_budget.usage_snapshot()['failed'] == 1
    assert ai_budget.usage_snapshot()['spent_usd'] == 0.000195


def test_kafka_and_mysql_specialized_discovery():
    listing = '''<div class="td-blog-posts-list__body"><h5><a href="/blog/2026/10/23/apache-kafka-4.3.2-release-announcement/">Apache Kafka 4.3.2 Release Announcement</a></h5></div>'''
    kafka = parse_kafka_blog(listing)
    assert len(kafka) == 1 and kafka[0].published_at == '2026-10-23'
    tags = '''<feed xmlns="http://www.w3.org/2005/Atom">
    <entry><title>mysql-cluster-9.7: change</title><link href="https://github.com/mysql/mysql-server/releases/tag/mysql-cluster-9.7"/><content>Cluster source change</content></entry>
    <entry><title>mysql-9.7.0: change</title><link href="https://github.com/mysql/mysql-server/releases/tag/mysql-9.7.0"/><content>Server source change for maintainers</content></entry>
    </feed>'''
    mysql = parse_mysql_tags(tags)
    assert len(mysql) == 1 and mysql[0].title == 'MySQL 9.7.0 source tag'
    assert mysql[0].kind == 'update'


def test_public_status_page_incident_and_component_fallback():
    base = 'https://www.githubstatus.com'
    status = {'status': {'indicator': 'major', 'description': 'Partial outage'},
              'components': [{'id': 'api', 'name': 'API', 'status': 'partial_outage'}],
              'incidents': [{'id': 'abc', 'name': 'API delays', 'status': 'investigating',
                             'impact': 'major', 'updated_at': '2026-11-05T10:00:00Z',
                             'incident_updates': [{'body': 'Investigating API delays.'}]}]}
    provider, incidents = parse_status_page('github', 'GitHub', base, status)
    assert provider['indicator'] == 'major'
    assert len(incidents) == 1 and incidents[0]['url'] == base + '/incidents/abc'
    assert incidents[0]['summary'] == 'Investigating API delays.'
    status['incidents'] = []
    _, fallback = parse_status_page('github', 'GitHub', base, status)
    assert len(fallback) == 1 and fallback[0]['title'] == 'API'
    status['status'] = {'indicator': 'none', 'description': 'All Systems Operational'}
    _, stale_monitoring = parse_status_page('github', 'GitHub', base, status)
    assert stale_monitoring == []


def test_cloud_status_adapters_only_show_active_public_events():
    aws, aws_incidents = parse_aws_events([
        {'status': '3', 'service_name': 'EC2', 'region_name': 'Mumbai', 'event_log': []},
        {'status': '2', 'service_name': 'S3', 'region_name': 'Mumbai', 'date': '1772369485',
         'event_log': [{'timestamp': 1772369485, 'message': 'Elevated errors'}]},
    ])
    assert aws['indicator'] == 'major' and len(aws_incidents) == 1
    assert 'S3' in aws_incidents[0]['title']
    gcp, gcp_incidents = parse_google_events([
        {'id': 'resolved', 'end': '2026-11-05T10:00:00Z'},
        {'id': 'active', 'end': None, 'external_desc': 'Cloud SQL degraded',
         'updates': [{'text': 'Investigating Cloud SQL'}]},
    ])
    assert gcp['indicator'] == 'major' and len(gcp_incidents) == 1
    assert gcp_incidents[0]['url'].endswith('/active')
    feed = '<rss version="2.0"><channel><title>Azure Status</title></channel></rss>'
    azure, azure_incidents = parse_azure_feed(feed)
    assert azure['indicator'] == 'none' and azure_incidents == []
    assert {'aws', 'google-cloud', 'azure', 'akamai'}.issubset({p[0] for p in PROVIDERS})


def test_source_health_tracks_success_failure_and_recovery(isolated_db, monkeypatch):
    pipeline.seed_rss_sources()
    with isolated_db.begin() as session:
        pipeline.record_fetch(session, 'go-blog', 'https://go.dev/blog/feed.atom', 200, 'first-hash')
    health = {item['id']: item for item in pipeline.source_health()}
    assert health['go-blog']['status'] == 'healthy'
    assert health['azure-blog']['status'] == 'pending'
    assert health['docker-blog']['status'] == 'disabled'
    old = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(timespec='seconds')
    with isolated_db.begin() as session:
        session.execute(text('INSERT INTO source_fetches (id,source_id,url,status_code,fetched_at) '
                             'VALUES (:id,:source,:url,200,:stamp)'),
                        {'id': uuid.uuid4().hex, 'source': 'azure-blog',
                         'url': 'https://azure.microsoft.com/en-us/blog/feed/', 'stamp': old})
    assert next(x for x in pipeline.source_health() if x['id'] == 'azure-blog')['status'] == 'stale'
    pipeline.fail_job({'id': 'nonexistent', 'kind': 'fetch-index', 'attempts': 1, 'max_attempts': 3,
                       'payload': {'source_id': 'go-blog'}}, ValueError('feed format changed'))
    assert next(x for x in pipeline.source_health() if x['id'] == 'go-blog')['status'] == 'error'
    monkeypatch.setattr(pipeline, 'get_html', lambda source, url, **kw: (None, 304, None, None))
    pipeline.process_rss_index({'id': 'recheck', 'payload': {'source_id': 'go-blog'}}, pipeline.source_record('go-blog'))
    assert next(x for x in pipeline.source_health() if x['id'] == 'go-blog')['status'] == 'healthy'
    with TestClient(main.app) as client:
        response = client.get('/v1/source-health')
        assert response.status_code == 200
        data = response.json()
        assert data['counts']['disabled'] >= 1
        assert all(item['adapter'] != 'fixture_python' for item in data['items'])
