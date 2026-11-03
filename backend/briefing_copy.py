"""Editorial length budget for a complete, one-screen briefing card.

Copy is reviewed or rewritten before publication; never truncate factual text.
"""

FIELD_LIMITS = {
    'title': 55,
    'summary': 145,
    'why_it_matters': 70,
    'next_action': 65,
}
TOTAL_LIMIT = 280


def validate_briefing_copy(item: dict) -> list[str]:
    errors = []
    for field, limit in FIELD_LIMITS.items():
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f'{field} required')
            continue
        if len(value) > limit:
            errors.append(f'{field} exceeds {limit} characters')
        if value != value.strip() or '\n' in value:
            errors.append(f'{field} must be a single trimmed line')

    if all(isinstance(item.get(field), str) for field in FIELD_LIMITS):
        total = sum(len(item[field]) for field in FIELD_LIMITS)
        if total > TOTAL_LIMIT:
            errors.append(f'briefing copy exceeds {TOTAL_LIMIT} characters total')
    return errors
