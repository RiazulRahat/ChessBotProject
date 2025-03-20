import chess

class ChessEngine:
    # Pre initialize a chess board
    def __init__(self):
        self.board = chess.Board()

    # Return the board's current state in ASCII notation
    def display_board(self):
        return str(self.board)

    # Method to display the board
    def make_move(self, move_san):
        """
        Attempt to make a move using SAN notation.
        
        Parameters:
            move_san (str): The move in Standard Algebraic Notation.
            
        Returns:
            tuple: (bool, str) where bool indicates success and str is a message.
        """
        try:
            # parse and Check if move is in SAN notation
            move = self.board.parse_san(move_san)
        except ValueError:
            return False, "Invalid move notation."

        self.board.push(move)
        return True, "Move applied Successfully!"
    
    # Method to check if game has ended
    def is_game_over(self):
        gameover = False

        gameover = self.board.is_stalemate() or self.board.is_insufficient_material() or \
                    self.board.is_game_over()
        
        return gameover
    
    # Method to return final result
    def get_result(self):
        return self.board.result()
    
    
