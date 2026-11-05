import json
from pathlib import Path

from backend.briefing_copy import validate_briefing_copy


def test_expanded_live_briefings_keep_source_identity_and_fit_card_budget():
    root = Path(__file__).parents[1] / 'backend'
    previous = json.loads((root / 'editorial_updates_20261104.json').read_text())
    expanded = json.loads((root / 'editorial_updates_20261105.json').read_text())
    assert len(previous) == len(expanded) == 31
    before = {item['id']: item for item in previous}
    assert len(before) == len(previous)
    for item in expanded:
        old = before[item['id']]
        assert item['source_url'] == old['source_url']
        assert item['summary'].startswith(old['summary'])
        assert len(item['summary']) >= len(old['summary']) + 100
        assert not validate_briefing_copy(item)
