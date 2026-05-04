import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from app import app
from utils.connect_db import get_connection
import chess

client = TestClient(app)

def debug_move():
    # Clean DB first
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM moves")
    cursor.execute("DELETE FROM games")
    cursor.execute("DELETE FROM game_ai_assignment")
    cursor.execute("DELETE FROM game_settings_snapshot")
    conn.commit()
    conn.close()

    # Create game
    response = client.post("/api/v1/games/")
    print("Create game response:", response.json())
    game_id = response.json()["game_id"]

    # Try the move that's failing
    move_data = {
        "from_square": "e2",
        "to_square": "e4",
        # No fen parameter
    }

    print("Attempting move with data:", move_data)

    # Let's also test what happens if we provide the fen
    move_data_with_fen = {
        "from_square": "e2",
        "to_square": "e4",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    }

    print("Attempting move with fen:", move_data_with_fen)
    response_with_fen = client.post(f"/api/v1/games/{game_id}/move", json=move_data_with_fen)
    print("Move with fen response:", response_with_fen.json())
    print("Move with fen status:", response_with_fen.status_code)

if __name__ == "__main__":
    debug_move()