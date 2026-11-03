import json
import os
import re
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import text
from backend.db import Session, migrate
from backend.data import fixture_items, TECHNOLOGIES, TOPICS, ROLES
from backend.pipeline import ingest
from backend.engine import (seed_source, seed_rss_sources, published_items, review_queue, review_decision,
                            manual_recheck, edit_brief, source_health, configure_source, event_detail, draft_detail)

@asynccontextmanager
async def lifespan(app):
    migrate()
    seed_source()
    seed_rss_sources()
    yield

app = FastAPI(title='TechWatch', lifespan=lifespan)
app.mount('/assets', StaticFiles(directory='web'), name='assets')

class Preferences(BaseModel):
    roles: list[str] = []
    topics: list[str] = []
    follows: list[str] = []
    signals: list[str] = []
    alert_delivery: str = 'in_app'
    text_size: str = 'regular'
    reduced_motion: bool = False
    onboarded: bool = False

class CandidateBatch(BaseModel):
    candidates: list[dict] = Field(default_factory=list)

class BriefEdit(BaseModel):
    title: str | None = None
    summary: str | None = None
    why_it_matters: str | None = None
    next_action: str | None = None

class SourceConfig(BaseModel):
    enabled: bool | None = None
    interval_seconds: int | None = None

def installation(value: str | None):
    if not value or len(value) > 100 or not all(c.isalnum() or c in '-_' for c in value):
        raise HTTPException(400, 'Valid X-Installation-ID required')
    return value

def prefs(ident):
    with Session() as db:
        row = db.execute(text('SELECT data FROM preferences WHERE installation_id=:id'), {'id': ident}).first()
    return Preferences.model_validate_json(row[0]) if row else Preferences()

def visible_items(demo: bool = False):
    stored = published_items()
    live = [item for item in stored if not item['fictional']]
    return stored + fixture_items() if demo or not live else live

def ai_relevant(item: dict) -> bool:
    if item['type'] == 'model' or item['topic'] == 'AI models & APIs':
        return True
    return bool(re.search(r'\b(?:AI|LLMs?|models?|agents?|Copilot|GPT|embeddings?|Antigravity)\b',
                          item['title'] + ' ' + item['summary'], re.IGNORECASE))

@app.get('/')
def index():
    return FileResponse('web/index.html')

@app.get('/health')
def health():
    return {'ok': True, 'mode': 'official-feeds-with-review', 'fictional_fallback': True}

@app.get('/v1/catalog')
def catalog():
    return {'technologies': TECHNOLOGIES, 'topics': TOPICS, 'roles': ROLES}

@app.get('/v1/preferences')
def get_preferences(x_installation_id: str | None = Header(None)):
    return prefs(installation(x_installation_id))

@app.put('/v1/preferences')
def put_preferences(body: Preferences, x_installation_id: str | None = Header(None)):
    ident = installation(x_installation_id)
    with Session.begin() as db:
        db.execute(text('DELETE FROM preferences WHERE installation_id=:id'), {'id': ident})
        db.execute(text('INSERT INTO preferences (installation_id,data) VALUES (:id,:data)'), {'id': ident, 'data': body.model_dump_json()})
    return body

@app.get('/v1/feed')
def feed(section: str = Query('feed', pattern='^(feed|stack|trending|ai)$'), topic: str = '', cursor: int = 0, limit: int = Query(100, ge=1, le=100), demo: bool = False, x_installation_id: str | None = Header(None)):
    ident = installation(x_installation_id)
    items = visible_items(demo)
    if section == 'stack':
        follows = set(prefs(ident).follows)
        items = [i for i in items if i['technology'] in follows]
    elif section == 'ai':
        items = [i for i in items if ai_relevant(i)]
    elif section == 'trending':
        items = sorted(items, key=lambda item: (item.get('score') or 0, item.get('published_at') or ''), reverse=True)
    if topic:
        items = [i for i in items if i['topic'] == topic]
    start = max(cursor, 0)
    end = start + limit
    return {'items': items[start:end], 'next_cursor': end if end < len(items) else None,
            'snapshot': 'reviewed-v1', 'fictional': all(i['fictional'] for i in items)}

@app.get('/v1/search')
def search(q: str = ''):
    q = q.casefold().strip()
    items = visible_items()
    return {'stories': [i for i in items if q and q in (' '.join([i['title'], i['summary'], i['technology']])).casefold()],
            'technologies': [t for t in TECHNOLOGIES if q and q in t.casefold()], 'fictional': all(i['fictional'] for i in items)}

