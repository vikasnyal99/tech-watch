"""Recorded-source pipeline and durable PostgreSQL job processing for the first Python slice."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import json
import os
import re

from sqlalchemy import text
from backend.db import Session, engine
from backend.briefing_copy import validate_briefing_copy
from backend.intelligence import analyze, verify, configured as intelligence_configured, eligible as intelligence_eligible, AnalysisError
from backend.ai_budget import PROMPT_VERSION, VERIFY_VERSION, reserve as reserve_ai, settle as settle_ai
from backend.publication_policy import routine_auto_publishable, needs_second_check, verified_auto_publishable
from backend.fetcher import fetch_html
from backend.python_source import discover_releases, parse_release
from backend.rss_source import (SOURCES, ENTRY_HOSTS, DISABLED_BY_DEFAULT, SOURCE_ADAPTERS,
                                ARTICLE_FEEDS, RELEASE_FEEDS, Entry, parse_feed)
from backend.special_sources import (parse_anthropic_news, article_excerpt,
                                     parse_github_advisories, parse_kernel_releases,
                                     parse_kafka_blog, parse_mysql_tags)
from backend.service_health import service_snapshot

FIXTURE_DIR = Path(__file__).parents[1] / 'fixtures' / 'python_source'


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def later(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat(timespec='seconds')


def uid() -> str:
    return uuid4().hex


def rows(result):
    return [dict(row) for row in result.mappings()]


def seed_source(source_id='python-downloads', adapter='python_downloads', enabled=False):
    stamp = now()
    with Session.begin() as db:
        db.execute(text('INSERT INTO technology_sources (id,technology,url,adapter,enabled,interval_seconds,next_due_at,created_at,updated_at) '
                        'VALUES (:id,:technology,:url,:adapter,:enabled,:interval,:due,:stamp,:stamp) ON CONFLICT(id) DO NOTHING'),
                   {'id': source_id, 'technology': 'Python', 'url': 'https://www.python.org/downloads/',
                    'adapter': adapter, 'enabled': int(enabled), 'interval': 3600, 'due': stamp,
                    'stamp': stamp})


def seed_rss_sources():
    stamp = now()
    with Session.begin() as db:
        for source_id, technology, url, _topic in SOURCES:
            interval = 600 if source_id in {'aws-security', 'node-security', 'github-advisories'} else 1800
            db.execute(text('INSERT INTO technology_sources (id,technology,url,adapter,enabled,interval_seconds,next_due_at,created_at,updated_at) '
                            'VALUES (:id,:technology,:url,:adapter,:enabled,:interval,:due,:stamp,:stamp) ON CONFLICT(id) DO NOTHING'),
                       {'id': source_id, 'technology': technology, 'url': url,
                        'adapter': SOURCE_ADAPTERS.get(source_id, 'rss'),
                        'enabled': int(source_id not in DISABLED_BY_DEFAULT), 'interval': interval,
                        'due': stamp, 'stamp': stamp})


def sync_service_incidents(snapshot: dict | None = None) -> int:
    """Create reviewable revisions from official active incidents; never auto-publish."""
    snapshot = snapshot if snapshot is not None else service_snapshot()
    if snapshot.get('offline'):
        return 0
    available = {provider['name'] for provider in snapshot.get('providers', []) if provider.get('available')}
    active_keys = set()
    created = 0
    stamp = now()
    with Session.begin() as db:
        for incident in snapshot.get('incidents', []):
            if incident['provider'] not in available:
                continue
            provider = incident['provider']
            source_id = 'status:' + re.sub(r'[^a-z0-9]+', '-', provider.casefold()).strip('-')
            db.execute(text('INSERT INTO technology_sources (id,technology,url,adapter,enabled,interval_seconds,next_due_at,created_at,updated_at) '
                            'VALUES (:id,:tech,:url,:adapter,0,300,NULL,:stamp,:stamp) ON CONFLICT(id) DO NOTHING'),
                       {'id': source_id, 'tech': provider, 'url': incident['url'], 'adapter': 'status', 'stamp': stamp})
            version = 'incident-' + sha256(incident['id'].encode()).hexdigest()[:24]
            active_keys.add((source_id, version))
            body = f"{incident['title']}\n{incident.get('summary') or ''}\n{incident.get('status') or ''}\n{incident.get('impact') or ''}"
            digest = sha256(body.encode()).hexdigest()
            release = db.execute(text('SELECT * FROM technology_releases WHERE technology=:tech AND version=:version'),
                                 {'tech': provider, 'version': version}).mappings().first()
            if release and release['latest_hash'] == digest:
                continue
            if release:
                release_id = release['id']
                db.execute(text('UPDATE technology_releases SET latest_hash=:digest,updated_at=:stamp,published_at=:published WHERE id=:id'),
                           {'digest': digest, 'stamp': stamp, 'published': incident.get('updated_at') or stamp, 'id': release_id})
            else:
                release_id = uid()
                db.execute(text('INSERT INTO technology_releases (id,technology,version,source_id,canonical_url,release_type,published_at,latest_hash,created_at,updated_at) '
                                'VALUES (:id,:tech,:version,:source,:url,:type,:published,:digest,:stamp,:stamp)'),
                           {'id': release_id, 'tech': provider, 'version': version, 'source': source_id,
                            'url': incident['url'], 'type': 'incident',
                            'published': incident.get('updated_at') or stamp, 'digest': digest, 'stamp': stamp})
            revision_id = uid()
            db.execute(text('INSERT INTO release_revisions (id,release_id,content_hash,raw_text,created_at) '
                            'VALUES (:id,:release,:digest,:raw,:stamp)'),
                       {'id': revision_id, 'release': release_id, 'digest': digest, 'raw': body, 'stamp': stamp})
            db.execute(text('INSERT INTO release_facts (id,revision_id,kind,description,evidence_excerpt,evidence_url,confidence) '
                            'VALUES (:id,:revision,:kind,:description,:evidence,:url,:confidence)'),
                       {'id': uid(), 'revision': revision_id, 'kind': 'incident', 'description': body,
                        'evidence': body[:1000], 'url': incident['url'], 'confidence': 'official_status'})
            impact = str(incident.get('impact') or 'unknown').casefold()
            severity = 'critical' if impact == 'critical' else 'high' if impact == 'major' else 'unknown'
            analysis = {'rule_version': 'official-status-v1', 'severity': severity, 'confidence': 'high' if severity != 'unknown' else 'low',
                        'provider_impact': impact, 'affected_regions': [], 'source_url': incident['url']}
            summary = (incident.get('summary') or '').strip()[:510]
            copy = {'title': incident['title'][:55], 'summary': summary,
                    'why_it_matters': f"{provider} reports an active service issue; check its stated scope.",
                    'next_action': 'Check the official status page for affected services and regions.'}
            status = 'needs_edit' if validate_briefing_copy(copy) else 'review_required'
            db.execute(text("UPDATE tech_briefs SET status='superseded',updated_at=:stamp "
                            "WHERE release_id=:release AND status IN ('review_required','needs_edit')"),
                       {'stamp': stamp, 'release': release_id})
            db.execute(text('INSERT INTO tech_briefs (id,release_id,revision_id,title,summary,why_it_matters,next_action,score,status,fictional,source_label,source_url,intelligence_json,created_at,updated_at) '
                            'VALUES (:id,:release,:revision,:title,:summary,:why,:action,:score,:status,0,:label,:url,:analysis,:stamp,:stamp)'),
                       {'id': uid(), 'release': release_id, 'revision': revision_id, **copy,
                        'why': copy['why_it_matters'], 'action': copy['next_action'],
                        'score': 90 if severity == 'critical' else 80 if severity == 'high' else 50,
                        'status': status, 'label': f'{provider} official status', 'url': incident['url'],
                        'analysis': json.dumps(analysis), 'stamp': stamp})
            created += 1
        # An unavailable provider is never interpreted as recovered.
        if available:
            previous = rows(db.execute(text("SELECT r.id,r.source_id,r.version,s.technology FROM technology_releases r "
                                            "JOIN technology_sources s ON s.id=r.source_id WHERE s.adapter='status'")))
            for release in previous:
                if release['technology'] in available and (release['source_id'], release['version']) not in active_keys:
                    db.execute(text("UPDATE tech_briefs SET status='superseded',updated_at=:stamp "
                                    "WHERE release_id=:release AND status IN ('published','review_required','needs_edit')"),
                               {'stamp': stamp, 'release': release['id']})
    return created


def enqueue(db, kind: str, payload: dict, key: str):
    ident, stamp = uid(), now()
    db.execute(text('INSERT INTO processing_jobs (id,kind,payload,status,attempts,max_attempts,available_at,idempotency_key,created_at,updated_at) '
                    'VALUES (:id,:kind,:payload,:status,0,3,:stamp,:key,:stamp,:stamp) ON CONFLICT(idempotency_key) DO NOTHING'),
               {'id': ident, 'kind': kind, 'payload': json.dumps(payload), 'status': 'pending', 'stamp': stamp, 'key': key})
    return db.execute(text('SELECT id FROM processing_jobs WHERE idempotency_key=:key'), {'key': key}).scalar_one()


def schedule_due():
    stamp = now()
    with Session.begin() as db:
        sql = 'SELECT * FROM technology_sources WHERE enabled=1 AND (next_due_at IS NULL OR next_due_at<=:stamp) ORDER BY id'
        if engine.dialect.name == 'postgresql':
            sql += ' FOR UPDATE SKIP LOCKED'
        due = rows(db.execute(text(sql), {'stamp': stamp}))
        for source in due:
            enqueue(db, 'fetch-index', {'source_id': source['id']}, f"poll:{source['id']}:{source['next_due_at'] or 'initial'}")
            db.execute(text('UPDATE technology_sources SET next_due_at=:due,updated_at=:stamp WHERE id=:id'),
                       {'due': later(source['interval_seconds']), 'stamp': stamp, 'id': source['id']})
    return len(due)


def manual_recheck(source_id: str):
    with Session.begin() as db:
        if not db.execute(text('SELECT id FROM technology_sources WHERE id=:id'), {'id': source_id}).first():
            raise ValueError('unknown source')
        return enqueue(db, 'fetch-index', {'source_id': source_id}, f'manual:{source_id}:{uid()}')


def claim_job():
    stamp = now()
    with Session.begin() as db:
        db.execute(text("UPDATE processing_jobs SET status='failed',last_error='Lease expired after final attempt',updated_at=:stamp "
                        "WHERE status='processing' AND lease_until<=:stamp AND attempts>=max_attempts"), {'stamp': stamp})
        sql = "SELECT * FROM processing_jobs WHERE ((status='pending' AND available_at<=:stamp) OR (status='processing' AND lease_until<=:stamp)) AND attempts<max_attempts ORDER BY available_at,id LIMIT 1"
        if engine.dialect.name == 'postgresql':
            sql += ' FOR UPDATE SKIP LOCKED'
        job = db.execute(text(sql), {'stamp': stamp}).mappings().first()
        if not job:
            return None
        item = dict(job)
        db.execute(text("UPDATE processing_jobs SET status='processing',attempts=attempts+1,lease_until=:lease,updated_at=:stamp WHERE id=:id"),
                   {'lease': later(120), 'stamp': stamp, 'id': item['id']})
        item['attempts'] += 1
        item['payload'] = json.loads(item['payload'])
        return item


def finish_job(job_id: str):
    with Session.begin() as db:
        db.execute(text("UPDATE processing_jobs SET status='succeeded',lease_until=NULL,updated_at=:stamp WHERE id=:id"), {'stamp': now(), 'id': job_id})


def fail_job(job: dict, error: Exception):
    terminal = job['attempts'] >= job['max_attempts']
    with Session.begin() as db:
        db.execute(text('UPDATE processing_jobs SET status=:status,available_at=:due,lease_until=NULL,last_error=:error,updated_at=:stamp WHERE id=:id'),
                   {'status': 'failed' if terminal else 'pending', 'due': later(min(30 * 2 ** job['attempts'], 3600)),
                    'error': f'{type(error).__name__}: {str(error)[:300]}', 'stamp': now(), 'id': job['id']})
        source_id = job['payload'].get('source_id')
        if source_id and job['kind'] in ('fetch-index', 'fetch-release'):
            message = f'{type(error).__name__}: {str(error)[:300]}'
            db.execute(text('UPDATE technology_sources SET last_error=:error,updated_at=:stamp WHERE id=:id'),
                       {'error': message, 'stamp': now(), 'id': source_id})
            url = job['payload'].get('url') or db.execute(text('SELECT url FROM technology_sources WHERE id=:id'),
                                                           {'id': source_id}).scalar_one()
            record_fetch(db, source_id, url, None, None, error=message)


def source_record(source_id: str):
    with Session() as db:
        row = db.execute(text('SELECT * FROM technology_sources WHERE id=:id'), {'id': source_id}).mappings().first()
        if not row:
            raise ValueError('unknown source')
        return dict(row)


def source_health():
    with Session() as db:
        data = rows(db.execute(text('SELECT s.id,s.technology,s.url,s.adapter,s.enabled,s.interval_seconds,s.next_due_at,s.last_error,s.updated_at, '
                                    '(SELECT MAX(f.fetched_at) FROM source_fetches f WHERE f.source_id=s.id AND f.url=s.url) last_attempt_at, '
                                    '(SELECT MAX(f.fetched_at) FROM source_fetches f WHERE f.source_id=s.id AND f.url=s.url AND f.status_code IN (200,304)) last_success_at '
                                    'FROM technology_sources s ORDER BY s.id')))
    stamp = datetime.now(timezone.utc)
    for source in data:
        if not source['enabled']:
            status = 'disabled'
        elif os.getenv('OFFLINE_MODE') == '1':
            status = 'paused'
        elif source['last_error']:
            status = 'error'
        elif not source['last_success_at']:
            status = 'pending'
        elif stamp - datetime.fromisoformat(source['last_success_at']) > timedelta(seconds=source['interval_seconds'] * 2 + 300):
            status = 'stale'
        else:
            status = 'healthy'
        source['status'] = status
    return data


def configure_source(source_id: str, *, enabled: bool | None = None, interval_seconds: int | None = None):
    if interval_seconds is not None and not 300 <= interval_seconds <= 604800:
        raise ValueError('interval must be between 300 and 604800 seconds')
    with Session.begin() as db:
        if not db.execute(text('SELECT id FROM technology_sources WHERE id=:id'), {'id': source_id}).first():
            raise ValueError('unknown source')
        if enabled is not None:
            db.execute(text('UPDATE technology_sources SET enabled=:enabled,next_due_at=:due,updated_at=:stamp WHERE id=:id'),
                       {'enabled': int(enabled), 'due': now(), 'stamp': now(), 'id': source_id})
        if interval_seconds is not None:
            db.execute(text('UPDATE technology_sources SET interval_seconds=:interval,updated_at=:stamp WHERE id=:id'),
                       {'interval': interval_seconds, 'stamp': now(), 'id': source_id})
    return source_record(source_id)


def get_html(source: dict, url: str, *, index=False):
    if source['adapter'] == 'fixture_python':
        path = FIXTURE_DIR / ('downloads.html' if index else 'release.html')
        return path.read_text(), 200, None, None
    if os.getenv('OFFLINE_MODE') == '1':
        raise RuntimeError('live source fetching is disabled in offline mode')
    if source['adapter'] not in ('python_downloads', 'rss', 'news_html', 'ghsa'):
        raise ValueError('unsupported source adapter')
    result = fetch_html(url, etag=source['etag'] if index else None,
                        last_modified=source['last_modified'] if index else None)
    return result.body, result.status_code, result.etag, result.last_modified


def record_fetch(db, source_id: str, url: str, status: int | None, digest: str | None,
                 error: str | None = None, body: str | None = None):
    db.execute(text('INSERT INTO source_fetches (id,source_id,url,status_code,content_hash,fetched_at,error,body_text) '
                    'VALUES (:id,:source,:url,:status,:digest,:stamp,:error,:body)'),
               {'id': uid(), 'source': source_id, 'url': url, 'status': status,
                'digest': digest, 'stamp': now(), 'error': error, 'body': body})


def process_index(job: dict):
    source = source_record(job['payload']['source_id'])
    if source['adapter'] in ('rss', 'news_html', 'ghsa'):
        return process_rss_index(job, source)
    body, status, etag, modified = get_html(source, source['url'], index=True)
    if status == 304:
        with Session.begin() as db:
            record_fetch(db, source['id'], source['url'], 304, source['last_hash'])
            db.execute(text('UPDATE technology_sources SET last_error=NULL,updated_at=:stamp WHERE id=:id'),
                       {'stamp': now(), 'id': source['id']})
            # The index can stay unchanged while existing release notes are revised.
            known = db.execute(text('SELECT version,canonical_url FROM technology_releases '
                                    'WHERE source_id=:source ORDER BY published_at DESC LIMIT 5'),
                               {'source': source['id']}).mappings().all()
            for release in known:
                enqueue(db, 'fetch-release', {'source_id': source['id'], 'version': release['version'],
                                              'url': release['canonical_url']},
                        f"release:{source['id']}:{release['version']}:{job['id']}")
        return
    if not body:
        raise ValueError('empty downloads page')
    digest = sha256(body.encode()).hexdigest()
    links = discover_releases(body, source['url'])
    if not links:
        raise ValueError('no Python release links found; source structure may have changed')
    with Session.begin() as db:
        record_fetch(db, source['id'], source['url'], status, digest, body=body)
        db.execute(text('UPDATE technology_sources SET etag=:etag,last_modified=:modified,last_hash=:digest,last_error=NULL,updated_at=:stamp WHERE id=:id'),
                   {'etag': etag, 'modified': modified, 'digest': digest, 'stamp': now(), 'id': source['id']})
        for link in links:
            enqueue(db, 'fetch-release', {'source_id': source['id'], 'version': link.version, 'url': link.url},
                    f"release:{source['id']}:{link.version}:{job['id']}")


def process_rss_index(job: dict, source: dict):
    body, status, etag, modified = get_html(source, source['url'], index=True)
    if status == 304:
        with Session.begin() as db:
            record_fetch(db, source['id'], source['url'], 304, source['last_hash'])
            db.execute(text('UPDATE technology_sources SET last_error=NULL,updated_at=:stamp WHERE id=:id'),
                       {'stamp': now(), 'id': source['id']})
        return
    if not body or status != 200:
        raise ValueError('RSS source unavailable')
    digest = sha256(body.encode()).hexdigest()
    stamp = now()
    if digest == source['last_hash']:
        with Session.begin() as db:
            record_fetch(db, source['id'], source['url'], status, digest)
            db.execute(text('UPDATE technology_sources SET etag=:etag,last_modified=:modified,last_error=NULL,updated_at=:stamp WHERE id=:id'),
                       {'etag': etag, 'modified': modified, 'stamp': stamp, 'id': source['id']})
        return
    if source['adapter'] == 'ghsa':
        entries = parse_github_advisories(body)
    elif source['adapter'] == 'news_html':
        entries = parse_kafka_blog(body) if source['id'] == 'kafka-blog' else parse_anthropic_news(body)
    elif source['id'] == 'linux-releases':
        entries = parse_kernel_releases(body)
    elif source['id'] == 'mysql-tags':
        entries = parse_mysql_tags(body)
    else:
        entries = parse_feed(body, source['url'], allowed_hosts=ENTRY_HOSTS.get(source['id']),
                             allow_missing_excerpt=source['id'] in ARTICLE_FEEDS,
                             force_release=source['id'] in RELEASE_FEEDS)
    with Session.begin() as db:
        record_fetch(db, source['id'], source['url'], status, digest, body=body)
        db.execute(text('UPDATE technology_sources SET etag=:etag,last_modified=:modified,last_hash=:digest,last_error=NULL,updated_at=:stamp WHERE id=:id'),
                   {'etag': etag, 'modified': modified, 'digest': digest, 'stamp': stamp, 'id': source['id']})
        if source['id'] in ARTICLE_FEEDS:
            for entry in entries:
                enqueue(db, 'fetch-article', {'source_id': source['id'], 'title': entry.title,
                                               'url': entry.url, 'published_at': entry.published_at,
                                               'kind': entry.kind, 'score': entry.score},
                        f"article:{source['id']}:{entry.key}:{digest}")
        else:
            store_entries(db, source, entries, stamp)


def process_article(job: dict):
    payload = job['payload']
    source = source_record(payload['source_id'])
    body, status, _, _ = get_html(source, payload['url'])
    if not body or status != 200:
        raise ValueError('article unavailable')
    excerpt, article_date = article_excerpt(body, source['id'])
    entry = Entry(sha256(payload['url'].encode()).hexdigest()[:24], payload['title'], payload['url'],
                  excerpt, payload['published_at'] or article_date, payload['kind'], payload['score'])
    with Session.begin() as db:
        record_fetch(db, source['id'], payload['url'], status, sha256(body.encode()).hexdigest(), body=body)
        store_entries(db, source, [entry], now())


def store_entries(db, source: dict, entries: list[Entry], stamp: str):
    for entry in entries:
        existing = db.execute(text('SELECT * FROM technology_releases WHERE canonical_url=:url'),
                              {'url': entry.url}).mappings().first()
        entry_hash = sha256((entry.title + '\n' + entry.excerpt).encode()).hexdigest()
        if existing and existing['latest_hash'] == entry_hash:
            continue
        if not existing:
            # A second official feed can syndicate the same story under a different URL.
            normalized = re.sub(r'[^a-z0-9]+', ' ', entry.title.casefold()).strip()
            candidate = db.execute(text("SELECT r.id,v.raw_text FROM technology_releases r JOIN release_revisions v ON v.release_id=r.id "
                                        "WHERE r.published_at=:published AND r.version LIKE 'rss-%'"),
                                   {'published': entry.published_at}).mappings().all()
            if any(re.sub(r'[^a-z0-9]+', ' ', x['raw_text'].split('\n', 1)[0].casefold()).strip() == normalized for x in candidate):
                continue
            release_id = uid()
            db.execute(text('INSERT INTO technology_releases (id,technology,version,source_id,canonical_url,release_type,published_at,latest_hash,created_at,updated_at) '
                            'VALUES (:id,:technology,:version,:source,:url,:kind,:published,:digest,:stamp,:stamp)'),
                       {'id': release_id, 'technology': entry.technology or source['technology'], 'version': f'rss-{entry.key}',
                        'source': source['id'], 'url': entry.url, 'kind': entry.kind,
                        'published': entry.published_at, 'digest': entry_hash, 'stamp': stamp})
        else:
            release_id = existing['id']
            db.execute(text('UPDATE technology_releases SET latest_hash=:digest,release_type=:kind,published_at=:published,technology=:technology,updated_at=:stamp WHERE id=:id'),
                       {'digest': entry_hash, 'kind': entry.kind, 'published': entry.published_at,
                        'technology': entry.technology or source['technology'],
                        'stamp': stamp, 'id': release_id})
        revision_id = uid()
        db.execute(text('INSERT INTO release_revisions (id,release_id,content_hash,raw_text,created_at) '
                        'VALUES (:id,:release,:digest,:raw,:stamp)'),
                   {'id': revision_id, 'release': release_id, 'digest': entry_hash,
                    'raw': entry.title + '\n' + entry.excerpt, 'stamp': stamp})
        db.execute(text('INSERT INTO release_facts (id,revision_id,kind,description,evidence_excerpt,evidence_url,confidence) '
                        'VALUES (:id,:revision,:kind,:description,:excerpt,:url,:confidence)'),
                   {'id': uid(), 'revision': revision_id, 'kind': entry.kind, 'description': entry.excerpt,
                    'excerpt': entry.excerpt, 'url': entry.url,
                    'confidence': 'official_advisory' if source['adapter'] == 'ghsa' else 'official_source_excerpt'})
        enqueue(db, 'generate-rss-brief', {'revision_id': revision_id, 'source_id': source['id'],
                                            'title': entry.title, 'score': entry.score}, f'rss-brief:{revision_id}')


def process_rss_brief(job: dict):
    payload = job['payload']
    with Session.begin() as db:
        row = db.execute(text('SELECT r.release_id,v.technology,v.canonical_url,v.release_type,v.published_at,f.description FROM release_revisions r '
                              'JOIN technology_releases v ON v.id=r.release_id JOIN release_facts f ON f.revision_id=r.id '
                              'WHERE r.id=:id LIMIT 1'), {'id': payload['revision_id']}).mappings().one()
        if db.execute(text('SELECT id FROM tech_briefs WHERE revision_id=:id'), {'id': payload['revision_id']}).first():
            return
        copy = {'title': payload['title'], 'summary': source_summary(row['description']),
                'why_it_matters': f"Official {row['technology']} update; review its relevance to your work.",
                'next_action': 'Read the official source for details.'}
        status = 'needs_edit' if validate_briefing_copy(copy) else 'review_required'
        db.execute(text('INSERT INTO tech_briefs (id,release_id,revision_id,title,summary,why_it_matters,next_action,score,status,fictional,source_label,source_url,intelligence_json,created_at,updated_at) '
                        'VALUES (:id,:release,:revision,:title,:summary,:why,:action,:score,:status,0,:label,:url,:analysis,:stamp,:stamp)'),
                   {'id': uid(), 'release': row['release_id'], 'revision': payload['revision_id'],
                    'title': copy['title'], 'summary': copy['summary'], 'why': copy['why_it_matters'],
                    'action': copy['next_action'], 'score': payload['score'], 'status': status,
                    'analysis': None,
                    'label': ('GitHub reviewed advisory' if payload['source_id'] == 'github-advisories'
                              else f"{row['technology']} official source"),
                    'url': row['canonical_url'], 'stamp': now()})
        if intelligence_configured() and intelligence_eligible(row['release_type'], payload['title'],
                                                                payload['source_id'], row['description'], row['published_at']):
            enqueue(db, 'analyze-brief', {'revision_id': payload['revision_id']},
                    f"ai:{payload['revision_id']}:{PROMPT_VERSION}")


def schedule_ai_backfill(limit: int = 6) -> int:
    """Select a few recent, untouched official RSS drafts for the existing review backlog."""
    if not intelligence_configured():
        return 0
    with Session.begin() as db:
        candidates = db.execute(text("SELECT b.revision_id,b.title,r.release_type,r.source_id,r.published_at,f.description "
                                     "FROM tech_briefs b JOIN technology_releases r ON r.id=b.release_id "
                                     "JOIN release_revisions v ON v.id=b.revision_id "
                                     "JOIN release_facts f ON f.revision_id=b.revision_id "
                                     "WHERE b.status IN ('needs_edit','review_required') AND b.intelligence_json IS NULL "
                                     "AND v.content_hash=r.latest_hash AND r.version LIKE 'rss-%' "
                                     "AND NOT EXISTS (SELECT 1 FROM review_audit a WHERE a.brief_id=b.id) "
                                     "AND NOT EXISTS (SELECT 1 FROM ai_requests a WHERE a.revision_id=b.revision_id "
                                     "AND a.prompt_version=:version) "
                                     "ORDER BY r.published_at DESC,b.score DESC LIMIT 100"),
                                {'version': PROMPT_VERSION}).mappings().all()
        created = 0
        for row in candidates:
            if not intelligence_eligible(row['release_type'], row['title'], row['source_id'],
                                         row['description'], row['published_at']):
                continue
            key = f"ai:{row['revision_id']}:{PROMPT_VERSION}"
            before = db.execute(text('SELECT 1 FROM processing_jobs WHERE idempotency_key=:key'),
                                {'key': key}).first()
            if before:
                continue
            enqueue(db, 'analyze-brief', {'revision_id': row['revision_id']}, key)
            created += 1
            if created >= limit:
                break
    return created


def publish_existing_routine_ai(limit: int = 20) -> int:
    """Recheck valid, unedited AI drafts against the current narrow publication policy."""
    if os.getenv('AUTO_PUBLISH_ROUTINE') != '1':
        return 0
    published = 0
    with Session.begin() as db:
        candidates = db.execute(text("SELECT b.id,b.intelligence_json,r.release_type,r.published_at,"
                                     "v.raw_text,f.description FROM tech_briefs b "
                                     "JOIN technology_releases r ON r.id=b.release_id "
                                     "JOIN release_revisions v ON v.id=b.revision_id "
                                     "JOIN release_facts f ON f.revision_id=b.revision_id "
                                     "WHERE b.status='review_required' AND b.intelligence_json IS NOT NULL "
                                     "AND v.content_hash=r.latest_hash "
                                     "AND NOT EXISTS (SELECT 1 FROM review_audit a WHERE a.brief_id=b.id) "
                                     "ORDER BY b.updated_at DESC LIMIT 100")).mappings().all()
        for row in candidates:
            analysis = json.loads(row['intelligence_json'])
            if not routine_auto_publishable(analysis, source_title=row['raw_text'].split('\n', 1)[0],
                                            source_text=row['description'],
                                            release_type=row['release_type'],
                                            published_at=row['published_at']):
                continue
            result = db.execute(text("UPDATE tech_briefs SET status='published',updated_at=:stamp "
                                     "WHERE id=:id AND status='review_required' "
                                     "AND NOT EXISTS (SELECT 1 FROM review_audit WHERE brief_id=:id)"),
                                {'stamp': now(), 'id': row['id']})
            if result.rowcount:
                db.execute(text("UPDATE tech_briefs SET status='superseded',updated_at=:stamp "
                                "WHERE release_id=(SELECT release_id FROM tech_briefs WHERE id=:id) "
                                "AND id<>:id AND status='published'"),
                           {'stamp': now(), 'id': row['id']})
                db.execute(text('INSERT INTO review_audit (id,brief_id,action,actor,created_at) '
                                'VALUES (:id,:brief,:action,:actor,:stamp)'),
                           {'id': uid(), 'brief': row['id'], 'action': 'auto_publish',
                            'actor': 'routine-policy-v2', 'stamp': now()})
                published += 1
                if published >= limit:
                    break
    return published


def schedule_verify_existing(limit: int = 6) -> int:
    """Queue a second check for recent consequential AI drafts already held."""
    if not intelligence_configured() or os.getenv('AUTO_PUBLISH_ROUTINE') != '1':
        return 0
    with Session.begin() as db:
        candidates = db.execute(text("SELECT b.id,b.revision_id,b.intelligence_json,v.raw_text,"
                                     "r.release_type,r.published_at,f.description "
                                     "FROM tech_briefs b JOIN technology_releases r ON r.id=b.release_id "
                                     "JOIN release_revisions v ON v.id=b.revision_id "
                                     "JOIN release_facts f ON f.revision_id=b.revision_id "
                                     "WHERE b.status='review_required' AND b.intelligence_json IS NOT NULL "
                                     "AND v.content_hash=r.latest_hash "
                                     "AND NOT EXISTS (SELECT 1 FROM review_audit a WHERE a.brief_id=b.id) "
                                     "AND NOT EXISTS (SELECT 1 FROM ai_requests a WHERE a.revision_id=b.revision_id "
                                     "AND a.prompt_version=:version) "
                                     "ORDER BY b.score DESC,r.published_at DESC LIMIT 100"),
                                {'version': VERIFY_VERSION}).mappings().all()
        created = 0
        for row in candidates:
            analysis = json.loads(row['intelligence_json'])
            if not needs_second_check(analysis, source_title=row['raw_text'].split('\n', 1)[0],
                                      source_text=row['description'], release_type=row['release_type'],
                                      published_at=row['published_at']):
                continue
            key = f"verify:{row['revision_id']}:{VERIFY_VERSION}"
            if db.execute(text('SELECT 1 FROM processing_jobs WHERE idempotency_key=:key'),
                          {'key': key}).first():
                continue
            enqueue(db, 'verify-brief', {'revision_id': row['revision_id']}, key)
            created += 1
            if created >= limit:
                break
    return created


def process_ai_brief(job: dict):
    revision_id = job['payload']['revision_id']
    with Session() as db:
        row = db.execute(text("SELECT b.id,b.status,b.intelligence_json,b.title,b.summary,b.why_it_matters,b.next_action,"
                              "r.canonical_url,r.release_type,r.source_id,r.published_at,r.latest_hash,v.content_hash,f.description "
                              "FROM tech_briefs b JOIN technology_releases r ON r.id=b.release_id "
                              "JOIN release_revisions v ON v.id=b.revision_id "
                              "JOIN release_facts f ON f.revision_id=b.revision_id "
                              "WHERE b.revision_id=:id LIMIT 1"), {'id': revision_id}).mappings().first()
        was_edited = bool(row and db.execute(text('SELECT 1 FROM review_audit WHERE brief_id=:id LIMIT 1'),
                                             {'id': row['id']}).first())
    if (not row or row['status'] not in ('needs_edit', 'review_required') or row['intelligence_json']
            or row['content_hash'] != row['latest_hash'] or was_edited or not intelligence_configured()):
        return
    reservation = reserve_ai(revision_id, urgent=row['release_type'] in ('security', 'deprecation')
                             or row['source_id'] == 'github-advisories')
    if reservation is None:
        return
    try:
        analysis = analyze(row['title'], row['description'], row['canonical_url'])
        if not analysis:
            raise AnalysisError('AI is not configured')
        usage = analysis.pop('_usage', {})
        copy = {field: analysis[field] for field in ('title', 'summary', 'why_it_matters', 'next_action')}
        automatic = os.getenv('AUTO_PUBLISH_ROUTINE') == '1' and routine_auto_publishable(
            analysis, source_title=row['title'], source_text=row['description'],
            release_type=row['release_type'], published_at=row['published_at'])
        second_check = os.getenv('AUTO_PUBLISH_ROUTINE') == '1' and not automatic and needs_second_check(
            analysis, source_title=row['title'], source_text=row['description'],
            release_type=row['release_type'], published_at=row['published_at'])
        with Session.begin() as db:
            result = db.execute(text("UPDATE tech_briefs SET title=:title,summary=:summary,why_it_matters=:why,"
                            "next_action=:action,intelligence_json=:analysis,status=:status,updated_at=:stamp "
                            "WHERE id=:id AND status IN ('needs_edit','review_required') AND intelligence_json IS NULL "
                            "AND NOT EXISTS (SELECT 1 FROM review_audit WHERE brief_id=:id) "
                            "AND EXISTS (SELECT 1 FROM technology_releases r JOIN release_revisions v "
                            "ON v.release_id=r.id WHERE v.id=:revision AND r.latest_hash=v.content_hash)"),
                       {'title': copy['title'], 'summary': copy['summary'], 'why': copy['why_it_matters'],
                        'action': copy['next_action'], 'analysis': json.dumps(analysis),
                        'status': 'published' if automatic else 'review_required', 'stamp': now(),
                        'id': row['id'], 'revision': revision_id})
            if result.rowcount and automatic:
                db.execute(text("UPDATE tech_briefs SET status='superseded',updated_at=:stamp "
                                "WHERE release_id=(SELECT release_id FROM tech_briefs WHERE id=:id) "
                                "AND id<>:id AND status='published'"),
                           {'stamp': now(), 'id': row['id']})
                db.execute(text('INSERT INTO review_audit (id,brief_id,action,actor,created_at) '
                                'VALUES (:id,:brief,:action,:actor,:stamp)'),
                           {'id': uid(), 'brief': row['id'], 'action': 'auto_publish',
                            'actor': 'routine-policy-v1', 'stamp': now()})
            if result.rowcount and second_check:
                enqueue(db, 'verify-brief', {'revision_id': revision_id},
                        f'verify:{revision_id}:{VERIFY_VERSION}')
            settle_ai(reservation, input_tokens=usage.get('input_tokens'), output_tokens=usage.get('output_tokens'),
                      error=None if result.rowcount else 'draft_changed_during_analysis', db=db)
    except Exception as error:
        usage = error.usage if isinstance(error, AnalysisError) else {}
        settle_ai(reservation, input_tokens=usage.get('input_tokens'),
                  output_tokens=usage.get('output_tokens'),
                  error=(str(error) if isinstance(error, AnalysisError) else type(error).__name__))


def process_verify_brief(job: dict):
    revision_id = job['payload']['revision_id']
    with Session() as db:
        row = db.execute(text("SELECT b.id,b.status,b.intelligence_json,b.title,b.summary,b.why_it_matters,"
                              "b.next_action,r.canonical_url,r.release_type,r.published_at,r.latest_hash,"
                              "v.content_hash,v.raw_text,f.description FROM tech_briefs b "
                              "JOIN technology_releases r ON r.id=b.release_id "
                              "JOIN release_revisions v ON v.id=b.revision_id "
                              "JOIN release_facts f ON f.revision_id=b.revision_id "
                              "WHERE b.revision_id=:id LIMIT 1"), {'id': revision_id}).mappings().first()
        was_edited = bool(row and db.execute(text('SELECT 1 FROM review_audit WHERE brief_id=:id LIMIT 1'),
                                             {'id': row['id']}).first())
    if (not row or row['status'] != 'review_required' or not row['intelligence_json']
            or row['content_hash'] != row['latest_hash'] or was_edited
            or not intelligence_configured() or os.getenv('AUTO_PUBLISH_ROUTINE') != '1'):
        return
    analysis = json.loads(row['intelligence_json'])
    source_title = row['raw_text'].split('\n', 1)[0]
    if not needs_second_check(analysis, source_title=source_title, source_text=row['description'],
                              release_type=row['release_type'], published_at=row['published_at']):
        return
    reservation = reserve_ai(revision_id, urgent=True, prompt_version=VERIFY_VERSION)
    if reservation is None:
        return
    try:
        verdict = verify(source_title, row['description'], row['canonical_url'], analysis)
        if not verdict:
            raise AnalysisError('AI verification is not configured')
        usage = verdict.pop('_usage', {})
        publish = verified_auto_publishable(analysis, verdict, source_text=row['description'])
        analysis['verification'] = verdict
        with Session.begin() as db:
            result = db.execute(text("UPDATE tech_briefs SET intelligence_json=:analysis,status=:status,"
                                     "updated_at=:stamp WHERE id=:id AND status='review_required' "
                                     "AND NOT EXISTS (SELECT 1 FROM review_audit WHERE brief_id=:id) "
                                     "AND EXISTS (SELECT 1 FROM technology_releases r JOIN release_revisions v "
                                     "ON v.release_id=r.id WHERE v.id=:revision AND r.latest_hash=v.content_hash)"),
                                {'analysis': json.dumps(analysis),
                                 'status': 'published' if publish else 'review_required',
                                 'stamp': now(), 'id': row['id'], 'revision': revision_id})
            if result.rowcount and publish:
                db.execute(text("UPDATE tech_briefs SET status='superseded',updated_at=:stamp "
                                "WHERE release_id=(SELECT release_id FROM tech_briefs WHERE id=:id) "
                                "AND id<>:id AND status='published'"),
                           {'stamp': now(), 'id': row['id']})
                db.execute(text('INSERT INTO review_audit (id,brief_id,action,actor,created_at) '
                                'VALUES (:id,:brief,:action,:actor,:stamp)'),
                           {'id': uid(), 'brief': row['id'], 'action': 'auto_publish_verified',
                            'actor': 'two-pass-policy-v1', 'stamp': now()})
            settle_ai(reservation, input_tokens=usage.get('input_tokens'), output_tokens=usage.get('output_tokens'),
                      error=None if result.rowcount else 'draft_changed_during_verification', db=db)
    except Exception as error:
        usage = error.usage if isinstance(error, AnalysisError) else {}
        settle_ai(reservation, input_tokens=usage.get('input_tokens'),
                  output_tokens=usage.get('output_tokens'),
                  error=(str(error) if isinstance(error, AnalysisError) else type(error).__name__))


def process_release(job: dict):
    source = source_record(job['payload']['source_id'])
    url = job['payload']['url']
    body, status, _, _ = get_html(source, url)
    if not body or status != 200:
        raise ValueError('release page unavailable')
    parsed = parse_release(body, url, job['payload']['version'])
    digest = sha256(body.encode()).hexdigest()
    with Session.begin() as db:
        record_fetch(db, source['id'], url, status, digest, body=body)
        release = db.execute(text('SELECT * FROM technology_releases WHERE technology=:tech AND version=:version'),
                             {'tech': 'Python', 'version': parsed.version}).mappings().first()
        stamp = now()
        if release and release['latest_hash'] == digest:
            return
        if release:
            release_id = release['id']
            db.execute(text('UPDATE technology_releases SET latest_hash=:digest,updated_at=:stamp,release_type=:type,published_at=:published WHERE id=:id'),
                       {'digest': digest, 'stamp': stamp, 'type': parsed.release_type,
                        'published': parsed.published_at, 'id': release_id})
        else:
            release_id = uid()
            db.execute(text('INSERT INTO technology_releases (id,technology,version,source_id,canonical_url,release_type,published_at,latest_hash,created_at,updated_at) '
                            'VALUES (:id,:tech,:version,:source,:url,:type,:published,:digest,:stamp,:stamp)'),
                       {'id': release_id, 'tech': 'Python', 'version': parsed.version, 'source': source['id'],
                        'url': parsed.url, 'type': parsed.release_type, 'published': parsed.published_at,
                        'digest': digest, 'stamp': stamp})
        revision_id = uid()
        db.execute(text('INSERT INTO release_revisions (id,release_id,content_hash,raw_text,created_at) VALUES (:id,:release,:digest,:raw,:stamp)'),
                   {'id': revision_id, 'release': release_id, 'digest': digest, 'raw': parsed.raw_text, 'stamp': stamp})
        db.execute(text('INSERT INTO release_facts (id,revision_id,kind,description,evidence_excerpt,evidence_url,confidence) '
                        'VALUES (:id,:revision,:kind,:description,:evidence,:url,:confidence)'),
                   {'id': uid(), 'revision': revision_id, 'kind': parsed.release_type, 'description': parsed.evidence,
                    'evidence': parsed.evidence, 'url': parsed.url, 'confidence': 'source_text'})
        enqueue(db, 'generate-brief', {'revision_id': revision_id, 'fictional': source['adapter'] == 'fixture_python'},
                f'brief:{revision_id}')


def first_sentence(value: str) -> str:
    return re.split(r'(?<=[.!?])\s+', value.strip(), maxsplit=1)[0]


def source_summary(value: str) -> str:
    """Keep complete source sentences when they fit; never cut a factual clause."""
    sentences = re.split(r'(?<=[.!?])\s+', value.strip())
    chosen = []
    for sentence in sentences:
        candidate = ' '.join([*chosen, sentence])
        if len(candidate) > 250:
            break
        chosen.append(sentence)
        if len(candidate) >= 150:
            break
    return ' '.join(chosen) if chosen else first_sentence(value)


def process_brief(job: dict):
    revision_id = job['payload']['revision_id']
    with Session.begin() as db:
        row = db.execute(text('SELECT r.id revision_id,r.release_id,v.version,v.release_type,v.canonical_url,v.published_at,v.source_id,f.description '
                              'FROM release_revisions r JOIN technology_releases v ON v.id=r.release_id '
                              'JOIN release_facts f ON f.revision_id=r.id WHERE r.id=:id LIMIT 1'),
                         {'id': revision_id}).mappings().first()
        if not row:
            raise ValueError('revision has no verified source fact')
        row = dict(row)
        fictional = bool(job['payload']['fictional'])
        copy = {
            'title': f"Python {row['version']} {'security release' if row['release_type']=='security' else 'release'}",
            'summary': source_summary(row['description']),
            'why_it_matters': f"Teams following Python {row['version'].rsplit('.', 1)[0]} may need to review this release.",
            'next_action': 'Review the release notes before upgrading.' if not fictional else 'Review the recorded sample evidence.',
        }
        errors = validate_briefing_copy(copy, allow_short_sample=fictional)
        status = 'needs_edit' if errors else ('published' if fictional else 'review_required')
        if db.execute(text('SELECT id FROM tech_briefs WHERE revision_id=:id'), {'id': revision_id}).first():
            return
        stamp = now()
        if status == 'published':
            db.execute(text("UPDATE tech_briefs SET status='superseded',updated_at=:stamp WHERE release_id=:release AND status='published'"),
                       {'stamp': stamp, 'release': row['release_id']})
        db.execute(text('INSERT INTO tech_briefs (id,release_id,revision_id,title,summary,why_it_matters,next_action,score,status,fictional,source_label,source_url,created_at,updated_at) '
                        'VALUES (:id,:release,:revision,:title,:summary,:why,:action,:score,:status,:fictional,:label,:url,:stamp,:stamp)'),
                   {'id': uid(), 'release': row['release_id'], 'revision': revision_id, **{'title': copy['title'], 'summary': copy['summary']},
                    'why': copy['why_it_matters'], 'action': copy['next_action'],
                    'score': 75 if row['release_type']=='security' else 50, 'status': status,
                    'fictional': int(fictional), 'label': 'Fictional recorded sample' if fictional else 'Python.org official release',
                    'url': None if fictional else row['canonical_url'], 'stamp': stamp})
        if not fictional and intelligence_configured() and intelligence_eligible(
                row['release_type'], copy['title'], row['source_id'], row['description'], row['published_at']):
            enqueue(db, 'analyze-brief', {'revision_id': revision_id},
                    f'ai:{revision_id}:{PROMPT_VERSION}')


def run_once():
    job = claim_job()
    if not job:
        return False
    try:
        {'fetch-index': process_index, 'fetch-release': process_release, 'fetch-article': process_article,
         'generate-brief': process_brief,
         'generate-rss-brief': process_rss_brief,
         'analyze-brief': process_ai_brief, 'verify-brief': process_verify_brief}[job['kind']](job)
        finish_job(job['id'])
    except Exception as error:
        fail_job(job, error)
    return True


def published_items():
    with Session() as db:
        data = rows(db.execute(text("SELECT b.*,r.technology,r.version,r.release_type,r.published_at,r.source_id FROM tech_briefs b "
                                    "JOIN technology_releases r ON r.id=b.release_id WHERE b.status='published' "
                                    'ORDER BY COALESCE(r.published_at,b.created_at) DESC,b.score DESC LIMIT 150')))
    return [
        {'id': x['id'], 'type': x['release_type'], 'technology': x['technology'], 'source_id': x['source_id'], 'title': x['title'],
         'summary': x['summary'], 'why_it_matters': x['why_it_matters'], 'next_action': x['next_action'],
         'source_label': x['source_label'], 'source_url': x['source_url'], 'fictional': bool(x['fictional']),
         'topic': ('Reliability & observability' if x['source_id'].startswith('status:') else
                   next((s[3] for s in SOURCES if s[0] == x['source_id']), 'Backend & APIs')),
         'published_at': x['published_at'], 'updated_at': x['updated_at'],
         'score': x['score'], 'intelligence': json.loads(x['intelligence_json']) if x['intelligence_json'] else None}
        for x in data
    ]


def event_detail(brief_id: str):
    with Session() as db:
        brief = db.execute(text("SELECT b.*,r.technology,r.version,r.release_type,r.published_at FROM tech_briefs b "
                                "JOIN technology_releases r ON r.id=b.release_id WHERE b.id=:id AND b.status='published'"),
                           {'id': brief_id}).mappings().first()
        if not brief:
            return None
        facts = rows(db.execute(text('SELECT kind,description,evidence_excerpt,evidence_url,confidence '
                                     'FROM release_facts WHERE revision_id=:id ORDER BY id'),
                                {'id': brief['revision_id']}))
        return {'id': brief['id'], 'technology': brief['technology'], 'version': None if brief['version'].startswith('rss-') else brief['version'],
                'type': brief['release_type'], 'title': brief['title'], 'summary': brief['summary'],
                'why_it_matters': brief['why_it_matters'], 'next_action': brief['next_action'],
                'source_label': brief['source_label'], 'source_url': brief['source_url'],
                'fictional': bool(brief['fictional']), 'published_at': brief['published_at'],
                'status': brief['status'], 'facts': facts}


def review_queue():
    with Session() as db:
        result = rows(db.execute(text("SELECT b.id,b.title,b.summary,b.status,b.source_url,b.source_label,b.score,b.created_at,b.intelligence_json,"
                                    "r.technology,r.release_type,r.published_at,substr(f.evidence_excerpt,1,320) evidence_preview "
                                    'FROM tech_briefs b JOIN technology_releases r ON r.id=b.release_id '
                                    'JOIN release_facts f ON f.revision_id=b.revision_id '
                                    "WHERE b.status IN ('review_required','needs_edit') ORDER BY b.score DESC,b.created_at DESC LIMIT 200")))
        for item in result:
            item['intelligence'] = json.loads(item.pop('intelligence_json')) if item['intelligence_json'] else None
        return result


def attention_queue(limit: int = 10):
    """A short, recent exception queue for the operator's daily review."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).date().isoformat()
    with Session() as db:
        result = rows(db.execute(text("SELECT b.id,b.title,b.summary,b.status,b.source_url,b.source_label,"
                                      "b.score,b.created_at,b.intelligence_json,r.technology,r.release_type,"
                                      "r.published_at,substr(f.evidence_excerpt,1,320) evidence_preview "
                                      "FROM tech_briefs b JOIN technology_releases r ON r.id=b.release_id "
                                      "JOIN release_facts f ON f.revision_id=b.revision_id "
                                      "WHERE b.status IN ('review_required','needs_edit') "
                                      "AND r.published_at>=:cutoff "
                                      "AND (r.release_type IN ('incident','security','deprecation') OR b.score>=70) "
                                      "ORDER BY CASE r.release_type WHEN 'incident' THEN 0 "
                                      "WHEN 'security' THEN 1 WHEN 'deprecation' THEN 2 ELSE 3 END, "
                                      "b.score DESC,r.published_at DESC LIMIT :limit"),
                                 {'cutoff': cutoff, 'limit': limit}))
    for item in result:
        item['intelligence'] = json.loads(item.pop('intelligence_json')) if item['intelligence_json'] else None
    return result


