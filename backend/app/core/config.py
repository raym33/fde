import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "virtudirector_labs.sqlite3"


def get_database_path() -> Path:
    configured = os.getenv("LABS_SQLITE_PATH")
    return Path(configured).expanduser().resolve() if configured else DEFAULT_DB_PATH

