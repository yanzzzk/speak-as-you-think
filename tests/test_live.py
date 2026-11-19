import asyncio

from speak_as_you_think.chunker import split_chunks
from speak_as_you_think.live import Connection, FakeSpeaker, Reply, Spoken

TEXT = (
    "Sure, here's the easiest way to get there from the station. "
    "Take the north exit and turn left onto Main Street. Keep walking."
)
CHUNKS = split_chunks(TEXT, 12, 30)


class OneSecondSpeaker:
    """Every chunk is one second of silence; records what it was asked to speak."""

    sample_rate = 8000

    def __init__(self) -> None:
        self.modes, self.calls = [], []

    def begin(self, mode: str) -> None:
        self.modes.append(mode)

    def speak(self, text: str, lookahead: str) -> Spoken:
        self.calls.append((text, lookahead))
        return Spoken(text, lookahead, bytes(16000), 1.0, 0.01, {"frames": 21})


class Outbox:
    def __init__(self) -> None:
        self.messages, self.audio = [], []

    async def send(self, message: dict, pcm: bytes | None) -> None:
        self.messages.append(message)
        if pcm is not None:
            self.audio.append(pcm)

    def of(self, kind: str) -> list[dict]:
        return [m for m in self.messages if m["type"] == kind]


async def until(condition, timeout: float = 2.0) -> None:
    for _ in range(int(timeout / 0.005)):
        if condition():
            return
        await asyncio.sleep(0.005)
    raise AssertionError("condition not reached")


def test_each_chunk_is_spoken_with_the_next_one_as_lookahead():
    async def scenario():
        speaker, out = OneSecondSpeaker(), Outbox()
        reply = Reply(speaker, out.send)
        task = asyncio.create_task(reply.run())
        for start in range(0, len(TEXT), 9):  # the text arrives 9 characters at a time
            reply.feed(TEXT[start : start + 9])
        reply.close()
        await task
        assert speaker.calls == list(zip(CHUNKS, CHUNKS[1:] + [""]))
        assert [m["text"] for m in out.of("audio")] == CHUNKS
        assert len(out.audio) == len(CHUNKS)
        assert out.messages[-1] == {"type": "finish", "reason": "done", "chunks": len(CHUNKS)}

    asyncio.run(scenario())


def test_audio_messages_say_how_the_chunk_ends_and_carry_the_speakers_edges():
    async def scenario():
        out = Outbox()
        reply = Reply(FakeSpeaker(rtf=0.0), out.send)
        task = asyncio.create_task(reply.run())
        reply.feed(TEXT)
        reply.close()
        await task
        audio = out.of("audio")
        # "Sure, here's the easiest way to" | "get there from the station." | ...
        assert [m["seam"] for m in audio[:2]] == ["word", "sentence"]
        assert all((m["lead_s"], m["trail_s"]) == (0.08, 0.08) for m in audio)

    asyncio.run(scenario())


def test_a_chunk_waits_until_its_lookahead_is_known():
    async def scenario():
        speaker, out = OneSecondSpeaker(), Outbox()
        reply = Reply(speaker, out.send)
        task = asyncio.create_task(reply.run())
        reply.feed("Sure, here's the easiest way to get there from the station. Take the north exit")
        await asyncio.sleep(0.05)
        # Three chunks are complete, but only the first has a lookahead that can no longer change.
        assert [text for text, _ in speaker.calls] == CHUNKS[:1]
        reply.close()
        await task
        assert len(speaker.calls) == 3 and speaker.calls[-1][1] == ""

    asyncio.run(scenario())


def test_interrupt_reports_what_the_listener_heard():
    async def scenario():
        speaker, out = OneSecondSpeaker(), Outbox()
        reply = Reply(speaker, out.send)
        task = asyncio.create_task(reply.run())
        reply.feed(TEXT)  # not closed: the fourth chunk waits for its lookahead
        await until(lambda: len(out.of("audio")) == 3)
        reply.interrupt(1.5)  # one chunk and a half were played
        await task
        finish = out.messages[-1]
        assert finish["reason"] == "interrupted"
        assert finish["heard_text"] == CHUNKS[0]
        assert finish["cut"] == {"text": CHUNKS[1], "heard": 0.5}
        assert finish["unheard_text"].endswith("Keep walking.")
        assert len(out.of("audio")) < len(CHUNKS)

    asyncio.run(scenario())


def test_interrupt_after_everything_was_generated_is_still_answered():
    # Generation runs ahead of playback: the listener interrupts audio that was
    # all made, and reported as done, a while ago.
    async def scenario():
        speaker, out = OneSecondSpeaker(), Outbox()
        connection = Connection(speaker, out.send, asyncio.Lock())
        await connection.handle({"type": "start"})
        await connection.handle({"type": "text", "text": TEXT})
        await connection.handle({"type": "flush"})
        await until(lambda: out.of("finish"))
        assert out.of("finish")[0]["reason"] == "done"

        await connection.handle({"type": "interrupt", "heard_s": 2.5})
        finish = out.messages[-1]
        assert finish["reason"] == "interrupted"
        assert finish["heard_text"] == " ".join(CHUNKS[:2])
        assert finish["cut"] == {"text": CHUNKS[2], "heard": 0.5}
        assert finish["unheard_text"] == " ".join(CHUNKS[3:])
        # A second interrupt of the same reply is not answered twice.
        await connection.handle({"type": "interrupt", "heard_s": 2.5})
        assert len(out.of("finish")) == 2

    asyncio.run(scenario())


