import chess
from reconchess.utilities import without_opponent_pieces, is_illegal_castle

def generate_all_possible_next_states(fen):
    """
    Takes a FEN string and returns all possible next states in alphabetical order.
    """
    board = chess.Board(fen)
    states = set()
    
    # Handle null move
    null_board = board.copy()
    null_board.push(chess.Move.null())
    states.add(null_board.fen())
    
    # Handle pseudo-legal moves
    for move in board.pseudo_legal_moves:
        new_board = board.copy()
        new_board.push(move)
        states.add(new_board.fen())
    
    # Handle RBC-specific castling moves
    for move in without_opponent_pieces(board).generate_castling_moves():
        if not is_illegal_castle(board, move):
            new_board = board.copy()
            try:
                new_board.push(move)
                states.add(new_board.fen())
            except chess.IllegalMoveError:
                # Skip if move is somehow illegal
                continue
    
    return sorted(list(states))

if __name__ == "__main__":
    fen = input().strip()
    for state in generate_all_possible_next_states(fen):
        print(state)