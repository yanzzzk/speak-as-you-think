"""Build the data and audio clips of the results page (docs/) from scored runs.

Usage: python experiments/page_data.py results/round2 --out docs

Every number on the page is recomputed here from the raw files of each seed folder:
  <text>/<variant>/chunk_XX.wav + meta.json   seam pauses (Silero VAD, as in week1_score.py)
  scores.csv                                  errors, leakage, speaker similarity
Writes <out>/data.js and <out>/audio/*.m4a (needs ffmpeg).
"""

import argparse
import csv
import json
import statistics
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchaudio

from speak_as_you_think.seams import VAD_RATE, SpeechDetector, edge_nonspeech, seam_rows

SAMPLE_RATE = VAD_RATE
MID_SENTENCE = ("word", "clause")
# Listening section, in page order: text id -> (first chunk, number of chunks). Every
# passage ends at a sentence end; two open a reply and one comes from the middle of one.
PASSAGES = {"en_train": (0, 7), "en_billing": (7, 7), "en_directions": (0, 4), "zh_trip": (0, 3)}
# streaming-round keeps every earlier round; streaming-round-w1 only the latest one.
CLIP_VARIANTS = ("independent", "fish_history", "streaming-round-w1", "streaming-round")
TARGET_DBFS = -23.0  # speech level of every clip, so loudness does not bias listening


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run", type=Path, help="folder holding the seed folders of week1_run.py")
    parser.add_argument("--out", type=Path, default=Path("docs"))
    parser.add_argument("--extra", type=Path, help="csv with utmos_joined per seed, text_id, variant")
    return parser.parse_args()


class Vad:
    """The speech detector of week1_score.py, run on a chunk's wav file."""

    def __init__(self) -> None:
        self.detector = SpeechDetector()

    def speech(self, path: Path) -> tuple[list[tuple[int, int]], int]:
        """Speech segments as sample indices at SAMPLE_RATE, and the clip length."""
        samples, sr = sf.read(path, dtype="float32", always_2d=True)
        wav = torch.from_numpy(samples).mean(dim=1).unsqueeze(0)
        wav = torchaudio.functional.resample(wav, sr, SAMPLE_RATE)[0].numpy()
        return self.detector.segments(wav), len(wav)


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_run(vad: Vad, folder: Path) -> dict:
    """One text/variant folder: meta.json plus the speech segments of every chunk."""
    meta = json.loads((folder / "meta.json").read_text())
    speech, lengths = [], []
    for index, chunk in enumerate(meta["chunks"]):
        segments, length = vad.speech(folder / f"chunk_{index:02d}.wav") if chunk["frames"] else ([], 0)
        speech.append(segments)
        lengths.append(length)
    edges = [edge_nonspeech(s, n, SAMPLE_RATE) for s, n in zip(speech, lengths)]
    return {"folder": folder, "meta": meta, "speech": speech, "lengths": lengths, "edges": edges}


def by_variant(values: dict, variants: list[str], stat) -> dict:
    return {v: round(stat(values[v]), 4) for v in variants if values[v]}


def seam_stats(seams: list[dict], variants: list[str], failed: set) -> dict:
    """Seam table by language and kind, plus the headline comparison."""
    groups = defaultdict(lambda: defaultdict(list))
    for s in seams:
        groups[s["lang"], s["kind"]][s["variant"]].append(s["pause_s"])
    table = [
        {
            "lang": lang,
            "kind": kind,
            "n": len(groups[lang, kind][variants[0]]),
            "median": by_variant(groups[lang, kind], variants, statistics.median),
            "mean": by_variant(groups[lang, kind], variants, statistics.mean),
        }
        for lang in ("en", "zh")
        for kind in ("word", "clause", "sentence")
        if (lang, kind) in groups
    ]

    lead = [s for s in seams if s["lang"] == "en" and s["kind"] == "word"]
    kept = defaultdict(list)
    over = defaultdict(list)
    first = defaultdict(list)
    later = defaultdict(list)
    for s in lead:
        over[s["variant"]].append(s["pause_s"] > 0.3)
        (first if s["seam"] == 0 else later)[s["variant"]].append(s["pause_s"])
        if (s["seed"], s["text_id"]) not in failed:
            kept[s["variant"]].append(s["pause_s"])
    return {
        "table": table,
        # The first seam of a text, where streaming has no spoken round behind it yet.
        "first_seam": {"n": len(first[variants[0]]), "median": by_variant(first, variants, statistics.median)},
        "later_seams": {"n": len(later[variants[0]]), "median": by_variant(later, variants, statistics.median)},
        "mean_without_failed": by_variant(kept, variants, statistics.mean),
        "n_without_failed": len(kept[variants[0]]),
        "share_over_0p3": by_variant(over, variants, statistics.mean),
        "paired_mid_phrase": paired(lead, variants, "streaming-round"),
        "paired_first_seam": paired([s for s in lead if s["seam"] == 0], variants, "streaming-round"),
        "paired_mid_phrase_last_round": paired(lead, variants, "streaming-round-w1"),
        "paired_mid_sentence": paired([s for s in seams if s["kind"] in MID_SENTENCE], variants, "streaming-round"),
        "paired_sentence_end": paired([s for s in seams if s["kind"] == "sentence"], variants, "streaming-round"),
    }


