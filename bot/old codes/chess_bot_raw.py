# bot/chess_bot.py
import chess, random, pickle, os

TABLE_FILE = "bot/eval_table.pkl"    # shared pickle on disk
DRAW_BIAS  = 0.2                     # +0.2 from White’s PoV → draw

INF = float("inf")


class ChessBotAgent:
    """
    Tiny TD-learning chess agent with
    • TD(0) value updates
    • ε-greedy NN-ply alpha-beta search (default depth = 3)
    """

    def __init__(self,
                 exploration_rate=0.1,
                 learning_rate=0.05,
                 save_interval=50,
                 table_path: str = TABLE_FILE,
                 search_depth: int = 3):
        self.exploration_rate = exploration_rate
        self.learning_rate    = learning_rate
        self.save_interval    = save_interval
        self._table_path      = table_path
        self.search_depth     = max(1, search_depth)
        self.games_since_save = 0
        self.evaluation_table = self._load_table()

    # ───────── Evaluation ────────────────────────────────────────────────
    @staticmethod
    def _material_score(board: chess.Board) -> float:
        vals = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9}
        return sum(v * (len(board.pieces(p, chess.WHITE)) -
                        len(board.pieces(p, chess.BLACK)))
                   for p, v in vals.items())

    def _state_value(self, board: chess.Board) -> float:
        return self.evaluation_table.get(board.fen(), self._material_score(board))

    # ───────── Public move selection ─────────────────────────────────────
    def choose_move(self, board: chess.Board):

        """ε-greedy search to self.search_depth plies."""
        legal = list(board.legal_moves)
        if not legal:
            return None

        # exploration
        if random.random() < self.exploration_rate:
            return random.choice(legal)

        # alpha-beta search
        maximise_white = board.turn == chess.WHITE
        _, best = self._alphabeta(board,
                                  depth=self.search_depth,
                                  alpha=-INF,
                                  beta=+INF,
                                  maximise_white=maximise_white)
        return best or random.choice(legal)

    # ───────── Alpha-beta with move ordering ─────────────────────────────
    def _alphabeta(self, board, depth, alpha, beta, maximise_white):
        if depth == 0 or board.is_game_over():
            return self._state_value(board), None

        best_move = None
        for mv in self._ordered_moves(board):
            board.push(mv)
            val, _ = self._alphabeta(board, depth-1, alpha, beta, maximise_white)
            board.pop()

            if maximise_white == board.turn:        # same colour => maximiser
                if val > alpha:
                    alpha, best_move = val, mv
                if alpha >= beta:
                    break                           # β cut-off
            else:                                   # minimiser
                if val < beta:
                    beta, best_move = val, mv
                if beta <= alpha:
                    break                           # α cut-off

        return (alpha, best_move) if maximise_white == board.turn else (beta, best_move)

    # simple MVV-LVA + checks first
    def _ordered_moves(self, board):
        caps, checks, quiet = [], [], []
        for mv in board.legal_moves:
            if board.is_capture(mv):
                caps.append(mv)
            elif board.gives_check(mv):
                checks.append(mv)
            else:
                quiet.append(mv)

        # Most-Valuable-Victim / Least-Valuable-Attacker
        def mvv_lva(m):
            """
            Most-Valuable-Victim / Least-Valuable-Attacker score.
            Works for normal captures *and* en-passant.
            """
            if board.is_en_passant(m):
                victim_type = chess.PAWN                      # the captured pawn
            else:
                v = board.piece_at(m.to_square)
                victim_type = v.piece_type if v else 0        # paranoid fallback

            attacker_type = board.piece_at(m.from_square).piece_type
            return (-victim_type, attacker_type)

        caps.sort(key=mvv_lva)
        return caps + checks + quiet

    # ───────── TD-0 learning ─────────────────────────────────────────────
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

    # ───────── persistence helpers ──────────────────────────────────────
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
