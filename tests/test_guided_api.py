"""End-to-end test for the "Learn to Play" endpoints.

    cd backend
    venv\\Scripts\\python.exe -m pytest tests/test_guided_api.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chess
from fastapi.testclient import TestClient

from app import app
from utils.triggers import TRIGGERS

client = TestClient(app)

KNOWN_CONCEPTS = {trigger.concept_id for trigger in TRIGGERS}


def start_game(difficulty=0):
    response = client.post("/api/v1/guided-games/", json={"difficulty": difficulty})
    assert response.status_code == 200, response.text
    return response.json()


def play_some_moves(session_id, fen, plies=3):
    """Play a few real moves (one user move + engine reply each)."""
    for _ in range(plies):
        board = chess.Board(fen)
        if board.is_game_over():
            break

        legal = list(board.legal_moves)
        assert legal, "the stored position should have legal moves"
        move = legal[0]

        response = client.post(
            f"/api/v1/guided-games/{session_id}/move",
            json={
                "from_square": chess.square_name(move.from_square),
                "to_square": chess.square_name(move.to_square),
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()

        assert data["fen"] != fen, "the position should have changed"
        for dialog in data["dialogs"]:
            assert dialog["concept_id"] in KNOWN_CONCEPTS

        if data["game_end"] != "no":
            return data

        # It must be our turn again after the engine answers.
        fen = data["fen"]
        assert chess.Board(fen).turn == board.turn, "engine reply missing"
        assert data["ai_from"] and data["ai_to"]

    return data


def test_guided_game_start_move_show_and_hint():
    started = start_game(difficulty=0)
    session_id = started["session_id"]
    fen = started["fen"]
    assert started["difficulty"] == 0

    data = play_some_moves(session_id, fen, plies=3)

    assert data["analysis"] is not None
    assert "classification" in data["analysis"]
    assert isinstance(data["dialogs"], list)

    shown = client.get(f"/api/v1/guided-games/{session_id}/show")
    assert shown.status_code == 200, shown.text
    assert shown.json()["status"] in ("active", "ended")

    hinted = client.post(f"/api/v1/guided-games/{session_id}/hint")
    assert hinted.status_code == 200, hinted.text
    top3 = hinted.json()["top3"]
    assert isinstance(top3, list)

    summary = client.get(f"/api/v1/guided-games/{session_id}/summary")
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["total_moves"] > 0
    assert isinstance(body["concepts_taught"], list)


def test_illegal_move_is_rejected():
    started = start_game(difficulty=0)
    response = client.post(
        f"/api/v1/guided-games/{started['session_id']}/move",
        json={"from_square": "a3", "to_square": "a5"},
    )
    assert response.status_code == 400


def test_unknown_session_is_404():
    shown = client.get("/api/v1/guided-games/does-not-exist/show")
    assert shown.status_code == 404


def test_unknown_difficulty_is_400():
    response = client.post("/api/v1/guided-games/", json={"difficulty": 99})
    assert response.status_code == 400


def test_guided_difficulty_is_saved_and_used_as_default():
    try:
        saved = client.post("/api/v1/settings", json={"guided_difficulty": 2})
        assert saved.status_code == 200, saved.text

        read_back = client.get("/api/v1/settings")
        assert read_back.status_code == 200
        assert read_back.json()["guided_difficulty"] == 2

        # No difficulty in the request -> the saved one is used.
        started = start_game(difficulty=None)
        assert started["difficulty"] == 2
    finally:
        client.post("/api/v1/settings", json={"guided_difficulty": 0})
