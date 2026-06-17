from typing import Optional, List
import requests
import json

def create_ai_prompt(fen: str, history: List[str]) -> str:
    """Generate LLM prompt for AI move generation."""
    # Limit history to last 20 moves for context
    if history:
        history_str = " ".join(history[-20:])
    else:
        history_str = "No history"
    
    prompt_parts = [
        "You are a chess AI.",
        f"Current board FEN: {fen}",
        f"Recent move history (SAN): {history_str}",
        'Respond ONLY with valid JSON.',
        'Normal move: {"from": "e2", "to": "e4", "promote": null}',
        'Kingside castling: {"castling": "O-O"}',
        'Queenside castling: {"castling": "O-O-O"}',
        'En passant: {"from": "e5E", "to": "d6", "promote": null} (append capital E to from square)',
        '"from"/"to": algebraic squares a-h1-8.',
        '"promote": "q"/"r"/"b"/"n" or null.',
        "Choose best move for your turn (use special formats for castling/en passant).",
        "No other text."
    ]
    return '\n'.join(prompt_parts)

def parse_llm_response(content: str) -> Optional[dict]:
    """Parse LLM response to extract move dict."""
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            if 'castling' in data:
                return data  # {'castling': 'O-O' or 'O-O-O'}
            if 'from' in data and 'to' in data:
                move_dict = {
                    'from': data['from'],
                    'to': data['to'],
                    'promote': data.get('promote')
                }
                if move_dict['from'].endswith('E'):
                    move_dict['from'] = move_dict['from'][:-1]
                    move_dict['is_enpassant'] = True
                return move_dict
        return None
    except json.JSONDecodeError:
        # Fallback regex for normal moves
        import re
        match = re.search(r'"from"\s*:\s*"([a-h][1-8E]?) "', content, re.I)
        if match:
            from_sq = match.group(1).lower()
            is_enpassant = from_sq.endswith('e')
            if is_enpassant:
                from_sq = from_sq[:-1]
            match_to = re.search(r'"to"\s*:\s*"([a-h][1-8])"', content, re.I)
            if match_to:
                return {'from': from_sq, 'to': match_to.group(1).lower(), 'promote': None, 'is_enpassant': is_enpassant}
        return None


def call_ai_api(model_name: str, endpoint: str, api_key: str, prompt: str) -> Optional[dict]:
    """Call external AI API and return parsed move dict."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    response = requests.post(endpoint, headers=headers, json=payload)
    if response.status_code == 200:
        try:
            content = response.json()['choices'][0]['message']['content']
            return parse_llm_response(content)
        except Exception:
            return None
    return None

def call_coach_api(model_name: str, endpoint: str, api_key: str, prompt: str):

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.5
    }

    response = requests.post(
        endpoint,
        headers=headers,
        json=payload
    )

    if response.status_code != 200:
        return None

    try:
        return response.json()["choices"][0]["message"]["content"]

    except Exception:
        return None