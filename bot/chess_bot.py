import chess, random, pickle, os

TABLE_FILE = "bot/eval_table.pkl"   # shared pickle
DRAW_BIAS  = 0.2                    # draw = +0.2 from White's view


class ChessBotAgent:
    """
    Tiny TD-0 learner with 2-ply mini-max search.
    """
    def __init__(self,
                 exploration_rate=0.1,
                 learning_rate=0.05,
                 save_interval=50,
                 table_path: str = TABLE_FILE):
        self.exploration_rate = exploration_rate
        self.learning_rate    = learning_rate
        self.save_interval    = save_interval
        self._table_path      = table_path
        self.games_since_save = 0
        self.evaluation_table = self._load_table()

    # ───────── Evaluation ────────────────────────────────────────────────
    @staticmethod
    def _material_score(board: chess.Board) -> float:
        vals = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9}
        s = sum(v * (len(board.pieces(p, chess.WHITE)) -
                     len(board.pieces(p, chess.BLACK)))
                for p, v in vals.items())
        return s

    def _state_value(self, board: chess.Board) -> float:
        return self.evaluation_table.get(board.fen(), self._material_score(board))

    # ───────── 2-ply ε-greedy search ────────────────────────────────────
    def choose_move(self, board: chess.Board):
        legal = list(board.legal_moves)
        if not legal:
            return None
        if random.random() < self.exploration_rate:
            return random.choice(legal)

        maximise = board.turn == chess.WHITE
        best_val = -float("inf") if maximise else float("inf")
        best_mv  = None

        for mv in legal:
            board.push(mv)
            opp_best = float("inf") if maximise else -float("inf")

            for reply in board.legal_moves:
                board.push(reply)
                v = self._state_value(board)
                board.pop()

                if maximise and v < opp_best:
                    opp_best = v
                elif not maximise and v > opp_best:
                    opp_best = v
            board.pop()

            if maximise and opp_best > best_val or (not maximise and opp_best < best_val):
                best_val, best_mv = opp_best, mv

        return best_mv or random.choice(legal)

    # ───────── TD-0 learning (backwards) ────────────────────────────────
    def update_evaluation(self, game_history, result):
        if   result == "1-0":  next_v = 1.0
        elif result == "0-1":  next_v = -1.0
        else:                  next_v = DRAW_BIAS

        for fen, white_to_move in reversed(game_history):
            target =  next_v if white_to_move else -next_v
            old    = self.evaluation_table.get(fen, 0.0)
            new    = old + self.learning_rate * (target - old)
            self.evaluation_table[fen] = new
            next_v = new if white_to_move else -new

        self.games_since_save += 1
        if self.games_since_save >= self.save_interval:
            self._save_table()
            self.games_since_save = 0

    # ───────── persistence ──────────────────────────────────────────────
    def _load_table(self):
        if os.path.exists(self._table_path):
            try:
                with open(self._table_path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                print("⚠️  could not load table:", e)
        return {}

    def _save_table(self):
        os.makedirs(os.path.dirname(self._table_path), exist_ok=True)
        with open(self._table_path, "wb") as f:
            pickle.dump(self.evaluation_table, f)
