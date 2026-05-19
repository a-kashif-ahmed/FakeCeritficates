from utils.get_parent_path import get_parent_path

import sqlite3
import os

from pathlib import Path
import sqlite3
# DB_PATH = get_parent_path() / "database" / "app.db" 
# os.makedirs(DB_PATH.parent, exist_ok=True) 

DB_PATH = "/tmp/app.db"

def get_connection(): 
    conn = sqlite3.connect(DB_PATH) 
    conn.row_factory = sqlite3.Row 
    return conn