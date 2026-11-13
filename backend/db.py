import os
from sqlalchemy import create_engine, inspect, text
from pathlib import Path
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./techwire.db')
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite:') else {})
Session = sessionmaker(bind=engine)

def migrate():
    with engine.begin() as c:
        c.execute(text('CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)'))
        for path in sorted((Path(__file__).parents[1] / 'migrations').glob('*.sql')):
            if c.execute(text('SELECT 1 FROM schema_migrations WHERE name=:name'), {'name': path.name}).first():
                continue
            for statement in path.read_text().split(';'):
                if statement.strip():
                    if (path.name == '008_job_priority.sql' and statement.lstrip().startswith('ALTER TABLE')
                            and 'priority' in {column['name'] for column in inspect(c).get_columns('processing_jobs')}):
                        continue
                    c.execute(text(statement))
            from datetime import datetime, timezone
            c.execute(text('INSERT INTO schema_migrations (name,applied_at) VALUES (:name,:stamp)'),
                      {'name': path.name, 'stamp': datetime.now(timezone.utc).isoformat(timespec='seconds')})
