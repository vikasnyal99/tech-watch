"""Apply a reviewed, source-linked copy set to existing published briefings.

Usage: python -m backend.apply_editorial_updates backend/editorial_updates_20261104.json
The existing review audit records each edit and publish decision. Re-running is safe.
"""

import json
import sys
from pathlib import Path

from sqlalchemy import text

from backend.briefing_copy import validate_briefing_copy
from backend.db import Session
from backend.engine import edit_brief, review_decision


def apply(path: Path) -> tuple[int, int]:
    entries = json.loads(path.read_text())
    if not isinstance(entries, list) or not entries:
        raise ValueError('expected a non-empty editorial update list')
    if len({item['id'] for item in entries}) != len(entries):
        raise ValueError('duplicate briefing ID')
    fields = ('title', 'summary', 'why_it_matters', 'next_action')
    with Session() as db:
        for item in entries:
            errors = validate_briefing_copy(item)
            if errors:
                raise ValueError(f"{item['id']}: {', '.join(errors)}")
            row = db.execute(text('SELECT source_url,fictional,status FROM tech_briefs WHERE id=:id'),
                             {'id': item['id']}).mappings().first()
            if not row or row['fictional'] or row['source_url'] != item['source_url']:
                raise ValueError(f"{item['id']}: source or briefing mismatch")
            if row['status'] not in ('published', 'review_required', 'needs_edit'):
                raise ValueError(f"{item['id']}: unexpected status {row['status']}")
    edited = skipped = 0
    actor = f'editorial-{path.stem}'
    for item in entries:
        copy = {key: item[key] for key in fields}
        with Session() as db:
            row = db.execute(text('SELECT title,summary,why_it_matters,next_action,status FROM tech_briefs WHERE id=:id'),
                             {'id': item['id']}).mappings().one()
        if all(row[key] == value for key, value in copy.items()) and row['status'] == 'published':
            skipped += 1
            continue
        edit_brief(item['id'], copy, actor=actor)
        review_decision(item['id'], 'publish', actor=actor)
        edited += 1
    return edited, skipped


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python -m backend.apply_editorial_updates <updates.json>')
    count, skipped = apply(Path(sys.argv[1]))
    print(f'Published {count} editorial updates; {skipped} already current.')
