"""
Self‑play trainer.  Run with:

    python -m bot.continuous_train --games 1000
or
    PYTHONLOGLEVEL=DEBUG python -m bot.continuous_train --games 20
"""
import argparse, datetime, statistics, random
import chess

from bot.utils.debug import dprint
from bot.utils.zobrist import zobrist
from bot.chess_bot import ChessBotAgent

# ─── hyper‑parameters you may tweak ─────────────────────────────────────
DEFAULT_GAMES     = 1_000_000
INITIAL_EPS       = 0.20   # more diverse positions early on
DECAY_EVERY       = 200    # decay more frequently
DECAY_FACTOR      = 0.88   # steeper per-cycle decay
EPS_FLOOR         = 0.03   # never stop exploring entirely
LEARNING_RATE     = 0.15
GAMMA             = 0.99   # TD discount: earlier positions weighted less
SEARCH_DEPTH      = 2   # UCI engine plays at depth 5; kept lower here for training speed
USE_QUIESCENCE    = True   
QUIESCENCE_DEPTH  = 3     
SAVE_INTERVAL     = 50
PRINT_EVERY       = 100
PRUNE_EVERY       = 2_000  # games between auto-prunes (0 = never)
MIN_VISITS        = 2      # keep entries seen >= this many times
MAX_ENTRIES       = 180_000  # hard ceiling
ENDGAME_PIECES    = 7        # entries with <= this many pieces arent pruned
VALUE_KEEP        = 0.5    # protect entries with |value| over this
TABLE_PATH        = "bot/evaluation_table_current/eval_table_zobrist_pruned.pkl"
BOOK_PATH         = "book_library/Perfect2023.bin"
# ────────────────────────────────────────────────────────────────────────


def play_one(wbot: ChessBotAgent, bbot: ChessBotAgent):
    """Return (result_str, history_list)."""
    # Clear per-game search caches (TT and history heuristic table)
    wbot.tt.clear(); bbot.tt.clear()
    wbot.history = [[0]*64 for _ in range(64)]
    bbot.history = [[0]*64 for _ in range(64)]

    board, hist = chess.Board(), []
    while not board.is_game_over():
        fen = board.fen() if (wbot.track_fens or bbot.track_fens) else None
        hist.append((zobrist.hash(board), board.turn == chess.WHITE, fen,
                     chess.popcount(board.occupied)))
        mv = wbot.choose_move(board) if board.turn == chess.WHITE else bbot.choose_move(board)
        board.push(mv)
    return board.result(), hist

def prune_table(agent, max_entries=MAX_ENTRIES, min_visits=MIN_VISITS,
                endgame_pieces=ENDGAME_PIECES):
    
    table, stats = agent.evaluation_table, agent.zkey_stats
    before = len(table)
    if before == 0:
        return
    # no stats → don't wipe the table
    if not stats:
        print(f"[prune] skipped: {before:,} entries but zkey_stats is empty "
              f"(stats file missing or desynced)")
        return

    # protect endgames
    endgames = {k for k in table
                if stats.get(k, {}).get("pieces", 99) <= endgame_pieces}

    # keep decisive values, trim lowest |v| if over cap
    valued = [k for k in table
              if k not in endgames and abs(table[k]) > VALUE_KEEP]
    room = max_entries - len(endgames)
    if len(valued) > room:
        valued.sort(key=lambda k: abs(table[k]), reverse=True)
        valued = valued[:max(0, room)]
    valued = set(valued)

    protected = endgames | valued

    # fill rest by visits, then |v|
    candidates = [k for k in table
                  if k not in protected
                  and stats.get(k, {}).get("visits", 0) >= min_visits]
    room = max_entries - len(protected)
    if room < len(candidates):
        candidates.sort(key=lambda k: (stats.get(k, {}).get("visits", 0),
                                       abs(table[k])), reverse=True)
        candidates = candidates[:max(0, room)]

    keep = protected | set(candidates)

    agent.evaluation_table = {k: table[k] for k in keep}
    agent.zkey_to_fen = {k: agent.zkey_to_fen[k]
                         for k in keep if k in agent.zkey_to_fen}
    agent.zkey_stats = {k: stats[k] for k in keep if k in stats}
    kept = len(agent.evaluation_table)
    over = "  [over cap: endgame floor]" if kept > max_entries else ""
    print(f"[prune] {before:,} → {kept:,} entries "
          f"(cap {max_entries:,}; {len(endgames):,} endgame, {len(valued):,} valued){over}")


