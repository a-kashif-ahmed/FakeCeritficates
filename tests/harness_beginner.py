"""Strength harness for the "Learn to Play" opponent.

Plays a batch of games for each weak-engine configuration against a fixed
full-strength reference, then measures how good the weak moves actually are.

Reported per configuration:
  - legality      : fraction of moves that were legal (must be 100%)
  - match vs ref  : how often it played the reference's first choice
  - avg cp loss   : centipawns worse than the best move, capped at 1000
                    per move so a single "allowed mate" does not drown it
  - blunder rate  : moves losing more than 200cp
  - sec / move    : how long the weak engine takes
  - est. Elo      : rough estimate interpolated between three anchors
                    (full strength, stockfish's weakest level, random moves)

Run it:
    cd backend
    venv\\Scripts\\python.exe tests\\harness_beginner.py --games 4 --plies 24
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chess
from utils.stockfish_service import (
    DIFFICULTY_PRESETS,
    _engine_lock,
    get_engine,
    get_weak_move,
)

REFERENCE_SKILL = 20
REFERENCE_DEPTH = 10

# Rough anchor points for the Elo estimate. The three anchor configurations
# below are believed to play at roughly these strengths, so their measured
# centipawn losses let us interpolate an estimate for everything else.
FULL_STRENGTH_ELO = 3190
SKILL_ZERO_ELO = 1320
RANDOM_MOVE_ELO = 350


def reference(fen):
    """Full-strength best move and evaluation (centipawns, side to move)."""
    with _engine_lock:
        move, score = get_engine().get_best_move(
            fen, depth=REFERENCE_DEPTH, skill=REFERENCE_SKILL
        )
    return move, score_to_cp(score)


def score_to_cp(score):
    if score is None:
        return 0
    if score["type"] == "mate":
        return 100000 if score["value"] > 0 else -100000
    return score["value"]


def play_batch(label, settings, games, plies):
    """Play `games` short games with this configuration and measure it."""
    stats = {
        "label": label,
        "moves": 0,
        "legal": 0,
        "matches": 0,
        "cp_total": 0,
        "blunders": 0,
        "seconds": 0.0,
    }

    for game_number in range(games):
        # Alternate colours so we sample both first moves and replies.
        player_is_white = game_number % 2 == 0
        board = chess.Board()

        for _ in range(plies):
            if board.is_game_over():
                break
            if (board.turn == chess.WHITE) != player_is_white:
                # Reference's turn.
                move, _ = reference(board.fen())
                if move is None:
                    break
                board.push(chess.Move.from_uci(move))
                continue

            fen_before = board.fen()
            started = time.time()
            played = get_weak_move(fen_before, **settings)
            stats["seconds"] += time.time() - started

            if played is None:
                break

            stats["moves"] += 1

            try:
                move_obj = chess.Move.from_uci(played)
            except ValueError:
                move_obj = None

            if move_obj is None or move_obj not in board.legal_moves:
                break  # illegal move ends this game, counted against legality
            stats["legal"] += 1

            best_move, before_cp = reference(fen_before)
            if played == best_move:
                stats["matches"] += 1

            board.push(move_obj)
            _, after_cp = reference(board.fen())

            # before_cp is from our side's point of view, after_cp is from
            # the opponent's, so flip it before comparing. The loss is
            # capped at 1000 because a move that allows mate scores as
            # 100000 and would drown the average.
            loss = max(0, before_cp + after_cp)
            stats["cp_total"] += min(loss, 1000)
            if loss > 200:
                stats["blunders"] += 1

    return stats


def estimate_elo(avg_cp, anchors):
    """Rough Elo by interpolating between measured anchors.

    anchors is a list of (avg_cp_loss, elo) sorted from strongest
    (lowest cp loss) to weakest (highest cp loss).
    """
    anchors = sorted(anchors, key=lambda item: item[0])

    if avg_cp <= anchors[0][0]:
        return anchors[0][1]

    for (low_cp, low_elo), (high_cp, high_elo) in zip(anchors, anchors[1:]):
        if avg_cp <= high_cp:
            if high_cp == low_cp:
                return high_elo
            share = (avg_cp - low_cp) / (high_cp - low_cp)
            return int(low_elo + share * (high_elo - low_elo))

    return anchors[-1][1]


def show(stats, anchors):
    moves = stats["moves"] or 1
    avg_cp = stats["cp_total"] / moves
    elo = estimate_elo(avg_cp, anchors)
    print("")
    print(stats["label"])
    print(f"  moves       : {stats['moves']}")
    print(f"  legal       : {stats['legal']}/{stats['moves']}"
          f" ({100 * stats['legal'] / moves:.0f}%)")
    print(f"  match vs ref: {100 * stats['matches'] / moves:.0f}%")
    print(f"  avg cp loss : {avg_cp:.0f} (capped at 1000/move)")
    print(f"  blunders    : {100 * stats['blunders'] / moves:.0f}%")
    print(f"  sec / move  : {stats['seconds'] / moves:.2f}")
    if elo is not None:
        print(f"  est. Elo    : ~{elo} (rough)")
    return avg_cp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=4)
    parser.add_argument("--plies", type=int, default=24)
    args = parser.parse_args()

    # The first three configurations are the measuring sticks: their real
    # playing strength is known, so their measured centipawn losses become
    # the anchors for the Elo estimates of everything else.
    configs = [
        (
            "anchor: full strength (skill 20, depth 15)",
            {"skill": 20, "depth": 15, "blunder_chance": 0.0},
            FULL_STRENGTH_ELO,
        ),
        (
            "anchor: stockfish weakest (skill 0, depth 15)",
            {"skill": 0, "depth": 15, "blunder_chance": 0.0},
            SKILL_ZERO_ELO,
        ),
        (
            "anchor: random legal moves",
            {"skill": 0, "depth": 1, "blunder_chance": 1.0},
            RANDOM_MOVE_ELO,
        ),
    ]
    for key in sorted(DIFFICULTY_PRESETS):
        preset = DIFFICULTY_PRESETS[key]
        configs.append(
            (
                f"preset {key}: {preset['name']} (skill {preset['skill']}, "
                f"depth {preset['depth']}, blunder {preset['blunder_chance']:.0%})",
                {
                    "skill": preset["skill"],
                    "depth": preset["depth"],
                    "blunder_chance": preset["blunder_chance"],
                },
                None,
            )
        )

    results = []
    for index, (label, settings, _) in enumerate(configs):
        print(f"\n[{index + 1}/{len(configs)}] running {label} ...")
        results.append(play_batch(label, settings, args.games, args.plies))

    anchors = [
        (results[i]["cp_total"] / (results[i]["moves"] or 1), elo)
        for i, (_, _, elo) in enumerate(configs)
        if elo is not None
    ]

    for stats in results:
        show(stats, anchors)

    illegal_found = any(
        stats["moves"] and stats["legal"] < stats["moves"] for stats in results
    )
    if illegal_found:
        print("\nWARNING: at least one configuration produced illegal moves!")
        return 1

    print("\nAll configurations produced only legal moves.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
