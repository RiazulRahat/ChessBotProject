#!/usr/bin/env python3
import sys, os, traceback, pickle

# ensure we can import bot/ from the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import chess
from bot.chess_bot import ChessBotAgent
from bot.utils.zobrist import zobrist

fen_map = {}
FEN_MAP_OUT = os.path.join(os.path.dirname(__file__), "fen_map_live.pkl")

_table_path = os.path.join(PROJECT_ROOT, "bot", "evaluation_table_current", "eval_table_zobrist_pruned.pkl")
_book_path  = os.path.join(PROJECT_ROOT, "book_library", "Perfect2023.bin")

agent = None
try:
    agent = ChessBotAgent(
        exploration_rate=0.01,
        search_depth=5,
        save_interval=10**9,
        use_quiescence=True,
        quiescence_depth=5,
        table_path=_table_path,
        book_bin_path=_book_path,
    )
except Exception:
    traceback.print_exc()
    sys.exit(2)

board = chess.Board()
game_history = []   # list of (zkey, white_to_move_bool, fen) for TD updates
best_move = None

if __name__ == "__main__":
    try:
        while True:
            line = sys.stdin.readline().strip()
            if not line:
                continue
            parts = line.split()
            cmd = parts[0]

            if cmd == "ucinewgame":
                game_history.clear()
                agent.tt.clear()
                board.reset()
                fen_map.setdefault(zobrist.hash(board), board.fen())
                continue

            if cmd == "uci":
                print("id name MyChessBot", flush=True)
                print("id author RiazulRahat", flush=True)
                print("uciok", flush=True)

            elif cmd == "isready":
                print("readyok", flush=True)

            elif cmd == "position":
                if parts[1] == "startpos":
                    board.reset()
                    move_list = parts[parts.index("moves") + 1:] if "moves" in parts else []
                elif parts[1] == "fen":
                    if "moves" in parts:
                        i = parts.index("moves")
                        fen_str = " ".join(parts[2:i])
                        move_list = parts[i + 1:]
                    else:
                        fen_str = " ".join(parts[2:])
                        move_list = []
                    board.set_fen(fen_str)
                else:
                    continue

                for uci_str in move_list:
                    board.push_uci(uci_str)
                    key = zobrist.hash(board)
                    game_history.append((key, board.turn == chess.WHITE, board.fen()))
                    fen_map.setdefault(key, board.fen())

            elif cmd == "go":
                key = zobrist.hash(board)
                game_history.append((key, board.turn == chess.WHITE, board.fen()))
                fen_map.setdefault(key, board.fen())

                # parse time controls
                wtime = btime = winc = binc = None
                try:
                    if "wtime" in parts: wtime = int(parts[parts.index("wtime") + 1])
                    if "btime" in parts: btime = int(parts[parts.index("btime") + 1])
                    if "winc"  in parts: winc  = int(parts[parts.index("winc")  + 1])
                    if "binc"  in parts: binc  = int(parts[parts.index("binc")  + 1])
                except (ValueError, IndexError):
                    pass

                our_ms  = wtime if board.turn == chess.WHITE else btime
                our_inc = (winc if board.turn == chess.WHITE else binc) or 0
                if our_ms is not None:
                    budget = (our_ms / 1000) / 40 + our_inc / 1000
                    move = agent.choose_move_timed(board, budget)
                else:
                    move = agent.choose_move(board)

                best_move = move
                print(f"bestmove {move.uci()}", flush=True)
                board.push(move)
                fen_map.setdefault(zobrist.hash(board), board.fen())

                if board.is_game_over():
                    agent.update_evaluation(game_history, board.result())
                    game_history.clear()

            elif cmd == "stop":
                if best_move is not None:
                    print(f"bestmove {best_move.uci()}", flush=True)
                else:
                    print("bestmove 0000", flush=True)

            elif cmd == "quit":
                with open(FEN_MAP_OUT, "wb") as f:
                    pickle.dump(fen_map, f)
                break

    except Exception:
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