@app.get('/v1/events/{event_id}')
def get_event(event_id: str):
    detail = event_detail(event_id)
    if detail:
        return detail
    raise HTTPException(404, 'Published event not found')

@app.get('/v1/bookmarks')
def bookmarks(x_installation_id: str | None = Header(None)):
    ident = installation(x_installation_id)
    with Session() as db:
        ids = {r[0] for r in db.execute(text('SELECT event_id FROM bookmarks WHERE installation_id=:id'), {'id': ident})}
    return {'items': [i for i in published_items() + fixture_items() if i['id'] in ids]}

@app.put('/v1/bookmarks/{event_id}')
def save(event_id: str, x_installation_id: str | None = Header(None)):
    ident = installation(x_installation_id)
    if event_id not in {i['id'] for i in published_items() + fixture_items()}:
        raise HTTPException(404)
    with Session.begin() as db:
        db.execute(text('DELETE FROM bookmarks WHERE installation_id=:id AND event_id=:event'), {'id': ident, 'event': event_id})
        db.execute(text('INSERT INTO bookmarks (installation_id,event_id) VALUES (:id,:event)'), {'id': ident, 'event': event_id})
    return {'saved': True}

@app.delete('/v1/bookmarks/{event_id}')
def unsave(event_id: str, x_installation_id: str | None = Header(None)):
    ident = installation(x_installation_id)
    with Session.begin() as db:
        db.execute(text('DELETE FROM bookmarks WHERE installation_id=:id AND event_id=:event'), {'id': ident, 'event': event_id})
    return {'saved': False}

@app.get('/v1/sources')
def sources():
    return [{key: source[key] for key in ('id', 'technology', 'url', 'adapter', 'enabled')}
            for source in source_health()]

@app.get('/v1/source-health')
def public_source_health():
    items = [{key: source[key] for key in ('id', 'technology', 'url', 'adapter', 'status',
                                           'last_attempt_at', 'last_success_at', 'next_due_at')}
             | {'error': (source['last_error'] or '')[:180] or None}
             for source in source_health() if source['adapter'] != 'fixture_python']
    counts = {status: sum(item['status'] == status for item in items)
              for status in ('healthy', 'stale', 'error', 'pending', 'disabled', 'paused')}
    return {'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'counts': counts, 'items': items}

def admin_guard(token: str | None):
    configured = os.getenv('ADMIN_TOKEN')
    if not configured or token != configured:
        raise HTTPException(403)

@app.get('/admin/review-queue')
def admin_review_queue(x_admin_token: str | None = Header(None)):
    admin_guard(x_admin_token)
    return {'items': review_queue()}

@app.get('/admin/review/{brief_id}')
def admin_review_detail(brief_id: str, x_admin_token: str | None = Header(None)):
    admin_guard(x_admin_token)
    result = draft_detail(brief_id)
    if not result:
        raise HTTPException(404, 'Brief not found')
    return result

@app.post('/admin/review/{brief_id}/{action}')
def admin_review(brief_id: str, action: str, x_admin_token: str | None = Header(None)):
    admin_guard(x_admin_token)
    try:
        return review_decision(brief_id, action)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error

@app.post('/admin/sources/{source_id}/recheck')
def admin_recheck(source_id: str, x_admin_token: str | None = Header(None)):
    admin_guard(x_admin_token)
    try:
        return {'job_id': manual_recheck(source_id)}
    except ValueError as error:
        raise HTTPException(404, str(error)) from error

@app.get('/admin/sources')
def admin_sources(x_admin_token: str | None = Header(None)):
    admin_guard(x_admin_token)
    return {'items': source_health()}

@app.patch('/admin/sources/{source_id}')
def admin_configure_source(source_id: str, body: SourceConfig, x_admin_token: str | None = Header(None)):
    admin_guard(x_admin_token)
    try:
        return configure_source(source_id, enabled=body.enabled, interval_seconds=body.interval_seconds)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error

@app.patch('/admin/review/{brief_id}')
def admin_edit_brief(brief_id: str, body: BriefEdit, x_admin_token: str | None = Header(None)):
    admin_guard(x_admin_token)
    try:
        return edit_brief(brief_id, body.model_dump(exclude_none=True))
    except ValueError as error:
        raise HTTPException(400, str(error)) from error

@app.post('/admin/ingest-preview')
def ingest_preview(body: CandidateBatch, x_admin_token: str | None = Header(None)):
    admin_guard(x_admin_token)
    accepted, held = ingest(body.candidates)
    return {'accepted': accepted, 'held': held, 'published': 0}
