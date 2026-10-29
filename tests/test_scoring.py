import pytest

from drama3_live.scoring import error_rate, leaked, normalize


def test_normalize_english():
    assert normalize("Hello, World! [sigh] It's 3:40.", "en") == "hello world it s 3 40"


def test_normalize_chinese_drops_spaces_and_punctuation():
    assert normalize("你好， 世界！", "zh") == "你好世界"


def test_error_rate():
    assert error_rate("the hall was empty", "the hall was empty.", "en") == 0
    assert error_rate("the hall was empty", "the wall was empty", "en") == pytest.approx(0.25)
    assert error_rate("你好世界", "你好时节", "zh") == pytest.approx(0.5)


def test_leak_detected_when_lookahead_is_spoken():
    assert leaked("It was late,", "and the hall was empty.", "It was late and the hall", "en")


def test_no_leak_on_clean_chunk():
    assert not leaked("It was late,", "and the hall was empty.", "It was late.", "en")


def test_phrase_in_own_chunk_is_not_a_leak():
    assert not leaked("I said and the hall", "and the hall was empty.", "I said and the hall", "en")


def test_chinese_leak():
    assert leaked("夜已经很深了，", "走廊里一个人也没有。", "夜已经很深了走廊里一", "zh")
