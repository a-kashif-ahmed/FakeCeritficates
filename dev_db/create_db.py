import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.connect_db import get_connection

def create_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS board_themes (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            white_sq_color TEXT NOT NULL,
            black_sq_color TEXT NOT NULL,
            white_sq_blob BLOB,
            black_sq_blob BLOB
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS board_theme_overrides (
            id INTEGER PRIMARY KEY,
            board_theme_id INTEGER REFERENCES board_themes(id),
            square TEXT NOT NULL,
            blob BLOB NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS piece_themes (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            w_pawn BLOB NOT NULL,
            w_rook BLOB NOT NULL,
            w_knight BLOB NOT NULL,
            w_bishop BLOB NOT NULL,
            w_queen BLOB NOT NULL,
            w_king BLOB NOT NULL,
            b_pawn BLOB NOT NULL,
            b_rook BLOB NOT NULL,
            b_knight BLOB NOT NULL,
            b_bishop BLOB NOT NULL,
            b_queen BLOB NOT NULL,
            b_king BLOB NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            elo INTEGER DEFAULT 800 CHECK (elo BETWEEN 100 AND 3600)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ui_settings (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            language TEXT NOT NULL DEFAULT 'en',
            board_theme_id INTEGER REFERENCES board_themes(id),
            piece_theme_id INTEGER REFERENCES piece_themes(id),
            toggle_bar INTEGER DEFAULT 0 CHECK (toggle_bar IN (0, 1)),
            money_widget INTEGER DEFAULT 1 CHECK (money_widget IN (0, 1))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_settings (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            user_color INTEGER DEFAULT 2 CHECK (user_color IN (0, 1, 2)),
            premove INTEGER DEFAULT 1 CHECK (premove IN (0, 1)),
            play_till INTEGER DEFAULT 1 CHECK (play_till IN (0, 1)),
            watch_only INTEGER DEFAULT 0 CHECK (watch_only IN (0, 1))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_settings (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            ai_illegal INTEGER DEFAULT 1 CHECK (ai_illegal IN (0, 1)),
            ai_allowed_offer INTEGER DEFAULT 1 CHECK (ai_allowed_offer IN (0, 1, 2)),
            long_horizon_planning INTEGER DEFAULT 0 CHECK (long_horizon_planning BETWEEN 0 AND 10)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            id TEXT PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            status TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            ended_at TIMESTAMP,
            result TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_settings_snapshot (
            game_id TEXT PRIMARY KEY REFERENCES games(id),
            user_color INTEGER,
            watch_only INTEGER,
            play_till INTEGER,
            ai_illegal INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS moves (
            id INTEGER PRIMARY KEY,
            game_id TEXT REFERENCES games(id),
            ply INTEGER NOT NULL,
            moved_by INTEGER CHECK (moved_by IN (0, 1)),
            fen TEXT NOT NULL,
            san TEXT,
            created_at TIMESTAMP NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_plans (
            game_id TEXT REFERENCES games(id),
            ply INTEGER NOT NULL,
            plan_json TEXT NOT NULL,
            PRIMARY KEY (game_id, ply)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS external_apis (
            id INTEGER PRIMARY KEY,
            service_name TEXT,
            endpoint TEXT,
            api_key TEXT,
            validated INTEGER CHECK (validated IN (0, 1))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_players (
            id INTEGER PRIMARY KEY,
            model_name TEXT,
            provider_id INTEGER REFERENCES external_apis(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_ai_assignment (
            game_id TEXT REFERENCES games(id),
            role TEXT CHECK (role IN ('model_a', 'model_b')),
            ai_player_id INTEGER REFERENCES ai_players(id),
            PRIMARY KEY (game_id, role)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_sessions (
            id INTEGER PRIMARY KEY,
            platform TEXT NOT NULL,
            used_by TEXT NOT NULL,
            game_id TEXT REFERENCES games(id),
            started_at TIMESTAMP NOT NULL,
            ended_at TIMESTAMP,
            status TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_calls (
            id INTEGER PRIMARY KEY,
            session_id INTEGER REFERENCES usage_sessions(id),
            model TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            vision_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            duration REAL NOT NULL,
            cost REAL NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY,
            session_id INTEGER REFERENCES usage_sessions(id),
            created_at TIMESTAMP NOT NULL,
            dialogue_json TEXT NOT NULL
        )
    """)
    ""
    

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_db()
    print("All database tables created successfully.")