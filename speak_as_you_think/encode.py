"""Segments -> Drama 3 prompt rows, the same encoding as fish-speech.

Rows are [rows, 1 + num_codebooks] int64: text rows are [token, 0, ..., 0], audio
rows are [c0 + semantic_start, c0..cN-1] (build_drama3_prompt in
fish_speech/models/text2semantic/fish_omni/generate.py).
"""

from collections.abc import Sequence

import torch

from speak_as_you_think.prompts import END_OF_TURN, Segment


def check_special_tokens(tokenizer) -> None:
    """The streaming format needs <|endofturn|> to be one special token."""
    token_id = tokenizer.token_to_id(END_OF_TURN)
    ids = tokenizer.encode(END_OF_TURN).ids
    if token_id is None or ids != [token_id]:
        raise ValueError(
            f"{END_OF_TURN} is not a single token in this tokenizer (ids={ids}); "
            "is this a Drama 3 checkpoint?"
        )


def encode_segments(segments: Sequence[Segment], tokenizer, config) -> torch.Tensor:
    num_codebooks = config.audio_decoder.num_codebooks
    rows = []
    for segment in segments:
        if isinstance(segment, str):
            ids = torch.tensor(tokenizer.encode(segment).ids, dtype=torch.long)
            text_rows = torch.zeros((len(ids), 1 + num_codebooks), dtype=torch.long)
            text_rows[:, 0] = ids
            rows.append(text_rows)
        else:
            codes = segment.to(device="cpu", dtype=torch.long)
            if codes.ndim != 2 or codes.shape[0] != num_codebooks:
                raise ValueError(
                    f"codes must be [{num_codebooks}, frames]; got {tuple(codes.shape)}"
                )
            main = codes[:1] + config.semantic_start_token_id
            rows.append(torch.cat((main, codes)).T)
    return torch.cat(rows)
