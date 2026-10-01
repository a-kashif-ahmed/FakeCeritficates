from fastapi import APIRouter, HTTPException
from models import LevelsListResponse, LevelStartResponse, LevelMoveRequest, LevelMoveResponse
from utils.level_service import get_levels_overview, start_level, submit_level_move

router = APIRouter(prefix="/api/v1/levels", tags=["levels"])


@router.get("/", response_model=LevelsListResponse)
async def list_levels_endpoint():
    try:
        levels = get_levels_overview()
        return {"levels": levels}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{level_number}/start", response_model=LevelStartResponse)
async def start_level_endpoint(level_number: int):
    try:
        result = start_level(level_number)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/move", response_model=LevelMoveResponse)
async def submit_level_move_endpoint(move_req: LevelMoveRequest):
    try:
        result = submit_level_move(
            move_req.session_id,
            move_req.from_square,
            move_req.to_square,
            promotion=move_req.promotion,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
