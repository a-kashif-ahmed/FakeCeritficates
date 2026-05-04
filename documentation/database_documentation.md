# Database Schema Documentation (Normalized, Full Version)

## users Table
- **id** (INTEGER): PRIMARY KEY – Unique identifier for each user.
- **username** (TEXT): UNIQUE, NOT NULL – User’s login or display name.
- **elo** (INTEGER): BETWEEN 100 AND 3600 – Default=800, user rating for AI matchmaking.

## ui_settings Table
- **user_id** (INTEGER): PRIMARY KEY, FOREIGN KEY → users(id)
- **language** (TEXT): NOT NULL – Default=en, system language.
- **board_theme_id** (INTEGER): FOREIGN KEY → board_themes(id) – Current board theme.
- **piece_theme_id** (INTEGER): FOREIGN KEY → piece_themes(id) – Current piece theme.
- **toggle_bar** (INTEGER): 0 or 1 – Default=0, show/hide info bar.
- **money_widget** (INTEGER): 0 or 1 – Default=1, enable/disable money widget.

## game_settings Table
- **user_id** (INTEGER): PRIMARY KEY, FOREIGN KEY → users(id)
- **user_color** (INTEGER): 0,1,2 – Default=2, 0=white,1=black,2=random.
- **premove** (INTEGER): 0 or 1 – Default=1, enable/disable premove.
- **play_till** (INTEGER): 0 or 1 – Default=1, 0=capture king,1=checkmate.
- **watch_only** (INTEGER): 0 or 1 – Default=0, 0=human vs AI, 1=AI vs AI.

## ai_settings Table
- **user_id** (INTEGER): PRIMARY KEY, FOREIGN KEY → users(id)
- **ai_illegal** (INTEGER): 0 or 1 – Default=1, AI allowed illegal moves.
- **ai_allowed_offer** (INTEGER): 0,1,2 – Default=1, 0=allowed,1=allowed with user approval,2=disallowed.
- **long_horizon_planning** (INTEGER): 0-10 – Default=0, number of previous moves AI can plan ahead.

## board_themes Table
- **id** (INTEGER): PRIMARY KEY – Unique board theme id.
- **name** (TEXT): UNIQUE, NOT NULL – Board theme name.
- **white_sq_color** (TEXT): NOT NULL – Base color for white squares (hex or rgb)
- **black_sq_color** (TEXT): NOT NULL – Base color for black squares (hex or rgb)
- **white_sq_blob** (BLOB): NULLABLE – Optional asset to replace all white squares.
- **black_sq_blob** (BLOB): NULLABLE – Optional asset to replace all black squares.

## board_theme_overrides Table
- **id** (INTEGER): PRIMARY KEY – Unique override id
- **board_theme_id** (INTEGER): FOREIGN KEY → board_themes(id) – Links override to a theme
- **square** (TEXT): NOT NULL – Specific square to replace (e.g., "e4")
- **blob** (BLOB): NOT NULL – Custom asset for this square (e.g., Spider-Man PNG)

## piece_themes Table
- **id** (INTEGER): PRIMARY KEY
- **name** (TEXT): UNIQUE, NOT NULL – Piece theme name.
- **w_pawn** (BLOB): NOT NULL – White pawn asset.
- **w_rook** (BLOB): NOT NULL – White rook asset.
- **w_knight** (BLOB): NOT NULL – White knight asset.
- **w_bishop** (BLOB): NOT NULL – White bishop asset.
- **w_queen** (BLOB): NOT NULL – White queen asset.
- **w_king** (BLOB): NOT NULL – White king asset.
- **b_pawn** (BLOB): NOT NULL – Black pawn asset.
- **b_rook** (BLOB): NOT NULL – Black rook asset.
- **b_knight** (BLOB): NOT NULL – Black knight asset.
- **b_bishop** (BLOB): NOT NULL – Black bishop asset.
- **b_queen** (BLOB): NOT NULL – Black queen asset.
- **b_king** (BLOB): NOT NULL – Black king asset.

## games Table
- **id** (TEXT): PRIMARY KEY – Game unique id.
- **user_id** (INTEGER): FOREIGN KEY → users(id)
- **status** (TEXT): NOT NULL – active/finished
- **created_at** (TIMESTAMP): NOT NULL
- **ended_at** (TIMESTAMP): Nullable
- **result** (TEXT): Nullable – 1-0,0-1,1/2-1/2

