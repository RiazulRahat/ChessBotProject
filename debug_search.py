#!/usr/bin/env python3
import chess
from bot.chess_bot import ChessBotAgent

agent = ChessBotAgent(
    exploration_rate=0.0,
    learning_rate=0.0,
    search_depth=1,
    use_quiescence=True,
    quiescence_depth=4,
)
# blank table so state_value=material+positional
agent.evaluation_table = {}

tests = [
    # no captures
    ("startpos", None),
    # single capture
    ("8/8/3p4/4P3/8/8/8/8 w - - 0 1", "e5d6"),
    # little tactical fork
    ("8/5r2/4P3/8/8/8/8/8 w - - 0 1", "e6f7"),
]

for fen, uci in tests:
    board = chess.Board() if fen=="startpos" else chess.Board(fen)
    α, β = -999, +999
    # full call via alphabeta at depth=0
    val0, _ = agent._alphabeta(board, 0, α, β, board.turn)
    print(f"\nFEN: {fen}")
    print(" raw stand:", agent._state_value(board))
    if uci:
        board.push(chess.Move.from_uci(uci))
        print(" after",uci,"val:", agent._state_value(board))
        board.pop()
    print(" via quiesce:", val0)
