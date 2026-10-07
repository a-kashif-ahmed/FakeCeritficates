"""Unit tests for the teaching triggers.

    cd backend
    venv\\Scripts\\python.exe -m pytest tests/test_triggers.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chess

from utils.triggers import pick_dialog


def play(fen, uci):
    """Build (board_before, move, board_after) for one move."""
    board_before = chess.Board(fen)
    move = chess.Move.from_uci(uci)
    board_after = board_before.copy(stack=True)
    board_after.push(move)
    return board_before, move, board_after


def pick(fen, uci, analysis=None, mover_is_user=True, taught=None):
    board_before, move, board_after = play(fen, uci)
    return pick_dialog(
        board_before,
        move,
        board_after,
        analysis,
        mover_is_user,
        taught or set(),
    )


# -------------------------------------------------------
# hanging pieces
# -------------------------------------------------------

# Knight hops onto b5, attacked by the black pawns a6 and c6.
HANGING_FEN = "4k3/8/p1p5/8/3N4/8/8/4K3 w - - 0 1"
HANGING_MOVE = "d4b5"

# Same, but the white rook b2 covers b5.
DEFENDED_FEN = "4k3/8/p1p5/8/3N4/8/1R6/4K3 w - - 0 1"


def test_hanging_piece_fires_when_left_undefended():
    dialog = pick(HANGING_FEN, HANGING_MOVE)
    assert dialog["concept_id"] == "hanging_piece"
    assert dialog["params"] == {"square": "b5", "piece": "knight"}


def test_hanging_piece_does_not_fire_when_defended():
    dialog = pick(DEFENDED_FEN, HANGING_MOVE)
    assert dialog is None or dialog["concept_id"] != "hanging_piece"


def test_hanging_piece_beats_blunder_on_priority():
    # Both fire: hanging_piece is priority 95, blunder is 90.
    analysis = {"classification": "Blunder"}
    dialog = pick(HANGING_FEN, HANGING_MOVE, analysis=analysis)
    assert dialog["concept_id"] == "hanging_piece"


# -------------------------------------------------------
# once-only concepts
# -------------------------------------------------------

CASTLING_FEN = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"


def test_castling_fires():
    dialog = pick(CASTLING_FEN, "e1g1")
    assert dialog["concept_id"] == "castling"


def test_castling_is_not_repeated_once_taught():
    dialog = pick(CASTLING_FEN, "e1g1",
                  taught={"castling", "first_piece_move"})
    assert dialog is None


def test_first_piece_move_reports_the_piece():
    dialog = pick("4k3/8/8/8/8/8/8/N3K3 w - - 0 1", "a1b3")
    assert dialog["concept_id"] == "first_piece_move"
    assert dialog["params"]["piece"] == "knight"


def test_promotion_beats_first_piece_move():
    dialog = pick("8/4P3/8/8/8/8/8/3K2k1 w - - 0 1", "e7e8q")
    assert dialog["concept_id"] == "promotion"
    assert dialog["params"]["piece"] == "queen"


def test_you_gave_check():
    dialog = pick("4k3/8/8/8/8/8/8/R3K3 w - - 0 1", "a1a8")
    assert dialog["concept_id"] == "you_gave_check"


def test_stalemate_rule():
    # Qb1-g6 leaves the black king on h8 with no safe square:
    # g8/g7 are covered by the white king on f7, h7 by the queen.
    dialog = pick("7k/5K2/8/8/8/8/8/1Q6 w - - 0 1", "b1g6")
    assert dialog["concept_id"] == "stalemate_rule"


# -------------------------------------------------------
# move quality (needs the analysis dict from analyze_user_move)
# -------------------------------------------------------

PAWN_FEN = "4k3/8/8/8/8/8/P7/4K3 w - - 0 1"


def test_blunder_comes_from_the_analysis():
    analysis = {"classification": "Blunder", "best_move": "e2e4",
                "played_move": "a2a3"}
    dialog = pick(PAWN_FEN, "a2a3", analysis=analysis)
    assert dialog["concept_id"] == "blunder"


def test_always_scope_ignores_already_taught():
    analysis = {"classification": "Blunder"}
    dialog = pick(PAWN_FEN, "a2a3", analysis=analysis, taught={"blunder"})
    assert dialog["concept_id"] == "blunder"


def test_missed_mate():
    analysis = {
        "classification": "Good",
        "before_score": {"type": "mate", "value": 1},
        "best_move": "a1a8",
        "played_move": "e1e2",
    }
    dialog = pick("4k3/8/8/8/8/8/8/R3K3 w - - 0 1", "e1e2", analysis=analysis)
    assert dialog["concept_id"] == "missed_mate"
    assert dialog["params"]["best_move"] == "a1a8"


def test_missed_mate_does_not_fire_when_the_mate_is_played():
    analysis = {
        "before_score": {"type": "mate", "value": 1},
        "best_move": "a1a8",
        "played_move": "a1a8",
    }
    dialog = pick("4k3/8/8/8/8/8/8/R3K3 w - - 0 1", "a1a8", analysis=analysis)
    assert dialog is None or dialog["concept_id"] != "missed_mate"


def test_missed_capture_of_an_undefended_piece():
    analysis = {"best_move": "d1d5", "played_move": "d1d2"}
    dialog = pick("4k3/8/8/3q4/8/8/8/3QK3 w - - 0 1", "d1d2", analysis=analysis)
    assert dialog["concept_id"] == "missed_capture"
    assert dialog["params"]["square"] == "d5"


def test_missed_capture_ignored_when_the_piece_is_defended():
    # The black rook d8 defends d5, so Qxd5 is only a trade.
    analysis = {"best_move": "d1d5", "played_move": "d1d2"}
    dialog = pick("3r1k2/8/8/3q4/8/8/8/3QK3 w - - 0 1", "d1d2", analysis=analysis)
    assert dialog is None or dialog["concept_id"] != "missed_capture"


# -------------------------------------------------------
# opponent moves
# -------------------------------------------------------

def test_opponent_hung_piece_fires_on_the_opponents_move():
    # Black plays Ra8-a5, right onto the white knight on b3.
    dialog = pick("r3k3/8/8/8/8/1N6/8/4K3 b - - 0 1", "a8a5",
                  mover_is_user=False)
    assert dialog["concept_id"] == "opponent_hung_piece"
    assert dialog["params"]["square"] == "a5"
    assert dialog["params"]["piece"] == "rook"


def test_opponent_hung_piece_never_fires_on_your_own_move():
    dialog = pick(HANGING_FEN, HANGING_MOVE)
    assert dialog["concept_id"] != "opponent_hung_piece"
