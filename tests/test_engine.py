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
from backend.fetcher import check_url
from backend.python_source import discover_releases, parse_release
from backend.rss_source import parse_feed, score, canonical_url, SOURCES, DISABLED_BY_DEFAULT


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    database = create_engine(f"sqlite:///{tmp_path / 'engine.db'}", connect_args={'check_same_thread': False})
    sessions = sessionmaker(bind=database)
    for module in (db, pipeline):
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
