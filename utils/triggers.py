"""Teaching triggers for the "Learn to Play" mode.

A trigger looks at one move that was just played and returns a concept id
when it has something to teach. Concept ids are turned into sentences by
the Flutter app, so nothing in this file writes English text.

Scope rules:
  "once"   - teach this concept at most once per account
  "always" - teach it every time it happens
"""

import chess


PIECE_NAMES = {
    chess.PAWN: "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK: "rook",
    chess.QUEEN: "queen",
    chess.KING: "king",
}

PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}


class Trigger:
    """One teaching rule."""

    def __init__(self, concept_id, scope, priority, evaluate):
        self.concept_id = concept_id
        self.scope = scope
        self.priority = priority
        self.evaluate = evaluate

    def __repr__(self):
        return f"<Trigger {self.concept_id} priority={self.priority}>"


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def _unprotected_pieces(board, color):
    """Squares with a non-king piece of `color` that is attacked and not
    defended by any piece of the same colour. Most valuable first."""
    enemy = not color
    found = []

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None or piece.color != color:
            continue
        if piece.piece_type == chess.KING:
            continue
        if not board.is_attacked_by(enemy, square):
            continue
        if board.is_attacked_by(color, square):
            continue
        found.append(square)

    found.sort(key=lambda sq: -PIECE_VALUES[board.piece_at(sq).piece_type])
    return found


def _piece_params(board, square):
    return {
        "square": chess.square_name(square),
        "piece": PIECE_NAMES[board.piece_at(square).piece_type],
    }


# -------------------------------------------------------
# Triggers
# -------------------------------------------------------

def _hanging_piece(ctx):
    """You moved and left one of your pieces with no defence."""
    if not ctx.mover_is_user:
        return None

    hanging = _unprotected_pieces(ctx.board_after, ctx.board_before.turn)
    if not hanging:
        return None

    return _piece_params(ctx.board_after, hanging[0])


def _opponent_hung_piece(ctx):
    """The opponent just left a piece undefended - go and take it."""
    if ctx.mover_is_user:
        return None

    hanging = _unprotected_pieces(ctx.board_after, ctx.board_before.turn)
    if not hanging:
        return None

    return _piece_params(ctx.board_after, hanging[0])


def _move_quality(ctx, wanted):
    """Fire when the move analysis landed on a specific classification."""
    if not ctx.mover_is_user or ctx.analysis is None:
        return None
    if ctx.analysis.get("classification") != wanted:
        return None
    return {}


def _blunder(ctx):
    return _move_quality(ctx, "Blunder")


def _mistake(ctx):
    return _move_quality(ctx, "Mistake")


def _brilliant(ctx):
    return _move_quality(ctx, "Brilliant")


def _missed_mate(ctx):
    """You had a forced mate and did not play it."""
    if not ctx.mover_is_user or ctx.analysis is None:
        return None

    score = ctx.analysis.get("before_score") or {}
    if score.get("type") != "mate" or score.get("value", 0) <= 0:
        return None
    if ctx.analysis.get("best_move") == ctx.analysis.get("played_move"):
        return None

    return {"best_move": ctx.analysis.get("best_move")}


def _missed_capture(ctx):
    """The best move won a piece for free and you played something else."""
    if not ctx.mover_is_user or ctx.analysis is None:
        return None

    best = ctx.analysis.get("best_move")
    if not best:
        return None
    if best == ctx.analysis.get("played_move"):
        return None

    try:
        best_move = chess.Move.from_uci(best)
    except ValueError:
        return None

    if not ctx.board_before.is_capture(best_move):
        return None

    target = best_move.to_square
    victim = ctx.board_before.piece_at(target)

    # En passant captures a pawn that is not on the target square.
    if victim is None and ctx.board_before.is_en_passant(best_move):
        victim = ctx.board_before.piece_at(chess.square(
            chess.square_file(best_move.to_square),
            chess.square_rank(best_move.from_square),
        ))

    if victim is None:
        return None

    # A defended piece is a trade, not a gift.
    if ctx.board_before.is_attacked_by(victim.color, target):
        return None

    return {"square": chess.square_name(target)}


def _is_castling(ctx):
    if not ctx.mover_is_user:
        return None
    if not ctx.board_before.is_castling(ctx.move):
        return None
    return {"move": ctx.move.uci()}


def _is_en_passant(ctx):
    if not ctx.mover_is_user:
        return None
    if not ctx.board_before.is_en_passant(ctx.move):
        return None
    return {"move": ctx.move.uci()}


def _is_promotion(ctx):
    if not ctx.mover_is_user:
        return None
    if ctx.move.promotion is None:
        return None
    return {"piece": PIECE_NAMES[ctx.move.promotion]}


def _you_gave_check(ctx):
    if not ctx.mover_is_user:
        return None
    if not ctx.board_after.is_check():
        return None
    return {}


def _you_are_in_check(ctx):
    if ctx.mover_is_user:
        return None
    if not ctx.board_after.is_check():
        return None
    return {}


def _stalemate(ctx):
    if not ctx.board_after.is_stalemate():
        return None
    return {}


def _first_piece_move(ctx):
    """The first time you move each kind of piece this account."""
    if not ctx.mover_is_user:
        return None
    piece = ctx.board_before.piece_at(ctx.move.from_square)
    if piece is None:
        return None
    return {"piece": PIECE_NAMES[piece.piece_type]}


# Order does not matter: pick_dialog sorts by priority. Higher priority
# wins when several triggers fire on the same move.
TRIGGERS = [
    Trigger("hanging_piece", "always", 95, _hanging_piece),
    Trigger("blunder", "always", 90, _blunder),
    Trigger("stalemate_rule", "once", 90, _stalemate),
    Trigger("missed_mate", "always", 88, _missed_mate),
    Trigger("mistake", "always", 85, _mistake),
    Trigger("en_passant", "once", 84, _is_en_passant),
    Trigger("promotion", "once", 83, _is_promotion),
    Trigger("you_are_in_check", "once", 82, _you_are_in_check),
    Trigger("castling", "once", 80, _is_castling),
    Trigger("you_gave_check", "once", 70, _you_gave_check),
    Trigger("missed_capture", "always", 65, _missed_capture),
    Trigger("opponent_hung_piece", "always", 62, _opponent_hung_piece),
    Trigger("brilliant", "always", 58, _brilliant),
    Trigger("first_piece_move", "once", 55, _first_piece_move),
]


class MoveContext:
    """Everything a trigger is allowed to look at."""

    def __init__(self, board_before, move, board_after, analysis, mover_is_user):
        self.board_before = board_before
        self.move = move
        self.board_after = board_after
        self.analysis = analysis
        self.mover_is_user = mover_is_user


def pick_dialog(board_before, move, board_after, analysis, mover_is_user,
                already_taught):
    """Return the best teaching dialog for this move, or None.

    `already_taught` is a set of concept ids the player has seen before.
    Only one dialog is returned: the highest priority trigger that fired.
    """
    ctx = MoveContext(board_before, move, board_after, analysis, mover_is_user)
    fired = []

    for trigger in TRIGGERS:
        if trigger.scope == "once" and trigger.concept_id in already_taught:
            continue

        params = trigger.evaluate(ctx)
        if params is None:
            continue

        fired.append({
            "concept_id": trigger.concept_id,
            "priority": trigger.priority,
            "scope": trigger.scope,
            "params": params or {},
        })

    if not fired:
        return None

    fired.sort(key=lambda item: -item["priority"])
    return fired[0]
