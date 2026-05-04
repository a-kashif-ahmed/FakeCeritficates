from fastapi import APIRouter, HTTPException
from models import ThemeListResponse, BoardThemeDetailResponse, PieceThemeDetailResponse
from utils.connect_db import get_connection
import base64

router = APIRouter(prefix="/api/v1/theme", tags=["themes"])

@router.get("/board/list", response_model=ThemeListResponse)
async def board_list():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM board_themes ORDER BY id")
    themes = [dict(row)['name'] for row in cursor.fetchall()]
    conn.close()
    return {"themes": themes}

@router.get("/board/{board_name}", response_model=BoardThemeDetailResponse)
async def board_detail(board_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM board_themes WHERE name = ?", (board_name,))
    theme_row = cursor.fetchone()
    if not theme_row:
        conn.close()
        raise HTTPException(404, "Board theme not found")
    theme = dict(theme_row)
    
    # Base64 blobs
    for field in ['white_sq_blob', 'black_sq_blob']:
        if theme[field]:
            theme[field] = base64.b64encode(theme[field]).decode('utf-8')
    
    # Overrides
    cursor.execute("""
        SELECT square, blob FROM board_theme_overrides 
        WHERE board_theme_id = ? 
        ORDER BY id
    """, (theme['id'],))
    overrides = []
    for row in cursor.fetchall():
        ov = dict(row)
        if ov['blob']:
            ov['blob'] = base64.b64encode(ov['blob']).decode('utf-8')
        overrides.append(ov)
    theme['overrides'] = overrides
    
    conn.close()
    return theme

@router.get("/piece/list", response_model=ThemeListResponse)
async def piece_list():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM piece_themes ORDER BY id")
    themes = [dict(row)['name'] for row in cursor.fetchall()]
    conn.close()
    return {"themes": themes}

@router.get("/piece/{piece_name}", response_model=PieceThemeDetailResponse)
async def piece_detail(piece_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM piece_themes WHERE name = ?", (piece_name,))
    theme_row = cursor.fetchone()
    if not theme_row:
        conn.close()
        raise HTTPException(404, "Piece theme not found")
    theme = dict(theme_row)
    
    # Base64 all piece blobs
    piece_fields = ['w_pawn', 'w_rook', 'w_knight', 'w_bishop', 'w_queen', 'w_king',
                    'b_pawn', 'b_rook', 'b_knight', 'b_bishop', 'b_queen', 'b_king']
    pieces = {}
    for field in piece_fields:
        if theme[field]:
            pieces[field] = base64.b64encode(theme[field]).decode('utf-8')
        else:
            pieces[field] = ""
    theme['pieces'] = pieces
    theme['name'] = piece_name
    
    conn.close()
    return theme
