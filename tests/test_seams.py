from pathlib import Path

import numpy as np
import pytest

from speak_as_you_think.seams import VAD_RATE, SpeechDetector, edge_nonspeech, seam_kind, seam_rows


def test_seam_kinds():
    assert seam_kind("Sure, here's the easiest way to") == "word"
    assert seam_kind("I've looked into your account,") == "clause"
    assert seam_kind("get there from the station.") == "sentence"
    assert seam_kind("老陈愣了一下，笑着说，") == "clause"
    assert seam_kind("还有没有吃的。") == "sentence"
    assert seam_kind('She said "thank you."') == "sentence"


def test_edge_nonspeech_measures_both_ends():
    assert edge_nonspeech([(3200, 8000), (9600, 12800)], 16000, 16000) == (0.2, 0.2)


def test_clip_without_speech_is_nonspeech_at_both_ends():
    assert edge_nonspeech([], 16000, 16000) == (1.0, 1.0)


def test_seam_pause_is_trailing_plus_leading_nonspeech():
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


def test_speech_detector_finds_no_speech_in_silence_or_in_a_tone():
    pytest.importorskip("faster_whisper")
    detector = SpeechDetector()
    silence = np.zeros(VAD_RATE, dtype=np.float32)
    assert detector.edges(silence) == (1.0, 1.0)
    tone = (0.2 * np.sin(2 * np.pi * 220 * np.arange(VAD_RATE) / VAD_RATE)).astype(np.float32)
    assert detector.segments(tone) == []


def test_speech_detector_measures_the_silence_around_real_speech():
    faster_whisper = pytest.importorskip("faster_whisper")
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    clip = Path(__file__).parent.parent / "docs/audio/en_directions_independent.m4a"
    assert clip.is_file()
    try:
        speech = faster_whisper.decode_audio(str(clip), sampling_rate=VAD_RATE)
    except Exception as error:  # noqa: BLE001  no decoder for the clip in this environment
        pytest.skip(f"cannot decode {clip.name}: {error}")
    detector = SpeechDetector()
    lead, trail = detector.edges(speech)
    pad = np.zeros(VAD_RATE // 2, dtype=np.float32)
    padded = np.concatenate([pad, speech, pad])
    padded_lead, padded_trail = detector.edges(padded)
    assert padded_lead - lead == pytest.approx(0.5, abs=0.1)
    assert padded_trail - trail == pytest.approx(0.5, abs=0.1)
    # The settings of round 2, spelled out: the scores depend on them.
    round2 = VadOptions(threshold=0.5, min_speech_duration_ms=250, min_silence_duration_ms=100, speech_pad_ms=30)
    direct = [(s["start"], s["end"]) for s in get_speech_timestamps(padded, round2)]
    assert direct and detector.segments(padded) == direct
