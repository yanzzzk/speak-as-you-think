"""The four week-1 synthesis modes. Needs fish-speech installed and a CUDA GPU.

Every mode returns one ChunkResult per generation call, in playback order.
"""

import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import torch
import torchaudio
from fish_speech.models.text2semantic.fish_omni.chunking import (
    DRAMA3_CHUNK_MAX_NEW_TOKENS,
    Drama3History,
)
from fish_speech.models.text2semantic.fish_omni.generate import (
    DRAMA3_DEFAULT_MAX_NEW_TOKENS,
    DRAMA3_MAX_PROMPT_ROWS,
    Drama3DecodeGraphs,
    build_drama3_prompt,
    generate_drama3,
)
from fish_speech.models.text2semantic.inference import (
    build_drama3_chunk_prompt,
    decode_to_audio,
    encode_audio,
    init_model,
    load_codec_model,
    resolve_codec_path,
)

from speak_as_you_think.encode import check_special_tokens, encode_segments
from speak_as_you_think.live import Spoken
from speak_as_you_think.prompts import RefStyle, Reference, Round, streaming_prompt
from speak_as_you_think.seams import VAD_RATE, SpeechDetector

MODES = ("full", "independent", "fish_history", "streaming")


@dataclass
class Sampling:
    temperature: float | None = None
    top_k: int | None = None
    top_p: float | None = None

    def kwargs(self) -> dict:
        return {k: v for k, v in vars(self).items() if v is not None}


@dataclass
class ChunkResult:
    text: str
    lookahead: str
    codes: torch.Tensor  # [num_codebooks, frames], CPU
    prompt_rows: int
    gen_seconds: float
    finish_reason: str


class Drama3:
    """Drama 3 plus its codec, loaded once."""

    def __init__(self, checkpoint: str | Path, device: str = "cuda:0") -> None:
        self.model, _ = init_model(str(checkpoint), device, torch.bfloat16)
        # The codec shares the tower's device and runs in the model's dtype.
        self.codec_device = str(self.model.device)
        self.codec = load_codec_model(
            resolve_codec_path(checkpoint), self.codec_device, self.model.dtype
        )
        self.tokenizer, self.config = self.model.tokenizer, self.model.config
        check_special_tokens(self.tokenizer)
        self.capacity = min(
            Drama3DecodeGraphs.graph_capacity(self.model),
            DRAMA3_MAX_PROMPT_ROWS + DRAMA3_DEFAULT_MAX_NEW_TOKENS,
        )

    @property
    def sample_rate(self) -> int:
        return self.codec.sample_rate

    def reference(self, audio: Path, text: str) -> Reference:
        return Reference(text, encode_audio(audio, self.codec, self.codec_device).cpu())

    def decode(self, codes: torch.Tensor) -> torch.Tensor:
        return decode_to_audio(codes.to(self.codec_device), self.codec).float().cpu()

    def generate(
        self, prompt: torch.Tensor, max_new_tokens: int, sampling: Sampling
    ) -> tuple[torch.Tensor, float, str]:
        if len(prompt) > DRAMA3_MAX_PROMPT_ROWS:
            raise ValueError(f"prompt has {len(prompt)} rows")
        budget = min(max_new_tokens, self.capacity - len(prompt))
        if budget < 1:
            raise ValueError(f"no room to generate after {len(prompt)} prompt rows")
        torch.cuda.synchronize()
        started = time.perf_counter()
        frames, finish = generate_drama3(
            self.model, prompt, max_new_tokens=budget, **sampling.kwargs()
        )
        torch.cuda.synchronize()
        return frames[:, 1:].T.contiguous(), time.perf_counter() - started, finish


def _fits(engine: Drama3, rows: int, max_new_tokens: int) -> bool:
    return rows <= DRAMA3_MAX_PROMPT_ROWS and rows + max_new_tokens <= engine.capacity


def run_full(
    engine: Drama3, text: str, refs: Sequence[Reference], sampling: Sampling
) -> list[ChunkResult]:
    """The whole text in one pass: the quality ceiling, not streamable."""
    prompt = build_drama3_prompt(
        text,
        engine.tokenizer,
        engine.config,
        [r.text for r in refs],
        [r.codes for r in refs],
    )
    codes, seconds, finish = engine.generate(
        prompt, DRAMA3_DEFAULT_MAX_NEW_TOKENS, sampling
    )
    return [ChunkResult(text, "", codes, len(prompt), seconds, finish)]


def run_independent(
    engine: Drama3, chunks: Sequence[str], refs: Sequence[Reference], sampling: Sampling
) -> list[ChunkResult]:
    """Each chunk alone with the reference: a sentence-per-request cascade."""
    results = []
    for chunk in chunks:
        prompt = build_drama3_prompt(
            chunk,
            engine.tokenizer,
            engine.config,
            [r.text for r in refs],
            [r.codes for r in refs],
        )
        codes, seconds, finish = engine.generate(
            prompt, DRAMA3_CHUNK_MAX_NEW_TOKENS, sampling
        )
        results.append(ChunkResult(chunk, "", codes, len(prompt), seconds, finish))
    return results


