from types import SimpleNamespace

from stalecheck_langchain import StaleCheckCallbackHandler


class _Message:
    content = "GPT-4o is the latest OpenAI model."


class _Generation:
    message = _Message()


class _Response:
    generations = [[_Generation()]]


class _Checker:
    def __init__(self, verdict: str) -> None:
        self.verdict = verdict
        self.last_text = None

    def check(self, text, mode=None, **kwargs):
        self.last_text = text
        self.last_mode = mode
        return SimpleNamespace(
            verdict=self.verdict,
            claims=[],
            run_id="sc_test",
            action="annotate" if self.verdict == "stale" else "allow",
        )


def test_handler_marks_stale_answer():
    handler = StaleCheckCallbackHandler(checker=_Checker("stale"), mode="annotate")
    handler.on_chat_model_end(_Response())
    assert handler.verdict == "stale"
    assert handler.is_stale is True
    assert handler.text == "GPT-4o is the latest OpenAI model."
    assert handler.result is not None
    assert handler.result["verdict"] == "stale"


def test_handler_marks_fresh_answer():
    handler = StaleCheckCallbackHandler(checker=_Checker("fresh"), mode="annotate")
    handler.on_chat_model_end(_Response())
    assert handler.verdict == "fresh"
    assert handler.is_stale is False
    assert handler.result is not None
    assert handler.result["verdict"] == "fresh"


def test_handler_handles_empty_response():
    class _Empty:
        generations = [[]]

    handler = StaleCheckCallbackHandler(checker=_Checker("stale"), mode="annotate")
    handler.on_chat_model_end(_Empty())
    assert handler.result is None
    assert handler.is_stale is False
