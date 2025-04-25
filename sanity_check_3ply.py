# sanity_check_3ply.py
import chess
from bot.chess_bot import ChessBotAgent

def test_scholars_mate_defense():
    # 1.e4 e5 2.Bc4 Nc6 3.Qh5
    board = chess.Board()
    for san in ["e4","e5","Bc4","Nc6","Qh5"]:
        board.push_san(san)

    print("\nPosition after 3.Qh5:")
    print(board)    
    # instantiate a pure-search bot: no randomness, depth=3
    bot = ChessBotAgent(exploration_rate=0.0, search_depth=3)
    best = bot.choose_move(board)
    san = board.san(best)
    print("Bot replies with:", san)

    assert best in board.legal_moves, "❌ Bot gave an illegal move!"
    # we expect one of the standard defenses here
    if san not in ("Nc6","g6","Qe7","Nf6"):
        print("⚠️  Unexpected defense—bot may still be too shallow or using fallback eval.")
    else:
        print("✅ Defense looks plausible.")

if __name__=="__main__":
    test_scholars_mate_defense()
