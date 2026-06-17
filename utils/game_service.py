import random
import chess
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from utils.connect_db import get_connection
from utils.settings import get_settings
from utils.ai import create_ai_prompt, call_ai_api
from utils.chess_utils import check_game_end
from utils.stockfish_service import (
    get_best_move,
    analyze_user_move
)


from utils.coach_service import coach_user_move



# ============================
# SAFETY HELPERS
# ============================

def safe_push_allow_illegal(board: chess.Board, move: chess.Move) -> bool:
    """
    Push a move that may be illegal by chess rules,
    but guarantees the resulting board is structurally valid:
    - both kings exist
    - FEN is reloadable
    - turn / ply remain consistent
    """
    board_copy = board.copy(stack=False)

    try:
        board_copy.push(move)
    except Exception:
        return False

    # Both kings must still exist
    if board_copy.king(chess.WHITE) is None:
        return False
    if board_copy.king(chess.BLACK) is None:
        return False

    # FEN must be reloadable
    try:
        chess.Board(board_copy.fen())
    except Exception:
        return False

    # Commit
    board.push(move)
    return True


# ============================
# AI MOVE EXECUTION
# ============================

# def perform_ai_move(
#     ai_info,
#     board: chess.Board,
#     history: List[str],
#     ai_illegal: int,
#     last_ply: int,
#     game_id: str,
#     settings: Dict[str, Any],
#     user_is_white: bool,
#     cursor,
#     conn
# ) -> Tuple[bool, Optional[str], Optional[str], str, str, int]:
#     """
#     Perform AI move.
#     Allows illegal moves if ai_illegal == 1,
#     but never allows king capture or broken FEN.
#     """
#     success = False
#     ai_from = None
#     ai_to = None
#     ai_san = ""
#     new_fen = board.fen()

#     ai_moved_by = 0 if board.turn == chess.WHITE else 1

#     # ============================
#     # ILLEGAL-ALLOWED MODE
#     # ============================
#     # if ai_illegal == 1:
#     #     prompt = create_ai_prompt(board.fen(), history)
#     #     ai_move_dict = call_ai_api(
#     #         ai_info['model_name'],
#     #         ai_info['endpoint'],
#     #         ai_info['api_key'],
#     #         prompt
#     #     )

#     #     if ai_move_dict:
#     #         fr = ai_move_dict.get('from', '')
#     #         to_ = ai_move_dict.get('to', '')
#     #         promote = ai_move_dict.get('promote')

#     #         if len(fr) == 2 and len(to_) == 2:
#     #             uci = fr + to_
#     #             if promote:
#     #                 uci += promote.lower()

#     #             try:
#     #                 move = chess.Move.from_uci(uci)
#     #                 if safe_push_allow_illegal(board, move):
#     #                     ai_from = fr
#     #                     ai_to = to_
#     #                     ai_san = uci
#     #                     success = True
#     #             except Exception:
#     #                 pass

#     # # ============================
#     # # STRICT MODE (LEGAL ONLY)
#     # # ============================
#     # else:
#     #     for _ in range(3):
#     #         prompt = create_ai_prompt(board.fen(), history)
#     #         ai_move_dict = call_ai_api(
#     #             ai_info['model_name'],
#     #             ai_info['endpoint'],
#     #             ai_info['api_key'],
#     #             prompt
#     #         )

#     #         if not ai_move_dict:
#     #             continue

#     #         uci = None
#     #         turn_white = board.turn == chess.WHITE

#     #         if 'castling' in ai_move_dict:
#     #             c = ai_move_dict['castling'].upper()
#     #             if c == 'O-O':
#     #                 uci = 'e1g1' if turn_white else 'e8g8'
#     #             elif c == 'O-O-O':
#     #                 uci = 'e1c1' if turn_white else 'e8c8'
#     #         else:
#     #             fr = ai_move_dict.get('from', '')
#     #             to_ = ai_move_dict.get('to', '')
#     #             if len(fr) == 2 and len(to_) == 2:
#     #                 uci = fr + to_
#     #                 promote = ai_move_dict.get('promote')
#     #                 if promote:
#     #                     uci += promote.lower()

#     #         if not uci:
#     #             continue

