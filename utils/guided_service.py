"""Live "Learn to Play" games against a deliberately weak Stockfish.

A guided game is an ordinary chess game with two differences:
  * the opponent plays badly on purpose (see utils.stockfish_service),
  * every move can produce a short teaching dialog (utils.triggers).
"""

import random
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import chess

from config import USER_ID
from utils.chess_utils import PROMOTION_PIECES, detect_game_end
from utils.connect_db import get_connection
from utils.settings import get_settings
from utils.stockfish_service import (
    DIFFICULTY_PRESETS,
    analyze_user_move,
    get_beginner_move,
    get_top3_moves,
)
from utils.triggers import pick_dialog


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# -------------------------------------------------------
# Small shared helpers
# -------------------------------------------------------

def _difficulty_or_default(difficulty, settings) -> int:
    if difficulty is None:
        difficulty = settings.get("guided_difficulty", 0)
    if difficulty not in DIFFICULTY_PRESETS:
        raise ValueError(f"Unknown difficulty: {difficulty}")
    return difficulty


def _pick_colour(settings) -> bool:
    """True when the player is white. Same rule as a normal game:
    0 = white, 1 = black, 2 = random."""
    setting = settings.get("user_color", 2)
    if setting == 2:
        return random.choice([True, False])
    return setting == 0


def _load_taught(cursor, user_id) -> Set[str]:
    cursor.execute(
        "SELECT concept_id FROM user_taught_concepts WHERE user_id = ?",
        (user_id,),
    )
    return {row[0] for row in cursor.fetchall()}


def _remember_taught(cursor, user_id, concept_id) -> None:
    now = _now()
    cursor.execute("""
        INSERT INTO user_taught_concepts
            (user_id, concept_id, times_shown, first_shown_at, last_shown_at)
        VALUES (?, ?, 1, ?, ?)
        ON CONFLICT(user_id, concept_id) DO UPDATE
            SET times_shown = times_shown + 1,
                last_shown_at = excluded.last_shown_at
    """, (user_id, concept_id, now, now))


def _next_ply(cursor, session_id) -> int:
    cursor.execute(
        "SELECT COALESCE(MAX(ply), 0) FROM guided_game_moves WHERE session_id = ?",
        (session_id,),
    )
    return cursor.fetchone()[0] + 1


