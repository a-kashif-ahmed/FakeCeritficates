from fastapi import APIRouter, HTTPException

from models import (
    GuidedHintResponse,
    GuidedMoveRequest,
    GuidedMoveResponse,
    GuidedShowResponse,
    GuidedStartRequest,
    GuidedStartResponse,
    GuidedSummaryResponse,
)
from utils.guided_service import (
    get_guided_state,
    get_hint,
    get_summary,
    start_guided_game,
    submit_guided_move,
)

router = APIRouter(prefix="/api/v1/guided-games", tags=["guided games"])


@router.post("/", response_model=GuidedStartResponse)
async def start_guided_game_endpoint(req: GuidedStartRequest):
    try:
        return start_guided_game(difficulty=req.difficulty)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/move", response_model=GuidedMoveResponse)
async def guided_move_endpoint(session_id: str, req: GuidedMoveRequest):
    try:
        return submit_guided_move(
            session_id,
            req.from_square,
            req.to_square,
            promotion=req.promotion,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/show", response_model=GuidedShowResponse)
async def show_guided_game_endpoint(session_id: str):
    try:
        return get_guided_state(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/hint", response_model=GuidedHintResponse)
async def hint_endpoint(session_id: str):
    try:
        return get_hint(session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{session_id}/summary", response_model=GuidedSummaryResponse)
async def summary_endpoint(session_id: str):
    try:
        return get_summary(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
