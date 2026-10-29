#!/usr/bin/env bash
# One-time setup on the GPU machine (Linux, NVIDIA, SM89+ with 48 GB+).
# Run from anywhere; fish-speech is cloned next to this repo unless FISH_SPEECH_DIR is set.
# CUDA_TAG picks the PyTorch build: cu126, cu128 or cu129 (default).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FISH="${FISH_SPEECH_DIR:-$ROOT/../fish-speech}"
CUDA_TAG="${CUDA_TAG:-cu129}"

echo "== GPU"
nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv
cap="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1)"
if awk "BEGIN {exit !($cap < 8.9)}"; then
    echo "WARNING: compute capability $cap < 8.9. Drama 3 FP8 experts will be"
    echo "dequantized to bf16 (~70 GB); use several GPUs via --device cuda:0,cuda:1"
fi

echo "== fish-speech"
if [ ! -d "$FISH" ]; then
    git clone https://github.com/fishaudio/fish-speech.git "$FISH"
fi
pip install --extra-index-url "https://download.pytorch.org/whl/$CUDA_TAG" -e "$FISH[$CUDA_TAG]"

echo "== drama3-live"
pip install -r "$ROOT/requirements.txt"
pip install -e "$ROOT"

echo "== weights (Drama 3 FP8 + the S2-Pro codec); run 'hf auth login' first if asked"
pip install -U "huggingface_hub[cli]"
hf download fishaudio/drama-3 --local-dir "$FISH/checkpoints/drama-3"
if [ ! -f "$FISH/checkpoints/drama-3/codec.pth" ]; then
    hf download fishaudio/s2-pro codec.pth --local-dir "$FISH/checkpoints/s2-pro"
fi

echo "== done. Checkpoint: $FISH/checkpoints/drama-3"
