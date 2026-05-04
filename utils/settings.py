from typing import Dict, Any
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.connect_db import get_connection


def get_settings(user_id: int) -> Dict[str, Any]:
    """Fetch merged settings from all tables for a user."""
    conn = get_connection()
    cursor = conn.cursor()

    def fetch_one(table):
        cursor.execute(f"SELECT * FROM {table} WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else {}

    settings = {
        **fetch_one("ui_settings"),
        **fetch_one("game_settings"),
        **fetch_one("ai_settings")
    }
    conn.close()
    return settings


def upsert_settings(user_id: int, table: str, data: Dict[str, Any]):
    """Insert or replace settings into the table."""
    if not data:
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO {} (user_id) VALUES (?)".format(table), (user_id,))
    updates = ", ".join("{} = ?".format(k) for k in data.keys())
    sql = "UPDATE {} SET {} WHERE user_id = ?".format(table, updates)
    values = list(data.values()) + [user_id]
    cursor.execute(sql, values)
    conn.commit()
    conn.close()
