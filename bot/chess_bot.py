# bot/chess_bot.py
import chess, random, pickle, os
TABLE_FILE = "bot/eval_table.pkl"          # where we persist learned values
DRAW_BIAS = 0.2                            # the value given for a draw


class ChessBotAgent:
    """
    A tiny TD‑learning chess agent.
    •   evaluation_table  – maps FEN strings ➜ float “score from White’s view”
    •   evaluate_board()  – fallback heuristic (simple material)
    •   choose_move()     – ε‑greedy one‑ply search
    •   update_evaluation() – TD‑0 update after every game
    """
    def __init__(self, exploration_rate=0.1, learning_rate=0.05, save_interval=50):
        self.exploration_rate = exploration_rate
        self.learning_rate   = learning_rate
        self.save_interval   = save_interval              
        self.games_since_save = 0                         
        self.evaluation_table = self._load_table()

    # ----------  Heuristics  ----------
    @staticmethod
    def _material_score(board: chess.Board) -> float:
        vals = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9}
        score = 0
        for p, v in vals.items():
            score += v * (len(board.pieces(p, chess.WHITE))
                          - len(board.pieces(p, chess.BLACK)))
        return score

    def _state_value(self, board: chess.Board) -> float:
        """Lookup FEN in table; if unseen, return heuristic material score."""
        fen = board.fen()
        return self.evaluation_table.get(fen, self._material_score(board))

    # ----------  Move selection (ε‑greedy 1‑ply)  ----------
    def choose_move(self, board: chess.Board):
        legal = list(board.legal_moves)
        if not legal:
            return None

        if random.random() < self.exploration_rate:
            return random.choice(legal)             # explore

        maximise = board.turn == chess.WHITE
        best_val = -float("inf") if maximise else float("inf")
        best_mv  = None

        for mv in legal:
            board.push(mv)
            val = self._state_value(board)
            board.pop()

            if maximise and val > best_val or (not maximise and val < best_val):
                best_val, best_mv = val, mv

        return best_mv or random.choice(legal)

    # ----------  Learning (TD‑0)  ----------
    # ----------  Learning (true TD‑0, update every ply)  ----------
    def update_evaluation(self, game_history, result):
        """
        Bootstrapped TD(0) update *backwards* through the game.
        game_history is a list in chronological order:
            [(fen_before_move_0, white_to_move_0),
             (fen_before_move_1, white_to_move_1), ...]
        """

        # final reward from White’s perspective
        if   result == "1-0":  next_v = 1.0
        elif result == "0-1":  next_v = -1.0
        else:                  next_v = DRAW_BIAS      # +0.2

        # Walk the history *backwards*
        for fen, white_to_move in reversed(game_history):
            # If it was Black to move, flip the perspective
            target =  next_v if white_to_move else -next_v

            old_val = self.evaluation_table.get(fen, 0.0)
            new_val = old_val + self.learning_rate * (target - old_val)
            self.evaluation_table[fen] = new_val

            # Bootstrapped target for the previous position
            next_v = new_val if white_to_move else -new_val

        # ---- deferred save ----
        self.games_since_save += 1
        if self.games_since_save >= self.save_interval:
            self._save_table()
            self.games_since_save = 0


    # ----------  Persistence helpers  ----------
    def _load_table(self):
        if os.path.exists(TABLE_FILE):
            try:
                with open(TABLE_FILE, "rb") as f:
                    return pickle.load(f)
            except Exception:
                pass
        return {}

    def _save_table(self):
        os.makedirs(os.path.dirname(TABLE_FILE), exist_ok=True)
        with open(TABLE_FILE, "wb") as f:
            pickle.dump(self.evaluation_table, f)