def run_fish_history(
    engine: Drama3, chunks: Sequence[str], refs: Sequence[Reference], sampling: Sampling
) -> list[ChunkResult]:
    """fish-speech's own chunking context (first + latest chunk), no lookahead."""
    history = Drama3History()
    ref_texts, ref_codes = [r.text for r in refs], [r.codes for r in refs]
    results = []
    for chunk in chunks:
        prompt = build_drama3_chunk_prompt(
            engine.model, chunk, ref_texts, ref_codes, history
        )
        codes, seconds, finish = engine.generate(
            prompt, DRAMA3_CHUNK_MAX_NEW_TOKENS, sampling
        )
        results.append(ChunkResult(chunk, "", codes, len(prompt), seconds, finish))
        if codes.shape[1]:
            history.push(chunk, codes)
    return results


def run_streaming(
    engine: Drama3,
    chunks: Sequence[str],
    refs: Sequence[Reference],
    sampling: Sampling,
    ref_style: RefStyle = "system",
    speaker_tag: bool = True,
    max_history: int | None = None,
) -> list[ChunkResult]:
    """Figure 10: chunk + <|endofturn|> + next chunk, earlier rounds in context.

    max_history keeps only that many recent rounds; the reference always stays.
    When the prompt outgrows the cache, the oldest rounds are dropped first.
    """
    history: list[Round] = []
    results = []
    for index, chunk in enumerate(chunks):
        lookahead = chunks[index + 1] if index + 1 < len(chunks) else ""
        first = 0 if max_history is None else max(0, len(history) - max_history)
        for start in range(first, len(history) + 1):
            segments = streaming_prompt(
                chunk, lookahead, history[start:], refs, ref_style, speaker_tag
            )
            prompt = encode_segments(segments, engine.tokenizer, engine.config)
            if _fits(engine, len(prompt), DRAMA3_CHUNK_MAX_NEW_TOKENS):
                break
        else:
            raise ValueError(f"chunk {index} does not fit even without history")
        codes, seconds, finish = engine.generate(
            prompt, DRAMA3_CHUNK_MAX_NEW_TOKENS, sampling
        )
        results.append(
            ChunkResult(chunk, lookahead, codes, len(prompt), seconds, finish)
        )
        if codes.shape[1]:
            history.append(Round(chunk, lookahead, codes))
    return results


class LiveSpeaker:
    """Speaks one reply chunk by chunk for speak_as_you_think.live: run_streaming, a chunk at a time."""

    def __init__(
        self,
        engine: Drama3,
        refs: Sequence[Reference],
        sampling: Sampling,
        speaker_tag: bool = True,
        detector: SpeechDetector | None = None,
    ) -> None:
        self.engine, self.refs, self.sampling = engine, refs, sampling
        self.speaker_tag = speaker_tag
        self.detector = detector  # given: each chunk reports the non-speech at its edges
        self.sample_rate = engine.sample_rate
        self.device_name = torch.cuda.get_device_name(engine.model.device)
        self.begin("streaming-last")

    def begin(self, mode: str) -> None:
        """Start a new reply: forget the last one and pick how much to remember."""
        self.independent = mode == "independent"
        self.max_history = None if mode == "streaming-all" else 1
        self.history: list[Round] = []

    def prompt(self, text: str, lookahead: str) -> torch.Tensor:
        if self.independent:
            return build_drama3_prompt(
                text,
                self.engine.tokenizer,
                self.engine.config,
                [r.text for r in self.refs],
                [r.codes for r in self.refs],
            )
        known = len(self.history)
        first = 0 if self.max_history is None else max(0, known - self.max_history)
        for start in range(first, known + 1):
            segments = streaming_prompt(
                text, lookahead, self.history[start:], self.refs, "round", self.speaker_tag
            )
            prompt = encode_segments(segments, self.engine.tokenizer, self.engine.config)
            if _fits(self.engine, len(prompt), DRAMA3_CHUNK_MAX_NEW_TOKENS):
                return prompt
        raise ValueError("chunk does not fit even without history")

    def speak(self, text: str, lookahead: str) -> Spoken:
        started = time.perf_counter()
        prompt = self.prompt(text, lookahead)
        # A chunk that will not stop must not hold up a live reply: about 4x normal speech.
        budget = min(DRAMA3_CHUNK_MAX_NEW_TOKENS, 60 + 6 * len(text))
        codes, model_s, finish = self.engine.generate(prompt, budget, self.sampling)
        audio = self.engine.decode(codes) if codes.shape[1] else torch.zeros(0)
        if not self.independent and codes.shape[1]:
            self.history.append(Round(text, lookahead, codes))
        pcm = (audio.clamp(-1, 1) * 32767).to(torch.int16).numpy().tobytes()
        info = {
            "prompt_rows": len(prompt),
            "frames": codes.shape[1],
            "finish_reason": finish,
            "model_s": round(model_s, 3),
        }
        if self.detector is not None and len(audio):
            # The pause at a seam is this chunk's trailing plus the next one's leading non-speech.
            with torch.inference_mode():  # grad mode is per thread: this runs on the speaker's
                at_vad_rate = torchaudio.functional.resample(audio, self.sample_rate, VAD_RATE)
            lead, trail = self.detector.edges(at_vad_rate.numpy())
            info |= {"lead_s": round(lead, 3), "trail_s": round(trail, 3)}
        return Spoken(
            text, lookahead, pcm, len(audio) / self.sample_rate, time.perf_counter() - started, info
        )
