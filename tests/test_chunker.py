import json

import pytest

from speak_as_you_think.chunker import StreamChunker, join_chunks, split_chunks


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


def test_hard_cut_keeps_the_period_with_its_sentence():
    text = "那天晚上下着小雨，老陈收摊比平时晚了一些。老陈把最后几个包子装进袋子里，"
    chunks = split_chunks(text, min_chars=6, max_chars=10)
    assert chunks[0] == "那天晚上下着小雨，老陈收摊比平时晚了一些。"


def test_short_tail_merges_into_previous():
    chunks = split_chunks("This is the first full sentence. Ok.", min_chars=5)
    assert chunks == ["This is the first full sentence. Ok."]


def test_special_tokens_and_cues_stay_whole():
    text = "[whisper] Come closer. I have a secret for you."
    assert split_chunks(text, min_chars=5)[0] == "[whisper] Come closer."


def test_bad_limits():
    with pytest.raises(ValueError):
        split_chunks("x", min_chars=10, max_chars=5)


def _stream(text: str, sizes: list[int], **limits) -> tuple[list[str], list[str]]:
    """Feed text in pieces of the given sizes; return (chunks before close, all chunks)."""
    chunker, early, position = StreamChunker(**limits), [], 0
    for index in range(len(text)):
        size = sizes[index % len(sizes)]
        if position >= len(text):
            break
        early += chunker.feed(text[position : position + size])
        position += size
    return early, early + chunker.close()


@pytest.mark.parametrize("sizes", [[1], [3], [7, 2, 11], [40], [1000]])
def test_stream_chunker_matches_split_chunks(sizes):
    limits = {"min_chars": 12, "max_chars": 30}
    for line in open("data/round2_texts.jsonl", encoding="utf-8"):
        text = json.loads(line)["text"]
        early, chunks = _stream(text, sizes, **limits)
        assert chunks == split_chunks(text, **limits)
        assert early == chunks[: len(early)]


def test_stream_chunker_hands_out_a_chunk_once_the_next_one_is_safe():
    chunker = StreamChunker(min_chars=12, max_chars=30)
    assert chunker.feed("It was late. And the") == []  # "And the" could still merge back
    assert chunker.feed(" hall was") == ["It was late."]
    assert chunker.close() == ["And the hall was"]


def test_stream_chunker_keeps_numbers_whole_across_pieces():
    chunker = StreamChunker(min_chars=5, max_chars=30)
    chunks = chunker.feed("The fee is 3.") + chunker.feed("5 dollars per month. See you then.") + chunker.close()
    assert chunks == ["The fee is 3.5 dollars per month.", "See you then."]


def test_join_chunks():
    assert join_chunks(["It was late,", "and the hall"]) == "It was late, and the hall"
    assert join_chunks(["夜已经很深了，", "走廊里没有人。"]) == "夜已经很深了，走廊里没有人。"
    assert join_chunks([]) == ""
