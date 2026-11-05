"""Editorial quality and length budget for one complete briefing card.

Short source excerpts remain drafts; editors add facts only after checking the source.
"""

import re

FIELD_LIMITS = {
    'title': 55,
    'summary': 510,
    'why_it_matters': 110,
    'next_action': 95,
}
MIN_SUMMARY = 130
TOTAL_LIMIT = 760


def validate_briefing_copy(item: dict, *, allow_short_sample: bool = False) -> list[str]:
    errors = []
    for field, limit in FIELD_LIMITS.items():
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f'{field} required')
            continue
        if len(value) > limit:
            errors.append(f'{field} exceeds {limit} characters')
        if field == 'summary' and len(value) < MIN_SUMMARY and not allow_short_sample:
            errors.append(f'summary needs at least {MIN_SUMMARY} source-backed characters')
        if value != value.strip() or '\n' in value:
            errors.append(f'{field} must be a single trimmed line')

    if isinstance(item.get('why_it_matters'), str) and re.fullmatch(
            r'Official .+ update; review its relevance to your work\.', item['why_it_matters']):
        errors.append('why_it_matters needs a specific implication')
    if item.get('next_action') == 'Read the official source for details.':
        errors.append('next_action needs a concrete check')

    if all(isinstance(item.get(field), str) for field in FIELD_LIMITS):
        total = sum(len(item[field]) for field in FIELD_LIMITS)
        if total > TOTAL_LIMIT:
            errors.append(f'briefing copy exceeds {TOTAL_LIMIT} characters total')
    return errors
