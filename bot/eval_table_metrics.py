"""
Quick diagnostics for a TD(0) value table.

Run:   python bot/eval_table_metrics.py
"""

import statistics, chess, random
from pathlib import Path
from chess_bot import ChessBotAgent     # your trained bot

TABLE_PATH = Path("bot/eval_table.pkl")
N_SAMPLE_STATES = 5000                  # random samples for stats
TEST_GAMES      = 50                   # vs baseline material bot

# ---------------------------------------------------------------------------
# 1) BASIC TABLE STATS
# ---------------------------------------------------------------------------
bot = ChessBotAgent(exploration_rate=0.0)   # loads the table
table = bot.evaluation_table
print("\n=== TABLE SUMMARY =============================================")
print("entries :", f"{len(table):,}")
values = list(table.values())
print("mean    :", f"{statistics.mean(values): .4f}")
print("stdev   :", f"{statistics.stdev(values): .4f}")
print("min..max:", f"{min(values): .2f}  …  {max(values): .2f}")

# sample a few entries
print("\nrandom samples:")
for fen in random.sample(list(table.keys()), k=min(5, len(table))):
    print(f"  {fen[:30]}…  ->  {table[fen]:+.3f}")

# ---------------------------------------------------------------------------
# 2) VALUE DISTRIBUTION CHECK
#    How many states favour White (>0), Black (<0), Neutral (≈0)
# ---------------------------------------------------------------------------
thr = 0.15
w_pos = sum(v >  thr for v in values)
b_pos = sum(v < -thr for v in values)
neu   = len(values) - w_pos - b_pos
print("\n> {:.2f} as positive / negative threshold".format(thr))
print(f"white‑lean : {w_pos:>7}  ({w_pos/len(values):.1%})")
print(f"black‑lean : {b_pos:>7}  ({b_pos/len(values):.1%})")
print(f"neutral    : {neu:>7}  ({neu /len(values):.1%})")

# ---------------------------------------------------------------------------
# 3) QUICK MATCH  – trained bot vs baseline 1‑ply material bot
# ---------------------------------------------------------------------------
class MaterialBot:
    """non‑learning material‑count bot for baseline"""
    def choose_move(self, board):
        vals = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
                chess.ROOK: 5, chess.QUEEN: 9}
        best, best_mv = (float("-inf"), None) if board.turn == chess.WHITE else (float("inf"), None)
        for mv in board.legal_moves:
            board.push(mv)
            score = sum(vals[p]*(len(board.pieces(p, chess.WHITE))-len(board.pieces(p, chess.BLACK)))
                        for p in vals)
            board.pop()
            if board.turn == chess.WHITE and score > best or \
               board.turn == chess.BLACK and score < best:
                best, best_mv = score, mv
        return best_mv or random.choice(list(board.legal_moves))

def play(white_bot, black_bot):
    board = chess.Board()
    while not board.is_game_over():
        mv = white_bot.choose_move(board) if board.turn == chess.WHITE else black_bot.choose_move(board)
        board.push(mv)
    return board.result()

print("\n=== HEAD‑TO‑HEAD  (trained as White)  ============================")
score = {"1-0":0,"0-1":0,"1/2-1/2":0}
for _ in range(TEST_GAMES):
    result = play(bot, MaterialBot())
    score[result]+=1
print(score)

print("\n=== HEAD‑TO‑HEAD  (trained as Black)  ============================")
score2 = {"1-0":0,"0-1":0,"1/2-1/2":0}
for _ in range(TEST_GAMES):
    result = play(MaterialBot(), bot)
    score2[result]+=1
print(score2)

print("\nDone.")
