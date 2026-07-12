#!/bin/sh
# entrypoint.sh
set -e

mkdir -p /data/tables /data/games /data/snapshots

if [ ! -f /data/zobrist_keys.pkl ]; then
    echo "FATAL: /data/zobrist_keys.pkl is missing."
    echo "Seed the volume first (8.1 -> 2)"
    exit 1
fi

ln -sf /data/zobrist_keys.pkl /app/bot/zobrist_keys.pkl
mkdir -p /app/bot/utils
ln -sf /data/zobrist_keys.pkl /app/bot/utils/zobrist_keys.pkl

rm -rf /app/bot/evaluation_table_current
ln -sfn /data/tables /app/bot/evaluation_table_current

exec "$@"
