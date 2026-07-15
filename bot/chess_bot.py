# bot/chess_bot.py
from bot.utils.debug import dprint
import os, sys, time, datetime, random, pickle
import chess

from bot.utils.zobrist import zobrist
from bot.utils.opening_book import load_opening_book
from bot.evaluation.positional_heuristics import positional_score
import chess.polyglot
# ---------------------------------------------------------------------------
TABLE_FILE = "bot/evaluation_table_current/eval_table_phaseA.pkl"
DRAW_BIAS  = 0.0
INF        = float("inf")

# piece values (centipawns)
_PV = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
       chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20_000}

def piece_value(piece: chess.Piece | None) -> int:
    return _PV.get(piece.piece_type, 0) if piece else 0

def victim_value(board: chess.Board, sq) -> int:
    return piece_value(board.piece_at(sq))

def attacker_value(board: chess.Board, sq) -> int:
    atk = [board.piece_at(s).piece_type for s in board.attackers(board.turn, sq)]
    return min(_PV[t] for t in atk) if atk else 0
# ---------------------------------------------------------------------------


class ChessBotAgent:
    """
    TD(lambda) learner (lambda=1.0 gives Monte-Carlo returns) with an
    epsilon-greedy alpha-beta search and capture-only quiescence.
    """

    def __init__(self,
                 exploration_rate=0.1,
                 learning_rate=0.02,
                 save_interval=50,
                 table_path=TABLE_FILE,
                 search_depth=5,
                 material_weight=0.15,
                 positional_weight=0.05,
                 gamma=0.99,
                 td_lambda=1.0,
                 use_quiescence=False,
                 quiescence_depth=5,
                 book_bin_path=None,
                track_fens=True):

        # config
        self.exploration_rate  = exploration_rate
        self.learning_rate     = learning_rate
        self.save_interval     = save_interval
        self.search_depth      = max(1, search_depth)
        self.material_weight   = material_weight
        self.positional_weight = positional_weight
        self.gamma             = gamma
        self.td_lambda         = td_lambda
        self.use_quiescence    = use_quiescence
        self.quiescence_depth  = quiescence_depth
        self.track_fens        = track_fens

        # persistent tables
        self._table_path      = table_path
        self.evaluation_table = self._load_table()
        self.zkey_to_fen      = {}
        self.zkey_stats       = {}
        self.tt               = {}   # key -> (depth, value, best_move)
        self.history          = [[0]*64 for _ in range(64)]  # [from_sq][to_sq]

        if self.track_fens and os.path.exists(table_path.replace(".pkl", "_zkey2fen.pkl")):
            with open(table_path.replace(".pkl", "_zkey2fen.pkl"), "rb") as f:
                self.zkey_to_fen = pickle.load(f)
        if os.path.exists(table_path.replace(".pkl", "_stats.pkl")):
            with open(table_path.replace(".pkl", "_stats.pkl"), "rb") as f:
                self.zkey_stats = pickle.load(f)

        # opening book: polyglot .bin first, FEN-dict pkl fallback
        self._book_bin_path = book_bin_path if book_bin_path and os.path.exists(book_bin_path) else None
        book_path = os.path.join(os.path.dirname(__file__), "opening_book.pkl")
        self.opening_book = load_opening_book(book_path)

        self.games_since_save = 0
        self.quiesce_calls    = 0
        dprint("Bot created  LR=%.3f  eps=%.3f  depth=%d",
               self.learning_rate, self.exploration_rate, self.search_depth)

    # --- evaluation helpers ---
    @staticmethod
    def _material(board: chess.Board) -> float:
        vals = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9}
        return sum(v * (len(board.pieces(p, chess.WHITE)) -
                        len(board.pieces(p, chess.BLACK)))
                   for p, v in vals.items())

    def _state_value(self, board: chess.Board, zKey: int | None = None) -> float:
        if zKey is None:
            zKey = zobrist.hash(board)
        if self.track_fens:
            self.zkey_to_fen.setdefault(zKey, board.fen())
        base = self.evaluation_table.get(zKey, 0.0)
        mat  = self._material(board)
        pos  = positional_score(board)
        return base + self.material_weight * mat + self.positional_weight * pos

    def _book_move(self, board):
        """Book move for this position, or None. Polyglot .bin first, FEN-dict fallback."""
        if self._book_bin_path:
            try:
                with chess.polyglot.open_reader(self._book_bin_path) as reader:
                    return reader.weighted_choice(board).move
            except IndexError:
                pass   # not in polyglot; try FEN-dict
        fen = board.fen()
        if fen in self.opening_book:
            return chess.Move.from_uci(random.choice(self.opening_book[fen]))
        return None

    def choose_move(self, board: chess.Board):
        """Pick a move: opening book, then epsilon-greedy random, then alpha-beta search."""
        self._deadline = None   # fixed-depth search: no time limit

        # opening book
        mv = self._book_move(board)
        if mv:
            return mv

        legal = list(board.legal_moves)
        if not legal:
            return None            # no legal moves: game over

        # epsilon-greedy: occasionally play a random move to keep exploring
        if random.random() < self.exploration_rate:
            return random.choice(legal)

        # search; White maximizes, Black minimizes
        maximise_white = (board.turn == chess.WHITE)
        val, mv = self._alphabeta(board, self.search_depth,
                                -INF, +INF, maximise_white)

        # fall back to a random move if search returned nothing
        return mv or random.choice(legal)

    def choose_move_timed(self, board: chess.Board, time_per_move: float):
        # opening book first
        mv = self._book_move(board)
        if mv:
            return mv
        start = time.time()
        self._deadline = start + time_per_move   # hard stop the search
        maximise = board.turn == chess.WHITE
        best = random.choice(list(board.legal_moves))
        DELTA = 0.20  # aspiration margin, about one pawn on this engine's scale

        # depth 1 on a full window for an initial score
        val, mv = self._alphabeta(board, 1, -INF, INF, maximise)
        if mv:
            best = mv

        # iterative deepening within the time budget
        for depth in range(2, self.search_depth + 1):
            if time.time() - start >= time_per_move * 0.35:
                break
            try:
                # narrow window around the last score
                lo, hi = val - DELTA, val + DELTA
                result_val, result_mv = self._alphabeta(board, depth, lo, hi, maximise)

                # fail-low: widen downward and re-search
                if result_val <= lo:
                    result_val, result_mv = self._alphabeta(board, depth, -INF, hi, maximise)
                # fail-high: widen upward and re-search
                elif result_val >= hi:
                    result_val, result_mv = self._alphabeta(board, depth, lo, INF, maximise)

                if result_mv:
                    best = result_mv
                val = result_val
            except TimeoutError:
                break

        return best

    def _alphabeta(self, board: chess.Board, depth: int, alpha: float, beta: float, maximise_white: bool):
        """
        Alpha-beta search with a transposition table and optional quiescence.

        Args:
            board           chess.Board, mutated in place via push/pop
            depth           plies left to search before the leaf
            alpha, beta     search-window bounds
            maximise_white  True if this node maximizes (White), else minimizes

        Returns (value, best_move); best_move is None at terminal/leaf nodes.
        """
        zKey = zobrist.hash(board)

        # time guard: stop if we have blown the move budget
        if getattr(self, "_deadline", None) and time.time() >= self._deadline:
            raise TimeoutError

        # terminal position
        if board.is_game_over():
            if board.is_checkmate():
                return (-INF if board.turn == chess.WHITE else INF), None
            return DRAW_BIAS, None  # stalemate / repetition / 50-move / material

        # transposition table: reuse a result searched at least this deep
        if zKey in self.tt and self.tt[zKey][0] >= depth:
            return self.tt[zKey][1], self.tt[zKey][2]

        # leaf: max depth reached
        if depth == 0:
            # cached quiescence result (depth flag -1)
            if zKey in self.tt and self.tt[zKey][0] == -1:
                return self.tt[zKey][1], None
            # extend on captures if quiescence is enabled
            if self.use_quiescence and not board.is_game_over():
                self.quiesce_calls += 1
                val = self.quiesce(board, alpha, beta,
                                board.turn == chess.WHITE, 0)
                return val, None
            # otherwise static evaluation
            return self._state_value(board, zKey), None

        # search each move (captures, checks, then quiet)
        best_move = None
        for mv in self._ordered_moves(board):
            board.push(mv)

            if board.halfmove_clock >= 8 and board.can_claim_draw():
                val = DRAW_BIAS
            else:
                # recurse one ply deeper; flip the side to move
                val, _ = self._alphabeta(board, depth - 1,
                                    alpha, beta, not maximise_white)
            board.pop()

            if maximise_white:              # maximizing (White)
                if val > alpha:
                    alpha, best_move = val, mv
                if alpha >= beta:           # beta cutoff
                    if not board.is_capture(mv):
                        self.history[mv.from_square][mv.to_square] += depth * depth
                    break
            else:                           # minimizing (Black)
                if val < beta:
                    beta, best_move = val, mv
                if beta <= alpha:           # alpha cutoff
                    if not board.is_capture(mv):
                        self.history[mv.from_square][mv.to_square] += depth * depth
                    break

        # no move chosen (e.g. everything pruned); fall back safely
        if best_move is None:
            moves = list(board.legal_moves)
            if moves:
                best_move = random.choice(moves)
            else:
                # no legal moves: treat as stalemate
                best_val = self._state_value(board)
                self.tt[zKey] = (depth, best_val, None)
                return best_val, None

        # best value is the tightened bound
        best_val = alpha if maximise_white else beta
        self.tt[zKey] = (depth, best_val, best_move)   # cache result
        return best_val, best_move

    # --- quiescence search ---
    def quiesce(self, board, alpha, beta, maximise_white, curr_depth):
        """
        Extend the search on captures only until the position is quiet.

        Keeps the caller's alpha-beta window and orders captures by MVV-LVA.
        Results are cached in the TT with depth flag -1 so the main search
        can tell them apart from full-depth entries.
        """
        zKey = zobrist.hash(board)

        if board.is_game_over():
            if board.is_checkmate():
                return -INF if board.turn == chess.WHITE else INF
            return DRAW_BIAS

        # cached quiescence result
        if zKey in self.tt and self.tt[zKey][0] == -1:
            return self.tt[zKey][1]

        # stand-pat evaluation, returned if every capture is pruned
        static_val = self._state_value(board, zKey)
        best = static_val

        if maximise_white:                  # maximizing (White)
            if static_val >= beta:
                return beta
            alpha = max(alpha, static_val)
        else:                               # minimizing (Black)
            if static_val <= alpha:
                return alpha
            beta = min(beta, static_val)

        # depth limit reached
        if curr_depth >= self.quiescence_depth:
            self.tt[zKey] = (-1, static_val, None)
            return static_val

        # captures only, in MVV-LVA order
        moves = [move for move in board.legal_moves if board.is_capture(move)]
        moves.sort(key=lambda m: (-victim_value(board, m.to_square),
                                attacker_value(board, m.from_square)))

        for m in moves:
            gain = piece_value(board.piece_at(m.to_square))

            # delta pruning: skip captures that cannot reach the window
            if maximise_white and static_val + gain < alpha:
                continue
            if not maximise_white and static_val - gain > beta:
                continue

            board.push(m)
            if board.can_claim_draw():
                score = DRAW_BIAS
            else:
                # recurse one capture deeper
                score = self.quiesce(board, alpha, beta,
                                    not maximise_white, curr_depth + 1)
            board.pop()

            if maximise_white:
                if score > best:
                    best = score
                alpha = max(alpha, score)
                if alpha >= beta:
                    self.tt[zKey] = (-1, beta, None)
                    return beta
            else:
                if score < best:
                    best = score
                beta = min(beta, score)
                if beta <= alpha:
                    self.tt[zKey] = (-1, alpha, None)
                    return alpha

        # fail-soft: return the best score found
        self.tt[zKey] = (-1, best, None)
        return best

    # --- move ordering ---
    def _ordered_moves(self, board):
        """Order moves (captures, checks, then quiet) so alpha-beta prunes sooner."""
        caps   = []   # captures
        checks = []   # non-capturing checks
        quiet  = []   # everything else

        for move in board.legal_moves:
            if board.is_capture(move):
                caps.append(move)
            elif board.gives_check(move):
                checks.append(move)
            else:
                quiet.append(move)

        # MVV-LVA: most valuable victim, least valuable attacker
        def mvv_lva(move):
            victim = chess.PAWN if board.is_en_passant(move) else \
                    (board.piece_at(move.to_square).piece_type
                    if board.piece_at(move.to_square) else 0)
            attacker = board.piece_at(move.from_square).piece_type
            return (-victim, attacker)

        caps.sort(key=mvv_lva)
        # quiet moves by history heuristic (more cutoffs first)
        quiet.sort(key=lambda m: self.history[m.from_square][m.to_square], reverse=True)
        return caps + checks + quiet

    # --- TD learning ---
    def update_evaluation(self, history, result):
        lam = self.td_lambda
        # game result from White's view: +1 win, -1 loss, 0 draw
        final_reward = 1.0 if result == "1-0" else -1.0 if result == "0-1" else DRAW_BIAS

        # value estimate and return of the position one ply later
        next_value = next_return = None
        for i, entry in enumerate(reversed(history)):
            zkey   = entry[0]
            fen    = entry[2] if len(entry) > 2 else None
            pieces = entry[3] if len(entry) > 3 else None
            if i == 0:
                target = final_reward         # terminal position: use the result directly
            else:
                # blend the successor's value (weight 1-lam) with its return (weight lam)
                target = self.gamma * ((1.0 - lam) * next_value + lam * next_return)
            old_value = self.evaluation_table.get(zkey, 0.0)
            new_value = old_value + self.learning_rate * (target - old_value)
            self.evaluation_table[zkey] = new_value

            if self.track_fens and fen is not None:
                self.zkey_to_fen.setdefault(zkey, fen)
            st = self.zkey_stats.get(zkey, {"visits": 0, "last_seen": None})
            st["visits"] += 1
            st["last_seen"] = datetime.datetime.utcnow().timestamp()
            if pieces is not None:
                st["pieces"] = pieces   # lets prune keep endgames
            self.zkey_stats[zkey] = st

            # this position is the successor for the next (earlier) ply
            next_value, next_return = new_value, target

        self.games_since_save += 1
        if self.games_since_save >= self.save_interval:
            self._save_table()
            self.games_since_save = 0

    # --- persistence ---
    def _load_table(self):
        if os.path.exists(self._table_path):
            try:
                with open(self._table_path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                print("could not load eval table:", e, file=sys.stderr)
        return {}

    def _atomic_dump(self, obj, path):
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            pickle.dump(obj, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)

    def _save_table(self):
        os.makedirs(os.path.dirname(self._table_path), exist_ok=True)
        self._atomic_dump(self.evaluation_table, self._table_path)
        if self.track_fens:
            self._atomic_dump(self.zkey_to_fen, self._table_path.replace(".pkl", "_zkey2fen.pkl"))
        self._atomic_dump(self.zkey_stats, self._table_path.replace(".pkl", "_stats.pkl"))
        dprint("Saved table entries=%d", len(self.evaluation_table))

    def board_to_zkey(self, board):      # external tool hook
        return zobrist.hash(board)
