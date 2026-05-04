# Chess LLM Backend API Documentation

This document describes the **public backend API** for the Chess LLM application.

It is intended **exclusively for frontend developers**. Internal implementation details (database schema, internal tables, and utilities) are intentionally **abstracted away**.

The API is stable, JSON‑based, and exposed via FastAPI.

---

## Base Information

* **Base URL:** `http://localhost:8000/api/v1`
* **Protocol:** HTTP / JSON
* **Authentication:** ❌ None
* **User Model:**

  * All requests implicitly operate on a single user session
  * No user IDs or auth tokens are required or accepted

---

## Settings API
## Settings Reference

Below is the complete list of supported settings, their possible values, defaults, and frontend-facing meaning.

---

### UI Settings

#### `language`

* **Type:** string
* **Default:** `"en"`
* **Description:**

  * Controls the application language.
  * Intended for UI text, labels, and messages.


#### `toggle_bar`

* **Type:** `0 | 1`
* **Default:** `0`
* **Description:**

  * Toggles the visibility of information bar. (who's winning)
  * `0` → Hidden
  * `1` → Visible

---

#### `money_widget`

* **Type:** `0 | 1`
* **Default:** `1`
* **Description:**

  * Enables or disables the money / cost tracking widget.
  * `0` → Disabled
  * `1` → Enabled

---

### Game Settings

#### `user_color`

* **Type:** `0 | 1 | 2`
* **Default:** `2`
* **Description:**

  * Determines which side the human player prefer.
  * `0` → White
  * `1` → Black
  * `2` → Random (decided at game start)

---

#### `premove`

* **Type:** `0 | 1`
* **Default:** `1`
* **Description:**

  * Enables premoves on the client.
  * When enabled, the frontend may allow users to queue a move before their turn.
  * The backend always validates the move before applying it.

---

#### `play_till`

* **Type:** `0 | 1`
* **Default:** `1`
* **Description:**

  * Defines the game-ending condition.
  * `0` → Game ends when the king is captured
  * `1` → Standard chess rules (checkmate)

---

#### `watch_only`

* **Type:** `0 | 1`
* **Default:** `0`
* **Description:**

  * Controls whether the user plays or only observes.
  * `0` → Human vs AI
  * `1` → AI vs AI (spectator mode)

---

### AI Settings

#### `ai_illegal`

* **Type:** `0 | 1`
* **Default:** `1`
* **Description:**

  * Determines whether the AI is allowed to suggest illegal moves.
  * `0` → AI restricted to legal chess moves
  * `1` → AI may propose illegal or experimental moves

---

#### `ai_allowed_offer`

* **Type:** `0 | 1 | 2`
* **Default:** `1`
* **Description:**

  * Controls whether the AI can offer non-move interactions (draws, resignations, suggestions).
  * `0` → Allowed automatically
  * `1` → Allowed, but requires user approval
  * `2` → Disallowed entirely

---

#### `long_horizon_planning`

* **Type:** number (`0–10`)
* **Default:** `0`
* **Description:**

  * Enables AI planning across multiple future moves.
  * Higher values allow the AI to reason further ahead.
  * `0` disables multi-move planning entirely.

---

### Frontend Notes

* All settings are **optional** when updating
* Missing fields are never reset or cleared
* Some settings (game rules, AI behavior) are **snapshotted at game creation** and do not affect ongoing games

---

### POST `/settings`

Update one or more user settings.

Only the fields provided in the request body are updated. All other settings remain unchanged.

#### Request Body

Partial settings object:

```json
{
  "language": "en",
  "user_color": 0,
  "watch_only": 1,
  "ai_illegal": 0
}
```
Full object:
```json
{
  "language": "en",
  "board_theme_name": "stonic",
  "piece_theme_name": "airal",
  "toggle_bar": 0,
  "money_widget": 1,
  "user_color": 2,
  "premove": 1,
  "play_till": 1,
  "watch_only": 0,
  "ai_illegal": 1,
  "ai_allowed_offer": 1,
  "long_horizon_planning": 0
}
```

#### Response

**200 OK**

```json
{ "status": "updated" }
```

---

## Games API

The Games API is used to **create games** and **play moves**.

The frontend does not need to manage turns, AI logic, or rule validation — all of that is handled server‑side.

### POST `/games/`

Create a new game.

#### Behavior (Frontend‑Relevant)

* A new game is created and activated
* The backend decides player colors and AI participation based on settings
* The initial board position is returned

#### Response

**200 OK**

```json
{
  "game_id": "123e4567-e89b-12d3-a456-426614174000",
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "user_color": "white", 
  "from":"a2", #if user's black
  "to":"b3" #this is the ai's move
}
```

#### Frontend Usage

* Store `game_id` for all future move requests
* Use `fen` to initialize the chessboard

---

### POST `/games/{game_id}/move`

Submit a user move and receive the updated game state.

The backend:

* Validates the move
* Applies game rules
* Generates AI moves if required
* Detects game end conditions

#### Path Parameters

* `game_id` — Game identifier returned from game creation

#### Request Body

```json
{
  "from_square": "e2",
  "to_square": "e4"
}
```

---

#### Response

**200 OK**

```json
{
  "ai_from": "e7",
  "ai_to": "e5",
  "fen": "rnbqkbnr/ppppppp1/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
  "game_end": "no"
}
```

#### Response Fields

| Field      | Description                               |
| ---------- | ----------------------------------------- |
| `fen`      | Updated board position (always present)   |
| `ai_from`  | AI move start square (null if no AI move) |
| `ai_to`    | AI move end square (null if no AI move)   |
| `game_end` | `"no"` or a terminal game state           |

#### `game_end` Values

* `"no"` — Game continues
* if `"ai_from"` and `"ai_to"` provided — display that. 
* if `"user_checkmate"`,`"ai_checkmate"`,`"stalemate"`, `"draw_by_repetition"`,`"user_kingdead"`,`"ai_kingdead"`, display pop up window as the problem after if an AI move is displayed. 

---

#### Errors

* **404 Not Found** — Invalid or unknown `game_id`
* **400 Bad Request** — Illegal move or invalid input

---

### GET `/games/{game_id}/show`

Return the **current game state** without making a move.

#### Purpose
Used to:
- Restore game state on page reload
- Poll current board position
- Determine orientation and turn
- Inspect last move

#### Response

**200 OK**

```json
{
  "game_id": "123e4567-e89b-12d3-a456-426614174000",
  "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  "orientation": "white",
  "turn": "white",
  "last_move": {
    "from": "e2",
    "to": "e4"
  },
  "status": "active"
}
```

#### Fields

| Field | Description |
|------|-------------|
| `fen` | Current board position |
| `orientation` | Board orientation for frontend rendering (`white` / `black`) |
| `turn` | Side to move (`white` / `black`) |
| `last_move` | Most recent move played (null if none) |
| `status` | `active` or `finished` |

---

### POST `/games/list`

List previously created games for the current user session.

#### Request Body

```json
{
  "count": 10
}
```

#### Behavior
- Returns the most recent finished or active games
- Ordered by `created_at` descending
- Limited by `count`

#### Response

**200 OK**

```json
{
  "games": [
    "123e4567-e89b-12d3-a456-426614174000",
    "987e6543-e21b-98d3-a456-426614174999"
  ]
}
```

---

## Theme APIs

### GET `/theme/board/list`

List all available board themes.

#### Response

```json
{
  "themes": [
    "classic",
    "stonic",
    "marble",
    "neon"
  ]
}
```

### GET `/theme/board/{board_name}`

Return **board theme details**.

#### Response

```json
{
  "name": "stonic",
  "white_sq_color": "#f0f0f0",
  "black_sq_color": "#3a3a3a",
  "white_sq_blob": null,
  "black_sq_blob": null,
  "overrides": [
    {
      "square": "e4",
      "blob": "<base64-encoded-asset>"
    }
  ]
}
```

#### Notes
- If `*_blob` is present, it overrides square color rendering
- Square-level overrides always take precedence

---

### GET `/theme/piece/list`

List all available piece themes.

#### Response

```json
{
  "themes": [
    "classic",
    "airal",
    "minimal",
    "fantasy"
  ]
}
```

---

### GET `/theme/piece/{piece_name}`

Return **piece theme assets**.

#### Response

```json
{
  "name": "airal",
  "pieces": {
    "w_pawn": "<base64>",
    "w_rook": "<base64>",
    "w_knight": "<base64>",
    "w_bishop": "<base64>",
    "w_queen": "<base64>",
    "w_king": "<base64>",
    "b_pawn": "<base64>",
    "b_rook": "<base64>",
    "b_knight": "<base64>",
    "b_bishop": "<base64>",
    "b_queen": "<base64>",
    "b_king": "<base64>"
  }
}
```

#### Notes
- Assets are returned as BLOBs (typically base64-encoded)
- Frontend is responsible for caching and rendering

---
