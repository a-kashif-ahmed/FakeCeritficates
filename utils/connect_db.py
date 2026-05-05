from utils.get_parent_path import get_parent_path

import sqlite3
import os

from pathlib import Path
import sqlite3

# On Vercel, only /tmp is writable
DB_PATH = get_parent_path()

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
