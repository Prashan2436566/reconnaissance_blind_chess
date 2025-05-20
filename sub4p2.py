# next_state_with_sensing.py

import chess

def parse_window(window_str):
    observations = {}
    for entry in window_str.split(';'):
        if entry:
            square, piece = entry.split(':')
            observations[square] = piece
    return observations

def filter_states_by_sensing(fen_list, sensing_window):
    observations = parse_window(sensing_window)
    consistent_states = []

    for fen in fen_list:
        board = chess.Board(fen)
        is_consistent = True
        for square, expected_piece in observations.items():
            actual_piece = board.piece_at(chess.parse_square(square))
            actual_symbol = actual_piece.symbol() if actual_piece else '?'
            if actual_symbol != expected_piece:
                is_consistent = False
                break
        if is_consistent:
            consistent_states.append(fen)

    return sorted(consistent_states)

if __name__ == "__main__":
    n = int(input().strip())
    fen_list = [input().strip() for _ in range(n)]
    window = input().strip()
    for fen in filter_states_by_sensing(fen_list, window):
        print(fen)
