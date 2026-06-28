# bot/chess_bot.py
from bot.utils.debug import dprint
import os, time, datetime, random, pickle
import chess

from bot.utils.zobrist import zobrist
from bot.utils.opening_book import load_opening_book
from bot.evaluation.positional_heuristics import positional_score
import chess.polyglot
# ────────────────────────────────────────────────────────────────────────
TABLE_FILE = "bot/evaluation_table_current/eval_table_phaseA.pkl"
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
                 save_interval=50,
                 table_path=TABLE_FILE,
                 search_depth=5,
                 material_weight=0.15,
                 positional_weight=0.05,
                 gamma=0.99,
                 use_quiescence=False,
                 quiescence_depth=5,
                 zobrist_keys_path="bot/zobrist_keys.pkl",
                 book_bin_path=None):

        # ── knobs --
        self.exploration_rate  = exploration_rate
        self.learning_rate     = learning_rate
        self.save_interval     = save_interval
        self.search_depth      = max(1, search_depth)
        self.material_weight   = material_weight
        self.positional_weight = positional_weight
        self.gamma             = gamma
        self.use_quiescence    = use_quiescence
        self.quiescence_depth  = quiescence_depth

        # ── persistent tables --
        self._table_path      = table_path
        self.evaluation_table = self._load_table()
        self.zkey_to_fen      = {}
        self.zkey_stats       = {}
        self.tt               = {}   # key → (depth, value, bestMove)
        self.history          = [[0]*64 for _ in range(64)]  # [from_sq][to_sq]

        if os.path.exists(table_path.replace(".pkl", "_zkey2fen.pkl")):
            with open(table_path.replace(".pkl", "_zkey2fen.pkl"), "rb") as f:
                self.zkey_to_fen = pickle.load(f)
        if os.path.exists(table_path.replace(".pkl", "_stats.pkl")):
            with open(table_path.replace(".pkl", "_stats.pkl"), "rb") as f:
                self.zkey_stats = pickle.load(f)

        # opening book — polyglot .bin takes priority; FEN-dict pkl is the fallback
        self._book_bin_path = book_bin_path if book_bin_path and os.path.exists(book_bin_path) else None
        book_path = os.path.join(os.path.dirname(__file__), "opening_book.pkl")
        self.opening_book = load_opening_book(book_path)

        # keep key array around for external tools
        with open(zobrist_keys_path, "rb") as f:
            self.zobrist_keys = pickle.load(f)

        self.games_since_save = 0
        self.quiesce_calls    = 0
        dprint("Bot created  LR=%.3f  ε=%.3f  depth=%d",
               self.learning_rate, self.exploration_rate, self.search_depth)

    # ───────── evaluation helper function──────────────────────────
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
        self.zkey_to_fen.setdefault(zKey, board.fen())
        base = self.evaluation_table.get(zKey, 0.0)
        mat  = self._material(board)
        pos  = positional_score(board)
        return base + self.material_weight * mat + self.positional_weight * pos




    def choose_move(self, board: chess.Board):
        """
        This Function takes in a Board state and returns the best move following a list of protocols

        --- Accessibility: Public ---

        Function: choose_move

        Parameter: chess.Board class
        Return: chess.Move class or None

        """
        
        # save fen of parameter - board object
        fen = board.fen()
        # save zobrist hash of parameter - board object
        zKey = zobrist.hash(board)

        # 0) Opening Book Fall-Through ----------
        # Try polyglot .bin book first (weighted random choice among book moves)
        if self._book_bin_path:
            try:
                with chess.polyglot.open_reader(self._book_bin_path) as reader:
                    entry = reader.weighted_choice(board)
                    return entry.move
            except IndexError:
                pass  # position not in polyglot book; fall through to FEN-dict

        if fen in self.opening_book:
            move = chess.Move.from_uci(random.choice(self.opening_book[fen]))
            return move

        # Check if there is any legal moves OR if no legal moves(eg Game Over) return None
        legal = list(board.legal_moves)
        if not legal:
            return None

        # 2) ε-greedy Exploration Rate - avoids overfitting on known paths ------
        if random.random() < self.exploration_rate:
            # Choose random legal move
            mv = random.choice(legal)
            return mv

        # 3) Search ------------------------------
        #    True if White's turn else False
        maximise_white = (board.turn == chess.WHITE)
        #    val - best_value, mv - best_move -> from αβ search (move object)
        val, mv = self._alphabeta(board, self.search_depth,
                                -INF, +INF, maximise_white)

        #    random legal move Fall-Back for no moves returned by αβ
        return mv or random.choice(legal)
    




    def choose_move_timed(self, board: chess.Board, time_per_move: float):
        start = time.time()
        maximise = board.turn == chess.WHITE
        best = random.choice(list(board.legal_moves))
        DELTA = 0.20  # ~1 pawn in this engine's evaluation scale

        # Depth 1: full window to get an initial score
        val, mv = self._alphabeta(board, 1, -INF, INF, maximise)
        if mv:
            best = mv

        for depth in range(2, self.search_depth + 1):
            if time.time() - start >= time_per_move:
                break
            lo, hi = val - DELTA, val + DELTA
            result_val, result_mv = self._alphabeta(board, depth, lo, hi, maximise)

            # Fail-low: widen downward and re-search
            if result_val <= lo:
                result_val, result_mv = self._alphabeta(board, depth, -INF, hi, maximise)
            # Fail-high: widen upward and re-search
            elif result_val >= hi:
                result_val, result_mv = self._alphabeta(board, depth, lo, INF, maximise)

            if result_mv:
                best = result_mv
            val = result_val

        return best



    def _alphabeta(self, board: chess.Board, depth: int, alpha: float, beta: float, maximise_white: bool):
        """
        α‑β search with transposition‐table and optional quiescence
    
        Recursively explores moves to the given depth, applying:
        1. State guard (checkmate/draw).
        2. TT lookup if a prior result at ≥ this depth is cached.
        3. At depth == 0: optional quiescence extension, else static evaluation.
        4. Main recursion with move ordering, α/β updates, and cutoffs.
        5. TT storage of (depth, best_value, best_move).

        --- Accessibility: Private ---

        Function: _alphabeta

        Parameters:
        board           – a chess.Board object (mutated via push/pop)
        depth           – remaining plies to search before quiescence(leaf)
        alpha, beta     – current α (max lower bound) and β (min upper bound).
        maximise_white  – True if this node maximizes(W), else minimizes(B)
        Return: Tuple  -> (value, best_move)
        – `value` is the minimax score from this board position  
        – `best_move` is the chosen chess.Move (or None for terminal/leaf)

        """
        
        # save zobrist hash of parameter - board object
        zKey = zobrist.hash(board)

        
        # 1) Terminal state ----------------------
        if board.is_game_over():
            if board.is_checkmate():
                # board.turn is the side that is checkmated (can't move, in check)
                return (-INF if board.turn == chess.WHITE else INF), None
            return DRAW_BIAS, None  # stalemate / repetition / 50-move / material
        # ----------------------------------------

        
        # 2) Look-up Transposition-Table ------
        
        # if zKey exists AND stored_depth is >= current depth (deeper search done)
        if zKey in self.tt and self.tt[zKey][0] >= depth:
            # return stored_value[1] and stored_move[2]
            return self.tt[zKey][1], self.tt[zKey][2]
        # -------------------------------------

        
        # 3) Base case, depth == 0, Leaf Positions 
        # Reached max given search depth ------
        if depth == 0:
            # quiescence hit before - uses special flag -1 for depth
            if zKey in self.tt and self.tt[zKey][0] == -1:
                # return previous quiescence call
                return self.tt[zKey][1], None
            # if quiescence turned on AND game is not over (defensive call - repeated)
            if self.use_quiescence and not board.is_game_over():
                # quiescence calls count (not really needed) - Uncomment for debugging
                # self.quiesce_calls += 1

                # extends search to include all captures/checks from this position
                val = self.quiesce(board, alpha, beta,
                                board.turn == chess.WHITE, 0)
                # returns a stable evaluation, than a raw evaluation score (slightly better)
                return val, None
            # if quiescence is disabled call static evaluation
            return self._state_value(board, zKey), None
        # ---------------------------------------

        
        # ^^ Move is not in TT and depth>0 and game is not over ^^
        
        
        # 4) Main Recursion Loop -----------------
        best_move = None
        
        # Loop through a sorted move list
        # Sort: TT move -> Captures -> ...
        for mv in self._ordered_moves(board):
            # apply move to board - for recursion only
            board.push(mv)
            # short-circuit: if this move immediately creates a claimable draw, penalise it
            # without recursing (prevents the bot from walking into repetition)
            if board.can_claim_draw():
                val = DRAW_BIAS
            else:
                # recursive call - (depth-1) - flip maximise_white because turn changes
                val, _ = self._alphabeta(board, depth - 1,
                                    alpha, beta, not maximise_white)
            # revert board
            board.pop()

            # White's turn (Maximizer)
            if maximise_white:
                # if the pushed move is better than alpha
                if val > alpha:
                    # update α and best_move (so far)
                    alpha, best_move = val, mv
                # β‑cutoff: Black will avoid this position
                if alpha >= beta:
                    if not board.is_capture(mv):
                        self.history[mv.from_square][mv.to_square] += depth * depth
                    break
            # Black's turn (Minimizer)
            else:
                # pushed move is better than beta
                if val < beta:
                    # update β and best_move (so far)
                    beta, best_move = val, mv
                # α-cutoff: White will avoid this position
                if beta <= alpha:
                    if not board.is_capture(mv):
                        self.history[mv.from_square][mv.to_square] += depth * depth
                    break

        
        # 5) If no move survived (legal moves might be empty in stalemate)
        # fall back instead of crashing
        if best_move is None:
            # if there is legal moves (rare case)
            moves = list(board.legal_moves)
            # if case - pick one at random
            if moves:
                best_move = random.choice(moves)
            # really no legal moves → treat as stalemate
            else:     
                # static value
                best_val = self._state_value(board)
                # add to TT
                self.tt[zKey] = (depth, best_val, None)
                return best_val, None

        # after if block ^ initialize the value to α for white and β for black
        best_val = alpha if maximise_white else beta
        # add to TT
        self.tt[zKey] = (depth, best_val, best_move)

        return best_val, best_move



    # ───────── quiescence search ────────────────────────────────────────
    def quiesce(self, board, alpha, beta, maximise_white, curr_depth):
        """
        This function extends the main α-β search in curr_depth layers deeper, for only captures

        Parameters:
            - board (chess.Board)
            - alpha (maximizer value)
            - beta (minimizer value)
            - maximise_white (True if white's turn, else False)
            - curr_depth (depth of quience search)

        Returns: val (float)

        Notes:
        * **Soundness:** Only 'legal' captures are explored and the algorithm maintains the α/β invariants
        * **Speed:** MVV-LVA ordering plus only captures so checks way less nodes
        * **Transposition Table:** entries are stored with '-1' depth so main search can distinguish between quiescence vs α/β
        """
        # Store the zobrist value of board object
        zKey = zobrist.hash(board)

        if board.is_game_over():
            if board.is_checkmate():
                return -INF if board.turn == chess.WHITE else INF
            return DRAW_BIAS

        # If key is in transposition table and previous quiescence search was done [-1]
        if zKey in self.tt and self.tt[zKey][0] == -1:
            return self.tt[zKey][1]    # return val

        # 'static' board state value (val)
        static_val = self._state_value(board, zKey)
        best = static_val  # stand-pat; returned when all captures are pruned

        # Compare static value
        # if white's turn
        if maximise_white:
            if static_val >= beta:
                return beta
            alpha = max(alpha, static_val)
        # if black's turn
        else:
            if static_val <= alpha:
                return alpha
            beta = min(beta, static_val)

        # limit search depth of quiescence
        if curr_depth >= self.quiescence_depth:
            # insert into transposition table
            self.tt[zKey] = (-1, static_val, None)
            return static_val

        # Filter: separate captures from all moves in a list
        moves = [move for move in board.legal_moves if board.is_capture(move)]

        # One-liner sort
        moves.sort(key=lambda m: (-victim_value(board, m.to_square),
                                attacker_value(board, m.from_square)))

        # iterate sorted move list
        for m in moves:
            # check the piece values
            gain = piece_value(board.piece_at(m.to_square))

            # If best capture does not improve val, continue
            if maximise_white and static_val + gain < alpha:
                continue
            if not maximise_white and static_val - gain > beta:
                continue

            # Push the best move into the board
            board.push(m)

            if board.can_claim_draw():
                score = DRAW_BIAS
            else:
                # Recursion - same alpha beta bounds, flip turn, increase depth by 1
                score = self.quiesce(board, alpha, beta,
                                    not maximise_white, curr_depth + 1)
            # Pop to restore position
            board.pop()

            # returns for cutoffs
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

        # Final Quiescence score — actual best found (fail-soft)
        self.tt[zKey] = (-1, best, None)
        return best


    # ───────── move ordering ────────────────────────────────────────────
    def _ordered_moves(self, board):
        """
        'Move Ordering' heuristic that makes α‑β search more efficient by trying the best moves first
        """
        # categorizing moves into lists
        caps = []    # All captures
        checks = []  # 
        quiet = []   # Not captures/checks

        # Iterate through the legal moves and add to empty lists
        for move in board.legal_moves:
            if board.is_capture(move):
                caps.append(move)
            elif board.gives_check(move):
                checks.append(move)
            else:
                quiet.append(move)

        # Most-Valuable-Victim, Least_Valuable_Attacker Key
        def mvv_lva(move):
            # Pawn for en_passant, else captured piece or 0
            victim = chess.PAWN if board.is_en_passant(move) else \
                    (board.piece_at(move.to_square).piece_type
                    if board.piece_at(move.to_square) else 0)
            # Attacking Piece
            attacker = board.piece_at(move.from_square).piece_type
            
            return (-victim, attacker)

        # sort by the mvv_lva value - explored first
        caps.sort(key=mvv_lva)
        # sort by history heuristic score (higher = tried more cutoffs)
        quiet.sort(key=lambda m: self.history[m.from_square][m.to_square], reverse=True)
        # Concatenate in order
        return caps + checks + quiet


    # TD(0) Learning Core
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

            # gamma discounts the value passed to earlier positions
            next_v = (new if white_move else -new) * self.gamma

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

    def board_to_zkey(self, board):      # external tool hook
        return zobrist.hash(board)


