"""Live demo, v0: text in over a WebSocket piece by piece, speech out chunk by chunk.

  python experiments/live_server.py --fake            # laptop: tones instead of speech
  python experiments/live_server.py \\
      --checkpoint ../fish-speech/checkpoints/drama-3 \\
      --ref-audio data/ref/voice.wav                  # one GPU, whole model on it

Open the printed address in a browser. The address carries a token: the socket
synthesizes speech in the reference voice, so it is not left open to everyone.
"""

import argparse
import asyncio
import json
import logging
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from aiohttp import WSMsgType, web

from speak_as_you_think.live import MODES, Connection, FakeSpeaker

# The page also runs without this server: on a static host it replays recorded runs (docs/live/recordings).
PAGE = Path(__file__).resolve().parent.parent / "docs" / "live" / "index.html"
logger = logging.getLogger("live")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fake", action="store_true", help="tones instead of the model")
    parser.add_argument("--checkpoint", help="Drama 3 checkpoint dir")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--ref-audio", type=Path)
    parser.add_argument("--ref-text", help="transcript; default: .lab/.txt next to audio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--token", default=secrets.token_urlsafe(9))
    parser.add_argument("--min-chars", type=int, default=12)
    parser.add_argument("--max-chars", type=int, default=30)
    args = parser.parse_args()
    if not args.fake and not (args.checkpoint and args.ref_audio):
        parser.error("give --checkpoint and --ref-audio, or --fake")
    return args


def load_speaker(args: argparse.Namespace):
    if args.fake:
        return FakeSpeaker()
    # Imported here so that --fake runs without fish-speech or a GPU.
    import torch
    from week1_run import reference_text

    from speak_as_you_think.modes import Drama3, LiveSpeaker, Sampling
    from speak_as_you_think.seams import SpeechDetector

    # A container is often allowed far fewer CPUs than the host has. One thread per host core gets the
    # process throttled, and generation slows with it (seen on a 128-core host with a 13-core allowance).
    torch.set_num_threads(min(torch.get_num_threads(), 8))
    engine = Drama3(args.checkpoint, args.device)
    refs = [engine.reference(args.ref_audio, reference_text(args.ref_audio, args.ref_text))]
    return LiveSpeaker(engine, refs, Sampling(), detector=SpeechDetector())


def warm_up(speaker, executor: ThreadPoolExecutor) -> None:
    """The first generation captures the CUDA graphs; do it before anyone is listening."""
    started = time.perf_counter()
    speaker.begin(MODES[0])
    spoken = executor.submit(speaker.speak, "Hello there, this is a warm-up.", "").result()
    logger.info(
        "warm-up: %.1f s of audio in %.1f s (%.1f s with start-up work)",
        spoken.audio_s, spoken.gen_s, time.perf_counter() - started,
    )


def build_app(speaker, executor: ThreadPoolExecutor, args: argparse.Namespace) -> web.Application:
    lock = asyncio.Lock()  # one reply at a time, across all clients

    async def page(request: web.Request) -> web.FileResponse:
        return web.FileResponse(PAGE)

    async def socket(request: web.Request) -> web.WebSocketResponse:
        if not secrets.compare_digest(request.query.get("token", ""), args.token):
            raise web.HTTPForbidden(text="bad or missing token")
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        sending = asyncio.Lock()

        async def send(message: dict, pcm: bytes | None) -> None:
            async with sending:  # keeps an audio message and its PCM frame together
                if ws.closed:
                    return
                try:
                    await ws.send_json(message)
                    if pcm is not None:
                        await ws.send_bytes(pcm)
                except ConnectionError:
                    pass  # the client went away mid-reply

        connection = Connection(speaker, send, lock, args.min_chars, args.max_chars, executor)
        ready = {
            "type": "ready",
            "sample_rate": speaker.sample_rate,
            "modes": list(MODES),
            "chunking": [args.min_chars, args.max_chars],
            "fake": args.fake,
            "device": speaker.device_name,
        }
        await send(ready, None)
        try:
            async for message in ws:
                if message.type != WSMsgType.TEXT:
                    continue
                try:
                    data = json.loads(message.data)
                except ValueError:
                    await connection.error("messages must be JSON objects")
                    continue
                await connection.handle(data if isinstance(data, dict) else {})
        finally:
            await connection.stop()  # whatever ended the socket, the reply must let go of the model
        return ws

    app = web.Application()
    app.add_routes([web.get("/", page), web.get("/ws", socket)])
    return app


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    speaker = load_speaker(args)
    # Every model call runs on this one thread.
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="speaker")
    warm_up(speaker, executor)
    logger.info("open http://localhost:%d/?token=%s", args.port, args.token)
    # No access log: every request line would carry the token.
    web.run_app(
        build_app(speaker, executor, args), host=args.host, port=args.port, print=None, access_log=None
    )


if __name__ == "__main__":
    main()
