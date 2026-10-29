"""Score a week-1 run: ASR errors, lookahead leakage, speaker similarity, timeline.

Writes <run>/scores.csv (one row per text and variant) and prints the mean per
variant. Error rates are WER for English and CER for Chinese.
"""

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

import torch
import torchaudio

from drama3_live.scoring import error_rate, leaked
from drama3_live.timeline import playback_timeline

COLUMNS = (
    "text_id",
    "lang",
    "variant",
    "chunks",
    "err_all",
    "err_chunk_mean",
    "leak_rate",
    "sim_all",
    "sim_chunk_min",
    "first_chunk_s",
    "stall_s",
    "stalls",
    "rtf",
    "hit_max_tokens",
)
# Lower is better for these; higher for the rest.
LOWER_IS_BETTER = {"err_all", "err_chunk_mean", "leak_rate", "first_chunk_s", "stall_s", "rtf"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run", type=Path, help="results directory of week1_run.py")
    parser.add_argument("--asr-model", default="large-v3")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--ref-audio", type=Path, help="default: the one in run.json")
    return parser.parse_args()


class Scorer:
    def __init__(self, asr_model: str, device: str) -> None:
        from faster_whisper import WhisperModel
        from speechbrain.inference.speaker import EncoderClassifier

        compute_type = "float16" if device == "cuda" else "int8"
        self.asr = WhisperModel(asr_model, device=device, compute_type=compute_type)
        self.speaker = EncoderClassifier.from_hparams(
            "speechbrain/spkrec-ecapa-voxceleb", run_opts={"device": device}
        )

    def transcribe(self, path: Path, lang: str) -> str:
        segments, _ = self.asr.transcribe(str(path), language=lang, beam_size=5)
        return " ".join(segment.text.strip() for segment in segments)

    @torch.inference_mode()
    def embed(self, path: Path) -> torch.Tensor:
        wav, sr = torchaudio.load(str(path))
        wav = torchaudio.functional.resample(wav.mean(dim=0, keepdim=True), sr, 16000)
        return self.speaker.encode_batch(wav).flatten()

    def similarity(self, a: torch.Tensor, b: torch.Tensor) -> float:
        return torch.nn.functional.cosine_similarity(a, b, dim=0).item()


def score_variant(scorer: Scorer, folder: Path, ref_embedding: torch.Tensor) -> dict:
    meta = json.loads((folder / "meta.json").read_text())
    lang, chunks = meta["lang"], meta["chunks"]
    errors, leaks, sims = [], [], []
    for index, chunk in enumerate(chunks):
        wav = folder / f"chunk_{index:02d}.wav"
        if chunk["frames"] == 0:
            errors.append(1.0)
            continue
        transcript = scorer.transcribe(wav, lang)
        errors.append(error_rate(chunk["text"], transcript, lang))
        if chunk["lookahead"]:
            leaks.append(leaked(chunk["text"], chunk["lookahead"], transcript, lang))
        sims.append(scorer.similarity(scorer.embed(wav), ref_embedding))

    all_wav = folder / "all.wav"
    timeline = playback_timeline(
        [c["gen_seconds"] for c in chunks], [c["audio_seconds"] for c in chunks]
    )
    return {
        "text_id": meta["text_id"],
        "lang": lang,
        "variant": meta["variant"],
        "chunks": len(chunks),
        "err_all": error_rate(meta["text"], scorer.transcribe(all_wav, lang), lang),
        "err_chunk_mean": statistics.mean(errors),
        "leak_rate": statistics.mean(leaks) if leaks else 0.0,
        "sim_all": scorer.similarity(scorer.embed(all_wav), ref_embedding),
        "sim_chunk_min": min(sims) if sims else 0.0,
        "first_chunk_s": timeline.first_audio_s,
        "stall_s": timeline.total_stall_s,
        "stalls": timeline.stalls,
        "rtf": sum(c["gen_seconds"] for c in chunks) / max(timeline.audio_s, 1e-6),
        "hit_max_tokens": sum(c["finish_reason"] != "eos" for c in chunks),
    }


def print_summary(rows: list[dict]) -> None:
    by_variant = defaultdict(list)
    for row in rows:
        by_variant[row["variant"]].append(row)
    metrics = COLUMNS[4:]
    print(f"\n{'variant':<17}" + "".join(f"{m:>15}" for m in metrics))
    for variant, group in by_variant.items():
        means = (statistics.mean(r[m] for r in group) for m in metrics)
        print(f"{variant:<17}" + "".join(f"{v:>15.3f}" for v in means))
    print("\nLower is better: " + ", ".join(sorted(LOWER_IS_BETTER)))


def main() -> None:
    args = parse_args()
    run_config = json.loads((args.run / "run.json").read_text())
    ref_audio = args.ref_audio or Path(run_config["ref_audio"])
    scorer = Scorer(args.asr_model, args.device)
    ref_embedding = scorer.embed(ref_audio)

    rows = []
    for meta_path in sorted(args.run.glob("*/*/meta.json")):
        row = score_variant(scorer, meta_path.parent, ref_embedding)
        rows.append(row)
        print(
            f"{row['text_id']:<12} {row['variant']:<17} err {row['err_all']:.3f}  "
            f"leak {row['leak_rate']:.2f}  sim {row['sim_all']:.3f}"
        )
    if not rows:
        raise SystemExit(f"no meta.json under {args.run}")

    with open(args.run / "scores.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print_summary(rows)
    print(f"\nWrote {args.run / 'scores.csv'}")


if __name__ == "__main__":
    main()