def paired(seams: list[dict], variants: list[str], subject: str) -> dict:
    """At how many seams (same seed, text and cut) the subject paused less, or more, than each other mode."""
    same = defaultdict(dict)
    for s in seams:
        same[s["seed"], s["text_id"], s["seam"]][s["variant"]] = s["pause_s"]
    result = {}
    for other in variants:
        if other == subject:
            continue
        pairs = [(g[subject], g[other]) for g in same.values() if subject in g and other in g]
        result[other] = {
            "shorter": sum(a < b for a, b in pairs),
            "longer": sum(a > b for a, b in pairs),
            "of": len(pairs),
        }
    return result


def item_stats(rows: list[dict], variants: list[str], extra: list[dict]) -> dict:
    """Per-clip scores (one clip = one text, seed and variant) averaged per variant."""
    columns = defaultdict(lambda: defaultdict(list))
    for r in rows:
        v = r["variant"]
        columns["err_" + r["lang"]][v].append(float(r["err_all"]))
        columns["err_chunk_" + r["lang"]][v].append(float(r["err_chunk_mean"]))
        for name in ("leak_rate", "sim_all", "sim_first", "sim_last"):
            columns[name][v].append(float(r[name]))
        columns["failed_chunks"][v].append(int(r["hit_max_tokens"]))
        columns["chunks"][v].append(int(r["chunks"]))
    stats = {name: by_variant(values, variants, statistics.mean) for name, values in columns.items()}
    for name in ("failed_chunks", "chunks"):
        stats[name] = {v: sum(columns[name][v]) for v in variants}
    stats["clips"] = len(columns["sim_all"][variants[0]])

    key = lambda r: (str(r["seed"]), r["text_id"])  # noqa: E731
    sim = defaultdict(dict)
    for r in rows:
        sim[key(r)][r["variant"]] = float(r["sim_all"])
    stats["sim_below_independent"] = {
        v: sum(g[v] < g["independent"] for g in sim.values()) for v in variants if v != "independent"
    }
    stats["sim_above_all_rounds"] = {
        v: sum(g[v] > g["streaming-round"] for g in sim.values()) for v in variants if v != "streaming-round"
    }
    if extra:
        utmos = defaultdict(dict)
        for r in extra:
            utmos[key(r)][r["variant"]] = float(r["utmos_joined"])
        scored = [v for v in variants if all(v in g for g in utmos.values())]  # UTMOS may cover fewer modes
        stats["utmos"] = {v: round(statistics.mean(g[v] for g in utmos.values()), 2) for v in scored}
        stats["utmos_above_independent"] = {
            v: sum(g[v] > g["independent"] for g in utmos.values()) for v in scored if v != "independent"
        }
    return stats


def typical_seed(seams: list[dict], text_id: str, start: int, count: int) -> str:
    """The seed whose pauses in the passage are closest to the average over seeds."""
    pauses = defaultdict(lambda: defaultdict(list))
    for s in seams:
        inside = start <= s["seam"] < start + count - 1
        if s["text_id"] == text_id and inside and s["variant"] in CLIP_VARIANTS:
            pauses[s["seed"]][s["variant"]].append(s["pause_s"])
    means = {seed: {v: statistics.mean(p[v]) for v in CLIP_VARIANTS} for seed, p in pauses.items()}
    center = {v: statistics.mean(m[v] for m in means.values()) for v in CLIP_VARIANTS}
    return min(means, key=lambda seed: sum((means[seed][v] - center[v]) ** 2 for v in CLIP_VARIANTS))


