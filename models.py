from pydantic import BaseModel
from typing import Optional, List, Dict

class Settings(BaseModel):
    language: Optional[str] = None
    board_theme_id: Optional[int] = None
    piece_theme_id: Optional[int] = None
    toggle_bar: Optional[int] = None
    money_widget: Optional[int] = None
    user_color: Optional[int] = None
    premove: Optional[int] = None
    play_till: Optional[int] = None
    watch_only: Optional[int] = None
    ai_illegal: Optional[int] = None
    ai_allowed_offer: Optional[int] = None
    long_horizon_planning: Optional[int] = None

    board_theme_name: Optional[str] = None
    piece_theme_name: Optional[str] = None

class MoveRequest(BaseModel):
    from_square: str
    to_square: str

class MoveResponse(BaseModel):
    ai_from: Optional[str] = None
    ai_to: Optional[str] = None
    fen: str
    game_end: str


class GameCreateResponse(BaseModel):
    game_id: str
    fen: str
    user_color: str
    from_square: Optional[str] = None
    to_square: Optional[str] = None


class GameShowResponse(BaseModel):
    game_id: str
    fen: str
    orientation: str
    turn: str
    last_move: Optional[Dict[str, str]] = None
    status: str


class GamesListRequest(BaseModel):
    count: int = 10


class GamesListResponse(BaseModel):
    games: List[str]


class ThemeListResponse(BaseModel):
    themes: List[str]


class BoardThemeDetailResponse(BaseModel):
    name: str
    white_sq_color: str
    black_sq_color: str
    white_sq_blob: Optional[str] = None
    black_sq_blob: Optional[str] = None
    overrides: List[Dict[str, str]] = []


class PieceThemeDetailResponse(BaseModel):
    name: str
    pieces: Dict[str, str]
