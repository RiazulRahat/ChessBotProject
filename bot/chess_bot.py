# bot/chess_bot.py
import time
import datetime
import chess, random, pickle, os
from bot.utils.zobrist import zobrist
from bot.evaluation.positional_heuristics import positional_score
from bot.utils.opening_book import load_opening_book

from bot.evaluation.positional_heuristics import pawn_structure_penalty, piece_square_bonus, piece_safety_penalty, king_safety_bonus, piece_development_bonus, passed_pawn_bonus, bishop_pair_bonus, positional_score   ## helper

TABLE_FILE = "bot/evaluation_table_current/eval_table_zobrist_pruned.pkl"    # shared pickle on disk
DRAW_BIAS  = 0.2                     # +0.2 from White’s PoV → draw

INF = float("inf")

# ─── Tactical helper functions for quiescence ───────────────────────────
PIECE_VALUES = {
    chess.PAWN:   100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK:   500,
    chess.QUEEN:  900,
    chess.KING:   20000
}

def piece_value(piece: chess.Piece | None) -> int:
    return PIECE_VALUES.get(piece.piece_type, 0) if piece else 0

def victim_value(board: chess.Board, sq: chess.Square) -> int:
    p = board.piece_at(sq)
    return piece_value(p)

def attacker_value(board: chess.Board, sq: chess.Square) -> int:
    # MVV-LVA: least-valuable attacker first
    attackers = [board.piece_at(sq2).piece_type
                 for sq2 in board.attackers(board.turn, sq)]
    if not attackers:
        return 0
    return min(PIECE_VALUES[t] for t in attackers)

def see(board: chess.Board, move: chess.Move) -> bool:
    try:
        return board.see(move) >= 0
    except AttributeError:
        # fallback if python-chess <1.7
        victim = piece_value(board.piece_at(move.to_square))
        attacker = piece_value(board.piece_at(move.from_square))
        return victim >= attacker
# ────────────────────────────────────────────────────────────────────────

