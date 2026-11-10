"""StaleCheck Python SDK."""

from .client import (
    CheckResult,
    Claim,
    Evidence,
    StaleCheck,
    StaleCheckError,
)
from .guard import GuardedAnswer, StaleAnswerError, guard_answer

__version__ = "1.0.0"

__all__ = [
    "CheckResult",
    "Claim",
    "Evidence",
    "GuardedAnswer",
    "StaleAnswerError",
    "StaleCheck",
    "StaleCheckError",
    "guard_answer",
]
