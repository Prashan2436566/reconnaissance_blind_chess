import os
import platform
import random
import chess
import chess.engine
from reconchess import Player
from chess import square_name 
import collections
import numpy as np

class RandomSensing(Player):
    def __init__(self):
        self.possible_boards = set()
        self.color = None
        self.capture_square = None

        # Setup Stockfish path
        if platform.system() == 'Windows':
            stockfish_path = './stockfish.exe'
        elif platform.system() == 'Linux':
            stockfish_path = '/usr/bin/stockfish'
        elif platform.system() == 'Darwin':
            stockfish_path = './stockfish-macos'
        else:
            raise EnvironmentError("Unsupported OS for Stockfish")

        if not os.path.exists(stockfish_path):
            raise FileNotFoundError(f"Stockfish not found at: {stockfish_path}")

        self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
        print(f"[INIT] Stockfish engine loaded from {stockfish_path}")

    def handle_game_start(self, color, board, opponent_name):
        self.color = color
        self.possible_boards = {board.fen()}
        print(f"[START] Game started. Playing as {'White' if color else 'Black'} against {opponent_name}")
        print(f"[START] Initial board FEN: {board.fen()}")

    def handle_opponent_move_result(self, captured_my_piece, capture_square):
        self.capture_square = capture_square
        print(f"[OPPONENT MOVE] Captured my piece: {captured_my_piece}, Capture square: {capture_square}")
        
        if not self.possible_boards:
            print("[OPPONENT MOVE] No possible boards to update!")
            return
        
        new_possible_boards = set()
        
        for fen in self.possible_boards:
            board = chess.Board(fen)
            
            # Skip boards where it's not the opponent's turn
            if board.turn == self.color:
                continue
                
            # Generate all possible opponent moves
            for move in board.legal_moves:
                # Check if the move is consistent with the capture information
                move_captures = board.is_capture(move)
                
                # If opponent captured and the move is a capture to the right square
                if captured_my_piece and move_captures and move.to_square == capture_square:
                    new_board = board.copy()
                    new_board.push(move)
                    new_possible_boards.add(new_board.fen())
                    
                # If opponent didn't capture and the move is not a capture
                elif not captured_my_piece and not move_captures:
                    new_board = board.copy()
                    new_board.push(move)
                    new_possible_boards.add(new_board.fen())
                    
                # If opponent didn't capture but move is en passant to capture square
                elif not captured_my_piece and move.to_square == capture_square:
                    new_board = board.copy()
                    new_board.push(move)
                    new_possible_boards.add(new_board.fen())
        
        before_count = len(self.possible_boards)
        self.possible_boards = new_possible_boards
        after_count = len(self.possible_boards)
        
        print(f"[OPPONENT MOVE] Updated boards: {before_count} -> {after_count}")
        
        # If we've eliminated all possible boards, we're in trouble
        if after_count == 0:
            print("[OPPONENT MOVE] WARNING: All boards eliminated! Creating new possibilities.")
            self.possible_boards = {chess.Board().fen()}

    def choose_sense(self, sense_actions, move_actions, seconds_left):
        valid_squares = [
            square for square in sense_actions
            if 1 <= square % 8 <= 6 and 1 <= square // 8 <= 6
        ]
        chosen = random.choice(valid_squares)
        print(f"[SENSE] Chosen sensing square: {square_name(chosen)}")
        return chosen

    def handle_sense_result(self, sense_result):
        print(f"[SENSE RESULT] Pieces sensed: {sense_result}")
        
        # If no possible boards, can't do filtering
        if not self.possible_boards:
            print("[SENSE RESULT] No possible boards to filter!")
            return
        
        # Convert to list for iteration since we'll be modifying the set
        consistent_boards = set()
        
        for fen in self.possible_boards:
            board = chess.Board(fen)
            is_consistent = True
            
            # Check that each sensed piece matches our possible board
            for square, piece in sense_result:
                if piece is None:  # Empty square
                    if board.piece_at(square) is not None:
                        is_consistent = False
                        break
                else:  # Square has a piece
                    board_piece = board.piece_at(square)
                    if board_piece is None or board_piece.symbol() != piece.symbol():
                        is_consistent = False

                        break
            
            if is_consistent:
                consistent_boards.add(fen)
        
        before_count = len(self.possible_boards)
        self.possible_boards = consistent_boards
        after_count = len(self.possible_boards)
        
        print(f"[SENSE RESULT] Filtered boards: {before_count} -> {after_count}")
        
        # If we've eliminated all possible boards, we're in trouble
        if after_count == 0:
            print("[SENSE RESULT] WARNING: All boards eliminated! Resetting to single random board.")
            # Create a standard chess board as fallback
            self.possible_boards = {chess.Board().fen()}

    def choose_move(self, move_actions, seconds_left):
        board_count = len(self.possible_boards)

        if board_count == 0:
            print("[MOVE] No possible boards — choosing random move.")
            return random.choice(move_actions) if move_actions else None

        if board_count > 10000:
            self.possible_boards = set(random.sample(list(self.possible_boards), 10000))
            board_count = 10000
            print("[MOVE] Pruned to 10,000 possible boards.")

        move_counter = collections.Counter()
        time_per_board = max(0.001, min(0.1, 10.0 / board_count))  # Min 1ms, max 100ms per board

        for fen in self.possible_boards:
            board = chess.Board(fen)
            try:
                if board.turn == self.color:
                    result = self.engine.play(board, chess.engine.Limit(time=time_per_board))
                    best_move = result.move
                    if best_move in move_actions:
                        move_counter[best_move] += 1
            except chess.engine.EngineTerminatedError:
                print("[ERROR] Stockfish engine died - restarting")
                try:
                    self.engine.quit()  # make sure it's fully shut down
                except:
                    pass

                # Re-detect the stockfish path
                if platform.system() == 'Windows':
                    stockfish_path = './stockfish.exe'
                elif platform.system() == 'Linux':
                    stockfish_path = '/usr/bin/stockfish'
                elif platform.system() == 'Darwin':
                    stockfish_path = './stockfish-macos'
                else:
                    raise EnvironmentError("Unsupported OS for Stockfish")

                # Restart the engine
                self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
            except Exception as e:
                print(f"[MOVE] Stockfish error on board: {fen[:30]}... Error: {e}")
                continue

        if not move_counter:
            print("[MOVE] No legal moves returned — picking randomly.")
            if not move_actions:
                print("[ERROR] No legal moves available!")
                return None
            return random.choice(move_actions)

        chosen_move, count = move_counter.most_common(1)[0]
        print(f"[MOVE] Chosen move: {chosen_move} with {count} votes (out of {board_count})")
        return chosen_move

    def handle_move_result(self, requested_move, taken_move, captured_opponent_piece, capture_square):
        print(f"[MOVE RESULT] Requested: {requested_move}, Taken: {taken_move}, Captured: {captured_opponent_piece}")
        
        if not self.possible_boards:
            print("[MOVE RESULT] No possible boards to update!")
            return
        
        new_possible_boards = set()
        
        for fen in self.possible_boards:
            board = chess.Board(fen)
            
            # Skip boards where it's not our turn
            if board.turn != self.color:
                continue
                
            # If the taken move is None, our requested move was illegal
            if taken_move is None:
                # Keep boards where the requested move is not legal
                if requested_move not in board.legal_moves:
                    new_possible_boards.add(fen)
                continue
                    
            # Check if the move is consistent with the capture information
            if taken_move in board.legal_moves:
                move_captures = board.is_capture(taken_move)
                move_to_square = taken_move.to_square
                
                # If we made a capture to the right square
                is_consistent = (
                    (captured_opponent_piece and move_captures and move_to_square == capture_square) or
                    (not captured_opponent_piece and not move_captures)
                )
                
                if is_consistent:
                    new_board = board.copy()
                    new_board.push(taken_move)
                    new_possible_boards.add(new_board.fen())
        
        before_count = len(self.possible_boards)
        self.possible_boards = new_possible_boards
        after_count = len(self.possible_boards)
        
        print(f"[MOVE RESULT] Updated boards: {before_count} -> {after_count}")
        
        # If we've eliminated all possible boards, we're in trouble
        if after_count == 0:
            print("[MOVE RESULT] WARNING: All boards eliminated! Creating new possibilities.")
            # Create a default board and apply the move if possible
            board = chess.Board()
            if board.turn != self.color:
                board.push(chess.Move.null())  # Skip to our turn
            if taken_move is not None and taken_move in board.legal_moves:
                board.push(taken_move)
            self.possible_boards = {board.fen()}

    def handle_game_end(self, winner_color, win_reason, game_history):
        result = "White wins" if winner_color == chess.WHITE else "Black wins" if winner_color == chess.BLACK else "Draw"
        print(f"[END] Game Over: {result}. Reason: {win_reason}")
        if self.engine:
            self.engine.quit()
            print("[END] Stockfish engine shut down.")
