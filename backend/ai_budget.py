"""Conservative, idempotent AI budget reservations for the single worker."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import text

from backend.db import Session, engine

MODEL = 'gpt-6-luna'
PROMPT_VERSION = 'techwatch-source-v5'
VERIFY_VERSION = 'techwatch-verify-v2'
# OpenAI Standard USD per million tokens, reviewed 2026-11-12.
INPUT_MICROUSD_PER_TOKEN = 0.10
OUTPUT_MICROUSD_PER_TOKEN = 0.50
MAX_SOURCE_CHARS = 4000
MAX_OUTPUT_TOKENS = 1000
# The input reservation covers the bounded excerpt, prompt, and schema overhead.
RESERVED_INPUT_TOKENS = 7000
RESERVATION_MICROUSD = int(RESERVED_INPUT_TOKENS * INPUT_MICROUSD_PER_TOKEN
                           + MAX_OUTPUT_TOKENS * OUTPUT_MICROUSD_PER_TOKEN)
DEFAULT_MONTHLY_CAP_MICROUSD = 5_000_000
DEFAULT_DAILY_CALL_CAP = 50
DEFAULT_DAILY_ROUTINE_CAP = 30


class BudgetUnavailable(Exception):
    def __init__(self, retry_at: str, reason: str):
        super().__init__(reason)
        self.retry_at = retry_at


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def monthly_cap() -> int:
    # Deliberately fixed in the first pilot. A larger limit needs a reviewed code change.
    return DEFAULT_MONTHLY_CAP_MICROUSD


def reserve(revision_id: str, *, urgent: bool = False,
            prompt_version: str = PROMPT_VERSION) -> str | None:
    """Return a reservation id, None for a duplicate, or raise for exhausted budget."""
    stamp = utc_now()
    month = stamp.strftime('%Y-%m')
    day = stamp.strftime('%Y-%m-%d')
    ident = uuid4().hex
    with Session.begin() as db:
        db.execute(text('INSERT INTO ai_budget_months (month,cap_microusd) VALUES (:month,:cap) ON CONFLICT(month) DO NOTHING'),
                   {'month': month, 'cap': monthly_cap()})
        sql = 'SELECT cap_microusd,reserved_microusd,spent_microusd FROM ai_budget_months WHERE month=:month'
        if engine.dialect.name == 'postgresql':
            sql += ' FOR UPDATE'
        budget = db.execute(text(sql), {'month': month}).mappings().one()
        if db.execute(text('SELECT 1 FROM ai_requests WHERE revision_id=:revision AND prompt_version=:version'),
                      {'revision': revision_id, 'version': prompt_version}).first():
            return None
        tomorrow = (stamp + timedelta(days=1)).strftime('%Y-%m-%d')
        used_today = db.execute(text('SELECT count(*) FROM ai_requests WHERE created_at>=:day AND created_at<:tomorrow'),
                                {'day': day, 'tomorrow': tomorrow}).scalar_one()
        routine_today = db.execute(text("SELECT count(*) FROM ai_requests WHERE created_at>=:day AND created_at<:tomorrow AND priority='routine'"),
                                   {'day': day, 'tomorrow': tomorrow}).scalar_one()
        if budget['spent_microusd'] + budget['reserved_microusd'] + RESERVATION_MICROUSD > budget['cap_microusd']:
            next_month = datetime(stamp.year + (stamp.month == 12), stamp.month % 12 + 1,
                                  1, 0, 5, tzinfo=timezone.utc)
            raise BudgetUnavailable(next_month.isoformat(timespec='seconds'), 'monthly AI budget reached')
        if used_today >= DEFAULT_DAILY_CALL_CAP or (not urgent and routine_today >= DEFAULT_DAILY_ROUTINE_CAP):
            next_day = datetime(stamp.year, stamp.month, stamp.day, tzinfo=timezone.utc) + timedelta(days=1, minutes=5)
            raise BudgetUnavailable(next_day.isoformat(timespec='seconds'), 'daily AI call limit reached')
        result = db.execute(text('INSERT INTO ai_requests (id,revision_id,prompt_version,model,status,priority,month,reserved_microusd,created_at,updated_at) '
                                 'VALUES (:id,:revision,:version,:model,:status,:priority,:month,:reserve,:stamp,:stamp) '
                                 'ON CONFLICT(revision_id,prompt_version) DO NOTHING'),
                            {'id': ident, 'revision': revision_id, 'version': prompt_version,
                             'model': MODEL, 'status': 'reserved', 'priority': 'urgent' if urgent else 'routine', 'month': month,
                             'reserve': RESERVATION_MICROUSD, 'stamp': stamp.isoformat(timespec='seconds')})
        if not result.rowcount:
            return None
        db.execute(text('UPDATE ai_budget_months SET reserved_microusd=reserved_microusd+:reserve WHERE month=:month'),
                   {'reserve': RESERVATION_MICROUSD, 'month': month})
    return ident


def settle(request_id: str, *, input_tokens: int | None, output_tokens: int | None,
           error: str | None = None, db=None) -> int:
    """Unknown token usage is charged at the reservation ceiling to avoid overspending."""
    known = isinstance(input_tokens, int) and isinstance(output_tokens, int) and input_tokens >= 0 and output_tokens >= 0
    spent = int(input_tokens * INPUT_MICROUSD_PER_TOKEN + output_tokens * OUTPUT_MICROUSD_PER_TOKEN) if known else RESERVATION_MICROUSD
    if db is None:
        with Session.begin() as own_db:
            return settle(request_id, input_tokens=input_tokens, output_tokens=output_tokens,
                          error=error, db=own_db)
    row = db.execute(text('SELECT month,reserved_microusd,status FROM ai_requests WHERE id=:id'),
                     {'id': request_id}).mappings().one()
    if row['status'] != 'reserved':
        return 0
    db.execute(text('UPDATE ai_requests SET status=:status,spent_microusd=:spent,input_tokens=:input,output_tokens=:output,error=:error,updated_at=:stamp WHERE id=:id'),
               {'status': 'failed' if error else 'succeeded', 'spent': spent, 'input': input_tokens,
                'output': output_tokens, 'error': error[:180] if error else None,
                'stamp': utc_now().isoformat(timespec='seconds'), 'id': request_id})
    db.execute(text('UPDATE ai_budget_months SET reserved_microusd=reserved_microusd-:reserve,spent_microusd=spent_microusd+:spent WHERE month=:month'),
               {'reserve': row['reserved_microusd'], 'spent': spent, 'month': row['month']})
    return spent


def usage_snapshot() -> dict:
    month = utc_now().strftime('%Y-%m')
    with Session() as db:
        row = db.execute(text('SELECT cap_microusd,reserved_microusd,spent_microusd FROM ai_budget_months WHERE month=:month'),
                         {'month': month}).mappings().first()
        totals = db.execute(text("SELECT count(*) calls,"
                                 "sum(CASE WHEN status='succeeded' THEN 1 ELSE 0 END) succeeded,"
                                 "sum(CASE WHEN status='failed' THEN 1 ELSE 0 END) failed,"
                                 "coalesce(sum(input_tokens),0) input_tokens,"
                                 "coalesce(sum(output_tokens),0) output_tokens "
                                 "FROM ai_requests WHERE month=:month"), {'month': month}).mappings().one()
    return {'month': month, 'cap_usd': monthly_cap() / 1_000_000,
            'reserved_usd': (row['reserved_microusd'] if row else 0) / 1_000_000,
            'spent_usd': (row['spent_microusd'] if row else 0) / 1_000_000,
            'calls': totals['calls'], 'succeeded': totals['succeeded'] or 0,
            'failed': totals['failed'] or 0, 'input_tokens': totals['input_tokens'],
            'output_tokens': totals['output_tokens']}