def draft_detail(brief_id: str):
    with Session() as db:
        brief = db.execute(text('SELECT b.*,r.technology,r.version,r.release_type,r.published_at '
                                'FROM tech_briefs b JOIN technology_releases r ON r.id=b.release_id WHERE b.id=:id'),
                           {'id': brief_id}).mappings().first()
        if not brief:
            return None
        facts = rows(db.execute(text('SELECT kind,description,evidence_excerpt,evidence_url,confidence '
                                     'FROM release_facts WHERE revision_id=:id ORDER BY id'),
                                {'id': brief['revision_id']}))
        result = dict(brief)
        result['intelligence'] = json.loads(result.pop('intelligence_json')) if result['intelligence_json'] else None
        return {**result, 'facts': facts}


def review_decision(brief_id: str, action: str, actor: str = 'local-admin'):
    if action not in ('publish', 'reject', 'withdraw'):
        raise ValueError('invalid review action')
    with Session.begin() as db:
        row = db.execute(text('SELECT * FROM tech_briefs WHERE id=:id'), {'id': brief_id}).mappings().first()
        if not row:
            raise ValueError('brief not found')
        row = dict(row)
        allowed = ('published',) if action == 'withdraw' else ('review_required', 'needs_edit')
        if row['status'] not in allowed:
            raise ValueError('brief is not awaiting review')
        if action == 'publish':
            errors = validate_briefing_copy(row)
            if errors:
                raise ValueError('brief copy needs editing: ' + ', '.join(errors))
            if not db.execute(text('SELECT id FROM release_facts WHERE revision_id=:id'), {'id': row['revision_id']}).first():
                raise ValueError('brief has no source evidence')
        status = {'publish': 'published', 'reject': 'rejected', 'withdraw': 'withdrawn'}[action]
        if status == 'published':
            db.execute(text("UPDATE tech_briefs SET status='superseded',updated_at=:stamp WHERE release_id=:release AND status='published'"),
                       {'stamp': now(), 'release': row['release_id']})
        db.execute(text('UPDATE tech_briefs SET status=:status,updated_at=:stamp WHERE id=:id'),
                   {'status': status, 'stamp': now(), 'id': brief_id})
        db.execute(text('INSERT INTO review_audit (id,brief_id,action,actor,created_at) VALUES (:id,:brief,:action,:actor,:stamp)'),
                   {'id': uid(), 'brief': brief_id, 'action': action, 'actor': actor, 'stamp': now()})
    return {'id': brief_id, 'status': status}


