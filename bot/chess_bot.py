# bot/chess_bot.py
from bot.utils.debug import dprint
import os, time, datetime, random, pickle
import chess

from bot.utils.zobrist import zobrist
from bot.utils.opening_book import load_opening_book
from bot.evaluation.positional_heuristics import positional_score

# ────────────────────────────────────────────────────────────────────────
TABLE_FILE = "bot/evaluation_table_current/eval_table_zobrist_pruned.pkl"
DRAW_BIAS  = 0.0
INF        = float("inf")

# unified piece values (centipawns)
_PV = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
       chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20_000}

def piece_value(piece: chess.Piece | None) -> int:
    return _PV.get(piece.piece_type, 0) if piece else 0

def victim_value(board: chess.Board, sq) -> int:
    return piece_value(board.piece_at(sq))

def attacker_value(board: chess.Board, sq) -> int:
    atk = [board.piece_at(s).piece_type for s in board.attackers(board.turn, sq)]
    return min(_PV[t] for t in atk) if atk else 0
# ------------------------------------------------------------------------


class ChessBotAgent:
    """
    TD(0) learner with ε‑greedy Alpha‑Beta and capture‑only quiescence.
    """

    def __init__(self,
                 exploration_rate=0.1,
                 learning_rate=0.02,
                 mobility_weight=0.05,
                 save_interval=50,
                 table_path=TABLE_FILE,
                 policy_path=None,
                 policy_mix=0.1,
                 search_depth=3,
                 positional_weight=1.0,
                 use_policy=True,
                 use_quiescence=False,
                 quiescence_depth=5,
                 zobrist_keys_path="bot/zobrist_keys.pkl"):

        # ── knobs
        self.exploration_rate  = exploration_rate
        self.learning_rate     = learning_rate
        self.mobility_weight   = mobility_weight
        self.save_interval     = save_interval
        self.search_depth      = max(1, search_depth)
        self.positional_weight = positional_weight
        self.use_policy        = use_policy
        self.policy_mix        = policy_mix
        self.use_quiescence    = use_quiescence
        self.quiescence_depth  = quiescence_depth

        # ── persistent tables
        self._table_path   = table_path
        self.evaluation_table = self._load_table()
        self.zkey_to_fen      = {}
        self.zkey_stats       = {}
        self.tt               = {}          # key → (depth, value, bestMove)

        if os.path.exists(table_path.replace(".pkl", "_zkey2fen.pkl")):
            with open(table_path.replace(".pkl", "_zkey2fen.pkl"), "rb") as f:
                self.zkey_to_fen = pickle.load(f)
        if os.path.exists(table_path.replace(".pkl", "_stats.pkl")):
            with open(table_path.replace(".pkl", "_stats.pkl"), "rb") as f:
                self.zkey_stats = pickle.load(f)

        self.policy: dict[int, dict[str, float]] = {}
        if policy_path:
            with open(policy_path, "rb") as f:
                self.policy = pickle.load(f)
            print(f"Loaded policy table ({len(self.policy):,})")

        # opening book
        book_path = os.path.join(os.path.dirname(__file__), "opening_book.pkl")
        self.opening_book = load_opening_book(book_path)

        # keep key array around for external tools
        with open(zobrist_keys_path, "rb") as f:
            self.zobrist_keys = pickle.load(f)

        self.games_since_save = 0
        self.quiesce_calls    = 0
        dprint("Bot created  LR=%.3f  ε=%.3f  depth=%d",
               self.learning_rate, self.exploration_rate, self.search_depth)

    # ───────── evaluation helpers ───────────────────────────────────────
    @staticmethod
    def _material(board: chess.Board) -> float:
        vals = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9}
        return sum(v * (len(board.pieces(p, chess.WHITE)) -
                        len(board.pieces(p, chess.BLACK)))
                   for p, v in vals.items())

    def _state_value(self, board: chess.Board) -> float:
        key = zobrist.hash(board)
        if key in self.evaluation_table:
            self.zkey_to_fen.setdefault(key, board.fen())
        base = self.evaluation_table.get(key, self._material(board))
        return base + self.positional_weight * positional_score(board)

    # ───────── public move pickers ──────────────────────────────────────
    def choose_move(self, board: chess.Board):
        fen = board.fen()

        # 0) opening book
        if fen in self.opening_book:
            move = chess.Move.from_uci(random.choice(self.opening_book[fen]))
            dprint("[BOOK] %s", move.uci())
            return move

        # 1) learned policy
        if self.use_policy and fen in self.policy and random.random() < self.policy_mix:
            moves, probs = zip(*self.policy[fen].items())
            mv = chess.Move.from_uci(random.choices(moves, probs)[0])
            dprint("[POLICY] %s", mv.uci())
            return mv

        legal = list(board.legal_moves)
        if not legal:
            return None

        # 2) exploration
        if random.random() < self.exploration_rate:
            mv = random.choice(legal)
            dprint("[EXPLORE] %s", mv.uci())
            return mv

        # 3) search
        maximise_white = board.turn == chess.WHITE
        val, mv = self._alphabeta(board, self.search_depth,
                                  -INF, +INF, maximise_white)
        dprint("[SEARCH] depth=%d  move=%s  val=%.1f",
               self.search_depth, mv.uci() if mv else "?", val)
        return mv or random.choice(legal)

    def choose_move_timed(self, board: chess.Board, time_per_move: float):
        start = time.time()
        best = random.choice(list(board.legal_moves))
        for depth in range(1, self.search_depth + 1):
            val, mv = self._alphabeta(board, depth, -INF, INF,
                                      board.turn == chess.WHITE)
            if mv:
                best = mv
            if time.time() - start >= time_per_move:
                break
        return best

    # ───────── alpha‑beta with TT ───────────────────────────────────────
    def _alphabeta(self, board, depth, alpha, beta, maximise_white):
        key = zobrist.hash(board)

        # ----- terminal position guard -------------
        if board.is_game_over():
            return self._state_value(board), None
        # -------------------------------------------

        dprint("αβ d=%d α=%.1f β=%.1f maxW=%s hash=%016x",
               depth, alpha, beta, maximise_white, key)

        if key in self.tt and self.tt[key][0] >= depth:
            dprint("TT‑hit depth=%d  val=%.1f", self.tt[key][0], self.tt[key][1])
            return self.tt[key][1], self.tt[key][2]

        if depth == 0:
            # quiescence hit?
            if key in self.tt and self.tt[key][0] == -1:
                return self.tt[key][1], None
            if self.use_quiescence and not board.is_game_over():
                self.quiesce_calls += 1
                val = self.quiesce(board, alpha, beta,
                                   board.turn == chess.WHITE, 0)
                return val, None
            return self._state_value(board), None

        best_move = None
        for mv in self._ordered_moves(board):
            board.push(mv)
            val, _ = self._alphabeta(board, depth - 1,
                                     alpha, beta, not maximise_white)
            board.pop()

            if maximise_white:
                if val > alpha:
                    alpha, best_move = val, mv
                if alpha >= beta:
                    break
            else:
                if val < beta:
                    beta, best_move = val, mv
                if beta <= alpha:
                    break

        # If no move survived (legal list might be empty in stalemate),
        # fall back gracefully instead of crashing.
        if best_move is None:
            moves = list(board.legal_moves)
            if moves:
                best_move = random.choice(moves)
            else:            # really no legal moves → treat as terminal
                best_val = self._state_value(board)
                self.tt[key] = (depth, best_val, None)
                return best_val, None

        best_val = alpha if maximise_white else beta
        self.tt[key] = (depth, best_val, best_move)
        dprint("αβ‑ret d=%d  best=%s  val=%.1f",
                depth, best_move.uci() if best_move else "?", best_val)
        return best_val, best_move

    # ───────── quiescence search ────────────────────────────────────────
    def quiesce(self, board, alpha, beta, maximise_white, ply):
        key = zobrist.hash(board)
        if key in self.tt and self.tt[key][0] == -1:
            dprint("QUI‑TT hit  val=%.1f", self.tt[key][1])
            return self.tt[key][1]

        stand = self._state_value(board)
        dprint("QUI ply=%d stand=%.1f α=%.1f β=%.1f", ply, stand, alpha, beta, lvl=2)

        if maximise_white:
            if stand >= beta:
                return beta
            alpha = max(alpha, stand)
        else:
            if stand <= alpha:
                return alpha
            beta = min(beta, stand)

        if ply >= self.quiescence_depth:
            self.tt[key] = (-1, stand, None)
            dprint("QUI‑store leaf  val=%.1f", stand)
            return stand

        moves = [m for m in board.legal_moves if board.is_capture(m)]
        moves.sort(key=lambda m: (-victim_value(board, m.to_square),
                                  attacker_value(board, m.from_square)))

        for mv in moves:
            gain = piece_value(board.piece_at(mv.to_square))
            if maximise_white and stand + gain < alpha:
                continue
            if not maximise_white and stand - gain > beta:
                continue

            board.push(mv)
            score = self.quiesce(board, alpha, beta,
                                 not maximise_white, ply + 1)
            board.pop()

            if maximise_white:
                if score >= beta:
                    self.tt[key] = (-1, beta, None)
                    return beta
                alpha = max(alpha, score)
            else:
                if score <= alpha:
                    self.tt[key] = (-1, alpha, None)
                    return alpha
                beta = min(beta, score)

        result = alpha if maximise_white else beta
        self.tt[key] = (-1, result, None)
        return result

    # ───────── move ordering ────────────────────────────────────────────
    def _ordered_moves(self, board):
        caps, checks, quiet = [], [], []
        for mv in board.legal_moves:
            if board.is_capture(mv):
                caps.append(mv)
            elif board.gives_check(mv):
                checks.append(mv)
            else:
                quiet.append(mv)

        def mvv_lva(m):
            victim = chess.PAWN if board.is_en_passant(m) else \
                     (board.piece_at(m.to_square).piece_type
                      if board.piece_at(m.to_square) else 0)
            attacker = board.piece_at(m.from_square).piece_type
            return (-victim, attacker)

        caps.sort(key=mvv_lva)
        # deterministic ordering keeps search results stable
        quiet.sort(key=lambda m: m.uci())
        return caps + checks + quiet

    # ───────── TD‑0 update & persistence ────────────────────────────────
    def update_evaluation(self, history, result):
        next_v = 1.0 if result == "1-0" else -1.0 if result == "0-1" else DRAW_BIAS
        for zkey, white_move, fen in reversed(history):
            target = next_v if white_move else -next_v
            old = self.evaluation_table.get(zkey, 0.0)
            new = old + self.learning_rate * (target - old)
            self.evaluation_table[zkey] = new

            self.zkey_to_fen.setdefault(zkey, fen)
            st = self.zkey_stats.get(zkey, {"visits": 0, "last_seen": None})
            st["visits"] += 1
            st["last_seen"] = datetime.datetime.utcnow().timestamp()
            self.zkey_stats[zkey] = st

            dprint("TD‑update z=%016x old=%.3f new=%.3f", zkey, old, new)
            next_v = new if white_move else -new

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
                print("⚠️  could not load eval table:", e)
        return {}

    def _save_table(self):
        os.makedirs(os.path.dirname(self._table_path), exist_ok=True)
        with open(self._table_path, "wb") as f:
            pickle.dump(self.evaluation_table, f)
        with open(self._table_path.replace(".pkl", "_zkey2fen.pkl"), "wb") as f:
            pickle.dump(self.zkey_to_fen, f)
        with open(self._table_path.replace(".pkl", "_stats.pkl"), "wb") as f:
            pickle.dump(self.zkey_stats, f)
        dprint("Saved table  entries=%d", len(self.evaluation_table))

    # ───────── policy helpers (unchanged) ───────────────────────────────
    def board_to_zkey(self, board):      # external tool hook
        return zobrist.hash(board)

    def build_policy_table(self):
        policy = {}
        for zkey, fen in self.zkey_to_fen.items():
            board = chess.Board(fen)
            counts = {}
            for mv in board.legal_moves:
                board.push(mv)
                ck = zobrist.hash(board)
                board.pop()
                counts[mv.uci()] = self.zkey_stats.get(ck, {}).get("visits", 0)
            total = sum(counts.values())
            if total:
                policy[zkey] = {u: v / total for u, v in counts.items()}
            elif counts:
                n = len(counts)
                policy[zkey] = {u: 1 / n for u in counts}
        self.policy = policy
        return policy

    def save_policy(self, path):
        if not self.policy:
            raise RuntimeError("Call build_policy_table() first.")
        with open(path, "wb") as f:
            pickle.dump(self.policy, f)
        print(f"Policy saved → {path}")
