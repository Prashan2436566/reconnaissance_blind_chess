# next_move_prediction.py

import chess
from reconchess.utilities import without_opponent_pieces, is_illegal_castle

def generate_all_possible_moves(fen):
    board = chess.Board(fen)
    moves = set()

    for move in board.pseudo_legal_moves:
        moves.add(move.uci())

    moves.add("0000")

    for move in without_opponent_pieces(board).generate_castling_moves():
        if not is_illegal_castle(board, move):
            moves.add(move.uci())

    return sorted(moves)

if __name__ == "__main__":
    fen = input().strip()
    for move in generate_all_possible_moves(fen):
        print(move)
