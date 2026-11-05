"""Small, bounded public incident snapshot, separate from feed-source health."""
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from html import unescape

import feedparser

from backend.fetcher import fetch_html

PROVIDERS = (
    ('aws', 'AWS', 'https://health.aws.amazon.com/health/status', 'aws'),
    ('google-cloud', 'Google Cloud', 'https://status.cloud.google.com/', 'gcp'),
    ('azure', 'Azure', 'https://azure.status.microsoft/en-us/status', 'azure'),
    ('cloudflare', 'Cloudflare', 'https://www.cloudflarestatus.com', 'statuspage'),
    ('akamai', 'Akamai', 'https://www.akamaistatus.com', 'statuspage'),
    ('github', 'GitHub', 'https://www.githubstatus.com', 'statuspage'),
    ('npm', 'npm', 'https://status.npmjs.org', 'statuspage'),
    ('vercel', 'Vercel', 'https://www.vercel-status.com', 'statuspage'),
    ('mongodb', 'MongoDB Cloud', 'https://status.mongodb.com', 'statuspage'),
    ('hashicorp', 'HashiCorp', 'https://status.hashicorp.com', 'statuspage'),
    ('grafana', 'Grafana Cloud', 'https://status.grafana.com', 'statuspage'),
    ('digitalocean', 'DigitalOcean', 'https://status.digitalocean.com', 'statuspage'),
    ('openai', 'OpenAI', 'https://status.openai.com', 'statuspage'),
    ('anthropic', 'Claude / Anthropic', 'https://status.claude.com', 'statuspage'),
)
CACHE_SECONDS = 180
_lock = threading.Lock()
_cached = None
_cached_until = 0.0


def parse_status_page(provider_id: str, name: str, homepage: str, payload: dict) -> tuple[dict, list[dict]]:
    if not isinstance(payload.get('status'), dict) or not isinstance(payload.get('components'), list):
        raise ValueError('status page response is incomplete')
    indicator = payload['status'].get('indicator', 'unknown')
    incidents = []
    for item in payload.get('incidents', []):
        if item.get('status') in ('resolved', 'postmortem'):
            continue
        incident_id = str(item.get('id', ''))
        if not incident_id:
            continue
        updates = item.get('incident_updates') or []
        incidents.append({
            'id': f'{provider_id}:{incident_id}', 'provider': name,
            'title': str(item.get('name') or 'Service incident')[:250],
            'status': str(item.get('status') or 'investigating'),
            'impact': str(item.get('impact') or 'unknown'),
            'summary': str(updates[0].get('body') or '')[:600] if updates else '',
            'updated_at': item.get('updated_at'),
            'started_at': item.get('created_at'),
            'url': f'{homepage}/incidents/{incident_id}',
        })
    # Some public status APIs expose component state but omit incident records.
    if not incidents:
        for component in payload['components']:
            status = component.get('status')
            if status not in ('degraded_performance', 'partial_outage', 'major_outage') or component.get('group'):
                continue
            incidents.append({
                'id': f"{provider_id}:component:{component.get('id', component.get('name', 'unknown'))}",
                'provider': name, 'title': str(component.get('name') or 'Affected service')[:250],
                'status': status.replace('_', ' '), 'impact': 'unknown',
                'summary': 'Provider reports this component as affected. Open the official status page for details.',
                'updated_at': component.get('updated_at'), 'started_at': None,
                'url': homepage,
            })
    # Some providers retain old monitoring posts and security advisories while
    # their overall service indicator is operational. They are not live outages.
    if indicator == 'none':
        incidents = []
    return ({'id': provider_id, 'name': name, 'url': homepage,
             'indicator': indicator, 'description': str(payload['status'].get('description') or ''),
             'available': True}, incidents)


def parse_aws_events(payload: list) -> tuple[dict, list[dict]]:
    if not isinstance(payload, list):
        raise ValueError('AWS public events response is incomplete')
    incidents = []
    for item in payload:
        status = str(item.get('status', ''))
        if status not in ('1', '2', '3'):
            raise ValueError('unrecognized AWS public event status')
        if status == '3':
            continue
        updates = item.get('event_log') or []
        latest = updates[-1] if updates else {}
        stamp = latest.get('timestamp') or item.get('date')
        updated = datetime.fromtimestamp(int(stamp), timezone.utc).isoformat() if stamp else None
        incidents.append({
            'id': f"aws:{item.get('arn', item.get('date', 'event'))}", 'provider': 'AWS',
            'title': f"{item.get('service_name') or 'AWS service'} · {item.get('region_name') or 'Global'}"[:250],
            'status': 'investigating' if status == '1' else 'updating', 'impact': 'unknown',
            'summary': str(latest.get('message') or item.get('summary') or '')[:600],
            'updated_at': updated, 'started_at': None,
            'url': 'https://health.aws.amazon.com/health/status',
        })
    return ({'id': 'aws', 'name': 'AWS', 'url': 'https://health.aws.amazon.com/health/status',
             'indicator': 'major' if incidents else 'none',
             'description': 'Public AWS Health events; account impact may differ', 'available': True}, incidents)


