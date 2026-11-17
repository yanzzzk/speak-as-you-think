"""Where two chunks meet: how the first one ends and how long the pause is (no torch).

A pause at a mid-phrase cut ("a light breeze from the | west") is what lookahead
should remove. Sentence ends are the control: a pause there is natural.
"""

from collections.abc import Sequence

from drama3_live.chunker import CLAUSE_MARKS, SENTENCE_ENDS

CLOSING_MARKS = "\"'”’)」』】"


def seam_kind(chunk: str) -> str:
    """How the chunk before a seam ends: "sentence", "clause" or "word" (mid-phrase)."""
    last = chunk.rstrip().rstrip(CLOSING_MARKS)[-1:]
    if last in SENTENCE_ENDS:
        return "sentence"
    return "clause" if last in CLAUSE_MARKS else "word"


def edge_nonspeech(
    speech: Sequence[tuple[int, int]], length: int, sample_rate: int
) -> tuple[float, float]:
    """Seconds of non-speech before the first and after the last speech segment.

    speech holds (start, end) sample indices from a voice activity detector. A clip
    without speech is non-speech at both ends. This counts non-speech, not quiet:
    generated audio copies the reference's room noise, so its pauses are not silent.
    """
    if not speech:
        return length / sample_rate, length / sample_rate
    return speech[0][0] / sample_rate, (length - speech[-1][1]) / sample_rate


def seam_rows(chunks: Sequence[dict], edges: Sequence[tuple[float, float]]) -> list[dict]:
    """One row per seam between consecutive chunks of a meta.json.

    edges holds each chunk's (leading, trailing) non-speech. time_s is where the
    seam falls in all.wav, to find it when listening.
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
