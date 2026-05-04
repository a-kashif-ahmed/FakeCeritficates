import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app import app
import chess
import json

client = TestClient(app)
current_game_id = None
game_ids = []
settings_cache = {}

def print_request(method: str, url: str, payload: dict | None = None):
    print("\n" + "="*60)
    print(f"🔵 REQUEST: {method.upper()} {url}")
    if payload:
        print("Payload:")
        print(json.dumps(payload, indent=2))
    print("="*60)

def print_response(response):
    print("\n" + "="*60)
    print(f"🟢 RESPONSE: Status {response.status_code}")
    try:
        resp_json = response.json()
        print(json.dumps(resp_json, indent=2))
        return resp_json
    except:
        print(response.text)
        return None
    print("="*60)

def print_board(fen: str, orientation='white'):
    board = chess.Board(fen)
    if orientation == 'black':
        board = board.mirror()
    print("\n📋 CHESS BOARD:")
    print(board.unicode())
    print()

def print_game_end(game_end: str):
    messages = {
        "no": "",
        "user_checkmate": "💥 USER CHECKMATE - You lost!",
        "ai_checkmate": "🏆 AI CHECKMATE - AI lost! You win!",
        "stalemate": "🤝 STALEMATE - Draw!",
        "draw_by_repetition": "🔄 DRAW by repetition!",
        "user_kingdead": "👑 USER KING DEAD - You lost!",
        "ai_kingdead": "🤴 AI KING DEAD - You win!"
    }
    print(messages.get(game_end, f"Game end: {game_end}"))

def get_settings():
    print_request("GET", "/api/v1/settings")
    resp = client.get("/api/v1/settings")
    data = print_response(resp)
    if data:
        settings_cache.update(data)
        print("📝 Current settings loaded.")
    return data

def update_settings():
    print("📝 Update settings (leave blank to skip):")
    changes = {}
    for key in ['language', 'toggle_bar', 'money_widget', 'user_color', 'premove', 'play_till', 'watch_only', 'ai_illegal', 'ai_allowed_offer', 'board_theme_name', 'piece_theme_name']:
        val = input(f"{key}: ").strip()
        if val:
            changes[key] = val if key in ['language', 'board_theme_name', 'piece_theme_name'] else int(val)
    if changes:
        print_request("POST", "/api/v1/settings", changes)
        resp = client.post("/api/v1/settings", json=changes)
        print_response(resp)
        get_settings()  # Refresh cache
    else:
        print("No changes.")

def list_games():
    count = input("Number of games (default 10): ").strip() or "10"
    payload = {"count": int(count)}
    print_request("POST", "/api/v1/games/list", payload)
    resp = client.post("/api/v1/games/list", json=payload)
    data = print_response(resp)
    if data:
        game_ids[:] = data['games']
        print(f"📋 Recent games: {game_ids}")

def show_game():
    gid = input("Game ID: ").strip() or current_game_id
    if not gid:
        print("No game ID.")
        return
    print_request("GET", f"/api/v1/games/{gid}/show")
    resp = client.get(f"/api/v1/games/{gid}/show")
    data = print_response(resp)
    if data:
        print_board(data['fen'], data['orientation'])
        print(f"Turn: {data['turn']}, Status: {data['status']}")
        if data['last_move']:
            print(f"Last move: {data['last_move']['from']}-{data['last_move']['to']}")

def create_game():
    global current_game_id
    print_request("POST", "/api/v1/games/")
    resp = client.post("/api/v1/games/")
    data = print_response(resp)
    if data:
        current_game_id = data['game_id']
        game_ids.append(current_game_id)
        print_board(data['fen'])
        print(f"🎮 New game: {current_game_id}, You are {data['user_color']}")
        if data.get('from_square') and data.get('to_square'):
            print(f"Initial AI move: {data['from_square']}-{data['to_square']}")

def make_move(gid=None):
    gid = gid or current_game_id or input("Game ID: ").strip()
    if not gid:
        print("No game ID.")
        return
    while True:
        move_input = input("Move (e.g. e2e4) or 'back': ").strip().lower()
        if move_input == 'back':
            break
        if len(move_input) != 4:
            print("Invalid: use e2e4")
            continue
        from_sq, to_sq = move_input[:2], move_input[2:]
        payload = {"from_square": from_sq, "to_square": to_sq}
        print_request("POST", f"/api/v1/games/{gid}/move", payload)
        resp = client.post(f"/api/v1/games/{gid}/move", json=payload)
        data = print_response(resp)
        if data:
            print_board(data['fen'])
            if data.get('ai_from') and data['ai_to']:
                print(f"🤖 AI: {data['ai_from']}-{data['ai_to']}")
            print_game_end(data['game_end'])
            if data['game_end'] != "no":
                break

def watch_game():
    gid = current_game_id or input("Game ID: ").strip()
    if not gid:
        return
    print("👀 Watch mode (AI vs AI or advance): press Enter to advance.")
    while True:
        input("Press Enter to advance...")
        make_move(gid)

def themes_menu():
    typ = input("board or piece? ").strip().lower()
    if typ in ['board', 'b']:
        print_request("GET", "/api/v1/theme/board/list")
        resp = client.get("/api/v1/theme/board/list")
        data = print_response(resp)
        if data:
            name = input("Board theme name: ").strip()
            if name:
                print_request("GET", f"/api/v1/theme/board/{name}")
                resp = client.get(f"/api/v1/theme/board/{name}")
                print_response(resp)
    elif typ in ['piece', 'p']:
        print_request("GET", "/api/v1/theme/piece/list")
        resp = client.get("/api/v1/theme/piece/list")
        data = print_response(resp)
        if data:
            name = input("Piece theme name: ").strip()
            if name:
                print_request("GET", f"/api/v1/theme/piece/{name}")
                resp = client.get(f"/api/v1/theme/piece/{name}")
                print_response(resp)

def test_scenarios():
    print("🧪 Test scenarios:")
    print("1. Watch only AI vs AI")
    print("2. Play till king capture")
    print("3. Random color")
    choice = input("Choose (or skip): ").strip()
    if choice == '1':
        update_settings()  # Set watch_only=1
        create_game()
        watch_game()
    # Add more...

def main_menu():
    while True:
        print("\n🏠 MAIN MENU:")
        print("1. Get Settings")
        print("2. Update Settings")
        print("3. List Games")
        print("4. Create Game")
        print("5. Show Game State")
        print("6. Make Move")
        print("7. Watch Game (AI vs AI)")
        print("8. Themes")
        print("9. Test Scenarios")
        print("0. Quit")
        choice = input("Choose: ").strip()
        if choice == '0':
            break
        elif choice == '1':
            get_settings()
        elif choice == '2':
            update_settings()
        elif choice == '3':
            list_games()
        elif choice == '4':
            create_game()
        elif choice == '5':
            show_game()
        elif choice == '6':
            make_move()
        elif choice == '7':
            watch_game()
        elif choice == '8':
            themes_menu()
        elif choice == '9':
            test_scenarios()
        else:
            print("Invalid.")

if __name__ == "__main__":
    print("🚀 Chess Backend Tester CLI")
    main_menu()
