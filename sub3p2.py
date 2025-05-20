# next_state_with_capture.py

import chess

def generate_next_states_with_capture(fen, capture_square):
    board = chess.Board(fen)
    capture_index = chess.parse_square(capture_square)
    states = set()

    for move in board.pseudo_legal_moves:
        if move.to_square == capture_index and board.is_capture(move):
            new_board = board.copy()
            new_board.push(move)
            states.add(new_board.fen())

    return sorted(states)

if __name__ == "__main__":
    fen = input().strip()
    capture_square = input().strip()
    for state in generate_next_states_with_capture(fen, capture_square):
        print(state)