## game_settings_snapshot Table
- **game_id** (TEXT): PRIMARY KEY, FOREIGN KEY → games(id)
- **user_color** (INTEGER): 0,1,2 – Captured at game start
- **watch_only** (INTEGER): 0 or 1 – 0=human vs AI, 1=AI vs AI
- **play_till** (INTEGER): 0 or 1 – Captured at game start
- **ai_illegal** (INTEGER): 0 or 1 – Captured at game start

## moves Table
- **id** (INTEGER): PRIMARY KEY
- **game_id** (TEXT): FOREIGN KEY → games(id)
- **ply** (INTEGER): NOT NULL – Halfmove number
- **moved_by** (INTEGER): 0 or 1 – 0=white,1=black
- **fen** (TEXT): NOT NULL – FEN after this move
- **san** (TEXT): Optional – SAN notation
- **created_at** (TIMESTAMP): NOT NULL

## ai_plans Table
- **game_id** (TEXT): FOREIGN KEY → games(id)
- **ply** (INTEGER): NOT NULL
- **plan_json** (TEXT): NOT NULL – Serialized AI plan (if long_horizon_planning enabled)

## external_apis Table
- **id** (INTEGER): PRIMARY KEY
- **service_name** (TEXT): Optional – API provider
- **endpoint** (TEXT): Optional – API endpoint
- **api_key** (TEXT): Optional
- **validated** (INTEGER): 0 or 1 – API validated

## ai_players Table
- **id** (INTEGER): PRIMARY KEY
- **model_name** (TEXT): Optional – Model name
- **provider_id** (INTEGER): FOREIGN KEY → external_apis(id)

## game_ai_assignment Table
- **game_id** (TEXT): FOREIGN KEY → games(id)
- **role** (TEXT): 'model_a','model_b' – AI role in game
- **ai_player_id** (INTEGER): FOREIGN KEY → ai_players(id)

## usage_sessions Table
- **id** (INTEGER): PRIMARY KEY
- **platform** (TEXT): NOT NULL – e.g., OpenAI, Ollama
- **used_by** (TEXT): NOT NULL – purpose
- **game_id** (TEXT): FOREIGN KEY → games(id)
- **started_at** (TIMESTAMP): NOT NULL
- **ended_at** (TIMESTAMP): Nullable
- **status** (TEXT): waiting-platform, completed, failed-api, failed-response

## api_calls Table
- **id** (INTEGER): PRIMARY KEY
- **session_id** (INTEGER): FOREIGN KEY → usage_sessions(id)
- **model** (TEXT): NOT NULL – Model used
- **input_tokens** (INTEGER): NOT NULL
- **vision_tokens** (INTEGER): NOT NULL
- **output_tokens** (INTEGER): NOT NULL
- **duration** (REAL): NOT NULL – seconds
- **cost** (REAL): NOT NULL
- **created_at** (TIMESTAMP): NOT NULL

## conversations Table
- **id** (INTEGER): PRIMARY KEY – Unique conversation id
- **session_id** (INTEGER): FOREIGN KEY → usage_sessions(id) – Allows multiple conversations per session
- **created_at** (TIMESTAMP): NOT NULL
- **dialogue_json** (TEXT): NOT NULL – Serialized conversation history

# Notes
- Foreign keys must be enabled in SQLite: `PRAGMA foreign_keys = ON;`
- Timestamps can be stored as INTEGER (Unix epoch)
- JSON fields are stored as TEXT but queryable with SQLite json1 functions
- BLOBs store piece and board assets; can also store file paths for large assets
- Totals like cost, tokens, and current positions are **computed**, not stored, keeping the DB normalized
- `watch_only=0` → human vs AI, `watch_only=1` → AI vs AI
- `game_ai_assignment` determines which AI is playing, if any, and allows human vs AI or AI vs AI
- Board theme BLOB hierarchy preserved:
  1. Base colors (`white_sq_color` / `black_sq_color`)
  2. Base blobs (`white_sq_blob` / `black_sq_blob`) → overrides color
  3. `board_theme_overrides` → specific square BLOBs override everything else
- Conversations can have multiple entries per usage session to track AI thinking or chat per move
