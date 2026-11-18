"""Text normalization, error rates and lookahead leakage (no torch)."""

import re
import unicodedata

import jiwer


def normalize(text: str, lang: str) -> str:
    """Lowercase, drop punctuation and [cues]; Chinese also drops spaces."""
    text = re.sub(r"\[[^\[\]]*\]|<\|[^|>]*\|>", " ", text)
    text = unicodedata.normalize("NFKC", text).lower()
    text = "".join(" " if unicodedata.category(ch)[0] in "PS" else ch for ch in text)
    if lang == "zh":
        return re.sub(r"\s+", "", text)
    return " ".join(text.split())


def units(text: str, lang: str) -> list[str]:
    """Words for English, characters for Chinese."""
    text = normalize(text, lang)
    return list(text) if lang == "zh" else text.split()


def error_rate(reference: str, hypothesis: str, lang: str) -> float:
    """WER for English, CER for Chinese."""
    ref, hyp = normalize(reference, lang), normalize(hypothesis, lang)
    if not ref:
        return 0.0 if not hyp else 1.0
    return jiwer.cer(ref, hyp) if lang == "zh" else jiwer.wer(ref, hyp)


def _contains(haystack: list[str], needle: list[str]) -> bool:
    n = len(needle)
    return any(haystack[i : i + n] == needle for i in range(len(haystack) - n + 1))


def leaked(chunk: str, lookahead: str, transcript: str, lang: str) -> bool:
    """True when the start of the lookahead is heard in this chunk's audio.

    Checks the first 3 words (English) or 4 characters (Chinese) of the lookahead;
    a phrase that also occurs in the chunk's own text cannot count as a leak.
    """
    n = 4 if lang == "zh" else 3
    probe = units(lookahead, lang)[:n]
    if len(probe) < n:
        return False
    return _contains(units(transcript, lang), probe) and not _contains(
        units(chunk, lang), probe
    )
