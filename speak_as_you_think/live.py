"""A spoken reply as a message exchange: text in piece by piece, audio out chunk by chunk.

Client messages follow Fish Audio's live TTS socket (start, text, flush, stop) plus
interrupt; the server answers with audio and finish. Nothing here needs a GPU: the
speaker is anything with begin(mode) and a blocking speak(text, lookahead).

    client                          server
    start {mode}
    text {text} ...                 audio {index, text, ...} + one binary PCM frame, per chunk
    flush                           finish {reason: "done"}
    interrupt {heard_s}             finish {reason: "interrupted", heard_text, cut, unheard_text}
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from concurrent.futures import Executor
from dataclasses import dataclass, field

import numpy as np

from speak_as_you_think.chunker import StreamChunker, join_chunks

MODES = ("streaming-last", "streaming-all", "independent")
Send = Callable[[dict, bytes | None], Awaitable[None]]
logger = logging.getLogger(__name__)


@dataclass
class Spoken:
    """One synthesized chunk: 16-bit mono PCM and how it was made."""

    text: str
    lookahead: str
    pcm: bytes
    audio_s: float
    gen_s: float
    info: dict = field(default_factory=dict)


class Reply:
    """One reply: chunks the incoming text and speaks each chunk once its lookahead is known."""

    def __init__(
        self,
        speaker,
        send: Send,
        min_chars: int = 12,
        max_chars: int = 30,
        executor: Executor | None = None,
    ) -> None:
        self.speaker, self.send = speaker, send
        self.executor = executor  # where speak() runs; a GPU model wants one fixed thread
        self.chunker = StreamChunker(min_chars, max_chars)
        self.chunks: list[str] = []  # chunks that can no longer change
        self.closed = False  # no more text will come
        self.heard_s: float | None = None  # audio the listener heard before interrupting
        self.sent: list[Spoken] = []
        self.changed = asyncio.Event()

    def feed(self, text: str) -> None:
        self.chunks += self.chunker.feed(text)
        self.changed.set()

    def close(self) -> None:
        self.chunks += self.chunker.close()
        self.closed = True
        self.changed.set()

    def interrupt(self, heard_s: float) -> None:
        self.heard_s = max(0.0, heard_s)
        self.changed.set()

    async def run(self) -> None:
        index = 0
        while self.heard_s is None:
            has_lookahead = index + 1 < len(self.chunks)
            if has_lookahead or (self.closed and index < len(self.chunks)):
                lookahead = self.chunks[index + 1] if has_lookahead else ""
                spoken = await asyncio.get_running_loop().run_in_executor(
                    self.executor, self.speaker.speak, self.chunks[index], lookahead
                )
                if self.heard_s is not None:
                    break  # interrupted while this chunk was being made: it is never played
                message = {
                    "type": "audio",
                    "index": index,
                    "text": spoken.text,
                    "lookahead": spoken.lookahead,
                    "audio_s": round(spoken.audio_s, 3),
                    "gen_s": round(spoken.gen_s, 3),
                    **spoken.info,
                }
                await self.send(message, spoken.pcm)
                self.sent.append(spoken)
                index += 1
            elif self.closed:
                break
            else:
                # Nothing between the check above and here awaits, so no feed() is lost.
                self.changed.clear()
                await self.changed.wait()
        await self.send(self.finish(), None)

    def finish(self) -> dict:
        if self.heard_s is None:
            return {"type": "finish", "reason": "done", "chunks": len(self.sent)}
        heard, cut, start = [], None, 0.0
        for spoken in self.sent:
            end = start + spoken.audio_s
            if end <= self.heard_s + 0.01:
                heard.append(spoken.text)
            elif start < self.heard_s and cut is None:
                cut = {"text": spoken.text, "heard": round((self.heard_s - start) / spoken.audio_s, 2)}
            start = end
        rest = self.chunks[len(heard) + (cut is not None) :]
        if self.chunker.pending.strip():
            rest = rest + [self.chunker.pending.strip()]
        return {
            "type": "finish",
            "reason": "interrupted",
            "heard_s": round(self.heard_s, 3),
            "heard_text": join_chunks(heard),  # chunks played to the end
            "cut": cut,  # the chunk that was playing, and how much of it was heard
            "unheard_text": join_chunks(rest),
        }


class Connection:
    """The messages of one client, in order. One reply at a time."""

    def __init__(
        self,
        speaker,
        send: Send,
        lock: asyncio.Lock,
        min_chars: int = 12,
        max_chars: int = 30,
        executor: Executor | None = None,
    ) -> None:
        self.speaker, self.send, self.lock = speaker, send, lock
        self.min_chars, self.max_chars, self.executor = min_chars, max_chars, executor
        self.reply: Reply | None = None
        self.task: asyncio.Task | None = None

    async def handle(self, message: dict) -> None:
        kind = message.get("type")
        if kind == "start":
            mode = message.get("mode", MODES[0])
            if mode not in MODES:
                return await self.error(f"unknown mode {mode!r}; use one of {', '.join(MODES)}")
            await self.stop()
            self.reply = Reply(
                self.speaker, self.send, self.min_chars, self.max_chars, self.executor
            )
            self.task = asyncio.create_task(self.run(self.reply, mode))
        elif kind == "stop":
            await self.stop()
        elif self.reply is None:
            await self.error(f"{kind!r} before start")
        elif kind == "text":
            self.reply.feed(str(message.get("text", "")))
        elif kind == "flush":
            self.reply.close()
        elif kind == "interrupt":
            self.reply.interrupt(float(message.get("heard_s", 0.0)))
        else:
            await self.error(f"unknown message type {kind!r}")

    async def run(self, reply: Reply, mode: str) -> None:
        try:
            async with self.lock:  # the model speaks one reply at a time
                self.speaker.begin(mode)
                await reply.run()
        except Exception as error:  # noqa: BLE001  report it to the client instead of dying silently
            logger.exception("reply failed")
            await self.error(f"{type(error).__name__}: {error}")

    async def stop(self) -> None:
        """End the running reply. A chunk being generated cannot be cancelled, so wait for it."""
        if self.task is not None and not self.task.done():
            self.reply.interrupt(0.0)
            await self.task
        self.reply = self.task = None

    async def error(self, text: str) -> None:
        await self.send({"type": "error", "message": text}, None)


class FakeSpeaker:
    """Stands in for the model on a laptop: one tone per chunk, about as long as speech."""

    sample_rate = 44100

    def __init__(self, rtf: float = 0.7) -> None:
        self.rtf = rtf  # seconds of work per second of audio
        self.round = 0

    def begin(self, mode: str) -> None:
        self.round = 0

    def speak(self, text: str, lookahead: str) -> Spoken:
        started = time.perf_counter()
        seconds = 0.3 + 0.085 * len(text.encode("utf-8"))  # about 11 Latin letters a second
        t = np.arange(round(seconds * self.sample_rate)) / self.sample_rate
        tone = 0.2 * np.sin(2 * np.pi * (220, 277, 330)[self.round % 3] * t)
        tone *= np.minimum(1.0, np.minimum(t, seconds - t) / 0.02)  # 20 ms fades
        silence = np.zeros(round(0.08 * self.sample_rate))
        audio = np.concatenate([silence, tone, silence])
        self.round += 1
        time.sleep(len(audio) / self.sample_rate * self.rtf)
        return Spoken(
            text,
            lookahead,
            (audio * 32767).astype("<i2").tobytes(),
            len(audio) / self.sample_rate,
            time.perf_counter() - started,
            {"frames": round(len(audio) / 2048), "prompt_rows": 0, "finish_reason": "eos"},
        )
