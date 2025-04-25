#!/usr/bin/env python3
import os, pickle

# ── Config ──────────────────────────────────────────────────────────────
IN_PATH    = "bot/eval_table_zobrist.pkl"        # your live table
BACKUP_DIR = "bot/backups"                       # where to stash old tables
THRESHOLD  = 0.02                                # pawn-unit cutoff
OUT_PATH   = IN_PATH.replace(".pkl", "_pruned.pkl")
# ────────────────────────────────────────────────────────────────────────

def main():
    # 1) Load
    print(f"Loading {IN_PATH}…", end="", flush=True)
    with open(IN_PATH, "rb") as f:
        table = pickle.load(f)
    orig_n = len(table)
    print(f" {orig_n:,} entries loaded.")

    # 2) Backup
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_path = os.path.join(BACKUP_DIR,
                               os.path.basename(IN_PATH).replace(".pkl", "_bak.pkl"))
    pickle.dump(table, open(backup_path, "wb"))
    print(f"Backed up original to {backup_path}")

    # 3) Prune
    to_delete = [k for k, v in table.items() if abs(v) < THRESHOLD]
    for k in to_delete:
        del table[k]
    pruned_n = len(table)
    print(f"Pruned {len(to_delete):,} entries ({len(to_delete)/orig_n:.1%})")
    print(f"Remaining entries: {pruned_n:,}")

    # 4) Save
    with open(OUT_PATH, "wb") as f:
        pickle.dump(table, f)
    print(f"Saved pruned table to {OUT_PATH}")

if __name__ == "__main__":
    main()
