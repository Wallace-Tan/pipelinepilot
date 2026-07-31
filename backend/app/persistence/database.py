from __future__ import annotations

import sqlite3
from pathlib import Path


MIGRATIONS_PATH = Path(__file__).with_name("migrations")


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        self.apply_migrations(connection)
        return connection

    @staticmethod
    def apply_migrations(connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"
        )
        applied = {
            row[0] for row in connection.execute("SELECT version FROM schema_migrations")
        }
        for migration_path in sorted(MIGRATIONS_PATH.glob("*.sql")):
            version = int(migration_path.stem.split("_", 1)[0])
            if version in applied:
                continue
            connection.executescript(migration_path.read_text(encoding="utf-8"))
            connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
            connection.commit()


def json_text(value: object) -> str:
    import json

    return json.dumps(value, separators=(",", ":"), sort_keys=True)
