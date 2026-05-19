from fastapi import APIRouter
from models import Settings, LLMDetails
from utils.settings import get_settings, upsert_settings
from config import USER_ID

router = APIRouter(prefix="/api/v1", tags=["settings"])

@router.get("/settings")
async def get_all_settings():
    return get_settings(USER_ID)

@router.post("/settings")
async def update_settings(settings: Settings):
    from utils.connect_db import get_connection
    data = settings.dict(exclude_unset=True)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    ui_data = {k: v for k, v in data.items() if k in ['language', 'board_theme_id', 'piece_theme_id', 'toggle_bar', 'money_widget']}
    game_data = {k: v for k, v in data.items() if k in ['user_color', 'premove', 'play_till', 'watch_only']}
    ai_data = {k: v for k, v in data.items() if k in ['ai_illegal', 'ai_allowed_offer', 'long_horizon_planning']}

    # Theme name lookup for UI
    if 'board_theme_name' in data:
        cursor.execute("SELECT id FROM board_themes WHERE name = ?", (data['board_theme_name'],))
        row = cursor.fetchone()
        if row:
            ui_data['board_theme_id'] = row['id']
    if 'piece_theme_name' in data:
        cursor.execute("SELECT id FROM piece_themes WHERE name = ?", (data['piece_theme_name'],))
        row = cursor.fetchone()
        if row:
            ui_data['piece_theme_id'] = row['id']

    conn.close()
    upsert_settings(USER_ID, "ui_settings", ui_data)
    upsert_settings(USER_ID, "game_settings", game_data)
    upsert_settings(USER_ID, "ai_settings", ai_data)
    return {"status": "updated"}

@router.post("/providers")
async def update_llm(llmDetails:LLMDetails):

    
    return{"status" : "hitted", "llm_details":llmDetails}



