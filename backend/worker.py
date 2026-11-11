"""Run separately from HTTP; PROCESS_ONCE=1 provides a deterministic smoke command."""
import os
import time
from backend.db import migrate
from backend.engine import (run_once, schedule_due, schedule_ai_backfill, schedule_verify_existing,
                            publish_existing_routine_ai,
                            seed_source, seed_rss_sources, sync_service_incidents)


def main():
    migrate()
    seed_source()
    seed_rss_sources()
    once = os.getenv('PROCESS_ONCE') == '1'
    next_incident_check = 0.0
    next_ai_backfill = 0.0
    while True:
        if os.getenv('OFFLINE_MODE') != '1':
            schedule_due()
            if time.monotonic() >= next_incident_check:
                try:
                    sync_service_incidents()
                except Exception as error:
                    print(f'Incident synchronization failed: {type(error).__name__}: {error}', flush=True)
                next_incident_check = time.monotonic() + 300
            if time.monotonic() >= next_ai_backfill:
                publish_existing_routine_ai()
                schedule_verify_existing()
                schedule_ai_backfill()
                next_ai_backfill = time.monotonic() + 21600
        processed = run_once()
        if once:
            return
        if not processed:
            time.sleep(2)


if __name__ == '__main__':
    main()
