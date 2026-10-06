import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import chess

from utils.connect_db import get_connection
from utils.stockfish_service import analyze_user_move
from config import USER_ID

TOTAL_LEVELS = 22

# Classification (from utils/stockfish_service.classify_move) -> stars out of 5.
_CLASSIFICATION_STARS = {
    "Brilliant": 5,
    "Excellent": 5,
    "Good": 4,
    "Inaccuracy": 3,
    "Mistake": 2,
    "Blunder": 1,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_levels_overview(user_id: int = USER_ID) -> List[Dict[str, Any]]:
    """
    List all 20 levels with the user's progress (stars/completed) and whether
    each one is locked. Level 1 is always unlocked; level N unlocks once
    level N-1 is completed.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT l.level_number, l.title, l.description,
               COALESCE(p.stars, 0) AS stars,
               COALESCE(p.completed, 0) AS completed
        FROM levels l
        LEFT JOIN user_level_progress p
            ON p.level_id = l.id AND p.user_id = ?
        ORDER BY l.level_number ASC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    result = []
    prev_completed = True  # level 1 is always unlocked
    for row in rows:
        level_number, title, description, stars, completed = row
        locked = not prev_completed
        result.append({
            "level_number": level_number,
            "title": title,
            "description": description,
            "stars": stars,
            "completed": bool(completed),
            "locked": locked,
        })
        prev_completed = bool(completed)

    return result


def _get_level_and_step(cursor, level_number: int):
    cursor.execute("SELECT id FROM levels WHERE level_number = ?", (level_number,))
    level_row = cursor.fetchone()
    if not level_row:
        raise ValueError(f"Level {level_number} does not exist")
    level_id = level_row[0]

    cursor.execute("""
        SELECT step_order, fen, instruction, piece_icon, correct_from, correct_to, promotion, step_type
        FROM level_steps WHERE level_id = ? ORDER BY step_order ASC
    """, (level_id,))
    steps = cursor.fetchall()
    if not steps:
        raise ValueError(f"Level {level_number} has no steps configured")
    if steps[0][7] != "user_move":
        # A level must always open with something for the player to do.
        raise ValueError(f"Level {level_number}'s first step must be a user_move")

    return level_id, steps


def start_level(level_number: int, user_id: int = USER_ID) -> Dict[str, Any]:
    """
    Start (or restart) a level. Creates a fresh session beginning at step 1,
    regardless of any previous attempt - levels are short and meant to be
    retried freely.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    level_id, steps = _get_level_and_step(cursor, level_number)
    first_step = steps[0]
    _, fen, instruction, piece_icon, correct_from, correct_to, promotion, _step_type = first_step

    session_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO level_sessions (id, user_id, level_id, current_step_order, fen, attempts, status, created_at)
        VALUES (?, ?, ?, 1, ?, 0, 'active', ?)
    """, (session_id, user_id, level_id, fen, _now()))

    conn.commit()
    conn.close()

    return {
        "session_id": session_id,
        "level_number": level_number,
        "step_order": 1,
        "total_steps": len(steps),
        "fen": fen,
        "instruction": instruction,
        "piece_icon": piece_icon,
        "hint_from": correct_from,
        "hint_to": correct_to,
    }


def submit_level_move(
    session_id: str,
    from_square: str,
    to_square: str,
    promotion: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Submit a move attempt for the current step of a level session.

    - If it matches the step's intended move: apply it, award stars (5 minus
      a small penalty per prior wrong attempt), persist progress, and either
      advance to the next step or mark the level complete.
    - If it's a different but legal move: don't apply/persist it. Run it
      through the same Stockfish-based analysis used for normal Human vs AI
      coaching (utils.stockfish_service.analyze_user_move) and return a star
      rating for that move, with no piece_icon - the board stays on the same step
      so the user can try again.
    - If it isn't even a legal move: raise ValueError (400 at the router).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("""
        SELECT user_id, level_id, current_step_order, fen, attempts, status
        FROM level_sessions WHERE id = ?
    """, (session_id,))
    session_row = cursor.fetchone()
    if not session_row:
        conn.close()
        raise ValueError("Level session not found")

    user_id, level_id, step_order, fen, attempts, status = session_row
    if status != "active":
        conn.close()
        raise ValueError("This level session has already ended")

    cursor.execute("""
        SELECT step_order, instruction, piece_icon, correct_from, correct_to, promotion, step_type
        FROM level_steps WHERE level_id = ? ORDER BY step_order ASC
    """, (level_id,))
    steps = cursor.fetchall()
    step_index = step_order - 1
    if step_index < 0 or step_index >= len(steps):
        conn.close()
        raise ValueError("Invalid step for this session")

    _, instruction, piece_icon, correct_from, correct_to, correct_promotion, step_type = steps[step_index]
    if step_type != "user_move":
        # Shouldn't happen - current_step_order should only ever point at a
        # user_move step, since opponent_move steps are auto-played below.
        conn.close()
        raise ValueError("This step isn't awaiting a player move")

    board = chess.Board(fen)
    uci = from_square + to_square + (promotion or "")
    try:
        move = chess.Move.from_uci(uci)
    except Exception:
        conn.close()
        raise ValueError("Malformed move")

    if move not in board.legal_moves:
        conn.close()
        raise ValueError("That move isn't legal in this position")

    is_correct = (
        from_square == correct_from
        and to_square == correct_to
        and (promotion or None) == (correct_promotion or None)
    )

    if is_correct:
        board.push(move)
        new_fen = board.fen()

        # Walk forward through any scripted opponent_move steps - these are
        # pre-authored content, not live engine play, so they're auto-played
        # unconditionally. Still checked against legal_moves as a safety net
        # against bad content rather than silently corrupting the board.
        opponent_moves: List[Dict[str, str]] = []
        next_index = step_index + 1
        while next_index < len(steps) and steps[next_index][6] == "opponent_move":
            (_, _, _, opp_from, opp_to, opp_promo, _) = steps[next_index]
            opp_uci = opp_from + opp_to + (opp_promo or "")
            opp_move = chess.Move.from_uci(opp_uci)
            if opp_move not in board.legal_moves:
                conn.close()
                raise ValueError(
                    f"Scripted opponent move {opp_uci} is illegal at step {next_index + 1} "
                    f"of this level - content needs fixing"
                )
            board.push(opp_move)
            new_fen = board.fen()
            opponent_moves.append({"from": opp_from, "to": opp_to})
            next_index += 1

        is_level_complete = next_index >= len(steps)

        if is_level_complete:
            # Stars reflect every wrong attempt across the whole level, not
            # just the final step.
            stars = max(5 - min(attempts, 3), 2)

            cursor.execute("""
                INSERT INTO user_level_progress (user_id, level_id, stars, completed)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id, level_id) DO UPDATE SET
                    stars = MAX(stars, excluded.stars),
                    completed = 1
            """, (user_id, level_id, stars))

            cursor.execute("""
                UPDATE level_sessions SET fen = ?, status = 'completed' WHERE id = ?
            """, (new_fen, session_id))

            conn.commit()

            cursor.execute("SELECT level_number FROM levels WHERE id = ?", (level_id,))
            level_number = cursor.fetchone()[0]
            conn.close()

            return {
                "correct": True,
                "level_complete": True,
                "stars": stars,
                "piece_icon": piece_icon,
                "message": "Level complete! Great job.",
                "fen": new_fen,
                "next_level_number": level_number + 1 if level_number < TOTAL_LEVELS else None,
                "hint_from": correct_from,
                "hint_to": correct_to,
                "opponent_moves": opponent_moves,
            }
        else:
            next_step = steps[next_index]
            (next_order, next_instruction, next_piece_icon,
             next_correct_from, next_correct_to, _, _) = next_step

            # Attempts accumulate across the whole session now (not reset
            # per step), so the final star count reflects the full level.
            cursor.execute("""
                UPDATE level_sessions
                SET fen = ?, current_step_order = ?
                WHERE id = ?
            """, (new_fen, next_order, session_id))
            conn.commit()
            conn.close()

            message = "Nicely done! On to the next move."
            if opponent_moves:
                message = "Nicely done! The opponent replies - now it's your move again."

            return {
                "correct": True,
                "level_complete": False,
                "stars": None,
                "piece_icon": next_piece_icon,
                "message": message,
                "fen": new_fen,
                "step_order": next_order,
                "instruction": next_instruction,
                "hint_from": next_correct_from,
                "hint_to": next_correct_to,
                "opponent_moves": opponent_moves,
            }
    else:
        # Legal, but not the intended teaching move. Rate it honestly with
        # the same engine-backed analysis used in normal games, but don't
        # let it progress the lesson or persist to the session's board.
        analysis = analyze_user_move(fen, uci)
        stars = _CLASSIFICATION_STARS.get(analysis["classification"], 1)

        cursor.execute("""
            UPDATE level_sessions SET attempts = attempts + 1 WHERE id = ?
        """, (session_id,))
        conn.commit()
        conn.close()

        return {
            "correct": False,
            "level_complete": False,
            "stars": stars,
            "piece_icon": None,  # piece_icon is removed once the user deviates from the taught move
            "message": f"That's a legal move ({analysis['classification']}), but not the move this lesson is teaching. Try again!",
            "fen": fen,  # board stays put - this attempt is not applied
            "step_order": step_order,
            "instruction": instruction,
            "classification": analysis["classification"],
            "hint_from": correct_from,
            "hint_to": correct_to,
        }
