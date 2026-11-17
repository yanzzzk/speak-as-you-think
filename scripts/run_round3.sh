#!/usr/bin/env bash
# Round 3: streaming that remembers only the last 1 or 4 chunks besides the reference.
# Adds two variants next to the round-2 results, then re-scores every variant.
# Usage: bash scripts/run_round3.sh [device]
#   several cards:  bash scripts/run_round3.sh cuda:0,cuda:1,cuda:2
#   seed 1 only:    SEEDS=1 bash scripts/run_round3.sh cuda:0
#   round 2 elsewhere:  OUT=path/to/round2 bash scripts/run_round3.sh cuda:0
# Safe to rerun after a crash or Ctrl-C: finished work is skipped.
set -euo pipefail
cd "$(dirname "$0")/.."

DEVICE="${1:-cuda:0}"
CHECKPOINT="${CHECKPOINT:-../fish-speech/checkpoints/drama-3}"
read -ra SEED_LIST <<< "${SEEDS:-1 2 3}"
OUT="${OUT:-results/round2}"

python experiments/week1_run.py \
    --checkpoint "$CHECKPOINT" \
    --device "$DEVICE" \
    --ref-audio data/ref/voice.wav \
    --texts data/round2_texts.jsonl \
    --variants streaming-round-w1 streaming-round-w4 \
    --seeds "${SEED_LIST[@]}" \
    --out "$OUT" \
    2>&1 | tee -a round3_run.log

python experiments/week1_score.py "$OUT"/seed* 2>&1 | tee round3_score.log

zip -qr round3_results.zip "$OUT"/seed*/*/streaming-round-w* \
    "$OUT"/seed*/scores.csv "$OUT"/seed*/seams.csv round3_run.log round3_score.log
echo "Done. Send back round3_results.zip"
