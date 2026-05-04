from fastapi import APIRouter, HTTPException
from models import MoveRequest, MoveResponse, GameCreateResponse, GameShowResponse, GamesListRequest, GamesListResponse
from utils.game_service import create_game, process_move, get_game_state, list_games

router = APIRouter(prefix="/api/v1/games", tags=["games"])

@router.post("/", response_model=GameCreateResponse)
async def create_game_endpoint():
    try:
        result = create_game()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{game_id}/move", response_model=MoveResponse)
async def make_move(game_id: str, move_req: MoveRequest):
    try:
        result = process_move(game_id, move_req.from_square, move_req.to_square)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{game_id}/show", response_model=GameShowResponse)
async def show_game(game_id: str):
    try:
        result = get_game_state(game_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/list", response_model=GamesListResponse)
async def list_games_endpoint(req: GamesListRequest):
    try:
        games = list_games(count=req.count)
        return {"games": games}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
