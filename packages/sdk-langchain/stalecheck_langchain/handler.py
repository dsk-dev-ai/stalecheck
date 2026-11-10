from __future__ import annotations

from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from stalecheck.client import StaleCheck


class StaleCheckCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that runs StaleCheck on chat-model responses.

    Install on a runnable / chain / chat model via the LangChain callback manager:

        from stalecheck.client import StaleCheck
        from stalecheck_langchain import StaleCheckCallbackHandler

        handler = StaleCheckCallbackHandler(checker=StaleCheck(base_url="http://localhost:8000"), mode="annotate")
        chain = runnable_with_config({"callbacks": [handler]})
    """

    def __init__(self, checker: StaleCheck, mode: str = "annotate") -> None:
        super().__init__()
        self.checker = checker
        self.mode = mode
        self.text = ""
        self.result: dict[str, Any] | None = None

    @property
    def verdict(self) -> str | None:
        if not self.result:
            return None
        verdict = self.result.get("verdict")
        return str(verdict) if verdict else None

    @property
    def is_stale(self) -> bool:
        return self.verdict == "stale"

    def _extract_text(self, response: Any) -> str:
        try:
            generations = list(getattr(response, "generations", None) or [])
            if generations and generations[0]:
                generation = generations[0][0]
                message = getattr(generation, "message", None)
                text = getattr(message, "content", None) or getattr(message, "text", None) or ""
                if text:
                    return str(text)
        except Exception:  # noqa: BLE001 - best-effort extraction
            return ""
        return ""

    def on_chat_model_end(self, response: Any, **kwargs: Any) -> None:
        self.text = self._extract_text(response)
        result = self._run(self.text)
        self.result = result

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        # For completion-style LLMs we use the generation text.
        text = ""
        generations = list(getattr(response, "generations", None) or [])
        if generations and generations[0]:
            generation = generations[0][0]
            text = str(getattr(generation, "text", "") or "")
        self.text = text
        result = self._run(text)
        self.result = result

    def _run(self, text: str) -> dict[str, Any] | None:
        if not text or not text.strip() or len(text) > 20_000:
            return None
        try:
            check_result = self.checker.check(text, mode=self.mode)
            verdict = check_result.verdict
            claims = [c.text for c in check_result.claims if c.verdict == "stale"]
            return {
                "verdict": verdict,
                "stale_claims": claims,
                "run_id": check_result.run_id,
                "action": check_result.action,
            }
        except Exception:  # noqa: BLE001 - callback handlers must not break the chain
            return None