#     #         try:
#     #             move = chess.Move.from_uci(uci)
#     #             if move in board.legal_moves:
#     #                 ai_san = board.san(move)
#     #                 board.push(move)
#     #                 ai_from = uci[:2]
#     #                 ai_to = uci[2:4]
#     #                 success = True
#     #                 break
#     #         except Exception:
#     #             continue

#     # ============================
#     # FINAL FALLBACK (ALWAYS SAFE)
#     # ============================
#     if not success:
#         legal_moves = list(board.legal_moves)
#         if legal_moves:
#             move = random.choice(legal_moves)
#             ai_san = board.san(move)
#             board.push(move)
#             uci = move.uci()
#             ai_from = uci[:2]
#             ai_to = uci[2:4]
#             success = True

#     # ============================
#     # COMMIT MOVE
#     # ============================
#     new_ply = last_ply + 1 if success else last_ply
#     game_end = "no"

#     if success:
#         cursor.execute("""
#             INSERT INTO moves (game_id, ply, moved_by, fen, san, created_at)
#             VALUES (?, ?, ?, ?, ?, ?)
#         """, (
#             game_id,
#             new_ply,
#             ai_moved_by,
#             board.fen(),
#             ai_san,
#             datetime.now().isoformat()
#         ))

#         new_fen = board.fen()
#         game_end = check_game_end(
#             board, settings, user_is_white, game_id, cursor, conn
#         )

#     return success, ai_from, ai_to, new_fen, game_end, new_ply

def perform_ai_move(
    ai_info,
    board: chess.Board,
    history,
    ai_illegal,
    last_ply,
    game_id,
    settings,
    user_is_white,
    cursor,
    conn
):
    """
    Uses Stockfish instead of the LLM to generate the AI move.
    The LLM is now only used for coaching.
    """

    ai_from = None
    ai_to = None
    ai_san = ""
    success = False

    # ----------------------------
    # Ask Stockfish
    # ----------------------------

    result = get_best_move(board.fen())

    best_move = result["move"]

    if best_move is None:

        legal = list(board.legal_moves)

        if not legal:

            return (
                False,
                None,
                None,
                board.fen(),
                "no",
                last_ply
            )

        move = random.choice(legal)

    else:

        move = chess.Move.from_uci(best_move)

    # ----------------------------
    # Play move
    # ----------------------------

    ai_san = board.san(move)

    board.push(move)

    success = True

    uci = move.uci()

    ai_from = uci[:2]

    ai_to = uci[2:4]

    ai_moved_by = 0 if not user_is_white else 1

    new_ply = last_ply + 1

    cursor.execute(
        """
        INSERT INTO moves
        (
            game_id,
            ply,
            moved_by,
            fen,
            san,
            created_at
        )
        VALUES
        (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """,
        (
            game_id,
            new_ply,
            ai_moved_by,
            board.fen(),
            ai_san,
            datetime.now().isoformat()
        )
    )

    game_end = check_game_end(
        board,
        settings,
        user_is_white,
        game_id,
        cursor,
        conn
    )

    return (
        success,
        ai_from,
        ai_to,
        board.fen(),
        game_end,
        new_ply
    )
# ============================
# GAME CREATION / STATE
# ============================

from config import USER_ID


def get_ai_info(cursor, game_id: str, role: str) -> Optional[Dict[str, str]]:
    cursor.execute("""
        SELECT ap.model_name, ea.endpoint, ea.api_key
        FROM game_ai_assignment gaa
        JOIN ai_players ap ON gaa.ai_player_id = ap.id
        JOIN external_apis ea ON ap.provider_id = ea.id
        WHERE gaa.game_id = ? AND gaa.role = ?
    """, (game_id, role))
    row = cursor.fetchone()
    return dict(row) if row else None


