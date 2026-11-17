from drama3_live.seams import edge_nonspeech, seam_kind, seam_rows


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
