import pytest

from speak_as_you_think.timeline import playback_timeline


def test_no_stall_when_generation_is_faster_than_playback():
    t = playback_timeline([0.5, 0.5, 0.5], [2.0, 2.0, 2.0])
    assert t.first_audio_s == 0.5
    assert t.stalls == 0 and t.total_stall_s == 0
    assert t.finish_s == pytest.approx(6.5)


def test_stall_when_next_chunk_is_late():
    # Chunk 0 plays 1.0-2.0; chunk 1 is ready at 4.0 -> 2.0 s of silence.
    t = playback_timeline([1.0, 3.0], [1.0, 1.0])
    assert t.stalls == 1
    assert t.total_stall_s == pytest.approx(2.0)
    assert t.finish_s == pytest.approx(5.0)


def test_single_chunk():
    t = playback_timeline([2.0], [5.0])
    assert (t.first_audio_s, t.stalls, t.finish_s, t.audio_s) == (2.0, 0, 7.0, 5.0)


def test_mismatched_lengths():
    with pytest.raises(ValueError):
        playback_timeline([1.0], [])
