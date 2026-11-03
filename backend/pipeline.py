"""Offline ingestion contract. Network collectors remain disabled."""
from dataclasses import dataclass
from urllib.parse import urlparse
import ipaddress
import re
from backend.briefing_copy import validate_briefing_copy

@dataclass(frozen=True)
class Source:
    id: str
    name: str
    kind: str
    domain: str | None
    enabled: bool = False

REGISTRY = [Source('fixture', 'Fictional development fixture', 'fixture', None, True),
            Source('official-rss-template', 'Official RSS template (unconfigured)', 'rss', None, False)]

def url_allowed(url: str, domain: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ''
        if parsed.scheme != 'https' or host != domain or parsed.username or parsed.password:
            return False
        try:
            address = ipaddress.ip_address(host)
            return address.is_global
        except ValueError:
            return bool(re.fullmatch(r'[A-Za-z0-9.-]+', host)) and not host.endswith('.local')
    except ValueError:
        return False

def dedupe_key(item: dict) -> tuple:
    # Exact source identity; versions remain distinct when IDs differ.
    return item['source_id'], item['external_id']

def validate_candidate(item: dict) -> list[str]:
    errors = validate_briefing_copy(item)
    for field in ('source_id', 'external_id', 'technology', 'type'):
        if not item.get(field):
            errors.append(f'{field} required')
    if item.get('type') in ('security', 'breaking', 'pricing') and not item.get('reviewed'):
        errors.append('human review required')
    for claim in ('version', 'cve', 'affected_versions', 'fixed_versions', 'price'):
        if item.get(claim) and claim not in item.get('evidence', {}):
            errors.append(f'{claim} lacks evidence')
    if item.get('claims_user_affected') and not item.get('verified_installation'):
        errors.append('user impact unverified')
    return errors

def ingest(candidates: list[dict]) -> tuple[list[dict], list[dict]]:
    seen = set(); accepted = []; held = []
    for item in candidates:
        key = dedupe_key(item)
        if key in seen:
            continue
        seen.add(key)
        errors = validate_candidate(item)
        (held if errors else accepted).append({'candidate': item, 'errors': errors})
    return accepted, held
