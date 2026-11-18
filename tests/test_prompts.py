from speak_as_you_think.prompts import (
    END_OF_TURN,
    GENERATION_START,
    MESSAGE_END,
    STREAM_INSTRUCTION,
    USER_START,
    Reference,
    Round,
    streaming_prompt,
)

REF = Reference("Hello there.", "REF_CODES")


def test_first_round_without_reference_matches_figure_10():
    segments = streaming_prompt("It was late", "and the hall was empty.", [], [], speaker_tag=False)
    assert segments == [
        "<|im_start|>system\n",
        STREAM_INSTRUCTION,
        MESSAGE_END,
        USER_START,
        "It was late",
        END_OF_TURN,
        "and the hall was empty.",
        MESSAGE_END,
        GENERATION_START,
    ]


def test_last_round_has_empty_lookahead():
    segments = streaming_prompt("Nobody answered.", "", [], [], speaker_tag=False)
    user = segments[segments.index(USER_START) :]
    assert user == [USER_START, "Nobody answered.", END_OF_TURN, MESSAGE_END, GENERATION_START]


def test_history_rounds_are_completed_turns():
    history = [Round("It was late", "and the hall was empty.", "CODES_0")]
    segments = streaming_prompt(
        "and the hall was empty.", "Nobody answered.", history, [], speaker_tag=False
    )
    i = segments.index("CODES_0")
    assert segments[i - 1] == GENERATION_START and segments[i + 1] == MESSAGE_END
    assert segments[-1] == GENERATION_START
    assert segments.count(USER_START) == 2


def test_reference_in_system_turn():
    segments = streaming_prompt("A.", "B.", [], [REF], ref_style="system")
    assert segments[1] == STREAM_INSTRUCTION + " reference to the following:"
    assert segments[2] == "\n\n[Reference 1]\nText: <|speaker:0|> Hello there.\nSpeech: "
    assert segments[3] == "REF_CODES"


def test_reference_as_round_zero_looks_ahead_to_first_chunk():
    segments = streaming_prompt("A.", "B.", [], [REF], ref_style="round", speaker_tag=False)
    assert segments[1] == STREAM_INSTRUCTION
    first_user = segments.index(USER_START)
    assert segments[first_user : first_user + 4] == [USER_START, "Hello there.", END_OF_TURN, "A."]
    assert segments[segments.index("REF_CODES") - 1] == GENERATION_START


def test_round_zero_lookahead_stays_first_chunk_later():
    history = [Round("A.", "B.", "CODES_0")]
    segments = streaming_prompt("B.", "", history, [REF], ref_style="round", speaker_tag=False)
    first_user = segments.index(USER_START)
    assert segments[first_user + 3] == "A."


def test_speaker_tag_prefixes_user_text():
    segments = streaming_prompt("A.", "B.", [], [])
    assert "<|speaker:0|> A." in segments
