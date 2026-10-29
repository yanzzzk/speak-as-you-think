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

## Setup (GPU machine)

Needs a CUDA GPU with **SM89+ and 48 GB+** (L40, L40S, RTX 6000 Ada, H100).
fish-speech loads only the FP8 Drama 3 checkpoint natively, and FP8 experts need
SM89+; on older cards (A6000, A100) the experts are dequantized to bf16 (~70 GB).

```bash
bash scripts/setup_gpu.sh            # clones fish-speech, installs, downloads weights
```

Put a 10-20 s reference recording and its exact transcript in `data/ref/`
(`voice.wav` + `voice.lab`). Use your own voice or audio you have rights to.

## Run

From the repo root, after `pip install -e .` (the setup script does this):

```bash
python experiments/week1_run.py \
    --checkpoint ../fish-speech/checkpoints/drama-3 \
    --ref-audio data/ref/voice.wav \
    --out results/week1

python experiments/week1_score.py results/week1
```

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
