import reconchess
import chess

def print_ascii_board(fen):
    board = chess.Board(fen=fen)
    for rank in range(8, 0, -1):
        row = ""
        for file in range(8):
            square = chess.square(file, rank - 1)
            piece = board.piece_at(square)
            row += (piece.symbol() if piece else '.') + ' '
        print(row.strip())

if __name__ == "__main__":
    #input
    fen_input = input().strip()
    print_ascii_board(fen_input)
