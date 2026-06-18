import chess
import os
import platform
from stockfish import Stockfish

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


ENGINE_PATH = os.path.join(BASE_DIR, "engines", "stockfish")

stockfish = Stockfish(path=ENGINE_PATH)

stockfish.set_depth(15)
stockfish.set_skill_level(20)
# -------------------------------------------------------
# Configure Stockfish
# -------------------------------------------------------

# stockfish = Stockfish(
#     path="engines/stockfish.exe"
# )

# stockfish.set_depth(15)
# stockfish.set_skill_level(20)


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def _score(eval_dict):
    """
    Converts Stockfish evaluation to centipawns.

    cp -> actual value

    mate -> huge score
    """

    if eval_dict["type"] == "cp":
        return eval_dict["value"]

    if eval_dict["type"] == "mate":
        return 100000 if eval_dict["value"] > 0 else -100000

    return 0


def classify_move(cp_loss: int):

    if cp_loss <= 20:
        return "Brilliant"

    if cp_loss <= 50:
        return "Excellent"

    if cp_loss <= 100:
        return "Good"

    if cp_loss <= 200:
        return "Inaccuracy"

    if cp_loss <= 400:
        return "Mistake"

    return "Blunder"


# -------------------------------------------------------
# Engine Move
# -------------------------------------------------------

def get_best_move(fen: str):

    stockfish.set_fen_position(fen)

    best_move = stockfish.get_best_move()

    evaluation = stockfish.get_evaluation()

    return {
        "move": best_move,
        "evaluation": evaluation
    }


# -------------------------------------------------------
# Analyse User Move
# -------------------------------------------------------

def analyze_user_move(before_fen: str, user_move: str):

    board = chess.Board(before_fen)

    # Engine best move BEFORE user move
    stockfish.set_fen_position(before_fen)

    best_move = stockfish.get_best_move()

    best_eval = stockfish.get_evaluation()

    best_cp = _score(best_eval)

    # Play user's move
    board.push(chess.Move.from_uci(user_move))

    after_fen = board.fen()

    # Evaluate AFTER user's move
    stockfish.set_fen_position(after_fen)

    played_eval = stockfish.get_evaluation()

    played_cp = _score(played_eval)

    cp_loss = abs(best_cp - played_cp)

    return {

        "best_move": best_move,

        "played_move": user_move,

        "before_eval": best_cp,

        "after_eval": played_cp,

        "cp_loss": cp_loss,

        "classification": classify_move(cp_loss)

    }