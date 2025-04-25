import pickle, chess
V = pickle.load(open("bot/eval_table.pkl","rb"))
P = pickle.load(open("bot/policy_book.pkl","rb"))
total, covered = 0, 0
for fen in V:
    board = chess.Board(fen)
    if list(board.legal_moves):
        total += 1
        if fen in P:
            covered += 1
print(f"Coverage: {covered}/{total} = {covered/total:.1%}")
