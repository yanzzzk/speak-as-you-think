"""Week 1: synthesize every test text in every mode with the same reference voice.

Writes, per seed, text and variant:
  <out>/seed<N>/run.json                           settings of this seed's run
  <out>/seed<N>/<text_id>/<variant>/chunk_XX.wav   each chunk decoded on its own
  <out>/seed<N>/<text_id>/<variant>/all.wav        all chunk codes decoded together
  <out>/seed<N>/<text_id>/<variant>/meta.json      chunks, timings, prompt sizes
  <out>/seed<N>/<text_id>/<variant>/codes.pt       per-chunk codes, for re-decoding

Folders that already have meta.json are skipped, so an interrupted run resumes.
A text can set its own min_chars and max_chars in the texts file.
"""

import argparse
import json
import sys
from pathlib import Path

import soundfile as sf
import torch

from speak_as_you_think.chunker import split_chunks
from speak_as_you_think.modes import (
    Drama3,
    Sampling,
    run_fish_history,
    run_full,
    run_independent,
    run_streaming,
)

VARIANTS = (
    "full",
    "independent",
    "fish_history",
    "streaming-system",
    "streaming-round",
    # Round 3: the same, remembering only the last 1 or 4 rounds besides the reference.
    "streaming-round-w1",
    "streaming-round-w4",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--checkpoint", required=True, help="Drama 3 checkpoint dir")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--ref-audio", type=Path, required=True)
    parser.add_argument("--ref-text", help="transcript; default: .lab/.txt next to audio")
    parser.add_argument("--texts", type=Path, default=Path("data/week1_texts.jsonl"))
    parser.add_argument("--only", nargs="*", help="text ids to run (default: all)")
    parser.add_argument("--variants", nargs="*", choices=VARIANTS, default=VARIANTS)
    parser.add_argument(
        "--speaker-tag", action=argparse.BooleanOptionalAction, default=True
    )
    parser.add_argument("--min-chars", type=int, default=12, help="unless the text sets it")
    parser.add_argument("--max-chars", type=int, default=80, help="unless the text sets it")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42])
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--top-p", type=float)
    parser.add_argument("--out", type=Path, default=Path("results/week1"))
    return parser.parse_args()


def reference_text(audio: Path, given: str | None) -> str:
    if given:
        return given
    for suffix in (".lab", ".txt"):
        sidecar = audio.with_suffix(suffix)
        if sidecar.is_file():
            return sidecar.read_text(encoding="utf-8").strip()
    sys.exit(f"no transcript for {audio}: pass --ref-text or write {audio.with_suffix('.lab')}")


def run_variant(engine, variant, text, chunks, refs, sampling, speaker_tag):
    if variant == "full":
        return run_full(engine, text, refs, sampling)
    if variant == "independent":
        return run_independent(engine, chunks, refs, sampling)
    if variant == "fish_history":
        return run_fish_history(engine, chunks, refs, sampling)
    # "streaming-round-w4" -> ref_style "round", window 4
    ref_style, _, window = variant.removeprefix("streaming-").partition("-w")
    max_history = int(window) if window else None
    return run_streaming(engine, chunks, refs, sampling, ref_style, speaker_tag, max_history)


def save(out_dir: Path, engine: Drama3, item: dict, variant: str, results) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    sr = engine.sample_rate
    chunks = []
    for index, result in enumerate(results):
        audio = engine.decode(result.codes) if result.codes.shape[1] else torch.zeros(0)
        sf.write(out_dir / f"chunk_{index:02d}.wav", audio.numpy(), sr)
        chunks.append(
            {
                "text": result.text,
                "lookahead": result.lookahead,
                "frames": result.codes.shape[1],
                "prompt_rows": result.prompt_rows,
                "gen_seconds": round(result.gen_seconds, 4),
                "audio_seconds": round(len(audio) / sr, 4),
                "finish_reason": result.finish_reason,
            }
        )
    nonempty = [r.codes for r in results if r.codes.shape[1]]
    if nonempty:
        sf.write(out_dir / "all.wav", engine.decode(torch.cat(nonempty, dim=1)).numpy(), sr)
    torch.save([r.codes for r in results], out_dir / "codes.pt")
    meta = {
        "text_id": item["id"],
        "lang": item["lang"],
        "text": item["text"],
        "variant": variant,
        "sample_rate": sr,
        "chunks": chunks,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return meta


def report(variant: str, meta: dict) -> None:
    chunks = meta["chunks"]
    gen = sum(c["gen_seconds"] for c in chunks)
    audio = sum(c["audio_seconds"] for c in chunks)
    not_eos = sum(c["finish_reason"] != "eos" for c in chunks)
    print(
        f"  {variant:<20} audio {audio:6.2f}s  gen {gen:6.2f}s  "
        f"first chunk {chunks[0]['gen_seconds']:5.2f}s  "
        f"max prompt {max(c['prompt_rows'] for c in chunks)} rows"
        + (f"  [{not_eos} chunk(s) hit max_new_tokens]" if not_eos else "")
    )


def main() -> None:
    args = parse_args()
    items = [json.loads(line) for line in args.texts.read_text().splitlines() if line.strip()]
    if args.only:
        items = [item for item in items if item["id"] in args.only]
    if not items:
        sys.exit("no texts selected")

    engine = Drama3(args.checkpoint, args.device)
    refs = [engine.reference(args.ref_audio, reference_text(args.ref_audio, args.ref_text))]
    sampling = Sampling(args.temperature, args.top_k, args.top_p)
    run_config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}

    # Seeds outermost, so the first seed is complete early.
    for seed in args.seeds:
        run_dir = args.out / f"seed{seed}"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "run.json").write_text(json.dumps(run_config | {"seed": seed}, indent=1))
        for item in items:
            chunks = split_chunks(
                item["text"],
                item.get("min_chars", args.min_chars),
                item.get("max_chars", args.max_chars),
            )
            print(f"\n== seed {seed}, {item['id']} ({item['lang']}): {len(chunks)} chunks")
            for variant in args.variants:
                out_dir = run_dir / item["id"] / variant
                if (out_dir / "meta.json").is_file():
                    print(f"  {variant:<20} already done, skipped")
                    continue
                torch.manual_seed(seed)
                results = run_variant(
                    engine, variant, item["text"], chunks, refs, sampling, args.speaker_tag
                )
                report(variant, save(out_dir, engine, item, variant, results))
    runs = " ".join(str(args.out / f"seed{seed}") for seed in args.seeds)
    print(f"\nDone. Score with: python experiments/week1_score.py {runs}")


if __name__ == "__main__":
    main()
