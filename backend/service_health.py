"""Small, bounded public incident snapshot, separate from feed-source health."""
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from backend.fetcher import fetch_html

PROVIDERS = (
    ('cloudflare', 'Cloudflare', 'https://www.cloudflarestatus.com'),
    ('github', 'GitHub', 'https://www.githubstatus.com'),
    ('openai', 'OpenAI', 'https://status.openai.com'),
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
    return ({'id': provider_id, 'name': name, 'url': homepage,
             'indicator': indicator, 'description': str(payload['status'].get('description') or ''),
             'available': True}, incidents)


def _fetch_provider(config):
    provider_id, name, homepage = config
    try:
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
