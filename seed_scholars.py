# seed_scholars.py
import chess
from bot.chess_bot import ChessBotAgent

board = chess.Board()
for san in ["e4","e5","Bc4","Nc6","Qh5","Nge7"]:
    board.push_san(san)
bot = ChessBotAgent(exploration_rate=0.0, search_depth=1)
# force 50 random draws from that FEN
for _ in range(100):
    bot.update_evaluation([(board.fen(), False)], "1-0")
bot._save_table()
