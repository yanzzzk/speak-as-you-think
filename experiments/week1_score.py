"""Score week-1 runs: ASR errors, lookahead leakage, speaker similarity, seams, timeline.

Writes, in each run directory (one seed folder of week1_run.py):
  scores.csv   one row per text and variant
  seams.csv    one row per seam between chunks: kind of cut and pause length
               (non-speech found by Silero VAD at the chunk edges)
and prints the means per variant over all runs given. Error rates are WER for
English and CER for Chinese.
"""

import argparse
import csv
import json
import statistics
from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

import soundfile as sf
import torch
import torchaudio

from drama3_live.scoring import error_rate, leaked
from drama3_live.seams import edge_nonspeech, seam_rows
from drama3_live.timeline import playback_timeline

COLUMNS = (
    "text_id",
    "lang",
    "variant",
    "seed",
    "chunks",
    "err_all",
    "err_chunk_mean",
    "leak_rate",
    "sim_all",
    "sim_chunk_min",
    "sim_first",
    "sim_last",
    "first_chunk_s",
    "stall_s",
    "stalls",
    "rtf",
    "hit_max_tokens",
)
SEAM_COLUMNS = ("text_id", "lang", "variant", "seed", "seam", "kind", "time_s", "pause_s", "at")
# Lower is better for these; higher for the rest.
LOWER_IS_BETTER = {"err_all", "err_chunk_mean", "leak_rate", "first_chunk_s", "stall_s", "rtf"}
SAMPLE_RATE = 16000  # what the speaker model expects
WINDOW_S = 6.0  # voice drift: similarity of the first vs the last window of all.wav


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("runs", nargs="+", type=Path, help="seed folders of week1_run.py")
    parser.add_argument("--asr-model", default="large-v3")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--ref-audio", type=Path, help="default: the one in run.json")
    return parser.parse_args()


class Scorer:
    def __init__(self, asr_model: str, device: str) -> None:
        from faster_whisper import WhisperModel
        from faster_whisper.vad import VadOptions, get_speech_timestamps
        from speechbrain.inference.speaker import EncoderClassifier

        compute_type = "float16" if device == "cuda" else "int8"
        self.asr = WhisperModel(asr_model, device=device, compute_type=compute_type)
        self.speaker = EncoderClassifier.from_hparams(
            "speechbrain/spkrec-ecapa-voxceleb", run_opts={"device": device}
        )
        # Silero VAD as bundled with faster-whisper, with the settings of round 2.
        self.detect_speech = get_speech_timestamps
        self.vad_options = VadOptions(
            threshold=0.5, min_speech_duration_ms=250, min_silence_duration_ms=100, speech_pad_ms=30
        )

    def transcribe(self, path: Path, lang: str) -> str:
        segments, _ = self.asr.transcribe(str(path), language=lang, beam_size=5)
        return " ".join(segment.text.strip() for segment in segments)

    def load(self, path: Path) -> torch.Tensor:
        """Mono waveform at SAMPLE_RATE, [1, samples]."""
        samples, sr = sf.read(path, dtype="float32", always_2d=True)
        wav = torch.from_numpy(samples).mean(dim=1).unsqueeze(0)
        return torchaudio.functional.resample(wav, sr, SAMPLE_RATE)

    @torch.inference_mode()
    def embed(self, wav: torch.Tensor) -> torch.Tensor:
        return self.speaker.encode_batch(wav).flatten()

    def nonspeech_edges(self, wav: torch.Tensor) -> tuple[float, float]:
        """Seconds of non-speech before the first and after the last speech."""
        samples = wav[0].numpy()
        speech = self.detect_speech(samples, self.vad_options)
        return edge_nonspeech([(s["start"], s["end"]) for s in speech], len(samples), SAMPLE_RATE)

    def similarity(self, a: torch.Tensor, b: torch.Tensor) -> float:
        return torch.nn.functional.cosine_similarity(a, b, dim=0).item()

    def window_similarities(self, wav: torch.Tensor, ref: torch.Tensor) -> list[float]:
        """Similarity to the reference of consecutive windows of about WINDOW_S."""
        count = max(1, round(wav.shape[1] / (WINDOW_S * SAMPLE_RATE)))
        parts = torch.tensor_split(wav, count, dim=1)
        return [self.similarity(self.embed(part), ref) for part in parts]


