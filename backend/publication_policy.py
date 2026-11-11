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


def routine_auto_publishable(analysis: dict, *, source_title: str, source_text: str,
                             release_type: str, published_at: str | None,
                             today: date | None = None) -> bool:
    """Fail closed unless a fresh, low-risk AI draft has exact source support."""
    if release_type not in ('update', 'release') or RISK_WORDS.search(source_title + ' ' + source_text[:500]):
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
