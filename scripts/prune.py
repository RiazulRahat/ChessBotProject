#!/usr/bin/env python3
import argparse
import pickle
from bot.chess_bot import ChessBotAgent

def main():
    p = argparse.ArgumentParser(
        description="Prune your Z-table & stats by visit count + unmapped-preserve"
    )
    p.add_argument(
        "--stats",
        default="eval_table_zobrist_pruned_stats.pkl",
        help="Path to zkey_stats pickle",
    )
    p.add_argument(
        "--zkey2fen",
        default="eval_table_zobrist_pruned_zkey2fen.pkl",
        help="Path to zkey→fen pickle",
    )
    p.add_argument(
        "--table",
        default="eval_table_zobrist_pruned.pkl",
        help="Path to evaluation_table pickle",
    )
    p.add_argument(
        "--max_entries",
        type=int,
        required=True,
        help="Maximum total entries after pruning",
    )
    p.add_argument(
        "--min_visits",
        type=int,
        default=0,
        help="Drop any mapped state with fewer visits than this",
    )
    p.add_argument(
        "--out_stats",
        default="eval_table_zobrist_pruned_stats_pruned.pkl",
        help="Output path for pruned stats",
    )
    p.add_argument(
        "--out_zkey2fen",
        default="eval_table_zobrist_pruned_zkey2fen_pruned.pkl",
        help="Output path for pruned zkey→fen",
    )
    p.add_argument(
        "--out_table",
        default="eval_table_zobrist_pruned_pruned.pkl",
        help="Output path for pruned evaluation_table",
    )
    args = p.parse_args()

    # 1) instantiate agent
    agent = ChessBotAgent(table_path=args.table)

    # 2) load pickles into agent attributes
    agent.zkey_stats = pickle.load(open(args.stats, "rb"))
    agent.zkey_to_fen = pickle.load(open(args.zkey2fen, "rb"))
    agent.evaluation_table = pickle.load(open(args.table, "rb"))

    # 3) prune
    agent.prune_table(max_entries=args.max_entries, min_visits=args.min_visits)

    # 4) write back out
    with open(args.out_stats, "wb") as f:
        pickle.dump(agent.zkey_stats, f)
    with open(args.out_zkey2fen, "wb") as f:
        pickle.dump(agent.zkey_to_fen, f)
    with open(args.out_table, "wb") as f:
        pickle.dump(agent.evaluation_table, f)

    print("All done! Pruned files written to:")
    print("  ", args.out_stats)
    print("  ", args.out_zkey2fen)
    print("  ", args.out_table)

if __name__ == "__main__":
    main()
