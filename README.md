# drama3-live

Speak-as-you-think streaming speech for realtime voice agents, built on
[Fish Audio Drama 3](https://huggingface.co/fishaudio/drama-3).

Drama 3 was trained on a **streaming-text interleave format**: each round gives the
model the text chunk to speak, `<|endofturn|>`, and the *next* chunk as lookahead,
while earlier audio stays in context
([technical report](https://arxiv.org/html/2610.18010v2), Appendix A, Figure 10).
No open serving engine exposes this mode yet: fish-speech and SGLang-Omni synthesize
each chunk as an independent turn. This project makes the mode usable for voice
agents and measures what it buys.

## Status: week 1, format validation

Question for week 1: **does the streaming format work on the open weights, and is
it clearly better than what engines do today?**

Each test text is split into the chunks an LLM would stream, then synthesized in
four modes with the same reference voice:

| Mode | What it does | Why |
|---|---|---|
| `full` | Whole text in one pass | Quality ceiling (not streamable) |
| `independent` | Each chunk on its own, reference only | What a sentence-per-request cascade does today |
| `fish_history` | Each chunk with fish-speech's history (first + latest chunk), no lookahead | Strongest existing baseline (fish-speech `generate_long_drama3`) |
| `streaming` | Figure 10 format: chunk + `<\|endofturn\|>` + next chunk, all earlier rounds in context | This project |

`streaming` has two open design questions, exposed as flags:

- `--ref-style system`: reference blocks in the system message, as fish-speech does
- `--ref-style round`: the reference becomes round 0 of the conversation, so the
  model "continues" in that voice
- `--speaker-tag / --no-speaker-tag`: prefix `<|speaker:0|>` to user turns or not

Scored per text and mode: WER/CER of the whole answer, per-chunk errors, **lookahead
leakage** (next chunk's words spoken early), speaker similarity to the reference,
and a playback timeline (time to first chunk, stalls).

Week 1 timing is per chunk, not per frame: `generate_drama3` returns a chunk's frames
all at once. Frame-level time-to-first-audio comes with the engine work in week 2.

## Running the experiment (GPU machine)

### Requirements

- Linux with an NVIDIA GPU that has **48 GB+ and SM89+** (L40, L40S, RTX 6000 Ada, H100).
  fish-speech loads only the FP8 Drama 3 checkpoint natively, and FP8 experts need
  SM89+. On older cards (A6000, A100) the experts are dequantized to bf16 (~70 GB).
  Avoid RTX 50-series cards (near-silent output reported on sm_120).
- About 100 GB of disk for the weights and results.
- Python 3.12 in a fresh environment, as fish-speech recommends:
  `conda create -n drama3 python=3.12 && conda activate drama3`
- System audio packages: `sudo apt install portaudio19-dev libsox-dev ffmpeg`
- A Hugging Face login if the download asks for one: `hf auth login`, and accept the
  Drama 3 license on its model page.
- The reference voice, which is **not in this repo**. Get `voice.wav` (10-20 s) and
  `voice.lab` (its exact transcript) from Yan and put both in `data/ref/`. To use
  another voice, use only audio you have the rights to.

### 1. Install

```bash
git clone https://github.com/yanzzzk/drama3-live.git
cd drama3-live
bash scripts/setup_gpu.sh 2>&1 | tee setup.log
```

This clones fish-speech next to this repo, installs both projects, and downloads the
weights. Set `CUDA_TAG=cu126` or `cu128` first if your CUDA is older than 12.9.

### 2. Smoke test

One text in two modes, to catch problems before the full run:

```bash
python experiments/week1_run.py \
    --checkpoint ../fish-speech/checkpoints/drama-3 \
    --ref-audio data/ref/voice.wav \
    --out results/smoke \
    --only en_story --variants full streaming-system \
    2>&1 | tee smoke.log
```

### 3. Full run and scoring

```bash
python experiments/week1_run.py \
    --checkpoint ../fish-speech/checkpoints/drama-3 \
    --ref-audio data/ref/voice.wav \
    --out results/week1 \
    2>&1 | tee run.log

python experiments/week1_score.py results/week1 2>&1 | tee score.log
```

### 4. Send back the results

`results/` is git-ignored, so zip it and send it directly (Drive, WeTransfer, etc.):

```bash
zip -r week1_results.zip results/week1 *.log
```

The most important file is `results/week1/scores.csv`. Each
`results/week1/<text>/<variant>/all.wav` is the full audio for listening.

**If anything fails**, there is no need to debug it. Send the matching `.log` file;
after a fix, `git pull` and rerun that step.

## Layout

```
drama3_live/
  chunker.py    split text into LLM-like streaming chunks (no torch)
  prompts.py    Figure 10 streaming prompt as segments (no torch)
  encode.py     segments -> Drama 3 prompt rows
  modes.py      the four synthesis modes (needs fish-speech + GPU)
  scoring.py    text normalization, WER/CER, lookahead leakage (no torch)
  timeline.py   playback timeline and stall metrics (no torch)
experiments/    week-1 run and scoring scripts
data/           test texts; reference voice goes in data/ref/ (git-ignored)
tests/          pytest, runs on a laptop without a GPU
```

## Roadmap

1. Week 1: validate the format offline (this)
2. Weeks 2-4: persistent streaming session in SGLang-Omni, barge-in rollback to the
   heard frame, deadline-aware chunking
3. Week 5: WebSocket protocol, TypeScript SDK, demo
4. Week 6: benchmark, listening test, write-up

## License

Drama 3 weights and fish-speech are under the Fish Audio Community License. This
project is non-commercial research; audio outputs are not used to train other
models. Built with Fish Audio.
