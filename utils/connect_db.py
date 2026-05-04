from utils.get_parent_path import get_parent_path

import sqlite3
#tryinf
DB_PATH = get_parent_path() / "database" / "app.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
