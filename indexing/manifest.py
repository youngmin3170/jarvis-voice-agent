import sqlite3
from contextlib import closing
from pathlib import Path


def initialize_manifest(db_path: Path) -> None:
    with closing(sqlite3.connect(db_path)) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS indexed_files (
                relative_path TEXT PRIMARY KEY,
                size_bytes    INTEGER NOT NULL,
                mtime_ns      INTEGER NOT NULL,
                sha256        TEXT NOT NULL,
                index_config  TEXT NOT NULL
            )
        """)
        db.commit()