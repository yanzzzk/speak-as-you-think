import pytest

from drama3_live.chunker import split_chunks


def test_sentences_become_chunks():
    text = "It was late, and the hall was empty. Nobody answered."
    assert split_chunks(text) == ["It was late, and the hall was empty.", "Nobody answered."]


def test_short_sentences_wait_for_min_chars():
    assert split_chunks("Hi. Okay. Let's go now.", min_chars=12) == ["Hi. Okay. Let's go now."]


def test_numbers_and_urls_stay_whole():
    text = "The fee is 3.5 dollars per month. See https://example.com/a.b for 50% off."
    chunks = split_chunks(text, min_chars=5)
    assert chunks == [
        "The fee is 3.5 dollars per month.",
        "See https://example.com/a.b for 50% off.",
    ]


def test_times_stay_whole():
    chunks = split_chunks("It shipped at 3:40 today. It arrives Friday.", min_chars=5)
    assert chunks[0] == "It shipped at 3:40 today."


def test_chinese_sentence_ends():
    text = "今天天气很好。我们去公园散步吧！"
    assert split_chunks(text, min_chars=4) == ["今天天气很好。", "我们去公园散步吧！"]


def test_long_sentence_breaks_at_clause_after_max_chars():
    text = "one two three four five six seven, eight nine ten eleven twelve."
    chunks = split_chunks(text, min_chars=5, max_chars=20)
    assert all(len(chunk) <= 40 for chunk in chunks)
    assert " ".join(chunks).split() == text.split()


def test_text_without_breaks_is_cut_at_twice_max_chars():
    chunks = split_chunks("字" * 50, min_chars=1, max_chars=10)
    assert [len(c) for c in chunks] == [20, 20, 10]


def test_short_tail_merges_into_previous():
    chunks = split_chunks("This is the first full sentence. Ok.", min_chars=5)
    assert chunks == ["This is the first full sentence. Ok."]


def test_special_tokens_and_cues_stay_whole():
    text = "[whisper] Come closer. I have a secret for you."
    assert split_chunks(text, min_chars=5)[0] == "[whisper] Come closer."


def test_bad_limits():
    with pytest.raises(ValueError):
        split_chunks("x", min_chars=10, max_chars=5)