class ChessBotAgent:
    """
    Tiny TD-learning chess agent with
    • TD(0) value updates
    • ε-greedy NN-ply alpha-beta search (default depth = 3)
    """

    def __init__(self,
                 exploration_rate=0.1,
                 learning_rate=0.05, mobility_weight=0.05,
                 save_interval=50,
                 table_path: str = TABLE_FILE,
                 search_depth: int = 3,
                 positional_weight: float = 1.0,
                 use_policy: bool = True,
                 use_quiescence: bool = False,
                 quiescence_depth: int = 5):     # added quiescence
        self.exploration_rate = exploration_rate
        self.learning_rate    = learning_rate
        self.mobility_weight = mobility_weight
        self.save_interval    = save_interval
        self._table_path      = table_path
        self.search_depth     = max(1, search_depth)
        self.positional_weight = positional_weight
        self.use_policy       = use_policy
        self.use_quiescence = use_quiescence
        self.quiescence_depth = quiescence_depth

        self.games_since_save = 0
        self.evaluation_table = self._load_table()
        fen_path = self._table_path.replace(".pkl", "_zkey2fen.pkl")
        if os.path.exists(fen_path):
            with open(fen_path, "rb") as f:
                self.zkey_to_fen = pickle.load(f)
        else:
            self.zkey_to_fen = {}
        self.zkey_stats    = {}
        self.tt = {}  
        stats_path = self._table_path.replace(".pkl", "_stats.pkl")
        if os.path.exists(stats_path):
            with open(stats_path, "rb") as f:
                self.zkey_stats = pickle.load(f)
        self.policy = {}
        policy_path = os.path.join(os.path.dirname(__file__), "policy_book.pkl")
        try:
            with open(policy_path, "rb") as f:
                self.policy = pickle.load(f)
        except FileNotFoundError:
            pass

        # Loading the book to the bot
        book_path = os.path.join(os.path.dirname(__file__),
                                 "opening_book.pkl")
        self.opening_book = load_opening_book(book_path)


    # Add this helper:
    @staticmethod
    def piece_value(piece: chess.Piece) -> float:
        # small lookup by type in pawn‐units
        vals = {chess.PAWN:1.0, chess.KNIGHT:3.0, chess.BISHOP:3.0,
                chess.ROOK:5.0, chess.QUEEN:9.0}
        return vals.get(piece.piece_type, 0.0)  
    # ───────── Evaluation ────────────────────────────────────────────────
    @staticmethod
    def _material_score(board: chess.Board) -> float:
        vals = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9}
        return sum(v * (len(board.pieces(p, chess.WHITE)) -
                        len(board.pieces(p, chess.BLACK)))
                   for p, v in vals.items())

    def _state_value(self, board: chess.Board) -> float:
        # 1) lookup by Zobrist hash; fallback to material
        key  = zobrist.hash(board)
        # ensure every key gets a FEN mapping, even if we never update it
        if key in self.evaluation_table:
            self.zkey_to_fen.setdefault(key, board.fen())
        
        base = self.evaluation_table.get(key, self._material_score(board))
        # 2) positional + mobility bonus
        pos = positional_score(board)
        return base + self.positional_weight * pos

    # ───────── Public move selection ─────────────────────────────────────
    def choose_move(self, board: chess.Board):

        fen = board.fen()

        # 0) Opening book lookup
        if fen in self.opening_book:
            # pick randomly among book moves to add variety
            uci_move = random.choice(self.opening_book[fen])
            # print(f"[Book] {'White' if board.turn else 'Black'} plays {uci_move} from book")    # Debug line
            return chess.Move.from_uci(uci_move)
        

        # 1) instant lookup if we have it
        if self.use_policy and fen in self.policy:
                return chess.Move.from_uci(self.policy[fen])
        
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
        key = zobrist.hash(board)
        if key in self.tt and self.tt[key][0] >= depth:
            return self.tt[key][1], self.tt[key][2]

        if depth == 0 and self.use_quiescence and not board.is_game_over():
            val = self.quiesce(board, alpha, beta, maximise_white)
            return val, None
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

        val = alpha if maximise_white == board.turn else beta
        self.tt[key] = (depth, val, best_move)
        return val, best_move
    
    
    
    def quiesce(self, board: chess.Board, alpha: float, beta: float, maximise_white: bool, ply=0, max_ply=None) -> float:
        """
        Simple capture‐and‐check quiescence search.
        """
        if max_ply is None:
            max_ply = self.quiescence_depth

        stand = self._state_value(board)
        # 1) Stand check
        if maximise_white:
            if stand >= beta:
                return beta
            alpha = max(alpha, stand)
        else:
            if stand <= alpha:
                return alpha
            beta = min(beta, stand)

        # 2) Only captures/checks
        caps = [mv for mv in board.legal_moves
            if board.is_capture(mv) or board.gives_check(mv)]
        # (optional: sort by MVV-LVA here)
        caps.sort(key=lambda m: (
            -victim_value(board, m.to_square),
            attacker_value(board, m.from_square)
        ))

        improved = False
        for mv in caps:
            if ply >= max_ply:
                continue

            # delta-pruning (material gain only)
            gain = self.piece_value(board.piece_at(mv.to_square))
            if maximise_white:
                if stand + gain < alpha:
                    continue
            else:
                if stand - gain > beta:
                    continue

            improved = True
            board.push(mv)
            # propagate the minimax signs
            score = self.quiesce(board, alpha, beta, not maximise_white, ply+1, max_ply)
            board.pop()

            if maximise_white:
                if score >= beta:
                    return beta
                alpha = max(alpha, score)
            else:
                if score <= alpha:
                    return alpha
                beta = min(beta, score)

        return stand if not improved else (alpha if maximise_white else beta)
    
    def choose_move_timed(self, board: chess.Board, time_per_move: float):
        """
        Iterative‐deepening wrapper over _alphabeta that runs up to time_per_move seconds.
        """
        best_move = None
        start     = time.time()
        # You can iterate to some max depth (e.g. self.search_depth or a new max)
        max_d = self.search_depth
        for depth in range(1, max_d+1):
            val, mv = self._alphabeta(board, depth, -INF, +INF, board.turn)
            if mv:
                best_move = mv
            # stop if we’ve run out of time
            if time.time() - start > time_per_move:
                break
        return best_move or random.choice(list(board.legal_moves))

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
        
        # Randomizing the top move
        random.shuffle(quiet)

        return caps + checks + quiet

    # ───────── TD-0 learning ─────────────────────────────────────────────
    def update_evaluation(self, game_history, result):
        if   result == "1-0":  next_v = 1.0
        elif result == "0-1":  next_v = -1.0
        else:                  next_v = DRAW_BIAS

        for zkey, white_to_move, fen in reversed(game_history):
            target = next_v if white_to_move else -next_v
            old    = self.evaluation_table.get(zkey, 0.0)
            new    = old + self.learning_rate * (target - old)
            self.evaluation_table[zkey] = new
            # record the FEN (only first occurrence is kept)
            self.zkey_to_fen.setdefault(zkey, fen)
            # update per-key stats
            stats = self.zkey_stats.get(zkey, {"visits": 0, "last_seen": None})
            stats["visits"]   += 1
            stats["last_seen"] = datetime.datetime.utcnow().timestamp()
            self.zkey_stats[zkey] = stats
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
        # save Zobrist-keyed table
        with open(self._table_path, "wb") as f:
            pickle.dump(self.evaluation_table, f)

        with open(self._table_path.replace(".pkl", "_zkey2fen.pkl"), "wb") as f:
            pickle.dump(self.zkey_to_fen, f)

        # also save per-key stats
        stats_path = self._table_path.replace(".pkl", "_stats.pkl")
        with open(stats_path, "wb") as f:
            pickle.dump(self.zkey_stats, f)


    def prune_table(self, max_entries: int, min_visits: int = 0):
        """
        Prune evaluation_table so it ends up with at most `max_entries` entries:
        1. Keep every key that has no fen mapping (we never drop these).
        2. Of the remaining mapped-and-eligible keys (visits ≥ min_visits),
            keep the top (max_entries - num_unmapped) by visit count.
        3. Drop all mapped keys whose visit count < min_visits.
        4. Finally, drop everything else from evaluation_table, zkey_to_fen, and zkey_stats.
        """
        # 1) collect unmapped (always keep)
        unmapped = set(self.evaluation_table) - set(self.zkey_to_fen)
        num_unmapped = len(unmapped)

        # 2) filter mapped keys by min_visits
        #    (only consider keys that both have a fen mapping and a stats entry)
        eligible_mapped = {
            k for k in self.evaluation_table
            if (k in self.zkey_to_fen
                and k in self.zkey_stats
                and self.zkey_stats[k]["visits"] >= min_visits)
        }

        # 3) how many “visited” slots remain?
        slots_for_visited = max_entries - num_unmapped
        if slots_for_visited < 0:
            # too many unmapped → keep them all, drop all mapped
            slots_for_visited = 0
            print(
                f"Warning: {num_unmapped} unmapped entries > max_entries={max_entries}. "
                "Keeping all unmapped; dropping all mapped."
            )

        # 4) pick the top‐visited among eligible_mapped
        #    sort by visits descending, then slice
        sorted_by_visits = sorted(
            eligible_mapped,
            key=lambda k: self.zkey_stats[k]["visits"],
            reverse=True
        )
        top_mapped = set(sorted_by_visits[:slots_for_visited])

        # 5) final keep set = unmapped ∪ top_mapped
        keep = unmapped | top_mapped

        # 6) prune all three tables
        self.evaluation_table = {
            k: v for k, v in self.evaluation_table.items() if k in keep
        }
        self.zkey_to_fen = {
            k: f for k, f in self.zkey_to_fen.items() if k in keep
        }
        self.zkey_stats = {
            k: s for k, s in self.zkey_stats.items() if k in keep
        }

        print(
            f"Pruned to {len(self.evaluation_table)} entries "
            f"(target ≤ {max_entries}, min_visits={min_visits})."
        )
