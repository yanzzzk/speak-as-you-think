# Speak as you think

Streaming-text speech for realtime voice agents. **Built with Fish Audio**
([Drama 3](https://huggingface.co/fishaudio/drama-3)).

An LLM writes its reply a few words at a time. To start speaking early, a voice
agent has to cut that text before the sentence is finished, and a chunk that ends
mid-phrase is then followed by a gap before the next one.

Drama 3 was trained on a format made for this. Each round gives the model the chunk
to speak, `<|endofturn|>`, and the *next* chunk as lookahead, while earlier rounds
stay in context ([tech report](https://arxiv.org/html/2610.18010v2), Appendix A,
Figure 10). As of November 2026 none of the open engines I checked (fish-speech,
SGLang-Omni, vLLM-Omni) builds these rounds. This repo measures what the mode
changes and is building the session engine for it.

**Result so far:** at cuts inside a phrase, the streaming-text format cuts the
median gap from **0.45 s** to **0.14 s**. Keeping the voice stable costs part of
that: with one round of memory the gap is 0.25 s. On one L40 the model decodes at
about twice real time.

**[Results page with audio](https://yanzzzk.github.io/speak-as-you-think/)** ·
[How to run it](docs/RUNNING.md)

| Median non-speech at the cut | Independent chunks | fish-speech history | Streaming, last round | Streaming, all rounds |
|---|---|---|---|---|
| Mid-phrase, English (138 seams per mode) | 0.45 s | 0.41 s | 0.25 s | **0.14 s** |
| At a comma, English (15) | 0.72 s | 0.75 s | 0.70 s | 0.64 s |
| At a sentence end, English (39) | 0.77 s | 0.68 s | 0.98 s | 0.86 s |
| Voice similarity to the reference, whole clip | 0.760 | 0.706 | 0.752 | 0.687 |

Same text, same cuts, same voice in every mode; three seeds; pauses measured with
Silero VAD on each chunk's audio; speaker similarity with ECAPA.

## What is compared

| Mode | What it does |
|---|---|
| Independent chunks (`independent`) | Each chunk synthesized alone with the reference voice: a chunk-per-request cascade |
| fish-speech history (`fish_history`) | fish-speech's long-form context rule on the same cuts: the first and the latest chunk, no lookahead |
| Streaming, all rounds (`streaming-round`) | Figure 10 format: chunk + `<\|endofturn\|>` + next chunk, every earlier round in context, the reference as round 0 |
| Streaming, last round (`streaming-round-w1`) | The same, keeping only the latest round besides the reference (`-w4`: the last four) |
| Whole text (`full`) | One pass over the full text: the quality ceiling, not streamable (round 1 only) |

## Results

**Round 1** (8 short texts, cut mostly at sentence ends). The format works on the
open weights: no lookahead text was spoken early, and word errors and predicted
naturalness matched whole-text synthesis (UTMOS 3.52 vs 3.50). Cut at sentence
ends, the pause at the cut was about the same in every mode (mean 0.62 to 0.73 s),
so round 2 moved the cuts inside sentences.

**Round 2** (6 longer texts, 4 English and 2 Chinese, chunks of about 30 characters
in English and 14 in Chinese; 3 seeds; 264 chunks per mode).

- **With every round in memory, the gap inside a phrase shrinks to a third.**
  Streaming paused less than independent chunks at 117 of 138 English mid-phrase
  seams. Its pauses grow with the punctuation (0.14 s mid-phrase, 0.64 s at a comma,
  0.86 s at a sentence end).
- **Medians, because one chunk failed.** An independent chunk never stopped after
  the fragment "in time. The doors slid open with": 27 s of non-speech up to the
  token limit. The mid-phrase means are 0.72 / 0.49 / 0.21 s with it (independent /
  fish-speech history / streaming, all rounds), and 0.53 / 0.48 / 0.21 s when that
  text's seed-1 run is left out in every mode.
- **The first seam of a reply gets no short pause.** At the first cut of a text,
  streaming left a median 0.72 s (9 seams), against 0.13 s from the second cut on.
  Against independent chunks the first cut is mixed: a higher median (0.72 s vs
  0.48 s), yet shorter at 6 of the 9.
- **No lookahead was spoken early** (0% of chunks, by transcribing each chunk), and
  predicted naturalness tied (UTMOS 3.33 / 3.37 / 3.42).
- **The voice drifts.** With all rounds in memory, speaker similarity to the
  reference fell from 0.685 in the first 6 s to 0.591 in the last 6 s of a clip
  (independent chunks: 0.711 to 0.687).
- The Chinese texts were cut at punctuation only, so the mid-phrase effect is tested
  in English. At Chinese commas the modes are close.

**Round 3** (the same texts and seeds, streaming with a short memory).

- **Memory trades the gap against the voice.** Keeping only the last round holds
  the voice (0.752 over whole clips, higher than the all-rounds mode on all 18
  clips, 0.700 to 0.662 from first to last 6 s) and leaves a 0.25 s mid-phrase gap:
  shorter than independent chunks at 87 of 138 seams. Keeping the last four rounds
  keeps the short gap (0.16 s) and does not stop the drift (0.555 at the end).
  No setting gives both yet.
- **Lookahead and history both count.** Lookahead plus one round of history: 0.25 s.
  fish-speech history, with the first and the latest chunk and no lookahead: 0.41 s.
- **Word errors.** Whole-reply English WER is 1.7% / 0.9% / 3.4% / 0.4% (order of
  the table above). The 3.4% comes from two clips whose chunks, transcribed one by
  one, are at 1.0% and 3.6%; whether the recogniser or the audio is at fault is not
  settled. One last-four-rounds chunk ran long (17.5 s for five words).
- **Speed.** On one L40 with FP8 experts and CUDA graphs the model decodes 44.8
  frames per second (real time: 21.5), and this offline harness, which re-reads the
  context for every chunk, ran at RTF 0.75. Split across two cards without CUDA
  graphs: 10.6 frames per second.

## Limits

- Pause timing, plus one informal blind check by the author (8 random mid-phrase
  cuts, three round-2 modes: streaming picked 4 times, fish-speech history 3,
  independent chunks 1). No listening test with other listeners.
- One reference voice (the author's own), six texts, three seeds.
- Two hardware setups: the short-memory modes ran on L40 cards with FP8 experts,
  the other modes on A40 and A100 cards in bf16. A control run of every mode on the
  same card is pending.
- The single 44 GB L40 ran out of memory when a whole reply's waveform was decoded
  at once; the timings above come from the 7 runs finished before that.

## What is next

A session engine for the mode: keep the model's caches between rounds instead of
re-reading the context per chunk, stream audio frame by frame, and roll the context
back to the last frame the listener heard when they interrupt. Then a WebSocket
protocol, a TypeScript client and a recorded live demo.

## Layout

```
speak_as_you_think/
  chunker.py    split text into the chunks a streaming LLM would hand over (no torch)
  prompts.py    Figure 10 streaming prompt as segments (no torch)
  encode.py     segments -> Drama 3 prompt rows
  modes.py      the synthesis modes (needs fish-speech + GPU)
  scoring.py    text normalization, WER/CER, lookahead leakage (no torch)
  seams.py      seam kinds and pauses (no torch)
  timeline.py   playback timeline and stall metrics (no torch)
experiments/    run, score and page-build scripts
scripts/        GPU setup and one-command rounds
data/           test texts; the reference voice goes in data/ref/ (git-ignored)
docs/           results page, its data and clips, and the run guide
tests/          pytest, runs on a laptop without a GPU
```

`pytest` runs the pure-Python parts. `experiments/page_data.py` recomputes the
pause numbers from the raw audio and reads word errors and speaker similarity from
each seed's `scores.csv`. UTMOS was scored in a separate pass, the speed figures
come from the run logs, and the round-1 figures from the round-1 run report.

## License and attribution

Built with Fish Audio. Drama 3 and fish-speech are under the Fish Audio Community
License, Version 1.0 (copy in `LICENSE-FISH-AUDIO`). A few functions here are
adapted from fish-speech; `NOTICE` lists them. No model weights are included. This
project is non-commercial research and is not affiliated with or endorsed by Fish
Audio. Audio outputs are not used to train other models. The voice in the clips is
the author's own.
