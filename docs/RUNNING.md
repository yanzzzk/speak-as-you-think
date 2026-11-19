# Running the experiments

Everything that needs the model runs on a GPU machine. The tests, the chunker and
the page build run on a laptop.

## Requirements

- Linux with one NVIDIA GPU that has **48 GB or more and compute capability 8.9+**
  (L40, L40S, RTX 6000 Ada, H100, H200). fish-speech loads only the FP8 Drama 3
  checkpoint natively, and the FP8 experts need capability 8.9+.
- Older cards (A40, A6000, A100) work across several GPUs, e.g.
  `--device cuda:0,cuda:1,cuda:2`. Quality results are valid there, but the model
  runs in bf16 (~70 GB) and fish-speech turns off its CUDA graphs when a model spans
  several GPUs, so timings from such a run say nothing about the model.
- Avoid RTX 50-series cards (near-silent output reported on sm_120).
- About 100 GB of disk for the weights and results.
- Python 3.12 in a fresh environment, as fish-speech recommends:
  `conda create -n drama3 python=3.12 && conda activate drama3`
- System packages: `sudo apt install portaudio19-dev libsox-dev ffmpeg zip`
- The weights download without a login. Using them means accepting the Fish Audio
  Community License on the [Drama 3 model page](https://huggingface.co/fishaudio/drama-3),
  including its rules on voice consent.
- A reference voice, which is **not in this repo**: `data/ref/voice.wav` (10-20 s)
  and `data/ref/voice.lab` (its exact transcript). Use only a voice that is yours or
  that you have consent to use.

## 1. Install

```bash
git clone https://github.com/yanzzzk/speak-as-you-think.git
cd speak-as-you-think
bash scripts/setup_gpu.sh 2>&1 | tee setup.log
```

This clones fish-speech next to this repo, installs both projects, and downloads the
weights. Set `CUDA_TAG=cu126` or `cu128` first if your CUDA is older than 12.9.

## 2. Smoke test

One text in two modes, to catch problems before a long run:

```bash
python experiments/week1_run.py \
    --checkpoint ../fish-speech/checkpoints/drama-3 \
    --ref-audio data/ref/voice.wav \
    --out results/smoke \
    --only en_story --variants full streaming-round \
    2>&1 | tee smoke.log
```

## 3. The rounds

| Round | Command | What it runs |
|---|---|---|
| 2 | `bash scripts/run_round2.sh cuda:0` | 6 long texts cut mid-sentence, 3 modes, 3 seeds |
| 3 | `bash scripts/run_round3.sh cuda:0` | adds streaming with a short memory (last 1 or 4 rounds) next to round 2 and re-scores every mode |

Both scripts generate, score and zip the results. They can be stopped and restarted
at any time: finished work is skipped. On several older cards pass all of them, e.g.
`bash scripts/run_round3.sh cuda:0,cuda:1,cuda:2`. `SEEDS=1` runs one seed only.

Round 3 expects the round-2 results in `results/round2/seedN/`; point it elsewhere
with `OUT=path/to/round2`. Rough time on 3× A40: about 2 hours.

Each seed folder ends up with `scores.csv` (one row per text and mode) and
`seams.csv` (one row per seam: kind of cut, pause, and `time_s`, where the seam
falls in that text's `all.wav`).

**If a run fails**, the error is at the end of `round3_run.log` or
`round3_score.log`. Rerun the same command after fixing it: finished work is skipped.

## 4. Speed test on a single GPU

The numbers that matter for a live demo need the whole model on one card, so that
fish-speech keeps the FP8 experts and captures its CUDA graphs:

```bash
python experiments/week1_run.py \
    --checkpoint ../fish-speech/checkpoints/drama-3 \
    --device cuda:0 \
    --ref-audio data/ref/voice.wav \
    --texts data/round2_texts.jsonl \
    --variants independent streaming-round streaming-round-w1 streaming-round-w4 \
    --seeds 1 --out results/speed 2>&1 | tee speed.log
```

`meta.json` in each output folder records frames, prompt rows and generation seconds
per chunk. The first chunk of a run includes the one-time CUDA graph capture.

## 5. Rebuild the results page

On a laptop with ffmpeg, from scored results:

```bash
pip install -e . -r requirements.txt torch torchaudio
python experiments/page_data.py results/round2 --out docs
```

This recomputes the pause numbers from the raw audio, reads the other scores from
each seed's `scores.csv`, and rewrites `docs/data.js` and the clips in `docs/audio/`.
UTMOS is added only if a CSV with `utmos_joined` per seed, text and mode is there:
`combined_metrics.csv` in the run folder, or any file passed with `--extra`.

## 6. Live demo (v0)

Text goes in over a WebSocket piece by piece; speech comes back chunk by chunk and
plays in the browser, with an interrupt button. Try the page on a laptop first, with
tones standing in for the model:

```bash
pip install -e . -r requirements.txt
python experiments/live_server.py --fake
```

On the GPU machine, with the whole model on one card:

```bash
python experiments/live_server.py \
    --checkpoint ../fish-speech/checkpoints/drama-3 \
    --ref-audio data/ref/voice.wav
```

Open the address it prints. It carries a token, because the socket speaks in the
reference voice: keep it private. The page takes the token out of the address bar
once it has read it and keeps it for that browser tab; after a restart the server
prints a new address.

The page speaks one reply in three ways (each chunk alone, lookahead with the last
round, lookahead with all rounds). It marks every cut in the reply text with the gap
measured there, by the same detector and settings as the scores of the experiments;
draws text arrival, generation and playback on one clock; and after an interruption
shows the server's report of what was heard. With `--fake` the gaps are those of the
tones and are not compared with the experiments.

v0 sends whole chunks, so the first audio waits for the first chunk to be generated,
and it waits for the next chunk's text in all three ways. Frame-by-frame streaming
and rolling back to the exact frame on interruption are not built yet.

### The page without a server: recorded replay

`docs/live/index.html` is the same page. Opened without a token, as on GitHub Pages,
it replays the runs in `docs/live/recordings/`: the messages the server sent, at the
times they arrived, with the audio. Nothing is generated, text cannot be changed, and
continuing after an interruption is not offered. To record new runs, with the live
server running on the GPU machine:

```bash
python experiments/live_record.py --token <token> --raw results/live_recordings
```

and to pack them for the page, anywhere with ffmpeg:

```bash
python experiments/live_record.py --raw results/live_recordings --out docs/live/recordings
```

Every take is kept and the page plays them in turn. The audio is in the reference
voice: publish it only if that voice may be public.
