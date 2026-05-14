import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import get_connection, init_db, migration_status  # noqa: E402

if __name__ == "__main__":
    init_db()
    with get_connection() as conn:
        status = migration_status(conn)
    print(
        "SQLite migrations complete. "
        f"latest={status['latest']} applied={status['applied']} pending={status['pending']}"
    )
