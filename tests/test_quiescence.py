import chess
import pytest
from bot.chess_bot import ChessBotAgent, piece_value

@pytest.fixture
def agent():
    a = ChessBotAgent(
        exploration_rate=0.0,
        learning_rate=0.0,
        search_depth=1,
        use_quiescence=True,
        quiescence_depth=5,
    )
    # empty table -> _state_value = material + positional only
    a.evaluation_table = {}
    return a

def test_quiesce_no_captures_returns_stand(agent):
    board = chess.Board()  # startpos has no captures available at depth 0
    stand = agent._state_value(board)
    q = agent.quiesce(board, -999, +999, board.turn == chess.WHITE, 0)
    assert q == pytest.approx(stand)

def test_quiesce_single_capture(agent):
    # White pawn on e5, Black pawn on d6; kings in corners keep is_game_over False
    board = chess.Board("7k/8/3p4/4P3/8/8/8/7K w - - 0 1")
    mv = chess.Move.from_uci("e5d6")
    board.push(mv)
    after = agent._state_value(board)
    board.pop()
    q = agent.quiesce(board, -999, +999, board.turn == chess.WHITE, 0)
    assert q == pytest.approx(after)

def test_quiesce_delta_pruning(agent):
    # Bishop on e6 vs White pawn on e5; kings keep position valid
    board = chess.Board("7k/8/4b3/4P3/8/8/8/7K w - - 0 1")
    stand = agent._state_value(board)
    gain = piece_value(board.piece_at(chess.E6))  # bishop value in centipawns
    # set alpha so stand + gain < alpha -> delta pruning skips the capture
    alpha = stand + gain + 0.1
    q = agent.quiesce(board, alpha, +999, board.turn == chess.WHITE, 0)
    assert q == pytest.approx(stand)

def test_quiesce_tactical_fork(agent):
    # White pawn on e6 captures Black rook on f7
    board = chess.Board("7k/5r2/4P3/8/8/8/8/7K w - - 0 1")
    mv = chess.Move.from_uci("e6f7")
    board.push(mv)
    after = agent._state_value(board)
    board.pop()
    q = agent.quiesce(board, -999, +999, board.turn == chess.WHITE, 0)
    assert q == pytest.approx(after)
