import os
import random
import subprocess
import threading
import chess
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ENGINE_PATH = os.path.join(BASE_DIR, "engines", "stockfish")


# Strength presets for the "Learn to Play" mode.
# Stockfish's own Skill Level 0..19 covers roughly 1320..3190 Elo, so below
# ~1320 we also search shallowly and sometimes throw in a random legal move.
#
# Measured with tests/harness_beginner.py (48 moves each, 100% legal):
#   Beginner : 119 avg cp lost per move, 15% blunders, ~890 Elo,  0.00s/move
#   Casual   :  48 avg cp lost per move,  4% blunders, ~1300 Elo, 0.01s/move
#   Strong   :  15 avg cp lost per move,  0% blunders, ~2580 Elo, 0.13s/move
DIFFICULTY_PRESETS = {
    0: {"name": "Beginner", "skill": 0, "depth": 2, "blunder_chance": 0.25},
    1: {"name": "Casual", "skill": 8, "depth": 6, "blunder_chance": 0.10},
    2: {"name": "Strong", "skill": 15, "depth": 10, "blunder_chance": 0.0},
}


class StockfishEngine:

    def __init__(self):

        self.process = subprocess.Popen(
            [ENGINE_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        print("PID:", self.process.pid)

        self.send("uci")
        self.wait_for("uciok")

        self.send("isready")
        self.wait_for("readyok")

        self.configure()

    def send(self, command):

        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

    def configure(self, skill=20, multi_pv=1):
        """Reset every option that influences which move is chosen.

        Every search calls this first, so settings from one request (for
        example a weak "Learn to Play" opponent) can never leak into the
        next request's search.
        """
        self.send("setoption name UCI_LimitStrength value false")
        self.send(f"setoption name Skill Level value {skill}")
        self.send(f"setoption name MultiPV value {multi_pv}")
        self.send("isready")
        self.wait_for("readyok")



    def wait_for(self, text, timeout=5):

        start = time.time()

        while True:

            if self.process.poll() is not None:
                stderr = self.process.stderr.read()
                stdout = self.process.stdout.read()

                raise RuntimeError(
                    f"""
    Stockfish exited.

    Return code: {self.process.returncode}

    STDOUT:
    {stdout}

    STDERR:
    {stderr}
    """
                )

            if time.time() - start > timeout:
                raise RuntimeError(f"Timed out waiting for {text}")

            line = self.process.stdout.readline()

            if text in line:
                return
    def get_top3_moves(self, fen, depth=15):

        self.configure(skill=20, multi_pv=3)

        self.send(f"position fen {fen}")
        self.send(f"go depth {depth}")

        top_moves = {}

        while True:

            line = self.process.stdout.readline().strip()

            if line.startswith("info") and " multipv " in line:

                try:

                    pv = int(line.split(" multipv ")[1].split()[0])

                    if pv > 3:
                        continue

                    if " pv " not in line:
                        continue

                    move = line.split(" pv ")[1].split()[0]

                    top_moves[pv] = move

                except Exception:
                    pass

            elif line.startswith("bestmove"):

                break

        return [
            top_moves.get(1),
            top_moves.get(2),
            top_moves.get(3)
        ]

    def get_best_move(self, fen, depth=15, skill=20):
        """Best move for one position.

        skill < 20 makes the engine deliberately weak (used by the
        "Learn to Play" mode); the default 20 is full strength.
        """

        # configure() also resets MultiPV, but a low Skill Level makes
        # Stockfish search several PVs internally anyway, so the read loop
        # below only accepts "multipv 1" score lines.
        self.configure(skill=skill, multi_pv=1)

        self.send(f"position fen {fen}")
        self.send(f"go depth {depth}")

        best = None
        evaluation = None
        started = time.time()

        while True:

            line = self.process.stdout.readline().strip()

            if not line:
                if self.process.poll() is not None:
                    raise RuntimeError("Stockfish exited during search")
                if time.time() - started > 60:
                    raise RuntimeError("Stockfish search timed out")
                continue

            if line.startswith("info"):

                # Ignore PV 2/3/4: their scores belong to weaker moves.
                if " multipv " in line:
                    try:
                        which_pv = int(line.split(" multipv ")[1].split()[0])
                    except ValueError:
                        which_pv = 1
                    if which_pv != 1:
                        continue

                if " score cp " in line:

                    cp = int(line.split(" score cp ")[1].split()[0])

                    evaluation = {
                        "type": "cp",
                        "value": cp
                    }

                elif " score mate " in line:

                    mate = int(line.split(" score mate ")[1].split()[0])

                    evaluation = {
                        "type": "mate",
                        "value": mate
                    }

            elif line.startswith("bestmove"):

                parts = line.split()
                best = parts[1] if len(parts) > 1 else None
                break

        return best, evaluation


_engine = None
# A single Stockfish subprocess is shared across every request. FastAPI can
# serve requests concurrently, so without this lock two overlapping games
# (e.g. two /step polls arriving close together) could interleave UCI
# commands/output on the same stdin/stdout and corrupt each other's moves.
_engine_lock = threading.Lock()

def get_engine():
    global _engine

    if _engine is None:
        print("Starting Stockfish...")

        _engine = StockfishEngine()

    return _engine

print("ENGINE PATH:", ENGINE_PATH)
print("EXISTS:", os.path.exists(ENGINE_PATH))

# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def _score(eval_dict):

    if eval_dict is None:
        return 0

    if eval_dict["type"] == "cp":
        return eval_dict["value"]

    if eval_dict["type"] == "mate":
        return 100000 if eval_dict["value"] > 0 else -100000

    return 0


def classify_move(cp_loss):

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

def get_top3_moves(fen):

    with _engine_lock:
        moves = get_engine().get_top3_moves(fen)

    return {
        "top3": [
            m for m in moves if m
        ]
    }

def get_best_move(fen, depth=15, skill=20):
    with _engine_lock:
        best, evaluation = get_engine().get_best_move(fen, depth=depth, skill=skill)
    return best, evaluation


def get_weak_move(fen, skill, depth, blunder_chance=0.0):
    """A deliberately weak engine move, used by the "Learn to Play" mode.

    skill 20 is full strength, skill 0 is Stockfish's weakest built-in
    level. blunder_chance is the probability of ignoring the engine and
    playing a random legal move instead.

    Uses the shared engine under the same lock as everything else;
    configure() inside get_best_move() means the weak settings apply to
    this call only.
    """
    board = chess.Board(fen)
    legal_moves = list(board.legal_moves)

    if not legal_moves:
        return None

    if blunder_chance and random.random() < blunder_chance:
        return random.choice(legal_moves).uci()

    with _engine_lock:
        best, _ = get_engine().get_best_move(fen, depth=depth, skill=skill)

    if best is None:
        return random.choice(legal_moves).uci()

    return best


def get_beginner_move(fen, difficulty=0):
    """Weak opponent move for a guided game. Returns a UCI move or None."""
    preset = DIFFICULTY_PRESETS.get(difficulty, DIFFICULTY_PRESETS[0])
    return get_weak_move(
        fen,
        skill=preset["skill"],
        depth=preset["depth"],
        blunder_chance=preset["blunder_chance"],
    )


# -------------------------------------------------------
# Analyse User Move
# -------------------------------------------------------

def analyze_user_move(before_fen, user_move):

    board = chess.Board(before_fen)

    # Both evaluations are taken under one lock acquisition so no other
    # request can land on the shared engine between the "before" and
    # "after" reads. get_best_move() always runs at full strength.
    with _engine_lock:
        engine = get_engine()

        best_move, best_eval = engine.get_best_move(before_fen)
        best_cp = _score(best_eval)

        board.push(chess.Move.from_uci(user_move))
        after_fen = board.fen()

        _, played_eval = engine.get_best_move(after_fen)
        played_cp = _score(played_eval)

    # A centipawn score is always reported from the point of view of the
    # side to move. Right after the user's move it is the opponent to move,
    # so flip the second score back to the user's point of view before
    # comparing the two.
    after_cp = -played_cp

    cp_loss = max(0, best_cp - after_cp)

    return {

        "best_move": best_move,

        "played_move": user_move,

        "before_eval": best_cp,

        "after_eval": after_cp,

        "cp_loss": cp_loss,

        "classification": classify_move(cp_loss),

        # Raw score of the position before the user moved. Used by the
        # teaching triggers to spot "you had a mate in 1".
        "before_score": best_eval

    }