def _record_move(cursor, session_id, ply, side, uci, san, fen, analysis=None):
    cursor.execute("""
        INSERT INTO guided_game_moves
            (session_id, ply, side, uci, san, fen, classification, cp_loss, best_move)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_id,
        ply,
        side,
        uci,
        san,
        fen,
        analysis.get("classification") if analysis else None,
        analysis.get("cp_loss") if analysis else None,
        analysis.get("best_move") if analysis else None,
    ))


def _dialogs_for(cursor, session_id, user_id, ply, board_before, move,
                 board_after, analysis, mover_is_user, taught) -> List[Dict[str, Any]]:
    """Run the teaching triggers for one move and store whatever fires."""
    dialog = pick_dialog(
        board_before, move, board_after, analysis, mover_is_user, taught
    )
    if dialog is None:
        return []

    cursor.execute(
        "INSERT INTO guided_dialog_log (session_id, ply, concept_id) VALUES (?, ?, ?)",
        (session_id, ply, dialog["concept_id"]),
    )

    # Once-only concepts stop firing the moment they have been shown.
    if dialog["scope"] == "once":
        _remember_taught(cursor, user_id, dialog["concept_id"])
        taught.add(dialog["concept_id"])

    return [{
        "concept_id": dialog["concept_id"],
        "params": dialog["params"],
    }]


def _load_session(cursor, session_id):
    cursor.execute("""
        SELECT user_id, difficulty, user_is_white, fen, status, result
        FROM guided_game_sessions WHERE id = ?
    """, (session_id,))
    row = cursor.fetchone()
    if row is None:
        raise ValueError("Unknown guided game session")
    return row


def _save_position(cursor, session_id, fen) -> None:
    cursor.execute(
        "UPDATE guided_game_sessions SET fen = ? WHERE id = ?",
        (fen, session_id),
    )


def _finish_session(cursor, session_id, game_end) -> None:
    cursor.execute("""
        UPDATE guided_game_sessions
        SET status = 'ended', result = ?, ended_at = ?
        WHERE id = ?
    """, (game_end, _now(), session_id))


def _play_engine_move(cursor, session_id, board, user_is_white, difficulty,
                      taught, user_id, settings, ply) -> Dict[str, Any]:
    """Let the weak engine make one move. The board is updated in place."""
    uci = get_beginner_move(board.fen(), difficulty)
    if uci is None:
        return {"from_square": None, "to_square": None, "ply": ply,
                "game_end": "no", "dialogs": []}

    move = chess.Move.from_uci(uci)
    board_before = board.copy(stack=True)
    san = board.san(move)
    board.push(move)

    ply += 1
    _record_move(cursor, session_id, ply, "ai", uci, san, board.fen())

    dialogs = _dialogs_for(
        cursor, session_id, user_id, ply,
        board_before, move, board, None, False, taught,
    )
    game_end = detect_game_end(board, settings, user_is_white)

    return {
        "from_square": chess.square_name(move.from_square),
        "to_square": chess.square_name(move.to_square),
        "ply": ply,
        "game_end": game_end,
        "dialogs": dialogs,
    }


def _parse_move(board, from_square, to_square, promotion) -> chess.Move:
    try:
        from_sq = chess.parse_square(from_square)
        to_sq = chess.parse_square(to_square)
    except ValueError:
        raise ValueError("Invalid square")

    piece = board.piece_at(from_sq)
    needs_promotion = piece is not None and piece.piece_type == chess.PAWN and (
        (board.turn == chess.WHITE and chess.square_rank(to_sq) == 7) or
        (board.turn == chess.BLACK and chess.square_rank(to_sq) == 0)
    )

    if needs_promotion:
        if promotion not in PROMOTION_PIECES:
            promotion = "q"  # same default as the normal game mode
        uci = from_square + to_square + promotion
    else:
        uci = from_square + to_square

    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        raise ValueError("Invalid move format")

    if move not in board.legal_moves:
        raise ValueError("Illegal move")

    return move


# -------------------------------------------------------
# Endpoints' service functions
# -------------------------------------------------------

def start_guided_game(difficulty: Optional[int] = None,
                      user_id: int = USER_ID) -> Dict[str, Any]:
    """Open a new guided game. If the player is black, the weak engine
    plays the first move so the player always has something to answer."""
    settings = get_settings(user_id)
    difficulty = _difficulty_or_default(difficulty, settings)
    user_is_white = _pick_colour(settings)

    board = chess.Board()
    session_id = str(uuid.uuid4())

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("""
        INSERT INTO guided_game_sessions
            (id, user_id, difficulty, user_is_white, fen, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'active', ?)
    """, (session_id, user_id, difficulty, int(user_is_white), board.fen(), _now()))

    taught = _load_taught(cursor, user_id)
    ply = 0
    ai_from = None
    ai_to = None
    dialogs = []
    game_end = "no"

    if not user_is_white:
        result = _play_engine_move(
            cursor, session_id, board, user_is_white, difficulty,
            taught, user_id, settings, ply,
        )
        ai_from = result["from_square"]
        ai_to = result["to_square"]
        ply = result["ply"]
        dialogs = result["dialogs"]
        game_end = result["game_end"]

    # Persist whatever position we reached, opening move or not.
    _save_position(cursor, session_id, board.fen())
    if game_end != "no":
        _finish_session(cursor, session_id, game_end)

    conn.commit()
    conn.close()

    preset = DIFFICULTY_PRESETS[difficulty]
    return {
        "session_id": session_id,
        "fen": board.fen(),
        "user_color": "white" if user_is_white else "black",
        "difficulty": difficulty,
        "difficulty_name": preset["name"],
        "from_square": ai_from,
        "to_square": ai_to,
        "dialogs": dialogs,
    }


def submit_guided_move(session_id: str, from_square: str, to_square: str,
                       promotion: Optional[str] = None) -> Dict[str, Any]:
    """Play one move for the human, then answer it with the weak engine."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    user_id, difficulty, user_is_white, fen, status, _result = \
        _load_session(cursor, session_id)

    if status != "active":
        conn.close()
        raise ValueError("This guided game has already finished")

    settings = get_settings(user_id)
    board = chess.Board(fen)

    move = _parse_move(board, from_square, to_square, promotion)
    board_before = board.copy(stack=True)
    before_fen = board_before.fen()
    san = board.san(move)

    analysis = analyze_user_move(before_fen, move.uci())
    board.push(move)

    taught = _load_taught(cursor, user_id)
    ply = _next_ply(cursor, session_id)
    _record_move(cursor, session_id, ply, "user", move.uci(), san,
                 board.fen(), analysis)

    dialogs = _dialogs_for(
        cursor, session_id, user_id, ply,
        board_before, move, board, analysis, True, taught,
    )

    game_end = detect_game_end(board, settings, user_is_white)
    ai_from = None
    ai_to = None

    if game_end == "no":
        result = _play_engine_move(
            cursor, session_id, board, user_is_white, difficulty,
            taught, user_id, settings, ply,
        )
        ai_from = result["from_square"]
        ai_to = result["to_square"]
        ply = result["ply"]
        dialogs += result["dialogs"]
        game_end = result["game_end"]

    _save_position(cursor, session_id, board.fen())
    if game_end != "no":
        _finish_session(cursor, session_id, game_end)

    conn.commit()
    conn.close()

    return {
        "fen": board.fen(),
        "game_end": game_end,
        "ai_from": ai_from,
        "ai_to": ai_to,
        "analysis": analysis,
        "dialogs": dialogs,
    }


def get_guided_state(session_id: str) -> Dict[str, Any]:
    """Everything needed to re-open a guided game on another device."""
    conn = get_connection()
    cursor = conn.cursor()

    _user_id, difficulty, user_is_white, fen, status, _result = \
        _load_session(cursor, session_id)
    ply = _next_ply(cursor, session_id) - 1
    conn.close()

    return {
        "session_id": session_id,
        "fen": fen,
        "status": status,
        "user_color": "white" if user_is_white else "black",
        "difficulty": difficulty,
        "ply": max(0, ply),
    }


def get_hint(session_id: str) -> Dict[str, Any]:
    """Best moves for the current position, straight from Stockfish."""
    conn = get_connection()
    cursor = conn.cursor()

    _user_id, _difficulty, _user_is_white, fen, status, _result = \
        _load_session(cursor, session_id)
    conn.close()

    if status != "active":
        raise ValueError("This guided game has already finished")

    return get_top3_moves(fen)


def get_summary(session_id: str) -> Dict[str, Any]:
    """Post-game report: how the player played and what they were taught."""
    conn = get_connection()
    cursor = conn.cursor()

    _user_id, difficulty, _user_is_white, _fen, status, result = \
        _load_session(cursor, session_id)

    cursor.execute("""
        SELECT classification FROM guided_game_moves
        WHERE session_id = ? AND side = 'user'
    """, (session_id,))
    classifications = Counter(
        row[0] for row in cursor.fetchall() if row[0]
    )

    cursor.execute("""
        SELECT concept_id FROM guided_dialog_log
        WHERE session_id = ? ORDER BY ply ASC
    """, (session_id,))
    concepts = list(dict.fromkeys(row[0] for row in cursor.fetchall()))

    cursor.execute(
        "SELECT COUNT(*) FROM guided_game_moves WHERE session_id = ?",
        (session_id,),
    )
    total_moves = cursor.fetchone()[0]
    conn.close()

    return {
        "session_id": session_id,
        "status": status,
        "result": result,
        "difficulty": difficulty,
        "total_moves": total_moves,
        "classifications": dict(classifications),
        "concepts_taught": concepts,
    }
