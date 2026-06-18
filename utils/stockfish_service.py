import os
import subprocess
import chess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_PATH = os.path.join(BASE_DIR, "engines", "stockfish")


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

        self.send("uci")
        self.wait_for("uciok")

        self.send("isready")
        self.wait_for("readyok")

        self.send("setoption name Skill Level value 20")
        self.send("isready")
        self.wait_for("readyok")

    def send(self, command):

        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()

    def wait_for(self, text):

        while True:
            line = self.process.stdout.readline().strip()

            if text in line:
                return

    def get_best_move(self, fen, depth=15):

        self.send(f"position fen {fen}")
        self.send(f"go depth {depth}")

        best = None
        evaluation = None

        while True:

            line = self.process.stdout.readline().strip()

            if line.startswith("info"):

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

                best = line.split()[1]
                break

        return best, evaluation


_engine = None


def get_engine():
    global _engine

    if _engine is None:
        print("Starting Stockfish...")
        _engine = StockfishEngine()

    return _engine

engine = get_engine()

print("ENGINE PATH:", ENGINE_PATH)
print("EXISTS:", os.path.exists(ENGINE_PATH))
print("PID:", self.process.pid)
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

def get_best_move(fen):

    move, evaluation = engine.get_best_move(fen)

    return {

        "move": move,

        "evaluation": evaluation

    }


# -------------------------------------------------------
# Analyse User Move
# -------------------------------------------------------

def analyze_user_move(before_fen, user_move):

    board = chess.Board(before_fen)

    best_move, best_eval = engine.get_best_move(before_fen)

    best_cp = _score(best_eval)

    board.push(chess.Move.from_uci(user_move))

    after_fen = board.fen()

    _, played_eval = engine.get_best_move(after_fen)

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