def score_variant(
    scorer: Scorer, folder: Path, ref_embedding: torch.Tensor
) -> tuple[dict, list[dict]]:
    meta = json.loads((folder / "meta.json").read_text())
    lang, chunks = meta["lang"], meta["chunks"]
    errors, leaks, sims, edges = [], [], [], []
    for index, chunk in enumerate(chunks):
        path = folder / f"chunk_{index:02d}.wav"
        if chunk["frames"] == 0:
            errors.append(1.0)
            edges.append((0.0, 0.0))
            continue
        transcript = scorer.transcribe(path, lang)
        errors.append(error_rate(chunk["text"], transcript, lang))
        if chunk["lookahead"]:
            leaks.append(leaked(chunk["text"], chunk["lookahead"], transcript, lang))
        wav = scorer.load(path)
        sims.append(scorer.similarity(scorer.embed(wav), ref_embedding))
        edges.append(scorer.nonspeech_edges(wav))

    all_wav = folder / "all.wav"
    whole = scorer.load(all_wav)
    windows = scorer.window_similarities(whole, ref_embedding)
    timeline = playback_timeline(
        [c["gen_seconds"] for c in chunks], [c["audio_seconds"] for c in chunks]
    )
    row = {
        "text_id": meta["text_id"],
        "lang": lang,
        "variant": meta["variant"],
        "chunks": len(chunks),
        "err_all": error_rate(meta["text"], scorer.transcribe(all_wav, lang), lang),
        "err_chunk_mean": statistics.mean(errors),
        "leak_rate": statistics.mean(leaks) if leaks else 0.0,
        "sim_all": scorer.similarity(scorer.embed(whole), ref_embedding),
        "sim_chunk_min": min(sims) if sims else 0.0,
        "sim_first": windows[0],
        "sim_last": windows[-1],
        "first_chunk_s": timeline.first_audio_s,
        "stall_s": timeline.total_stall_s,
        "stalls": timeline.stalls,
        "rtf": sum(c["gen_seconds"] for c in chunks) / max(timeline.audio_s, 1e-6),
        "hit_max_tokens": sum(c["finish_reason"] != "eos" for c in chunks),
    }
    return row, seam_rows(chunks, edges)


def write_csv(path: Path, columns: Sequence[str], rows: list[dict]) -> None:
    # utf-8-sig so that Excel shows the Chinese text correctly.
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict], seams: list[dict]) -> None:
    by_variant = defaultdict(list)
    for row in rows:
        by_variant[row["variant"]].append(row)
    metrics = COLUMNS[COLUMNS.index("err_all") :]
    print(f"\nMeans over texts and {len({r['seed'] for r in rows})} seed(s)")
    print(f"{'variant':<20}{'n':>4}" + "".join(f"{m:>15}" for m in metrics))
    for variant, group in by_variant.items():
        means = (statistics.mean(r[m] for r in group) for m in metrics)
        print(f"{variant:<20}{len(group):>4}" + "".join(f"{v:>15.3f}" for v in means))
    print("Lower is better: " + ", ".join(sorted(LOWER_IS_BETTER)))

    pauses = defaultdict(list)
    for seam in seams:
        pauses[seam["variant"], seam["kind"]].append(seam["pause_s"])
    kinds = ("word", "clause", "sentence")
    print("\nMean non-speech at seams in seconds (number of seams), by how the chunk before ends")
    print(f"{'variant':<20}" + "".join(f"{kind:>16}" for kind in kinds))
    for variant in by_variant:
        if not any(pauses[variant, kind] for kind in kinds):
            continue  # one chunk, no seams
        cells = []
        for kind in kinds:
            values = pauses[variant, kind]
            cells.append(f"{statistics.mean(values):.3f} ({len(values)})" if values else "-")
        print(f"{variant:<20}" + "".join(f"{cell:>16}" for cell in cells))


def main() -> None:
    args = parse_args()
    for run in args.runs:
        if not (run / "run.json").is_file():
            raise SystemExit(f"{run} has no run.json; pass the seed folders, e.g. {run}/seed*")
    configs = {run: json.loads((run / "run.json").read_text()) for run in args.runs}
    ref_audio = args.ref_audio or Path(configs[args.runs[0]]["ref_audio"])
    scorer = Scorer(args.asr_model, args.device)
    ref_embedding = scorer.embed(scorer.load(ref_audio))

    all_rows, all_seams = [], []
    for run in args.runs:
        seed = configs[run].get("seed")
        rows, seams = [], []
        for meta_path in sorted(run.glob("*/*/meta.json")):
            row, variant_seams = score_variant(scorer, meta_path.parent, ref_embedding)
            row["seed"] = seed
            key = {k: row[k] for k in ("text_id", "lang", "variant", "seed")}
            rows.append(row)
            seams += [key | seam for seam in variant_seams]
            print(
                f"seed {seed}  {row['text_id']:<14} {row['variant']:<20} "
                f"err {row['err_all']:.3f}  leak {row['leak_rate']:.2f}  sim {row['sim_all']:.3f}"
            )
        if not rows:
            raise SystemExit(f"no meta.json under {run}")
        write_csv(run / "scores.csv", COLUMNS, rows)
        write_csv(run / "seams.csv", SEAM_COLUMNS, seams)
        print(f"Wrote {run / 'scores.csv'} and {run / 'seams.csv'}")
        all_rows += rows
        all_seams += seams
    print_summary(all_rows, all_seams)


if __name__ == "__main__":
    main()
