"""Record real runs of the live server, and pack them for the page to replay without a server.

  # on the GPU machine, with live_server.py running
  python experiments/live_record.py --token <token> --raw results/live_recordings
  # anywhere with ffmpeg
  python experiments/live_record.py --raw results/live_recordings --out docs/live/recordings

Recording feeds each reply as the page does and keeps every audio message, its arrival time
and the audio. Every take is kept: the page plays them in turn. Packing writes one index.json
and one AAC file per run.
"""

import argparse
import asyncio
import json
import subprocess
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

# The page's preset replies, word for word: the page finds a recording by its text.
REPLIES = {
    "Directions": "Sure, here's the easiest way to get there from the station. Take the north exit and turn left onto Main Street. Keep walking until you see a small bakery with a green awning on the corner. Turn right just after the bakery, and the museum will be on your left, right across from the park. It's a short walk, so if you leave now, you should get there a little before it opens.",
    "Billing": "I've looked into your account, and I can see what happened with last month's bill. You were charged twice because the first payment went through, but the app showed an error, so you tried again. Our system flagged the second charge automatically, and the refund has already been approved on our side. Depending on your bank, it can take a few business days to show up.",
    "Two sentences": "Sure, here's the easiest way to get there from the station. Take the north exit and turn left onto Main Street.",
}
TAKES = {"Directions": 3, "Billing": 1, "Two sentences": 1}
WAYS = ("independent", "streaming-last", "streaming-all")
RATE, SEND_S = 80, 0.04  # characters per second and seconds between sends, as on the page


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--token", help="record from the live server that printed this token")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--raw", type=Path, required=True, help="folder of the recorded runs")
    parser.add_argument("--out", type=Path, help="pack the runs into this folder for the page")
    return parser.parse_args()


async def record_run(ws, sample_rate: int, reply: str, way: str, take: int, raw: Path) -> None:
    import aiohttp

    text = REPLIES[reply]
    await ws.send_json({"type": "start", "mode": way, "id": f"{reply}-{way}-{take}"})
    started = time.perf_counter()

    async def feed() -> float:
        sent = 0
        while sent < len(text):
            await asyncio.sleep(SEND_S)
            upto = min(len(text), round((time.perf_counter() - started) * RATE))
            if upto > sent:
                await ws.send_json({"type": "text", "text": text[sent:upto]})
                sent = upto
        await ws.send_json({"type": "flush"})
        return time.perf_counter() - started

    feeder = asyncio.create_task(feed())
    chunks, pcm, pending, done_s = [], [], None, None
    async for message in ws:
        now = time.perf_counter() - started
        if message.type == aiohttp.WSMsgType.BINARY:
            pending.pop("type"), pending.pop("reply", None)
            chunks.append(pending | {"arrive_s": round(now, 3), "samples": len(message.data) // 2})
            pcm.append(message.data)
            continue
        data = json.loads(message.data)
        if data["type"] == "audio":
            pending = data
        elif data["type"] == "finish" and data["reason"] == "done":
            done_s = now
            break
        else:
            raise RuntimeError(f"unexpected message while recording: {data}")
    name = f"run_{reply.lower().replace(' ', '-')}_{way}_{take}"
    with wave.open(str(raw / f"{name}.wav"), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(pcm))
    run = {
        "reply": reply, "text": text, "way": way, "take": take, "audio": f"{name}.m4a",
        "rate": RATE, "send_ms": round(SEND_S * 1000), "flush_s": round(await feeder, 3), "done_s": round(done_s, 3),
        "recorded": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "chunks": chunks,
    }  # fmt: skip
    (raw / f"{name}.json").write_text(json.dumps(run, ensure_ascii=False, indent=1))
    print(f"{name}: {len(chunks)} chunks, {sum(c['audio_s'] for c in chunks):.1f} s of audio", flush=True)


async def record(token: str, port: int, raw: Path) -> None:
    import aiohttp

    raw.mkdir(parents=True, exist_ok=True)
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(f"http://127.0.0.1:{port}/ws?token={token}", max_msg_size=0) as ws:
            ready = json.loads((await ws.receive()).data)
            names = []
            for reply, takes in TAKES.items():
                for take in range(1, takes + 1):
                    for way in WAYS:
                        await record_run(ws, ready["sample_rate"], reply, way, take, raw)
                        names.append(f"run_{reply.lower().replace(' ', '-')}_{way}_{take}.json")
            (raw / "index.json").write_text(json.dumps({"ready": ready, "runs": names}, indent=1))


def pack(raw: Path, out: Path) -> None:
    """One index.json for the page and one AAC file per run. Needs ffmpeg."""
    out.mkdir(parents=True, exist_ok=True)
    index = json.loads((raw / "index.json").read_text())
    ready, runs = index["ready"], []
    for name in index["runs"]:
        run = json.loads((raw / name).read_text())
        with wave.open(str(raw / name.replace(".json", ".wav"))) as wav:
            if wav.getnframes() != sum(chunk["samples"] for chunk in run["chunks"]):
                raise ValueError(f"{name}: the audio does not match its chunks")
        audio = name.removeprefix("run_").replace(".json", ".m4a")
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw / name.replace(".json", ".wav")),
             "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out / audio)],
            check=True,
        )  # fmt: skip
        takes = sum(1 for other in index["runs"] if other.rsplit("_", 1)[0] == name.rsplit("_", 1)[0])
        keep = ("reply", "text", "way", "take", "flush_s", "done_s", "chunks")
        runs.append({key: run[key] for key in keep} | {"takes": takes, "audio": audio})
    first = json.loads((raw / index["runs"][0]).read_text())
    page = {
        "recorded": first["recorded"][:10], "device": ready["device"], "sample_rate": ready["sample_rate"],
        "chunking": ready["chunking"], "modes": ready["modes"], "rate": first["rate"], "send_ms": first["send_ms"],
        "runs": runs,
    }  # fmt: skip
    (out / "index.json").write_text(json.dumps(page, ensure_ascii=False, separators=(",", ":")))
    size = sum(path.stat().st_size for path in out.iterdir()) / 1e6
    print(f"packed {len(runs)} runs into {out}: {size:.1f} MB")


def main() -> None:
    args = parse_args()
    if args.token:
        asyncio.run(record(args.token, args.port, args.raw))
    if args.out:
        pack(args.raw, args.out)


if __name__ == "__main__":
    main()
