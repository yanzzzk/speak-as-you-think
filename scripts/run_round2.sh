#!/usr/bin/env bash
# Round 2: long texts cut into small chunks, three modes, three seeds, then scoring.
# Usage: bash scripts/run_round2.sh [device]
#   one card:       bash scripts/run_round2.sh cuda:0
#   several cards:  bash scripts/run_round2.sh cuda:0,cuda:1,cuda:2
#   seed 1 only:    SEEDS=1 bash scripts/run_round2.sh cuda:0
# Safe to rerun after a crash or Ctrl-C: finished work is skipped.
set -euo pipefail
cd "$(dirname "$0")/.."

DEVICE="${1:-cuda:0}"
CHECKPOINT="${CHECKPOINT:-../fish-speech/checkpoints/drama-3}"
read -ra SEED_LIST <<< "${SEEDS:-1 2 3}"
OUT=results/round2

python experiments/week1_run.py \
    --checkpoint "$CHECKPOINT" \
    --device "$DEVICE" \
    --ref-audio data/ref/voice.wav \
    --texts data/round2_texts.jsonl \
    --variants independent fish_history streaming-round \
    --seeds "${SEED_LIST[@]}" \
    --out "$OUT" \
    2>&1 | tee -a round2_run.log

python experiments/week1_score.py "$OUT"/seed* 2>&1 | tee round2_score.log

zip -qr round2_results.zip "$OUT" round2_run.log round2_score.log
echo "Done. Send back round2_results.zip"
