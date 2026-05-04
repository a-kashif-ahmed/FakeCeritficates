import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from app import app
from utils.connect_db import get_connection
import chess

client = TestClient(app)

def debug_endpoint():
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

    # Test the move step by step
    move_data = {
        "from_square": "e2",
        "to_square": "e4",
        "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    }

    print("Testing move data:", move_data)

    # Let's manually test what the endpoint should be doing
    current_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    uci_move = "e2e4"

    print(f"Current FEN: {current_fen}")
    print(f"UCI Move: {uci_move}")

    try:
        board = chess.Board(current_fen)
        print("Board created successfully")
        print("Board FEN:", board.fen())

        move_obj = chess.Move.from_uci(uci_move)
        print(f"Move object created: {move_obj}")

        print(f"Is move legal? {move_obj in board.legal_moves}")

        san = board.san(move_obj)
        print(f"SAN: {san}")

        board.push_uci(uci_move)
        print("Move pushed successfully")

        new_fen = board.fen()
        print(f"New FEN: {new_fen}")

    except Exception as e:
        print(f"Error in manual test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_endpoint()