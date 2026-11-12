"""Where two chunks meet: how the first one ends and how long the pause is (no torch).

A pause at a mid-phrase cut ("a light breeze from the | west") is what lookahead
should remove. Sentence ends are the control: a pause there is natural.
"""

from collections.abc import Sequence

import numpy as np

from drama3_live.chunker import CLAUSE_MARKS, SENTENCE_ENDS

CLOSING_MARKS = "\"'”’)」』】"


def seam_kind(chunk: str) -> str:
    """How the chunk before a seam ends: "sentence", "clause" or "word" (mid-phrase)."""
    last = chunk.rstrip().rstrip(CLOSING_MARKS)[-1:]
    if last in SENTENCE_ENDS:
        return "sentence"
    return "clause" if last in CLAUSE_MARKS else "word"


def edge_silence(
    samples: np.ndarray, sample_rate: int, threshold_db: float = -40.0, frame_s: float = 0.01
) -> tuple[float, float]:
    """Seconds of silence at the start and at the end of a clip.

    A frame is silent when its RMS is more than threshold_db below the loudest
    frame, so breaths count as sound. An all-silent clip is silent at both ends.
    """
    frame = max(1, round(frame_s * sample_rate))
    count = len(samples) // frame
    duration = len(samples) / sample_rate
    if count == 0:
        return duration, duration
    frames = np.asarray(samples[: count * frame], dtype=np.float64).reshape(count, frame)
    rms = np.sqrt(np.mean(frames**2, axis=1))
    loud = rms > rms.max() * 10 ** (threshold_db / 20)
    if not loud.any():
        return duration, duration
    first = int(np.argmax(loud))
    end = count - int(np.argmax(loud[::-1]))  # one past the last loud frame
    return first * frame / sample_rate, duration - end * frame / sample_rate


def seam_rows(chunks: Sequence[dict], edges: Sequence[tuple[float, float]]) -> list[dict]:
    """One row per seam between consecutive chunks of a meta.json.

    edges holds each chunk's (leading, trailing) silence. time_s is where the seam
    falls in all.wav, to find it when listening.
    """
    rows, time = [], 0.0
    for index in range(len(chunks) - 1):
        time += chunks[index]["audio_seconds"]
        left, right = chunks[index]["text"], chunks[index + 1]["text"]
        rows.append(
            {
                "seam": index,
                "kind": seam_kind(left),
                "time_s": round(time, 2),
                "pause_s": round(edges[index][1] + edges[index + 1][0], 3),
                "at": f"{left[-24:]} | {right[:24]}",
            }
        )
    return rows
