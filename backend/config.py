"""Application configuration."""
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = os.environ.get("WDMMG_DB", str(ROOT_DIR / "data" / "wdmmg.db"))
API_PREFIX = "/api/v1"
