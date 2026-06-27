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
    # empty table → _state_value = material + positional
    a.evaluation_table = {}
    return a

def test_quiesce_no_captures_returns_stand(agent):
    board = chess.Board()  # startpos has no capture
    stand = agent._state_value(board)
    q = agent.quiesce(board, -999, +999, board.turn, 0)
    assert q == pytest.approx(stand)

def test_quiesce_single_capture(agent):
    # White pawn on e5, Black pawn on d6
    board = chess.Board("8/8/3p4/4P3/8/8/8/8 w - - 0 1")
    # compute stand and “after” manually
    stand = agent._state_value(board)
    mv = chess.Move.from_uci("e5d6")
    board.push(mv)
    after = agent._state_value(board)
    board.pop()
    # quiesce must pick the capture’s static value exactly
    q = agent.quiesce(board, -999, +999, board.turn, 0)
    assert q == pytest.approx(after)

def test_quiesce_delta_pruning(agent):
    # Position with only a bishop capture (small material gain)
    board = chess.Board("8/8/4b3/4P3/8/8/8/8 w - - 0 1")
    stand = agent._state_value(board)
    gain = piece_value(board.piece_at(chess.E6))  # bishop on e6
    # force alpha so stand+gain < alpha → skip capture
    alpha = stand + gain + 0.1
    q = agent.quiesce(board, alpha, +999, board.turn, 0)
    assert q == pytest.approx(stand)

def test_quiesce_tactical_fork(agent):
    # simple pawn fork e6→f7 attacking rook on f8
    board = chess.Board("8/5r2/4P3/8/8/8/8/8 w - - 0 1")
    mv = chess.Move.from_uci("e6f7")
    board.push(mv)
    after = agent._state_value(board)
    board.pop()
    q = agent.quiesce(board, -999, +999, board.turn, 0)
    assert q == pytest.approx(after)
