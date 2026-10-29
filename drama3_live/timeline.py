"""Playback timeline for chunked synthesis.

Chunks are generated one after another and played as soon as ready. Chunk i
starts at max(ready_i, end of chunk i-1); any gap before it is a stall the
listener hears as silence. Text is assumed to be available up front (offline).
"""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass
class Timeline:
    first_audio_s: float  # when chunk 0 is ready (per-chunk, not per-frame)
    total_stall_s: float  # silence inserted between chunks
    stalls: int
    finish_s: float  # when the last chunk finishes playing
    audio_s: float


def playback_timeline(
    gen_seconds: Sequence[float], audio_seconds: Sequence[float]
) -> Timeline:
    if len(gen_seconds) != len(audio_seconds) or not gen_seconds:
        raise ValueError("need one generation time and one duration per chunk")
    ready = end = 0.0
    total_stall, stalls = 0.0, 0
    for index, (gen, dur) in enumerate(zip(gen_seconds, audio_seconds)):
        ready += gen
        if index == 0:
            start = ready
        else:
            start = max(ready, end)
            if ready > end:
                total_stall += ready - end
                stalls += 1
        end = start + dur
    return Timeline(
        first_audio_s=gen_seconds[0],
        total_stall_s=total_stall,
        stalls=stalls,
        finish_s=end,
        audio_s=sum(audio_seconds),
    )