def create_game(user_id: int = USER_ID) -> Dict[str, Any]:
    settings = get_settings(user_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    game_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO games (id, user_id, status, created_at) VALUES (?, ?, 'active', ?)",
        (game_id, user_id, datetime.now().isoformat())
    )

    user_color_setting = settings.get('user_color', 2)
    user_is_white = random.choice([True, False]) if user_color_setting == 2 else user_color_setting == 0
    user_color = 0 if user_is_white else 1

    watch_only = settings.get('watch_only', 0) == 1
    play_till = settings.get('play_till', 1)
    ai_illegal = settings.get('ai_illegal', 1)

    cursor.execute("""
        INSERT INTO game_settings_snapshot (game_id, user_color, watch_only, play_till, ai_illegal)
        VALUES (?, ?, ?, ?, ?)
    """, (game_id, user_color, int(watch_only), play_till, ai_illegal))

    ai_player_id = 2
    if watch_only:
        cursor.execute("""
            INSERT INTO game_ai_assignment (game_id, role, ai_player_id)
            VALUES (?, 'model_a', ?), (?, 'model_b', ?)
        """, (game_id, ai_player_id, game_id, ai_player_id))
    else:
        role = 'model_b' if user_is_white else 'model_a'
        cursor.execute("""
            INSERT INTO game_ai_assignment (game_id, role, ai_player_id)
            VALUES (?, ?, ?)
        """, (game_id, role, ai_player_id))

    board = chess.Board()
    ai_from = None
    ai_to = None
    if not watch_only and not user_is_white:
        # AI (white, model_a) moves first
        history = []
        ai_info = get_ai_info(cursor, game_id, "model_a")
        if ai_info:
            success, ai_from_, ai_to_, new_fen, game_end, new_ply = perform_ai_move(
                ai_info, board, history, ai_illegal, 0, game_id, settings, user_is_white, cursor, conn
            )
            ai_from = ai_from_
            ai_to = ai_to_
            if game_end != "no":
                cursor.execute("UPDATE games SET status = 'ended' WHERE id = ?", (game_id,))

    conn.commit()
    conn.close()

    return {
        "game_id": game_id,
        "fen": board.fen(),
        "user_color": "white" if user_is_white else "black",
        "from_square": ai_from,
        "to_square": ai_to
    }


def list_games(count: int = 10) -> List[str]:
    """List recent game IDs for the user."""
    from config import USER_ID
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM games ORDER BY created_at DESC LIMIT ?",
        (count)
    )
    games = [row[0] for row in cursor.fetchall()]
    conn.close()
    return games


