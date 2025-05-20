import chess
import chess.engine

def capture_king_if_possible(board):
    for move in board.legal_moves:
        temp_board = board.copy()
        temp_board.push(move)
        # Check if opponent king is gone
        if not any(piece.piece_type == chess.KING and piece.color != board.turn
                   for piece in temp_board.piece_map().values()):
            return move
    return None

if __name__ == "__main__":
    fen = input().strip()
    board = chess.Board(fen)

    # First try capturing the king
    move = capture_king_if_possible(board)

    if move is None:
        #engine = chess.engine.SimpleEngine.popen_uci('./stockfish', setpgrp=True)
        engine = chess.engine.SimpleEngine.popen_uci('/opt/stockfish/stockfish', setpgrp=True)
        result = engine.play(board, chess.engine.Limit(time=0.5))
        move = result.move
        engine.quit()

    print(move.uci())
