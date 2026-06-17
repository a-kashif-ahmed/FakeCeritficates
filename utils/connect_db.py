from utils.get_parent_path import get_parent_path

import sqlite3
import os
from pathlib import Path

# Use environment variable to detect environment
IS_VERCEL = os.environ.get("VERCEL")  # Vercel sets this automatically

if IS_VERCEL:
    DB_PATH = "/tmp/app.db"
else:
    DB_PATH = Path(__file__).parent.parent / "database" / "app.db"
    os.makedirs(DB_PATH.parent, exist_ok=True)

def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn