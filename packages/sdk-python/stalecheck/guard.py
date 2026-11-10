from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .client import CheckResult, StaleCheck, StaleCheckError


class StaleAnswerError(StaleCheckError):
    """Raised in block mode when the generated answer contains stale claims."""

    def __init__(self, result: CheckResult) -> None:
        self.result = result
        stale = "; ".join(c.text for c in result.stale_claims[:3])
        super().__init__(f"Blocked stale answer: {stale}")
        self.stale_text = stale


@dataclass
class GuardedAnswer:
    text: str
    result: CheckResult
    refreshed: bool = False

    @property
    def is_stale(self) -> bool:
        return self.result.verdict == "stale"


def guard_answer(
    answer: str,
    checker: StaleCheck,
    mode: str = "annotate",
    refresh: Callable[[CheckResult], str] | None = None,
) -> GuardedAnswer:
    """Check an answer and apply the requested policy.

    - annotate: return the answer plus the verdict (caller shows a warning)
    - auto_refresh: if stale, call ``refresh(result)`` to regenerate the answer
    - block: raise ``StaleAnswerError`` when stale
    """
    result = checker.check(answer, mode=mode)
    if result.verdict != "stale":
        return GuardedAnswer(text=answer, result=result)

    if mode == "block":
        raise StaleAnswerError(result)

    if mode == "auto_refresh" and refresh is not None:
        return GuardedAnswer(text=refresh(result), result=result, refreshed=True)

    return GuardedAnswer(text=answer, result=result)