def get_game_state(game_id: str) -> Dict[str, Any]:
    """Get current game state including last FEN, turn, orientation, last move."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("SELECT status FROM games WHERE id = ?", (game_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError("Game not found")
    status = row[0]
    cursor.execute("SELECT user_color FROM game_settings_snapshot WHERE game_id = ?", (game_id,))
    snap_row = cursor.fetchone()
    if not snap_row:
        conn.close()
        raise ValueError("No settings snapshot")
    user_color = snap_row[0]
    orientation = "white" if user_color == 0 else "black"
    cursor.execute("""
        SELECT fen, san FROM moves WHERE game_id = ? ORDER BY ply DESC LIMIT 1
    """, (game_id,))
    last_row = cursor.fetchone()
    last_move = None
    if last_row:
        fen, san = last_row
        board = chess.Board(fen)
        turn = "white" if board.turn == chess.WHITE else "black"
        try:
            prev_board = board.copy()
            prev_board.pop()
            move = prev_board.parse_san(san)
            last_move = {
                "from": chess.square_name(move.from_square),
                "to": chess.square_name(move.to_square)
            }
        except Exception:
            pass
    else:
        fen = chess.Board().fen()
        turn = "white"
    conn.close()
    return {
        "game_id": game_id,
        "fen": fen,
        "orientation": orientation,
        "turn": turn,
        "last_move": last_move,
        "status": status
    }


def process_move(game_id: str, from_square: str, to_square: str) -> Dict[str, Any]:
    """Process user move, check validity, save, check end, then AI response if applicable."""
    from config import USER_ID
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("SELECT user_id, status FROM games WHERE id = ?", (game_id,))
    game_row = cursor.fetchone()
    if not game_row or game_row[1] != "active":
        conn.close()
        raise ValueError("Game not found or not active")
    user_id = game_row[0]
    settings = get_settings(user_id)
    cursor.execute("""
        SELECT user_color, watch_only, play_till, ai_illegal
        FROM game_settings_snapshot WHERE game_id = ?
    """, (game_id,))
    snap_row = cursor.fetchone()
    if not snap_row:
        conn.close()
        raise ValueError("No game settings")
    user_color, watch_only, play_till, ai_illegal = map(int, snap_row)
    user_is_white = user_color == 0
    if watch_only == 1:
        conn.close()
        raise ValueError("Cannot move in watch-only game")
    # Load current board state
    cursor.execute("""
        SELECT ply, fen, moved_by FROM moves
        WHERE game_id = ? ORDER BY ply DESC LIMIT 1
    """, (game_id,))
    last_row = cursor.fetchone()
    if last_row:
        last_ply, last_fen, last_moved_by = last_row
        board = chess.Board(last_fen)
    else:
        last_ply = 0
        board = chess.Board()
        last_moved_by = None
    # Force user's turn from FEN if not already
    user_turn = chess.WHITE if user_is_white else chess.BLACK
    fen_str = board.fen()
    parts = fen_str.split()
    if len(parts) >= 2:
        current_turn = parts[1]
        expected_turn = 'w' if user_turn == chess.WHITE else 'b'
        if current_turn != expected_turn:
            parts[1] = expected_turn
            fen_str = ' '.join(parts)
            board = chess.Board(fen_str)
    # Parse and validate move
    uci = from_square + to_square
    from_sq = chess.parse_square(from_square)
    to_sq = chess.parse_square(to_square)
    piece = board.piece_at(from_sq)
    is_promotion = (
        piece and piece.piece_type == chess.PAWN and
        ((board.turn == chess.WHITE and chess.square_rank(to_sq) == 7) or
         (board.turn == chess.BLACK and chess.square_rank(to_sq) == 0))
    )
    if is_promotion:
        uci += "q"  # Default to queen
    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        conn.close()
        raise ValueError("Invalid move format")
    if move not in board.legal_moves:
        conn.close()
        raise ValueError("Illegal move")
    # Execute user move

    before_fen = board.fen()

    san = board.san(move)

    board.push(move)
    analysis = analyze_user_move(
    before_fen,
    move.uci()
)
    new_ply = last_ply + 1
    user_moved_by = 0 if user_is_white else 1
    cursor.execute("""
        INSERT INTO moves (game_id, ply, moved_by, fen, san, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (game_id, new_ply, user_moved_by, board.fen(), san, datetime.now().isoformat()))
    # Check if game ended after user move
    game_end = check_game_end(board, settings, user_is_white, game_id, cursor, conn)
    ai_from = None
    ai_to = None
    new_fen = board.fen()
    if game_end != "no":
        cursor.execute("UPDATE games SET status = 'ended' WHERE id = ?", (game_id,))
        conn.commit()
        conn.close()
        return {
            "ai_from": None,
            "ai_to": None,
            "fen": new_fen,
            "game_end": game_end
        }
    # Prepare AI move
    cursor.execute("SELECT san FROM moves WHERE game_id = ? ORDER BY ply ASC", (game_id,))
    history = [row[0] for row in cursor.fetchall()]
    opp_role = "model_b" if user_is_white else "model_a"
    ai_info = get_ai_info(cursor, game_id, opp_role)
    coach_feedback = None

    if ai_info:
        coach_feedback = coach_user_move(
            ai_info,
            analysis
        )
    #
    if ai_info:
        success, ai_from_, ai_to_, new_fen_, game_end_, new_ply_ = perform_ai_move(
            ai_info, board, history, ai_illegal, new_ply, game_id, settings, user_is_white, cursor, conn
        )
        ai_from = ai_from_
        ai_to = ai_to_
        new_fen = new_fen_
        game_end = game_end_
    conn.commit()
    conn.close()
    return {

    "ai_from": ai_from,

    "ai_to": ai_to,

    "fen": new_fen,

    "game_end": game_end,

    "coach_feedback": coach_feedback,

    "classification": analysis["classification"],

    "best_move": analysis["best_move"],

    "played_move": analysis["played_move"],

    "centipawn_loss": analysis["cp_loss"],

    "evaluation_before": analysis["before_eval"],

    "evaluation_after": analysis["after_eval"]

}