def write_clip(run: dict, start: int, count: int, path: Path) -> dict:
    """Join the chunks as a chunk player would, match the speech level, encode as AAC."""
    parts, speech, seams, offset, sr = [], [], [], 0.0, None
    end = start + count
    for index in range(start, end):
        samples, sr = sf.read(run["folder"] / f"chunk_{index:02d}.wav", dtype="float32", always_2d=True)
        parts.append(samples.mean(axis=1))
        speech += [(offset + a / SAMPLE_RATE, offset + b / SAMPLE_RATE) for a, b in run["speech"][index]]
        offset += len(samples) / sr
        if index < end - 1:
            trail, lead = run["edges"][index][1], run["edges"][index + 1][0]
            seams.append({"t": offset, "from": offset - trail, "to": offset + lead, "pause": trail + lead})
    audio = np.concatenate(parts)
    voiced = np.concatenate([audio[int(a * sr) : int(b * sr)] for a, b in speech]) if speech else audio
    gain = 10 ** (TARGET_DBFS / 20) / np.sqrt(np.mean(voiced**2))
    audio = audio * min(gain, 0.98 / np.abs(audio).max())
    with tempfile.TemporaryDirectory() as tmp:
        sf.write(Path(tmp) / "clip.wav", audio, sr)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(Path(tmp) / "clip.wav"),
             "-c:a", "aac", "-b:a", "96k", str(path)],
            check=True,
        )
    rows = seam_rows(run["meta"]["chunks"][start:end], run["edges"][start:end])
    for seam, row in zip(seams, rows):
        seam["kind"] = row["kind"]
    rounded = lambda x: round(x, 4)  # noqa: E731
    return {
        "variant": run["meta"]["variant"],
        "file": f"audio/{path.name}",
        "seconds": rounded(offset),
        "speech": [[rounded(a), rounded(b)] for a, b in speech],
        "seams": [{k: rounded(v) if isinstance(v, float) else v for k, v in s.items()} for s in seams],
    }


def main() -> None:
    args = parse_args()
    seed_dirs = sorted(d for d in args.run.glob("seed*") if (d / "run.json").is_file())
    if not seed_dirs:
        raise SystemExit(f"no seed folders with run.json under {args.run}")
    vad = Vad()
    runs, seams, rows = {}, [], []
    for seed_dir in seed_dirs:
        seed = str(json.loads((seed_dir / "run.json").read_text())["seed"])
        rows += [r | {"seed": seed} for r in read_csv(seed_dir / "scores.csv")]
        for meta_path in sorted(seed_dir.glob("*/*/meta.json")):
            run = read_run(vad, meta_path.parent)
            meta = run["meta"]
            runs[seed, meta["text_id"], meta["variant"]] = run
            key = {"seed": seed, "text_id": meta["text_id"], "lang": meta["lang"], "variant": meta["variant"]}
            for index, row in enumerate(seam_rows(meta["chunks"], run["edges"])):
                # Unrounded, so that each statistic is rounded only once, when it is written.
                pause = run["edges"][index][1] + run["edges"][index + 1][0]
                seams.append(key | row | {"pause_s": pause})
        print(f"read {seed_dir}")

    order = ("independent", "fish_history", "streaming-round", "streaming-round-w4", "streaming-round-w1")
    variants = [v for v in order if any(s["variant"] == v for s in seams)]
    failed = {(r["seed"], r["text_id"]) for r in rows if int(r["hit_max_tokens"])}
    extra_path = args.extra or args.run / "combined_metrics.csv"
    extra = read_csv(extra_path) if extra_path.is_file() else []

    (args.out / "audio").mkdir(parents=True, exist_ok=True)
    clips = []
    for text_id, (start, count) in PASSAGES.items():
        seed = typical_seed(seams, text_id, start, count)
        meta = runs[seed, text_id, CLIP_VARIANTS[0]]["meta"]
        clips.append(
            {
                "text_id": text_id,
                "lang": meta["lang"],
                "seed": int(seed),
                "first_chunk": start,
                "chunks": [c["text"] for c in meta["chunks"][start : start + count]],
                "modes": [
                    write_clip(runs[seed, text_id, v], start, count, args.out / "audio" / f"{text_id}_{v}.m4a")
                    for v in CLIP_VARIANTS
                ],
            }
        )
        print(f"clip {text_id}: seed {seed}, chunks {start}-{start + count - 1}")

    data = {
        "source": {"seeds": [d.name for d in seed_dirs], "variants": variants, "texts": len({s["text_id"] for s in seams})},
        "seams": seam_stats(seams, variants, failed),
        "items": item_stats(rows, variants, extra),
        "clips": clips,
    }
    text = json.dumps(data, ensure_ascii=False, indent=1)
    (args.out / "data.js").write_text(f"window.PAGE_DATA = {text};\n", encoding="utf-8")
    print(f"wrote {args.out / 'data.js'} and {len(clips) * len(CLIP_VARIANTS)} clips")


if __name__ == "__main__":
    main()
