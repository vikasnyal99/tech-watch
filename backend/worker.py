"""Run separately from HTTP; PROCESS_ONCE=1 provides a deterministic smoke command."""
import os
import time
from backend.db import migrate
from backend.engine import run_once, schedule_due, seed_source, seed_rss_sources


def main():
    migrate()
    seed_source()
    seed_rss_sources()
    once = os.getenv('PROCESS_ONCE') == '1'
    while True:
        if os.getenv('OFFLINE_MODE') != '1':
            schedule_due()
        processed = run_once()
        if once:
            return
        if not processed:
            time.sleep(2)


if __name__ == '__main__':
    main()
