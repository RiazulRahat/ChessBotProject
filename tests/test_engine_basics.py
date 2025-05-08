import chess, pytest, random
from bot.chess_bot import ChessBotAgent
from bot.utils.zobrist import zobrist

BOT_KWARGS = dict(
    exploration_rate=0.0,    # keep it deterministic
    search_depth=2,          # quick
    use_quiescence=True,
)

@pytest.fixture(scope="module")
def bot():
    return ChessBotAgent(**BOT_KWARGS)

# ───── material / positional evaluation ──────────────────────────────
def test_eval_symmetry(bot):
    board = chess.Board()
    assert bot._state_value(board) == pytest.approx(0)

def test_zobrist_consistency(bot):
    board = chess.Board()
    key1 = zobrist.hash(board)
    board.push(chess.Move.from_uci("e2e4"))
    board.pop()
    key2 = zobrist.hash(board)
    assert key1 == key2, "Zobrist hash should round‑trip"

# ───── search invariants ─────────────────────────────────────────────
@pytest.mark.parametrize("fen", [
    chess.STARTING_FEN,
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",  # after 1…e5
    "8/8/8/8/8/8/8/K6k w - - 0 1",                                      # K vs k
])
def test_choose_move_returns_legal(bot, fen):
    board = chess.Board(fen)
    mv = bot.choose_move(board)
    assert mv in board.legal_moves

def test_search_value_monotonic(bot):
    board = chess.Board()
    v1, _ = bot._alphabeta(board, 1, -float('inf'), float('inf'), True)
    v2, _ = bot._alphabeta(board, 2, -float('inf'), float('inf'), True)
    assert abs(v2) >= abs(v1), "deeper search should refine value or keep it"

# ───── quiescence guard (no endless recapture loops) ────────────────
def test_quiesce_depth_cap(bot):
    board = chess.Board("8/8/8/5q2/6Q1/8/8/8 w - - 0 1")  # queen x queen skirmish
    bot.quiesce_calls = 0
    bot.quiesce(board, -float('inf'), float('inf'), True, 0)
    assert bot.quiesce_calls <= 50, "Quiescence should terminate quickly"
