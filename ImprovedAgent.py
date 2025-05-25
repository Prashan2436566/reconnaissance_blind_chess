import os
import platform
import random
import chess
import collections
import chess.engine
from reconchess import *
from typing import List, Tuple, Optional

def is_edge_square(square):
    #non edge
    row, col = square // 8, square % 8
    return row in (0, 7) or col in (0, 7)

def openEngine():
    if platform.system() == 'Windows':
        stockfish_path = './stockfish.exe'
    elif platform.system() == 'Linux':
        stockfish_path = '/opt/stockfish/stockfish'
    elif platform.system() == 'Darwin':
        stockfish_path = './stockfish-macos'
    else:
        raise EnvironmentError("Unsupported OS for Stockfish")

    engine = chess.engine.SimpleEngine.popen_uci(stockfish_path, setpgrp=True, timeout=None)
    engine.configure({"Threads": 2, "Hash": 128})

    return engine


class ImprovedAgent(Player):
    def __init__(self):
        self.possible_boards = set()
        self.color = None
        self.opponent_king_position = None
        self.start = False
        self.move_num = 0
        self.my_piece_captured_square = None
        self.last_sense_result = None
        self.check_sensing_enabled = True
        self.engine = None
        
        # Enhanced state tracking
        self.opponent_piece_likelihood = {}  # Track likelihood of opponent pieces at squares
        self.my_pieces_in_danger = set()     # Track our pieces that might be under attack


    def handle_game_start(self, color: Color, board: chess.Board, opponent_name: str):
        self.color = color
        self.possible_boards = {board.fen()}
        self.opponent_king_position = board.king(not self.color)
        
        # Initialize opponent piece likelihood (initially all opponent pieces are in their starting positions)
        self.opponent_piece_likelihood = {}
        for square in range(64):
            piece = board.piece_at(square)
            if piece and piece.color != self.color:
                self.opponent_piece_likelihood[square] = 1.0
        
        
        if color:  # If playing as white
            self.start = True

        self.engine = openEngine()


    def handle_opponent_move_result(self, captured_my_piece: bool, capture_square: Optional[int]):
        
        # Skip if it's the first move and we're playing as white
        if self.start:
            self.start = False
            return
            
        if not self.possible_boards:
            return
        
        if captured_my_piece:
            new_possible_boards = self.gen_next_positions_with_capture(capture_square)
            self.my_piece_captured_square = capture_square
            
            # Add captured square to pieces in danger
            self.my_pieces_in_danger.add(capture_square)
        else:
            new_possible_boards = self.generate_next_positions()
            self.my_piece_captured_square = None
        
        # If we've eliminated all possible boards, keep the old ones
        if not new_possible_boards:
            return
        
        before_count = len(self.possible_boards)
        self.possible_boards = new_possible_boards
        after_count = len(self.possible_boards)
        
        # Update opponent piece likelihood based on possible boards
        self.update_opponent_piece_likelihood()
        


    def choose_sense(self, sense_actions: List[int], move_actions: List[chess.Move], seconds_left: float) -> Optional[int]:
        """Oracle-like sensing strategy: prioritize detecting checks, then minimize expected states."""
        
        if self.my_piece_captured_square:
            capture_area = self.my_piece_captured_square
            return capture_area

        if self.move_num<=3 and self.color:
            if (random.random()>0.5):
                return chess.E6
            else:
                return chess.D6
        elif self.move_num<=3 and not self.color:
            if (random.random()>0.5):
                return chess.E4
            else:
                return chess.D4     

        
        # If no possible boards, choose randomly
        if not self.possible_boards:
            return random.choice(sense_actions)
        
        # Filter out edge squares for better sensing (unless very few options)
        valid_squares = [square for square in sense_actions if not is_edge_square(square)]
        if len(valid_squares) < 10:  # If too few valid squares, use all sense actions
            valid_squares = sense_actions
            
    
        # Check if we need to detect possible checks (like Oracle bot)
        if self.check_sensing_enabled:
            potential_check_squares, check_probability = self.find_potential_check_squares()
            if check_probability > 0.1 and potential_check_squares:  # If >10% chance of check
                # Pick a square that covers the most potential checks
                best_square = None
                best_coverage = 0
                
                for sense_square in valid_squares:
                    coverage = 0
                    # Consider the 3x3 grid around each sense square
                    for rank_offset in range(-1, 2):
                        for file_offset in range(-1, 2):
                            rank = chess.square_rank(sense_square) + rank_offset
                            file = chess.square_file(sense_square) + file_offset
                            
                            if 0 <= rank < 8 and 0 <= file < 8:
                                covered_square = chess.square(file, rank)
                                if covered_square in potential_check_squares:
                                    coverage += 1
                    
                    if coverage > best_coverage:
                        best_coverage = coverage
                        best_square = sense_square
                
                if best_square is not None and best_coverage > 0:
                    return best_square
        
        # If no checks to detect or check detection disabled, minimize expected states (like Oracle)
        min_expected_states = float('inf')
        best_sense_square = None
        
        # Limit evaluation to a subset of squares for performance
        squares_to_evaluate = valid_squares
        if len(squares_to_evaluate) > 25:  # Sample 15 squares if there are too many
            squares_to_evaluate = random.sample(squares_to_evaluate, 15)
            
            # Ensure squares with high opponent piece likelihood are included
            high_likelihood_squares = sorted(
                [(square, likelihood) for square, likelihood in self.opponent_piece_likelihood.items()],
                key=lambda x: x[1], reverse=True
            )[:5]
            
            for square, _ in high_likelihood_squares:
                if square in valid_squares and square not in squares_to_evaluate:
                    squares_to_evaluate.append(square)
                    
        # Evaluate expected states after sensing
        for sense_square in squares_to_evaluate:
            expected_states = self.get_expected_states_after_sensing(sense_square)
            
            if expected_states < min_expected_states:
                min_expected_states = expected_states
                best_sense_square = sense_square
        
        if best_sense_square is not None:
            return best_sense_square
        
        # Fallback to random sensing if all else fails
        return random.choice(valid_squares)


    def handle_sense_result(self, sense_result: List[Tuple[int, Optional[chess.Piece]]]):
        
        self.last_sense_result = sense_result
        
        if not self.possible_boards:
            return
        
        consistent_boards = set()
        
        # Update the opponent king position if sensed
        for square, piece in sense_result:
            if piece and piece.piece_type == chess.KING and piece.color != self.color:
                self.opponent_king_position = square
                break
        
        # Check each possible board against the sense result
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
                    if board_piece is None or board_piece.piece_type != piece.piece_type or board_piece.color != piece.color:
                        is_consistent = False
                        break
            
            if is_consistent:
                consistent_boards.add(fen)
        
        before_count = len(self.possible_boards)
        self.possible_boards = consistent_boards
        after_count = len(self.possible_boards)
        
        
        # If we've eliminated all possible boards, we're in trouble
        if after_count == 0:
            # Create a default board as fallback
            default_board = chess.Board()
            self.possible_boards = {default_board.fen()}
        
        # Update opponent piece likelihood after filtering
        self.update_opponent_piece_likelihood()


    def choose_move(self, move_actions: List[chess.Move], seconds_left: float) -> Optional[chess.Move]:
        """Oracle-like move selection with prioritized mate-in-4 search."""

        if (self.color and self.move_num==0):
            return chess.Move(chess.E2,chess.E4)
        
        board_count = len(self.possible_boards)

        if board_count == 0:
            return random.choice(move_actions) if move_actions else None

        
        # Limit the number of boards to consider to prevent slowdown
        boards_to_evaluate = list(self.possible_boards)

        maxBoardCount = 100
        minBoardSample = int(maxBoardCount*0.60)

        if board_count > maxBoardCount:
            # Bias sampling toward boards where the opponent king's position is known
            known_king_boards = []
            unknown_king_boards = []

            for fen in boards_to_evaluate:
                board = chess.Board(fen)
                king_sq = board.king(not self.color)
                if king_sq is not None:
                    known_king_boards.append(fen)
                else:
                    unknown_king_boards.append(fen)

            # Sample biased: prioritize 60% known king boards and 40% unknown
            sample_known = min(minBoardSample, len(known_king_boards))
            sample_unknown = maxBoardCount - sample_known
            boards_to_evaluate = random.sample(known_king_boards, sample_known) + \
                                random.sample(unknown_king_boards, min(sample_unknown, len(unknown_king_boards)))

            board_count = len(boards_to_evaluate)

        
        # First, check if we can directly capture the opponent's king
        for fen in boards_to_evaluate:
            board = chess.Board(fen)
            if board.turn != self.color:
                continue
                
            enemy_king_square = board.king(not self.color)
            if enemy_king_square:
                enemy_king_attackers = board.attackers(self.color, enemy_king_square)
                if enemy_king_attackers:
                    attacker_square = enemy_king_attackers.pop()
                    attacking_move = chess.Move(attacker_square, enemy_king_square)
                    if attacking_move in move_actions:
                        return attacking_move

        # NEW: Look for mate in 4 across possible boards
        mate_moves = collections.Counter()
        boards_with_mate_potential = 0
        
        # First check for mate in 4 across our possible boards
        for i, fen in enumerate(boards_to_evaluate):
            board = chess.Board(fen)
            try:
                if board.turn == self.color:
                    # Search specifically for mate
                    mate_result = self.engine.analyse(
                        board, 
                        chess.engine.Limit(depth=8),  # Depth 8 should find most mates in 4
                        multipv=1,
                        info=chess.engine.INFO_SCORE
                    )
                    
                    # Check if the position has a forced mate
                    if 'score' in mate_result[0]:
                        score = mate_result[0]['score']
                        if score.is_mate() and score.mate() > 0 and score.mate() <= 4:
                            boards_with_mate_potential += 1
                            
                            # Get the first move of the mating sequence
                            if 'pv' in mate_result[0] and mate_result[0]['pv']:
                                mate_move = mate_result[0]['pv'][0]
                                if mate_move in move_actions:
                                    # Weight by the mate distance - shorter mates get higher weight
                                    weight = 5 - score.mate()  # mate in 1 gets weight 4, mate in 4 gets weight 1
                                    mate_moves[mate_move] += weight * 10  # give mate moves higher priority
            except chess.engine.EngineTerminatedError:
                try:
                    self.engine.quit()  # make sure it's fully shut down
                except:
                    pass

                # TODO open egnine
                self.engine = openEngine()
            except Exception as e:
                continue
        
        # If we found mate in 4 for a significant portion of boards, choose the best mate move
        if mate_moves and boards_with_mate_potential >= max(1, board_count * 0.1):  # At least 10% of boards
            best_mate_move = mate_moves.most_common(1)[0][0]
            return best_mate_move

        # Otherwise, use Stockfish to evaluate moves across all possible boards
        move_counter = collections.Counter()
        time_per_board = max(0.001, min(0.05, 5.0 / board_count))  # Adjust time based on board count
        
        # For Oracle-like behavior, we count the most frequently recommended move
        # across all possible board states
        for i, fen in enumerate(boards_to_evaluate):
            board = chess.Board(fen)
            try:
                if board.turn == self.color:
                    # Get the top 3 moves from Stockfish for each board
                    result = self.engine.analyse(board, chess.engine.Limit(time=time_per_board), multipv=3)
                    for pv in result:
                        if 'pv' in pv and pv['pv']:
                            best_move = pv['pv'][0]
                            # Check if this move is legal in our current position
                            if best_move in move_actions:
                                # Weight by position in multipv (first suggestion gets more weight)
                                weight = 4 - pv.get('multipv', 3)  # multipv 1 gets weight 3, multipv 3 gets weight 1
                                move_counter[best_move] += weight
            except chess.engine.EngineTerminatedError:
                try:
                    self.engine.quit()  # make sure it's fully shut down
                except:
                    pass

                self.engine = openEngine()
            except Exception as e:
                continue

        if not move_counter:
            if not move_actions:
                return None
            return random.choice(move_actions)

        # Choose the move with the most votes (Oracle-like behavior)
        chosen_move, count = move_counter.most_common(1)[0]
        return chosen_move


    def handle_move_result(self, requested_move: Optional[chess.Move], taken_move: Optional[chess.Move],
                           captured_opponent_piece: bool, capture_square: Optional[int]):
        
        if not self.possible_boards:
            return
        
        new_possible_boards = set()
        
        # If we captured the opponent's king, remember that square for future sensing
        if captured_opponent_piece and capture_square is not None:
            for fen in self.possible_boards:
                board = chess.Board(fen)
                piece = board.piece_at(capture_square)
                if piece and piece.piece_type == chess.KING and piece.color != self.color:
                    break
        
        # Filter boards based on move result
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
                
                # If we made a capture to the right square
                is_consistent = (
                    (captured_opponent_piece and move_captures and taken_move.to_square == capture_square) or
                    (not captured_opponent_piece and not move_captures)
                )
                
                if is_consistent:
                    new_board = board.copy()
                    new_board.push(taken_move)
                    new_possible_boards.add(new_board.fen())
        
        before_count = len(self.possible_boards)
        self.possible_boards = new_possible_boards
        after_count = len(self.possible_boards)
        
        # If we've eliminated all possible boards, we're in trouble
        if after_count == 0:
            # Create a default board and apply the move if possible
            board = chess.Board()
            if board.turn != self.color:
                board.push(chess.Move.null())  # Skip to our turn
            if taken_move is not None and taken_move in board.legal_moves:
                board.push(taken_move)
            self.possible_boards = {board.fen()}
            
        self.move_num += 1
        
        # Update opponent piece likelihood
        self.update_opponent_piece_likelihood()


    def handle_game_end(self, winner_color: Optional[Color], win_reason: Optional[WinReason],
                        game_history: GameHistory):
        result = "White wins" if winner_color == chess.WHITE else "Black wins" if winner_color == chess.BLACK else "Draw"
        print(f"[END] Game Over: {result}. Reason: {win_reason}")
        if self.engine:
            try:
                self.engine.quit()
            except chess.engine.EngineTerminatedError:
                pass
    
    #UTIL
    def update_opponent_piece_likelihood(self):
        """Update the likelihood of opponent pieces being on each square."""
        # Reset likelihoods
        self.opponent_piece_likelihood = {}
        
        # Count occurrences of opponent pieces on each square across all possible boards
        piece_counts = {}
        for fen in self.possible_boards:
            board = chess.Board(fen)
            for square in range(64):
                piece = board.piece_at(square)
                if piece and piece.color != self.color:
                    if square not in piece_counts:
                        piece_counts[square] = 0
                    piece_counts[square] += 1
        
        # Convert counts to likelihoods
        board_count = max(1, len(self.possible_boards))  # Avoid division by zero
        for square, count in piece_counts.items():
            self.opponent_piece_likelihood[square] = count / board_count


    def generate_next_positions(self):
        """Generate all possible positions after opponent's move with no capture."""
        next_positions = set()

        for fen in self.possible_boards:
            board = chess.Board(fen)
            
            # Skip boards where it's not the opponent's turn
            if board.turn == self.color:
                continue
                
            # Generate all possible opponent moves including null move
            possible_moves = list(board.pseudo_legal_moves) + [chess.Move.null()]
            
            # Add castling possibilities
            next_positions.update(self.get_opponent_castling(board))
            
            # For each move that doesn't capture, add the resulting position
            for move in possible_moves:
                # Only consider non-capturing moves
                if board.piece_at(move.to_square) is None:
                    new_board = board.copy()
                    new_board.push(move)
                    next_positions.add(new_board.fen())
        
        return next_positions


    def gen_next_positions_with_capture(self, capture_square):
        """Generate all possible positions after opponent's move with capture at specified square."""
        next_positions = set()
        
        for fen in self.possible_boards:
            board = chess.Board(fen)
            
            # Skip boards where it's not the opponent's turn
            if board.turn == self.color:
                continue
                
            # Generate all possible opponent moves
            possible_moves = list(board.pseudo_legal_moves)
            
            # For each capturing move to the right square, add the resulting position
            for move in possible_moves:
                if (board.is_capture(move) or board.is_en_passant(move)) and move.to_square == capture_square:
                    new_board = board.copy()
                    new_board.push(move)
                    next_positions.add(new_board.fen())
        
        return next_positions


    def get_opponent_castling(self, board):
        """Generate positions resulting from opponent castling."""
        castling_positions = set()
        enemy_color = not self.color

        # Check kingside castling
        if board.has_kingside_castling_rights(enemy_color):
            king_square = board.king(enemy_color)
            target_square = chess.square(chess.square_file(king_square) + 2, chess.square_rank(king_square))
            move = chess.Move(king_square, target_square)
            
            # Attempt the castling move if it's legal
            if move in board.legal_moves:
                new_board = board.copy()
                new_board.push(move)
                castling_positions.add(new_board.fen())

        # Check queenside castling
        if board.has_queenside_castling_rights(enemy_color):
            king_square = board.king(enemy_color)
            target_square = chess.square(chess.square_file(king_square) - 2, chess.square_rank(king_square))
            move = chess.Move(king_square, target_square)
            
            # Attempt the castling move if it's legal
            if move in board.legal_moves:
                new_board = board.copy()
                new_board.push(move)
                castling_positions.add(new_board.fen())

        return castling_positions


    def find_potential_check_squares(self):
        """Find squares where sensing might reveal if our king is in check across possible boards."""
        potential_check_squares = set()
        king_under_attack_count = 0
        total_boards = len(self.possible_boards)
        
        for fen in self.possible_boards:
            board = chess.Board(fen)
            # Ensure it's our turn
            if board.turn != self.color:
                board.push(chess.Move.null())
                
            king_square = board.king(self.color)
            if king_square is None:
                continue
                
            # Check if our king is attacked
            attackers = board.attackers(not self.color, king_square)
            if attackers:
                king_under_attack_count += 1
                # Add attacking squares to potential check squares
                for attacker_square in attackers:
                    potential_check_squares.add(attacker_square)
                    
                    # Also add squares between attacker and king for sliding pieces
                    piece = board.piece_at(attacker_square)
                    if piece and piece.piece_type in [chess.BISHOP, chess.ROOK, chess.QUEEN]:
                        between_squares = chess.SquareSet(chess.between(attacker_square, king_square))
                        for square in between_squares:
                            potential_check_squares.add(square)
        
        # Check if there's a significant chance our king is in check
        check_probability = king_under_attack_count / max(1, total_boards)
        
        return potential_check_squares, check_probability
    
    #probility stuff
    def update_opponent_piece_likelihood(self):
        """Update the likelihood of opponent pieces being on each square."""
        # Reset likelihoods
        self.opponent_piece_likelihood = {}
        
        # Count occurrences of opponent pieces on each square across all possible boards
        piece_counts = {}
        for fen in self.possible_boards:
            board = chess.Board(fen)
            for square in range(64):
                piece = board.piece_at(square)
                if piece and piece.color != self.color:
                    if square not in piece_counts:
                        piece_counts[square] = 0
                    piece_counts[square] += 1
        
        # Convert counts to likelihoods
        board_count = max(1, len(self.possible_boards))  # Avoid division by zero
        for square, count in piece_counts.items():
            self.opponent_piece_likelihood[square] = count / board_count


    def get_expected_states_after_sensing(self, sense_square):
        """Calculate the expected number of states after sensing at a given square."""
        # Group possible boards by what would be observed at the sense square
        observation_groups = {}
        
        for fen in self.possible_boards:
            board = chess.Board(fen)
            
            # Generate the 3x3 grid around the sense square
            sense_result = []
            for rank_offset in range(-1, 2):
                for file_offset in range(-1, 2):
                    rank = chess.square_rank(sense_square) + rank_offset
                    file = chess.square_file(sense_square) + file_offset
                    
                    if 0 <= rank < 8 and 0 <= file < 8:
                        obs_square = chess.square(file, rank)
                        piece = board.piece_at(obs_square)
                        sense_result.append((obs_square, piece))
            
            # Convert sense result to a hashable representation
            sense_key = tuple(sorted([(sq, str(p)) for sq, p in sense_result]))
            
            if sense_key not in observation_groups:
                observation_groups[sense_key] = 0
            observation_groups[sense_key] += 1
        
        # Calculate the expected number of states after sensing
        total_boards = len(self.possible_boards)
        expected_states = 0
        for count in observation_groups.values():
            probability = count / total_boards
            expected_states += probability * count
            
        return expected_states
