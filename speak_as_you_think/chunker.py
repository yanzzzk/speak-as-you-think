"""Split text into the chunks a streaming LLM would hand to TTS.

A chunk ends at a sentence end once it has min_chars, or at a clause mark or space
once it has max_chars. Numbers, URLs, special tokens and [bracket] cues are never
split. A short tail is merged into the previous chunk.
"""

import re
import unicodedata

SENTENCE_ENDS = frozenset(".!?;。！？；…")
CLAUSE_MARKS = frozenset(",:，：、")
# Never split inside these spans.
PROTECTED_SPAN = re.compile(
    r"https?://\S+"  # URLs
    r"|\d+(?:[.,:/-]\d+)*%?"  # 3.5, 1,000, 10:30, 555-1234, 50%
    r"|<\|[^|>]*\|>"  # special tokens such as <|speaker:0|>
    r"|\[[^\[\]]*\]"  # [bracket] delivery cues
)


def _atoms(text: str) -> list[str]:
    """Characters, except that each protected span is one atom."""
    atoms, last = [], 0
    for match in PROTECTED_SPAN.finditer(text):
        atoms.extend(text[last : match.start()])
        atoms.append(match.group(0))
        last = match.end()
    atoms.extend(text[last:])
    return atoms


def _is_sentence_end(atom: str, next_atom: str | None) -> bool:
    if atom not in SENTENCE_ENDS:
        return False
    # "." only ends a sentence before white space or the end ("e.g" stays whole).
    return atom != "." or next_atom is None or next_atom.isspace()


def _is_punctuation(atom: str | None) -> bool:
    return atom is not None and len(atom) == 1 and unicodedata.category(atom)[0] == "P"


def split_chunks(text: str, min_chars: int = 12, max_chars: int = 80) -> list[str]:
    if min_chars < 1 or max_chars < min_chars:
        raise ValueError("need 1 <= min_chars <= max_chars")
    atoms = _atoms(text)
    chunks, buffer = [], ""
    for index, atom in enumerate(atoms):
        buffer += atom
        next_atom = atoms[index + 1] if index + 1 < len(atoms) else None
        size = len(buffer.strip())
        if _is_sentence_end(atom, next_atom) and size >= min_chars:
            cut = True
        elif size >= max_chars and (atom in CLAUSE_MARKS or atom.isspace()):
            cut = True
        else:
            # Text without marks or spaces (long Chinese runs) still gets cut, but
            # never right before a punctuation mark.
            cut = size >= 2 * max_chars and not _is_punctuation(next_atom)
        if cut:
            chunks.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        chunks.append(buffer.strip())
    if len(chunks) > 1 and len(chunks[-1]) < min_chars:
        tail = chunks.pop()
        chunks[-1] = join_chunks([chunks[-1], tail])
    return chunks


def join_chunks(chunks: list[str]) -> str:
    """Chunks back into text: a space between them, except next to CJK characters."""
    text = ""
    for chunk in chunks:
        joiner = " " if text and text[-1].isascii() and chunk[0].isascii() else ""
        text += joiner + chunk
    return text


class StreamChunker:
    """split_chunks for text that arrives piece by piece, as an LLM writes it.

    feed() returns the chunks that can no longer change: every chunk except the
    last one, which may still grow or be merged with a short tail. close() returns
    the rest. Together they are exactly split_chunks of the whole text.
    """

    def __init__(self, min_chars: int = 12, max_chars: int = 80) -> None:
        self.min_chars, self.max_chars = min_chars, max_chars
        self.pending = ""  # text not handed out yet

    def feed(self, text: str) -> list[str]:
        self.pending += text
        chunks = split_chunks(self.pending, self.min_chars, self.max_chars)[:-1]
        position = 0
        for chunk in chunks:
            position = self.pending.index(chunk, position) + len(chunk)
        self.pending = self.pending[position:]
        return chunks

    def close(self) -> list[str]:
        chunks = split_chunks(self.pending, self.min_chars, self.max_chars)
        self.pending = ""
        return chunks
