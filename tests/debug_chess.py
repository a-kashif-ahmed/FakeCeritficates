import chess

# Test the chess library directly
def test_chess_move():
    # Starting position
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    board = chess.Board(fen)

    print("Starting FEN:", board.fen())
    print("Board:")
    print(board)

    # Try the move e2e4
    uci_move = "e2e4"
    print(f"Trying move: {uci_move}")

    try:
        board.push_uci(uci_move)
        print("Move successful!")
        print("New FEN:", board.fen())
        print("New board:")
        print(board)
        print("SAN:", board.san(chess.Move.from_uci(uci_move)))
    except Exception as e:
        print(f"Move failed: {e}")
        print("Is e2e4 a legal move?", chess.Move.from_uci("e2e4") in board.legal_moves)

        # Let's check what legal moves are available from e2
        print("Legal moves from e2:")
        for move in board.legal_moves:
            if move.from_square == chess.E2:
                print(f"  {move.uci()}: {move}")

if __name__ == "__main__":
    test_chess_move()