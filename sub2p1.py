import chess
import reconchess

def execute_move(fen, move_uci):
    board = chess.Board(fen)
    move = chess.Move.from_uci(move_uci)

    if move in board.legal_moves:
        board.push(move)
        print(board.fen())
    else:
        print("Illegal MAte!")

if __name__ == "__main__":
    #inpu
    fen_input = input().strip()
    move_input = input().strip()

    execute_move(fen_input, move_input)
