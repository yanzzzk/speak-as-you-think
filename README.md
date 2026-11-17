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
leakage** (next chunk's words spoken early), speaker similarity to the reference
(whole answer, worst chunk, first vs last few seconds), the **pause at each seam**
by how the chunk before it ends (mid-phrase, comma or sentence end), and a playback
timeline (time to first chunk, stalls).

Week 1 timing is per chunk, not per frame: `generate_drama3` returns a chunk's frames
all at once. Frame-level time-to-first-audio comes with the engine work in week 2.

### Round 1 results

`data/week1_texts.jsonl` (8 short texts), default chunk sizes, all five variants,
one run each, on 3× A40:

- **The format works.** No lookahead was spoken early (0%), no chunk failed or ran
  to the token limit, and WER/CER and predicted naturalness (UTMOS) matched the
  whole-text ceiling: 3.52 for `streaming-round` vs 3.50 for `full`.
- **It beat independent chunks** (UTMOS 3.30; streaming was higher on 7 of 8 texts)
  **but only tied fish-speech's history** (3.43), which kept the voice most
  consistent from chunk to chunk (0.815 vs 0.779).
- `round` stayed closer to the reference voice than `system` (0.700 vs 0.668), so it
  is the streaming variant from now on.
- Why no clear winner: 18 of 21 seams fell at sentence ends, where independent
  chunks already sound fine. Lookahead should matter when a chunk ends mid-sentence.
- Timing from this run says nothing about the model: A40 has no FP8, so it ran in
  bf16 across three cards, and fish-speech turns off its CUDA graphs when a model
  spans several GPUs.

### Round 2 results

`data/round2_texts.jsonl`: six longer texts (4 English, 2 Chinese, 10-19 chunks
each), cut into small chunks (about 30 characters in English, 10 in Chinese) so
that most seams fall mid-sentence: 46 mid-phrase, 16 at a comma and 20 at a
sentence end as the control. Three modes, three seeds each, on 3× A40 and 3× A100.

| Non-speech at the seam (Silero VAD, mean) | `independent` | `fish_history` | `streaming-round` |
|---|---|---|---|
| Mid-phrase (English, 138 seams per mode) | 0.72 s | 0.49 s | **0.21 s** |
| At a comma (English) | 0.69 s | 0.66 s | 0.52 s |
| At a sentence end (English) | 0.78 s | 0.66 s | 0.87 s |

- **Lookahead works where it should.** `streaming-round` hardly pauses inside a
  phrase, pauses a little at commas and most at sentence ends, like natural speech;
  `independent` pauses the same everywhere. Seam by seam, streaming paused less than
  `independent` at 153 of 186 mid-sentence seams.
- No lookahead was spoken early, WER stayed under 2% for every mode, and predicted
  naturalness (UTMOS) tied.
- `independent` once ran to the token limit: 27 s of silence after the fragment
  "in time. The doors slid open with". Streaming never did.
- **New problem: the streaming voice drifts.** Its similarity to the reference fell
  from 0.685 in the first 6 s to 0.591 in the last 6 s (`independent`: 0.711 to
  0.687), and it was below `independent` on all 18 text-seed pairs. Background noise
  stayed flat, so this is the voice, not the noise.
- The round-2 energy pause (silence = 40 dB below the loudest frame) was wrong: the
  reference's room noise sits about 40 dB down and the model copies it, so pauses
  are not silent. Pauses are now measured with Silero VAD.

### Round 3 (now)

Streaming that remembers only the reference plus the last 1 or 4 rounds
(`streaming-round-w1`, `streaming-round-w4`), to keep the short mid-phrase pauses
without the drift. Same texts and seeds as round 2, so the round-2 runs are reused:
only the two new variants are generated, then every variant is re-scored.

## Running the experiment (GPU machine)

### Requirements

- Linux with an NVIDIA GPU that has **48 GB+ and SM89+** (L40, L40S, RTX 6000 Ada, H100).
  fish-speech loads only the FP8 Drama 3 checkpoint natively, and FP8 experts need
  SM89+. Older cards (A40, A6000, A100) also work across several GPUs, e.g.
  `--device cuda:0,cuda:1,cuda:2`: quality results are valid, but the model runs in
  bf16 (~70 GB) without CUDA graphs, so it is much slower.
  Avoid RTX 50-series cards (near-silent output reported on sm_120).
- About 100 GB of disk for the weights and results.
- Python 3.12 in a fresh environment, as fish-speech recommends:
  `conda create -n drama3 python=3.12 && conda activate drama3`
- System audio packages: `sudo apt install portaudio19-dev libsox-dev ffmpeg zip`
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

One text in two modes, to catch problems before a long run:

```bash
python experiments/week1_run.py \
    --checkpoint ../fish-speech/checkpoints/drama-3 \
    --ref-audio data/ref/voice.wav \
    --out results/smoke \
    --only en_story --variants full streaming-round \
    2>&1 | tee smoke.log
```

### 3. Round 3

Run it in the same folder as round 2. It adds the two new variants next to the
round-2 results in `results/round2/seedN/`, re-scores every variant and zips what
is new:

```bash
git pull
bash scripts/run_round3.sh cuda:0,cuda:1,cuda:2
```

If seed 3 of round 2 is still in `results/round2_parallel/seed3`, move it to
`results/round2/seed3` first, or point the script at your round-2 folder with
`OUT=...`. Rough time on 3× A40: about 2 hours, since the prompts stay short. The
run can be stopped and restarted at any time: finished work is skipped.

Round 2 was `bash scripts/run_round2.sh`, with the same options.

### 4. Send back the results

Send `round3_results.zip` (about 250 MB) by Drive, WeTransfer, etc. It holds the
new audio, `scores.csv` and `seams.csv` for each seed, and both logs. In
`seams.csv`, `time_s` is where each seam falls in that text's `all.wav`, for
listening.

**If anything fails**, there is no need to debug it. Send `round3_run.log` or
`round3_score.log`; after a fix, `git pull` and rerun the same command.

## Layout

```
drama3_live/
  chunker.py    split text into LLM-like streaming chunks (no torch)
  prompts.py    Figure 10 streaming prompt as segments (no torch)
  encode.py     segments -> Drama 3 prompt rows
  modes.py      the four synthesis modes (needs fish-speech + GPU)
  scoring.py    text normalization, WER/CER, lookahead leakage (no torch)
  seams.py      seam kinds and pause lengths (no torch)
  timeline.py   playback timeline and stall metrics (no torch)
experiments/    run and scoring scripts
scripts/        GPU setup and the one-command runs of rounds 2 and 3
data/           test texts of rounds 1 and 2; the reference voice goes in data/ref/ (git-ignored)
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
