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

    # OpenRouter
    cursor.execute("""
        INSERT OR IGNORE INTO external_apis (id, service_name, endpoint, api_key, validated)
        VALUES (2, 'openrouter', 'https://openrouter.ai/api/v1/chat/completions', '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', 1)
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO ai_players (id, model_name, provider_id)
        VALUES (2, 'google/gemini-2.5-flash', 2)
    """)

    # Update ui_settings with themes
    cursor.execute("""
        UPDATE ui_settings SET board_theme_id = 1, piece_theme_id = 1 WHERE user_id = 1
    """)

    # -------------------------------------------------------
    # Levels (guided learning mode)
    # -------------------------------------------------------

    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (1, 1, 'Queen Safety', 'Learn to spot when your most valuable piece is under attack.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (2, 2, 'Rook Safety', 'Keep your rooks out of danger.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (3, 3, 'Free Material', 'Always take free pawns when it''s safe to do so.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (4, 4, 'Winning Material', 'Spotting undefended pieces wins games.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (5, 5, 'Center Control', 'Controlling the center gives your pieces more power.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (6, 6, 'Knight Development', 'Develop knights toward the center early.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (7, 7, 'Bishop Development', 'Open lines for your bishops.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (8, 8, 'Deliver a Check', 'Checks force your opponent to react immediately.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (9, 9, 'Escape Check', 'When in check, you must resolve it immediately.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (10, 10, 'King Safety', 'Keep your King away from open lines when possible.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (11, 11, 'Knight Fork', 'Forks let one piece attack two targets at once.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (12, 12, 'Check Down the Rank', 'Rooks are strongest when they reach the enemy''s back rank.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (13, 13, 'Reposition for Attack', 'Sometimes the key move is repositioning a piece to a stronger diagonal.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (14, 14, 'Undermine the Defense', 'Sometimes the key move is removing what''s in your way.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (15, 15, 'Own the Open File', 'Rooks belong on open files where nothing blocks them.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (16, 16, 'Checkmate in One!', 'Deliver checkmate using your Queen, supported by your King.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (17, 17, 'Ladder Mate', 'Two rooks can checkmate a king trapped on the edge like a ladder.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (18, 18, 'Back Rank Mate', 'A king trapped behind its own pawns is vulnerable on the back rank.')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (19, 19, 'Promote Your Pawn', 'A pawn that reaches the last rank becomes a Queen!')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO levels (id, level_number, title, description)
        VALUES (20, 20, 'Master Checkmate', 'Combine everything you''ve learned to deliver the final blow.')
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (1, 1, '7k/8/8/8/3p4/4Q3/8/4K3 w - - 0 1', 'Your Queen is in danger! A pawn is attacking it. Move it to safety on h6.', 'white_queen', 'e3', 'h6', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (2, 1, '7k/8/8/8/1R6/b7/8/4K3 w - - 0 1', 'Your Rook on b4 is attacked by the bishop. Move it to safety on b8.', 'white_rook', 'b4', 'b8', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (3, 1, '7k/8/8/8/3p4/8/8/Q6K w - - 0 1', 'There''s a free pawn on d4! Capture it with your Queen.', 'white_queen', 'a1', 'd4', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (4, 1, '7k/8/8/8/8/3n4/8/3RK3 w - - 0 1', 'The Knight on d3 is undefended. Capture it with your Rook!', 'white_rook', 'd1', 'd3', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (5, 1, 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', 'Start the game strong! Push your King''s pawn two squares to e4.', 'white_pawn', 'e2', 'e4', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (6, 1, 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1', 'Develop your King''s Knight to its best square, f3.', 'white_knight', 'g1', 'f3', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (7, 1, 'rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 1', 'Develop your Bishop to c4, eyeing the weak f7 square.', 'white_bishop', 'f1', 'c4', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (8, 1, '7k/8/8/8/8/8/4Q3/4K3 w - - 0 1', 'Put the enemy King in check! Move your Queen to h5.', 'white_queen', 'e2', 'h5', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (9, 1, '4k3/8/4r3/8/8/8/8/4K3 w - - 0 1', 'You''re in check from the Rook! Move your King to d2 to escape.', 'white_king', 'e1', 'd2', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (10, 1, '3rk3/8/8/8/8/8/4Q3/4K3 b - - 0 1', 'Your King is a bit exposed on the open d and e files. Tuck it away on f8.', 'black_king', 'e8', 'f8', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (11, 1, '2r1k3/8/8/1N6/8/8/8/6K1 w - - 0 1', 'Fork the King and Rook! Jump your Knight to d6 - it attacks both at once and gives check.', 'white_knight', 'b5', 'd6', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (12, 1, '7k/8/8/8/8/8/8/3RK3 w - - 0 1', 'Bring your Rook all the way to d8 - it delivers check to the King along the 8th rank.', 'white_rook', 'd1', 'd8', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (13, 1, '7k/8/8/8/8/4B3/8/3RK3 w - - 0 1', 'Reposition your Bishop to d4, aiming down the long diagonal toward the enemy King on h8.', 'white_bishop', 'e3', 'd4', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (14, 1, '7k/8/8/8/3n4/8/8/3QK3 w - - 0 1', 'Capture the undefended Knight on d4 with your Queen.', 'white_queen', 'd1', 'd4', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (15, 1, '7k/8/8/8/8/8/8/3RK3 w - - 0 1', 'Bring your Rook deep down the open d-file to d7, one step from the back rank!', 'white_rook', 'd1', 'd7', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (16, 1, '6k1/8/7K/8/8/8/8/Q7 w - - 0 1', 'Checkmate is available! Move your Queen to g7 - it''s protected by your King.', 'white_queen', 'a1', 'g7', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (17, 1, '7k/R7/8/8/8/8/8/1R4K1 w - - 0 1', 'Finish the ladder mate! Move your Rook from b1 to b8.', 'white_rook', 'b1', 'b8', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (18, 1, '6k1/5ppp/8/8/8/8/8/4R1K1 w - - 0 1', 'The King is trapped behind its own pawns! Deliver mate with your Rook on e8.', 'white_rook', 'e1', 'e8', NULL)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (19, 1, '7k/4P3/4K3/8/8/8/8/8 w - - 0 1', 'Your pawn is one step from promotion! Push it to e8 and become a Queen.', 'white_pawn', 'e7', 'e8', 'q')
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO level_steps (level_id, step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion)
        VALUES (20, 1, '1k6/8/K7/8/8/8/8/7Q w - - 0 1', 'You''ve learned so much! Finish the game: checkmate with your Queen on b7.', 'white_queen', 'h1', 'b7', NULL)
    """)

    conn.commit()
    conn.close()
    print("Sample data inserted successfully.")

if __name__ == "__main__":
    insert_sample_data()
