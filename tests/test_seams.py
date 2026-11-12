import numpy as np
import pytest

from drama3_live.seams import edge_silence, seam_kind, seam_rows

SR = 16000


def tone(seconds: float, amplitude: float = 0.5) -> np.ndarray:
    t = np.arange(round(seconds * SR)) / SR
    return amplitude * np.sin(2 * np.pi * 220 * t)


def test_seam_kinds():
    assert seam_kind("Sure, here's the easiest way to") == "word"
    assert seam_kind("I've looked into your account,") == "clause"
    assert seam_kind("get there from the station.") == "sentence"
    assert seam_kind("老陈愣了一下，笑着说，") == "clause"
    assert seam_kind("还有没有吃的。") == "sentence"
    assert seam_kind('She said "thank you."') == "sentence"


def test_edge_silence_measures_both_ends():
    clip = np.concatenate([np.zeros(round(0.2 * SR)), tone(0.5), np.zeros(round(0.3 * SR))])
    lead, trail = edge_silence(clip, SR)
    assert lead == pytest.approx(0.2, abs=0.01)
    assert trail == pytest.approx(0.3, abs=0.01)


def test_quiet_noise_counts_as_silence():
    noise = 0.0005 * np.random.default_rng(0).standard_normal(round(0.2 * SR))  # ~57 dB down
    lead, trail = edge_silence(np.concatenate([noise, tone(0.5), noise]), SR)
    assert lead == pytest.approx(0.2, abs=0.01)
    assert trail == pytest.approx(0.2, abs=0.01)


def test_silent_clip_is_silent_at_both_ends():
    assert edge_silence(np.zeros(SR), SR) == (1.0, 1.0)


def test_seam_pause_is_trailing_plus_leading_silence():
    chunks = [
        {"text": "It was late,", "audio_seconds": 1.0},
        {"text": "and the hall", "audio_seconds": 2.0},
        {"text": "was empty.", "audio_seconds": 1.5},
    ]
    rows = seam_rows(chunks, [(0.1, 0.2), (0.05, 0.3), (0.0, 0.4)])
    assert [(r["kind"], r["time_s"], r["pause_s"]) for r in rows] == [
        ("clause", 1.0, 0.25),
        ("word", 3.0, 0.3),
    ]
    assert rows[1]["at"] == "and the hall | was empty."


def test_single_chunk_has_no_seams():
    assert seam_rows([{"text": "Hello.", "audio_seconds": 1.0}], [(0.0, 0.0)]) == []
