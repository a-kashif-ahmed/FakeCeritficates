import chess
from typing import Optional, Tuple, Dict, Any

PROMOTION_PIECES = {
    'q': chess.QUEEN,
    'r': chess.ROOK,
    'b': chess.BISHOP,
    'n': chess.KNIGHT
}

def force_ai_move(board: chess.Board, ai_move: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Force apply AI move by manually moving the piece, ignoring chess rules.
    Supports normal, promotion, castling (O-O/O-O-O), en passant (fromE).
    Returns (success, ai_from, ai_to) for animation.
    """
    current_turn_white = board.turn == chess.WHITE
    
    # Castling
    if 'castling' in ai_move:
        castling = ai_move['castling'].upper()
        color_key = 'white' if current_turn_white else 'black'
        
        king_moves = {
            'O-O': {'white': ('e1', 'g1'), 'black': ('e8', 'g8')},
            'O-O-O': {'white': ('e1', 'c1'), 'black': ('e8', 'c8')}
        }
        rook_moves = {
            'O-O': {'white': ('h1', 'f1'), 'black': ('h8', 'f8')},
            'O-O-O': {'white': ('a1', 'd1'), 'black': ('a8', 'd8')}
        }
        
        if castling in king_moves:
            king_from_str, king_to_str = king_moves[castling][color_key]
            rook_from_str, rook_to_str = rook_moves[castling][color_key]
            
            # Force king move
            king_from = chess.parse_square(king_from_str)
            king_to = chess.parse_square(king_to_str)
            king_piece = board.piece_at(king_from)
            if king_piece and king_piece.piece_type == chess.KING:
                board.remove_piece_at(king_to)
                board.remove_piece_at(king_from)
                board.set_piece_at(king_to, king_piece)
            # Removed color check for fun castling
            
            # Force rook move
            rook_from = chess.parse_square(rook_from_str)
            rook_to = chess.parse_square(rook_to_str)
            rook_piece = board.piece_at(rook_from)
            if rook_piece and rook_piece.piece_type == chess.ROOK:
                board.remove_piece_at(rook_to)
                board.remove_piece_at(rook_from)
                board.set_piece_at(rook_to, rook_piece)
            # Removed color check for fun castling
            
            board.turn = not board.turn
            board.ep_square = None
            if board.turn == chess.WHITE:
                board.fullmove_number += 1
            
            return True, king_from_str, king_to_str
        
        return False, None, None
    
    # Normal / promotion / en passant
    try:
        from_sq_str = ai_move['from'].lower()
        to_sq_str = ai_move['to'].lower()
        from_sq = chess.parse_square(from_sq_str)
        to_sq = chess.parse_square(to_sq_str)
        
        piece = board.piece_at(from_sq)
        if piece is None:
            return False, None, None
        # Removed color check for ai_illegal=1 fun moves: allow moving any piece
        
        # En passant capture
        is_enpassant = ai_move.get('is_enpassant', False)
        if is_enpassant:
            skipped_file = chess.square_file(to_sq)
            skipped_rank = 3 if current_turn_white else 4  # rank 4 (index 3) for white, rank 5 (4) for black
            skipped_sq = chess.square(skipped_file, skipped_rank)
            board.remove_piece_at(skipped_sq)
        
        # Capture destination
        board.remove_piece_at(to_sq)
        
        # Remove origin
        board.remove_piece_at(from_sq)
        
        # Promotion
        new_piece = piece
        promote = ai_move.get('promote')
        if promote and piece.piece_type == chess.PAWN:
            prom_type = PROMOTION_PIECES.get(promote.lower())
            if prom_type:
                new_piece = chess.Piece(prom_type, piece.color)
        
        # Place
        board.set_piece_at(to_sq, new_piece)
        
        # Update board state
        board.turn = not board.turn
        board.ep_square = None
        if board.turn == chess.WHITE:
            board.fullmove_number += 1
        
        return True, from_sq_str, to_sq_str
        
    except (ValueError, KeyError):
        return False, None, None

def check_game_end(
    board: chess.Board, 
    settings: Dict[str, Any], 
    user_is_white: bool, 
    game_id: str, 
    cursor, 
    conn
) -> str:
    """
    Check if game ended based on settings.
    Updates games table if ended.
    user_is_white: True if user plays as white.
    """
    from datetime import datetime
    
    game_end = "no"
    
    # Check king captures first (always ends game)
    white_king_gone = board.king(chess.WHITE) is None
    black_king_gone = board.king(chess.BLACK) is None
    if white_king_gone or black_king_gone:
        loser_is_white = white_king_gone
        loser_is_user = loser_is_white == user_is_white
        game_end = "user_kingdead" if loser_is_user else "ai_kingdead"
        now = datetime.now().isoformat()
        cursor.execute("UPDATE games SET status = 'finished', ended_at = ? WHERE id = ?", (now, game_id))
        conn.commit()
        return game_end
    
    play_till = settings.get('play_till', 1)
    if play_till == 1 and board.is_game_over():
        loser_is_white = board.turn == chess.WHITE  # loser is the one to move
        loser_is_user = loser_is_white == user_is_white
        if board.is_checkmate():
            game_end = "user_checkmate" if loser_is_user else "ai_checkmate"
        elif board.is_stalemate() or board.is_insufficient_material():
            game_end = "stalemate"
        elif board.is_repetition():
            game_end = "draw_by_repetition"
        else:
            game_end = "draw"
        now = datetime.now().isoformat()
        cursor.execute("UPDATE games SET status = 'finished', ended_at = ? WHERE id = ?", (now, game_id))
        conn.commit()
        return game_end
    
    return "no"