def edit_brief(brief_id: str, changes: dict, actor: str = 'local-admin'):
    copy_fields = {'title', 'summary', 'why_it_matters', 'next_action'}
    allowed = copy_fields | {'severity', 'evidence_quote'}
    if not changes or set(changes) - allowed:
        raise ValueError('unsupported briefing edit field')
    if ('severity' in changes) != ('evidence_quote' in changes):
        raise ValueError('severity and exact evidence quote must be provided together')
    with Session.begin() as db:
        row = db.execute(text('SELECT * FROM tech_briefs WHERE id=:id'), {'id': brief_id}).mappings().first()
        if not row or row['status'] not in ('review_required', 'needs_edit', 'published'):
            raise ValueError('brief is not awaiting review')
        copy = {key: changes.get(key, row[key]) for key in copy_fields}
        errors = validate_briefing_copy(copy)
        if errors:
            raise ValueError(', '.join(errors))
        analysis = json.loads(row['intelligence_json']) if row['intelligence_json'] else None
        retained_analysis = row['intelligence_json'] if analysis and analysis.get('rule_version') in ('official-status-v1', 'editorial-evidence-v1') else None
        if 'severity' in changes:
            if changes['severity'] not in ('critical', 'high', 'medium', 'low', 'unknown'):
                raise ValueError('invalid severity')
            quote = changes['evidence_quote'].strip()
            raw = db.execute(text('SELECT raw_text FROM release_revisions WHERE id=:id'),
                             {'id': row['revision_id']}).scalar_one()
            if len(quote) < 20 or len(quote) > 500 or quote not in raw:
                raise ValueError('severity evidence must be an exact 20–500 character source quote')
            retained_analysis = json.dumps({'rule_version': 'editorial-evidence-v1',
                                            'severity': changes['severity'], 'confidence': 'reviewed',
                                            'evidence_quote': quote, 'actor': actor})
        db.execute(text('UPDATE tech_briefs SET title=:title,summary=:summary,why_it_matters=:why,next_action=:action,status=:status,intelligence_json=:analysis,updated_at=:stamp WHERE id=:id'),
                   {'title': copy['title'], 'summary': copy['summary'], 'why': copy['why_it_matters'],
                    'action': copy['next_action'], 'status': 'review_required', 'analysis': retained_analysis,
                    'stamp': now(), 'id': brief_id})
        db.execute(text('INSERT INTO review_audit (id,brief_id,action,actor,created_at) VALUES (:id,:brief,:action,:actor,:stamp)'),
                   {'id': uid(), 'brief': brief_id, 'action': 'edit', 'actor': actor, 'stamp': now()})
    return {'id': brief_id, 'status': 'review_required'}
