import chess
import chess.engine
from collections import Counter

def select_most_common_move(fen_list):
    moves = []
    
    # Initialize engine once
    engine = chess.engine.SimpleEngine.popen_uci('/opt/stockfish/stockfish', setpgrp=True)
    #engine = chess.engine.SimpleEngine.popen_uci('./stockfish', setpgrp=True)
    try:
        for fen in fen_list:
            board = chess.Board(fen)
            
            # Quick check for king captures - much faster approach
            king_capture_made = False
            opponent_color = not board.turn
            
            # Get opponent's king position using board's built-in king_square method
            opponent_king_square = board.king(opponent_color)
            
            if opponent_king_square is not None:
                # Check if any of our pieces can attack the king
                attackers = board.attackers(board.turn, opponent_king_square)
                if attackers:
                    # Get the first attacker square
                    attacker_square = chess.square_name(chess.SQUARES[attackers.pop()])
                    king_square = chess.square_name(opponent_king_square)
                    king_capture_move = attacker_square + king_square
                    moves.append(king_capture_move)
                    king_capture_made = True
            
            if not king_capture_made:
                # Lower time limit to save time
                result = engine.play(board, chess.engine.Limit(time=0.1))
                moves.append(result.move.uci())
    
    except Exception as e:
        pass  # Continue with any moves we've collected
    
    finally:
        # Ensure engine is closed
        engine.quit()
    
    # Count moves and find most common
    if not moves:
        return "0000"  # Default move if something went wrong
        
    move_counter = Counter(moves)
    max_count = max(move_counter.values())
    most_common_moves = [move for move, count in move_counter.items() if count == max_count]
    
    # Return alphabetically first move among the most common
    return sorted(most_common_moves)[0]

if __name__ == "__main__":
    n = int(input().strip())
    fen_list = []
    
    for _ in range(n):
        fen_list.append(input().strip())
    
    move = select_most_common_move(fen_list)
    print(move)