"""Split text into the chunks a streaming LLM would hand to TTS.

A chunk ends at a sentence end once it has min_chars, or at a clause mark or space
once it has max_chars. Numbers, URLs, special tokens and [bracket] cues are never
split. A short tail is merged into the previous chunk.
"""

import re

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
            # Text without marks or spaces (long Chinese runs) still gets cut.
            cut = size >= 2 * max_chars
        if cut:
            chunks.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        chunks.append(buffer.strip())
    if len(chunks) > 1 and len(chunks[-1]) < min_chars:
        tail = chunks.pop()
        joiner = " " if chunks[-1][-1].isascii() and tail[0].isascii() else ""
        chunks[-1] += joiner + tail
    return chunks
