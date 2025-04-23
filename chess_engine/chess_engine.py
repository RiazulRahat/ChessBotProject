import chess

class ChessEngine:
    def __init__(self):
        self.board = chess.Board()

    def display_board(self):
        return str(self.board)

    def make_move(self, move_san):
        try:
            mv = self.board.parse_san(move_san)
        except ValueError:
            return False, "Invalid move"
        self.board.push(mv)
        return True, "Move applied"

    def is_game_over(self):
        return self.board.is_game_over()

    def get_result(self):
        return self.board.result()