def parse_google_events(payload: list) -> tuple[dict, list[dict]]:
    if not isinstance(payload, list):
        raise ValueError('Google Cloud incidents response is incomplete')
    incidents = []
    for item in payload:
        if item.get('end') or not item.get('id'):
            continue
        updates = item.get('updates') or []
        latest = updates[0] if updates else {}
        incidents.append({
            'id': f"google-cloud:{item['id']}", 'provider': 'Google Cloud',
            'title': str(item.get('external_desc') or 'Google Cloud incident')[:250],
            'status': 'active', 'impact': 'unknown',
            'summary': str(latest.get('text') or '')[:600],
            'updated_at': item.get('modified') or item.get('created'),
            'started_at': item.get('begin'),
            'url': f"https://status.cloud.google.com/incidents/{item['id']}",
        })
    return ({'id': 'google-cloud', 'name': 'Google Cloud', 'url': 'https://status.cloud.google.com/',
             'indicator': 'major' if incidents else 'none',
             'description': 'Public Google Cloud Service Health incidents', 'available': True}, incidents)


def parse_azure_feed(xml: str, now: datetime | None = None) -> tuple[dict, list[dict]]:
    feed = feedparser.parse(xml)
    if feed.bozo or not feed.feed.get('title'):
        raise ValueError('Azure public status feed is invalid')
    now = now or datetime.now(timezone.utc)
    incidents = []
    for item in feed.entries:
        published = item.get('published_parsed') or item.get('updated_parsed')
        if not published:
            continue
        stamp = datetime(*published[:6], tzinfo=timezone.utc)
        if stamp < now - timedelta(days=2):
            continue
        title = str(item.get('title') or 'Azure status update')
        summary = unescape(str(item.get('summary') or ''))
        if any(word in (title + ' ' + summary).casefold() for word in ('resolved', 'mitigated', 'restored')):
            continue
        incidents.append({
            'id': f"azure:{item.get('id') or item.get('link') or title}", 'provider': 'Azure',
            'title': title[:250], 'status': 'public update', 'impact': 'unknown',
            'summary': summary[:600], 'updated_at': stamp.isoformat(),
            'started_at': None, 'url': 'https://azure.status.microsoft/en-us/status',
        })
    return ({'id': 'azure', 'name': 'Azure', 'url': 'https://azure.status.microsoft/en-us/status',
             'indicator': 'major' if incidents else 'none',
             'description': 'Public Azure status feed; broad events only', 'available': True}, incidents)


def _fetch_provider(config):
    provider_id, name, homepage, adapter = config
    try:
        if adapter == 'aws':
            return parse_aws_events(json.loads(fetch_html('https://health.aws.amazon.com/public/currentevents').body or 'null'))
        if adapter == 'gcp':
            return parse_google_events(json.loads(fetch_html('https://status.cloud.google.com/incidents.json').body or 'null'))
        if adapter == 'azure':
            return parse_azure_feed(fetch_html('https://azure.status.microsoft/en-us/status/feed/').body or '')
        result = fetch_html(f'{homepage}/api/v2/summary.json')
        return parse_status_page(provider_id, name, homepage, json.loads(result.body or '{}'))
    except Exception:
        return ({'id': provider_id, 'name': name, 'url': homepage,
                 'indicator': 'unknown', 'description': 'Status temporarily unavailable',
                 'available': False}, [])


def service_snapshot(force: bool = False):
    global _cached, _cached_until
    if os.getenv('OFFLINE_MODE') == '1':
        return {'checked_at': None, 'offline': True, 'active_count': 0, 'complete': False,
                'providers': [], 'incidents': []}
    with _lock:
        if not force and _cached is not None and time.monotonic() < _cached_until:
            return _cached
        with ThreadPoolExecutor(max_workers=len(PROVIDERS)) as pool:
            results = list(pool.map(_fetch_provider, PROVIDERS))
        providers = [provider for provider, _ in results]
        incidents = [incident for _, found in results for incident in found]
        incidents.sort(key=lambda i: i.get('updated_at') or '', reverse=True)
        _cached = {'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                   'offline': False, 'active_count': len(incidents),
                   'complete': all(provider['available'] for provider in providers),
                   'providers': providers, 'incidents': incidents}
        _cached_until = time.monotonic() + CACHE_SECONDS
        return _cached
