#!/usr/bin/env python3 
import sys, os, traceback

# ─── ensure we can import bot/ from the project root ─────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# ────────────────────────────────────────────────────────────────────────────

import chess
from bot.chess_bot import ChessBotAgent, zobrist

import pickle
# ─── Global Z→FEN map & dump path ────────────────────────────────────────
fen_map = {}   # will collect key → fen
FEN_MAP_OUT = os.path.join(os.path.dirname(__file__), "fen_map_live.pkl")
# ─────────────────────────────────────────────────────────────────────────

agent = None
try:
    agent = ChessBotAgent(
         exploration_rate=0.01,
         search_depth=3,
         use_policy=True,
         save_interval=1,
         use_quiescence=True,
         quiescence_depth=5,
         policy_path=os.path.join(PROJECT_ROOT, "bot", "policy_table_v1.pkl")
     )
except Exception:
    traceback.print_exc()
    sys.exit(2)
board = chess.Board()

game_history = []   # list of (zkey, white_to_move) for TD updates

# UCI protocol loop
if __name__ == "__main__":
    try:
        while True:
            line = sys.stdin.readline().strip()
            if not line:
                continue
            parts = line.split()
            cmd = parts[0]

            # record the board→zkey→FEN any time we set/reset the board
            if cmd == "ucinewgame":
                # new game: clear history and reset board
                game_history.clear()
                board.reset()
                key = zobrist.hash(board)
                fen_map.setdefault(key, board.fen())
                continue

            if cmd == 'uci':
                print('id name MyChessBot', flush=True)
                print('id author YourName', flush=True)
                print('uciok', flush=True)

            elif cmd == 'isready':
                print('readyok', flush=True)

            elif cmd == 'position':
                if parts[1] == 'startpos':
                    board.reset()
                    move_list = parts[parts.index('moves')+1:] if 'moves' in parts else []
                elif parts[1] == 'fen':
                    if 'moves' in parts:
                        i = parts.index('moves')
                        fen_str = ' '.join(parts[2:i])
                        move_list = parts[i+1:]
                    else:
                        fen_str = ' '.join(parts[2:])
                        move_list = []
                    board.set_fen(fen_str)
                else:
                    continue

                for uci_str in move_list:
                    board.push_uci(uci_str)
                    key = zobrist.hash(board)
                    game_history.append((key, board.turn))
                    # record key→fen
                    fen_map.setdefault(key, board.fen())

            elif cmd == 'go':
                # bot’s turn to move
                key = zobrist.hash(board)
                game_history.append((key, board.turn))
                fen_map.setdefault(key, board.fen())
                
                move = agent.choose_move(board)
                best_move = move
                print(f"bestmove {move.uci()}", flush=True)
                board.push(move)

                # record after our move too
                key = zobrist.hash(board)
                fen_map.setdefault(key, board.fen())

                # if the game ended with that move, do learning
                if board.is_game_over():
                    result = board.result() 
                    agent.update_evaluation(game_history, result)
                    agent._save_table()
                    # keep game_history if you want to analyze further,
                    # or clear it here for next game:
                    game_history.clear()

            elif cmd == "stop":
                # called when your time slice is done—simply return the best move so far
                if best_move is not None:
                    print(f"bestmove {best_move.uci()}")
                else:
                    print("bestmove 0000")  # or random legal move

            elif cmd == 'quit':
                # at process-exit dump the fen_map to disk
                with open(FEN_MAP_OUT, "wb") as f:
                    pickle.dump(fen_map, f)
                break

    except Exception:
        import traceback
        traceback.print_exc(file=sys.stderr)
        # ensure you exit non-zero so lichess-bot knows you died
        sys.exit(1)