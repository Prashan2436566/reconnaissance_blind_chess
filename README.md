# reconnaissance_blind_chess
Download stockfish.exe from https://stockfishchess.org/download/

Two agents for playing Reconnaissance Blind Chess:

RandomSensing.py: The RandomSensing agent tracks possible board states, selects random sensing squares, and uses Stockfish to choose the most likely move based on majority vote.
ImprovedAgent.py: The ImprovedAgent maintains a set of possible board states (beliefs) and uses Stockfish-guided voting over these states to select strong moves, while strategically sensing to reduce uncertainty about the opponent's pieces, especially the king.
