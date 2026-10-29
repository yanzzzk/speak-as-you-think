"""Drama 3 prompts as segment lists: str literals and opaque audio codes.

Mirrors fish-speech's build_drama3_prompt (fish_omni/generate.py), which tokenizes
every literal on its own, so segment boundaries matter. The streaming layout follows
the Drama 3 technical report, Appendix A, Figure 10:

    system: "streaming speech continuation with one-chunk lookahead split by <|endofturn|>"
    user:   chunk_k <|endofturn|> chunk_k+1      (empty lookahead on the last round)
    assistant: <|voice|> codes of chunk_k

Earlier rounds stay in the prompt as completed turns.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

TTS_INSTRUCTION = "convert the provided text to speech"
STREAM_INSTRUCTION = (
    "streaming speech continuation with one-chunk lookahead split by <|endofturn|>"
)
REFERENCE_SUFFIX = " reference to the following:"
END_OF_TURN = "<|endofturn|>"
SYSTEM_START = "<|im_start|>system\n"
USER_START = "<|im_start|>user\n"
MESSAGE_END = "<|im_end|>\n"
GENERATION_START = "<|im_start|>assistant\n<|voice|>"
SPEAKER_0 = "<|speaker:0|>"

RefStyle = Literal["system", "round"]
Segment = Any  # str literal, or audio codes [num_codebooks, frames]


@dataclass
class Reference:
    text: str
    codes: Any


@dataclass
class Round:
    """A completed streaming round: text spoken, lookahead shown, codes produced."""

    text: str
    lookahead: str
    codes: Any


def _tagged(text: str, speaker_tag: bool) -> str:
    return f"{SPEAKER_0} {text}" if speaker_tag else text


def system_segments(
    instruction: str, references: Sequence[Reference], speaker_tag: bool = True
) -> list[Segment]:
    """System turn; references follow the instruction as in fish-speech."""
    segments: list[Segment] = [
        SYSTEM_START,
        instruction + REFERENCE_SUFFIX if references else instruction,
    ]
    for index, ref in enumerate(references, 1):
        transcript = _tagged(ref.text, speaker_tag)
        segments += [f"\n\n[Reference {index}]\nText: {transcript}\nSpeech: ", ref.codes]
    segments.append(MESSAGE_END)
    return segments


def _user_turn(text: str, lookahead: str, speaker_tag: bool) -> list[Segment]:
    segments: list[Segment] = [USER_START, _tagged(text, speaker_tag), END_OF_TURN]
    if lookahead:
        segments.append(lookahead)
    segments.append(MESSAGE_END)
    return segments


def streaming_prompt(
    current: str,
    lookahead: str,
    history: Sequence[Round],
    references: Sequence[Reference],
    ref_style: RefStyle = "system",
    speaker_tag: bool = True,
) -> list[Segment]:
    """Prompt that ends in the open assistant turn for `current`.

    ref_style "system" puts references in the system turn. "round" makes the first
    reference round 0, whose lookahead is the first chunk, so generation continues
    in that voice.
    """
    if ref_style == "system":
        segments = system_segments(STREAM_INSTRUCTION, references, speaker_tag)
        rounds = list(history)
    elif ref_style == "round":
        segments = system_segments(STREAM_INSTRUCTION, (), speaker_tag)
        rounds = list(history)
        if references:
            first_text = rounds[0].text if rounds else current
            ref = references[0]
            rounds.insert(0, Round(ref.text, first_text, ref.codes))
    else:
        raise ValueError(f"unknown ref_style {ref_style!r}")

    for done in rounds:
        segments += _user_turn(done.text, done.lookahead, speaker_tag)
        segments += [GENERATION_START, done.codes, MESSAGE_END]
    segments += _user_turn(current, lookahead, speaker_tag)
    segments.append(GENERATION_START)
    return segments
