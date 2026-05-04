import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.connect_db import get_connection
import uuid
from datetime import datetime

def insert_sample_data():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Create user
    cursor.execute("INSERT OR IGNORE INTO users (id, username, elo) VALUES (1, 'testuser', 800)")

    # UI settings
    cursor.execute("""
        INSERT OR IGNORE INTO ui_settings (user_id, language, board_theme_id, piece_theme_id, toggle_bar, money_widget)
        VALUES (1, 'en', NULL, NULL, 0, 1)
    """)

    # Game settings
    cursor.execute("""
        INSERT OR IGNORE INTO game_settings (user_id, user_color, premove, play_till, watch_only)
        VALUES (1, 2, 1, 1, 0)
    """)

    # AI settings
    cursor.execute("""
        INSERT OR IGNORE INTO ai_settings (user_id, ai_illegal, ai_allowed_offer, long_horizon_planning)
        VALUES (1, 1, 1, 0)
    """)

    # Sample board themes
    dummy_blob = b'default_board_blob'
    cursor.execute("""
        INSERT OR IGNORE INTO board_themes (id, name, white_sq_color, black_sq_color, white_sq_blob, black_sq_blob)
        VALUES 
        (1, 'default', '#f0d9b5', '#b58863', ?, ?),
        (2, 'stonic', '#f0f0f0', '#3a3a3a', ?, ?),
        (3, 'marble', '#ffffff', '#d0d0d0', ?, ?),
        (4, 'neon', '#00ff00', '#ff00ff', ?, ?),
        (5, 'classic', '#eedbd0', '#b58863', ?, ?)
    """, (dummy_blob, dummy_blob) * 5)

    # Sample piece themes (dummy blobs)
    dummy_blob = b'default_piece'
    piece_fields = ['w_pawn', 'w_rook', 'w_knight', 'w_bishop', 'w_queen', 'w_king', 'b_pawn', 'b_rook', 'b_knight', 'b_bishop', 'b_queen', 'b_king']
    placeholders = ', '.join(['?'] * 14)
    values = [2, 'airal'] + [dummy_blob] * 12
    cursor.execute(f"""
        INSERT OR IGNORE INTO piece_themes (id, name, {', '.join(piece_fields)})
        VALUES ({placeholders})
    """, values)

    values = [3, 'minimal'] + [dummy_blob] * 12
    cursor.execute(f"""
        INSERT OR IGNORE INTO piece_themes (id, name, {', '.join(piece_fields)})
        VALUES ({placeholders})
    """, values)

    values = [4, 'fantasy'] + [dummy_blob] * 12
    cursor.execute(f"""
        INSERT OR IGNORE INTO piece_themes (id, name, {', '.join(piece_fields)})
        VALUES ({placeholders})
    """, values)

    values = [1, 'classic'] + [dummy_blob] * 12
    cursor.execute(f"""
        INSERT OR IGNORE INTO piece_themes (id, name, {', '.join(piece_fields)})
        VALUES ({placeholders})
    """, values)

    



    # Update ui_settings with themes
    cursor.execute("""
        UPDATE ui_settings SET board_theme_id = 1, piece_theme_id = 1 WHERE user_id = 1
    """)

    conn.commit()
    conn.close()
    print("Sample data inserted successfully.")

if __name__ == "__main__":
    insert_sample_data()