def test_an_interrupt_after_a_failed_reply_is_still_answered():
    class FailsOnThird(OneSecondSpeaker):
        def speak(self, text: str, lookahead: str) -> Spoken:
            if len(self.calls) == 2:
                raise RuntimeError("out of memory")
            return super().speak(text, lookahead)

    async def scenario():
        out = Outbox()
        connection = Connection(FailsOnThird(), out.send, asyncio.Lock())
        await connection.handle({"type": "start", "id": 7})
        await connection.handle({"type": "text", "text": TEXT})
        await connection.handle({"type": "flush"})
        await until(lambda: out.of("error"))
        assert out.of("error")[0]["reply"] == 7
        # The listener is still hearing the two chunks that were made.
        await connection.handle({"type": "interrupt", "heard_s": 1.5})
        finish = out.messages[-1]
        assert (finish["reason"], finish["reply"]) == ("interrupted", 7)
        assert finish["heard_text"] == CHUNKS[0]
        assert finish["cut"] == {"text": CHUNKS[1], "heard": 0.5}

    asyncio.run(scenario())


def test_an_interrupt_is_answered_while_the_reply_waits_for_another_one():
    async def scenario():
        lock = asyncio.Lock()
        speaker, out = OneSecondSpeaker(), Outbox()
        connection = Connection(speaker, out.send, lock)
        await lock.acquire()  # another client's reply holds the model
        await connection.handle({"type": "start"})
        await connection.handle({"type": "text", "text": TEXT})
        await connection.handle({"type": "interrupt", "heard_s": 0.0})
        finish = out.messages[-1]
        assert finish["reason"] == "interrupted"
        assert (finish["heard_text"], finish["cut"]) == ("", None)
        assert finish["unheard_text"].startswith(CHUNKS[0])
        lock.release()
        await connection.stop()
        assert speaker.calls == []  # its turn came, and it did not speak
        assert len(out.of("finish")) == 1

    asyncio.run(scenario())


def test_a_malformed_interrupt_is_refused_and_the_reply_goes_on():
    async def scenario():
        speaker, out = OneSecondSpeaker(), Outbox()
        connection = Connection(speaker, out.send, asyncio.Lock())
        await connection.handle({"type": "start"})
        await connection.handle({"type": "text", "text": TEXT})
        for heard_s in (None, "soon", float("nan")):
            await connection.handle({"type": "interrupt", "heard_s": heard_s})
        assert len(out.of("error")) == 3
        await connection.handle({"type": "flush"})
        await until(lambda: out.of("finish"))
        assert out.of("finish")[0] == {"type": "finish", "reason": "done", "chunks": len(CHUNKS)}

    asyncio.run(scenario())


def test_messages_carry_the_id_of_their_reply():
    async def scenario():
        speaker, out = OneSecondSpeaker(), Outbox()
        connection = Connection(speaker, out.send, asyncio.Lock())
        await connection.handle({"type": "start", "id": "a1"})
        await connection.handle({"type": "text", "text": TEXT})
        await connection.handle({"type": "flush"})
        await until(lambda: out.of("finish"))
        assert {m["reply"] for m in out.of("audio") + out.of("finish")} == {"a1"}

    asyncio.run(scenario())


def test_connection_runs_a_reply_and_reports_bad_messages():
    async def scenario():
        speaker, out = OneSecondSpeaker(), Outbox()
        connection = Connection(speaker, out.send, asyncio.Lock())
        await connection.handle({"type": "text", "text": "too early"})
        await connection.handle({"type": "start", "mode": "no-such-mode"})
        assert [m["type"] for m in out.messages] == ["error", "error"]

        await connection.handle({"type": "start", "mode": "streaming-all"})
        await connection.handle({"type": "text", "text": TEXT})
        await connection.handle({"type": "flush"})
        await until(lambda: out.of("finish"))
        assert speaker.modes == ["streaming-all"]
        assert len(out.of("audio")) == len(CHUNKS)

    asyncio.run(scenario())


def test_a_new_start_ends_the_running_reply_first():
    async def scenario():
        speaker, out = OneSecondSpeaker(), Outbox()
        connection = Connection(speaker, out.send, asyncio.Lock())
        await connection.handle({"type": "start"})
        await connection.handle({"type": "text", "text": TEXT})  # never flushed
        await until(lambda: out.of("audio"))
        await connection.handle({"type": "start"})
        assert out.of("finish")[0]["reason"] == "interrupted"
        await connection.handle({"type": "text", "text": "Hello there, how are you today?"})
        await connection.handle({"type": "flush"})
        await until(lambda: len(out.of("finish")) == 2)
        assert out.messages[-1]["reason"] == "done"
        await connection.stop()

    asyncio.run(scenario())


def test_a_failing_speaker_is_reported_to_the_client():
    class Broken(OneSecondSpeaker):
        def speak(self, text: str, lookahead: str) -> Spoken:
            raise RuntimeError("out of memory")

    async def scenario():
        out = Outbox()
        connection = Connection(Broken(), out.send, asyncio.Lock())
        await connection.handle({"type": "start"})
        await connection.handle({"type": "text", "text": TEXT})
        await connection.handle({"type": "flush"})
        await until(lambda: out.of("error"))
        assert "out of memory" in out.of("error")[0]["message"]

    asyncio.run(scenario())
