import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # before any utils import

from dev_db.create_db import create_db
create_db()

# rest of your Flask/FastAPI app...
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 1. Import the middleware
from routers.settings import router as settings_router
from routers.games import router as games_router
from routers.themes import router as themes_router



app = FastAPI(title="Chess LLM Backend")

# 2. Define allowed origins
# You can use ["*"] to allow everything during development, 
# or be specific: ["http://localhost:3000", "http://127.0.0.1:3000"]
origins = ["*"]

# 3. Add the middleware to the app instance
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, OPTIONS, etc.
    allow_headers=["*"],  # Allows all headers (Content-Type, Authorization, etc.)
)



@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}


app.include_router(settings_router)
app.include_router(games_router)
app.include_router(themes_router)
app.include_router(use)

if __name__ == "__main__":
    import uvicorn
    # Change "localhost" to "0.0.0.0" if you want to access this 
    # from a physical phone on the same Wi-Fi network.
    uvicorn.run(app, host="0.0.0.0", port=8010)