AI Coder Brief – Chess LLM Project (Simplified)
1. Project Overview

We are building a chess platform with these key features:

Users play against AI (or watch AI vs AI).

AI can make illegal moves; the backend stores these moves and updates FEN.

Frontend rendering: only cares about which squares were moved (from/to) and the resulting FEN.

Settings are merged into a single endpoint for simplicity.

Each AI move is generated via an LLM request to the AI provider stored in the database (ai_players → external_apis).

2. Move Endpoint
Endpoint
POST /api/v1/games/{game_id}/move

User Move Handling

Frontend sends user move (SAN or from/to squares).

Backend:

Updates moves table (ply, moved_by, fen, san).

Takes a snapshot of game settings (game_settings_snapshot) if needed.

Backend triggers AI move generation (see AI section).

Returns JSON including:

User move

AI move (from/to squares + FEN)

Updated board FEN

Request Example
{
    "from": "b2",
    "to": "b3",
    "fen": "rnbqkbnr/pppppppp/8/8/7P/8/PPPPPPP/RNBQKBNR w KQkq - 0 2"
}

Response Example
{
    "from": "h3",
    "to": "h7",
    "fen": "rnbqkbnr/pppppppp/8/8/7P/8/PPPPPPP1/RNBQKBNR w KQkq - 0 2"
    "game_end": "no"
}

if backend response is 
{
    "game_end": "yes" #this one depends on setting, whether user want game to end at checkmate or king taken
} user is the winner

otherwise continue

3. AI Integration Workflow

After user move is processed, backend identifies the AI player assigned to the current role (game_ai_assignment).

Backend retrieves the API provider for this AI (ai_players → external_apis).

Backend generates LLM prompt containing:

Current FEN

Move history (if needed)

Game settings snapshot

Backend sends prompt to the AI API.

Receives AI move in SAN or from/to squares.

Stores AI move in moves table and optionally in ai_plans if long_horizon_planning is enabled.

Returns AI move to frontend with from/to + updated FEN.

Notes:

AI moves may be illegal; no validation is needed.

Frontend does not care about legality, only about highlighting squares and updating the board.

4. Settings Endpoint
Endpoint
GET /api/v1/settings → Fetch all settings
POST /api/v1/settings → Update any settings


Returns merged settings:

UI settings (language, board_theme, etc.)

Game settings (user_color, play_till, watch_only)

AI settings (ai_illegal, long_horizon_planning)

Single endpoint handles all reads/writes for simplicity.

5. Tables AI Coder Needs

games → current game info

moves → store all moves (user + AI)

game_ai_assignment → which AI is playing which side

ai_players → AI model info

external_apis → API provider credentials and endpoint

6. Data Flow Diagram (Text Version)
[Frontend] --(user move SAN/from-to)--> [Backend POST /move] 
       Backend:
         -> stores user move in moves table
         -> retrieves AI player & API info
         -> creates LLM prompt
         -> calls external AI API
         -> stores AI move in moves table
         -> returns user + AI move (from/to + FEN) --> Frontend

7. What to Code

Move endpoint:

Store user move

Trigger AI request

Store AI move

Return moves + FEN + squares to frontend

AI move generator:

Format prompt with current FEN + move history

Call external API for assigned AI player

Return move in SAN or from/to + updated FEN

Settings API:

Fetch and update all user settings in one endpoint