def main(total_games: int = DEFAULT_GAMES):
    # instantiate two identical bots
    bot_w = ChessBotAgent(exploration_rate=INITIAL_EPS, learning_rate=LEARNING_RATE,
                          save_interval=SAVE_INTERVAL, table_path=TABLE_PATH,
                          search_depth=SEARCH_DEPTH, use_quiescence=USE_QUIESCENCE,
                          quiescence_depth=QUIESCENCE_DEPTH, gamma=GAMMA,
                          book_bin_path=BOOK_PATH, track_fens=False)
    bot_b = ChessBotAgent(exploration_rate=INITIAL_EPS, learning_rate=LEARNING_RATE,
                          save_interval=10**9, table_path=TABLE_PATH,
                          search_depth=SEARCH_DEPTH, use_quiescence=USE_QUIESCENCE,
                          quiescence_depth=QUIESCENCE_DEPTH, gamma=GAMMA,
                          book_bin_path=BOOK_PATH, track_fens=False)

    bot_b.evaluation_table = bot_w.evaluation_table
    bot_b.zkey_to_fen      = bot_w.zkey_to_fen
    bot_b.zkey_stats       = bot_w.zkey_stats

    # prune once at startup
    prune_table(bot_w)
    # re-point
    bot_b.evaluation_table = bot_w.evaluation_table
    bot_b.zkey_to_fen      = bot_w.zkey_to_fen
    bot_b.zkey_stats       = bot_w.zkey_stats

    white_wins = black_wins = draws = 0
    eps = INITIAL_EPS

    try:
        g = 0
        for g in range(1, total_games + 1):
            white_bot, black_bot = (bot_w, bot_b) if g % 2 == 0 else (bot_b, bot_w)
            result, hist = play_one(white_bot, black_bot)
            dprint("--- game %d  result=%s  plies=%d", g, result, len(hist))

            # W‑L‑D accounting
            if result == "1-0":
                white_wins += white_bot is bot_w
                black_wins += white_bot is bot_b
            elif result == "0-1":
                white_wins += black_bot is bot_w
                black_wins += black_bot is bot_b
            else:
                draws += 1

            bot_w.update_evaluation(hist, result)

            # periodic logging
            if g % PRINT_EVERY == 0:
                now = datetime.datetime.now().strftime("%H:%M:%S")
                stdev = statistics.pstdev(bot_w.evaluation_table.values())
                size  = len(bot_w.evaluation_table)
                q_calls = bot_w.quiesce_calls + bot_b.quiesce_calls
                print(f"{now} | {g:,} games  stdev {stdev:.4f}  ε {eps:.3f}")
                print(f"    table entries: {size:,}")
                print(f"    record  W–L–D: {white_wins}–{black_wins}–{draws}, "
                      f"quiesce={q_calls}")
                bot_w.quiesce_calls = bot_b.quiesce_calls = 0
                dprint("ε now %.4f  table=%d", eps, size)

            if g % DECAY_EVERY == 0 and eps > EPS_FLOOR:
                eps = max(EPS_FLOOR, eps * DECAY_FACTOR)
                bot_w.exploration_rate = bot_b.exploration_rate = eps
                print(f"--- decayed ε → {eps:.3f} at game {g:,} ---")

            # periodic auto-prune
            if PRUNE_EVERY and g % PRUNE_EVERY == 0:
                prune_table(bot_w)
                bot_b.evaluation_table = bot_w.evaluation_table
                bot_b.zkey_to_fen      = bot_w.zkey_to_fen
                bot_b.zkey_stats       = bot_w.zkey_stats
                bot_w._save_table()   # persist the smaller table

    except KeyboardInterrupt:
        print("Interrupted – saving …")
    finally:
        bot_w._save_table()
        print(f"Table saved to {TABLE_PATH}")
        print(f"Final record  W–L–D: {white_wins}–{black_wins}–{draws}")
        print(f"Games completed: {g:,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=DEFAULT_GAMES,
                        help="number of self‑play games to run")
    args = parser.parse_args()
    main(args.games)
