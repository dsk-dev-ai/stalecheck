from __future__ import annotations

import re

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_FACT_MARKERS = re.compile(
    r"\b(is|are|was|were|has|have|had|can|will|supports?|uses?|costs?|requires?|"
    r"released?|launched?|succeeded|became|named|called)\b",
    re.IGNORECASE,
)
_TIME_MARKERS = re.compile(
    r"\b(latest|current(?:ly)?|newest|now|today|as of|this year|released?|"
    r"version|price|pricing|costs?|deprecated|end[- ]of[- ]life|eol|lts)\b",
    re.IGNORECASE,
)
_VERSION_RE = re.compile(r"\b(?:v|version\s*)?\d+(?:\.\d+){1,3}\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_MONEY_RE = re.compile(r"[$€£]\s?\d|\b\d+\s?(?:usd|eur|gbp|btc)\b", re.IGNORECASE)
_ENTITY_RE = re.compile(r"\b[A-Z][A-Za-z0-9.+/-]{1,}\b")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace("’", "'")).strip(" .!?")


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(text) if p and p.strip()]
    out: list[str] = []
    for part in parts:
        if len(part) < 8:
            continue
        # Split very long comma-heavy paragraphs further.
        out.append(part)
    return out


def is_claim_like(sentence: str) -> bool:
    if len(sentence) < 20 or len(sentence) > 400:
        return False
    return bool(_FACT_MARKERS.search(sentence) or _VERSION_RE.search(sentence))


def classify_volatility(sentence: str) -> tuple[str, bool]:
    """Return (high|medium|low, time_sensitive)."""
    has_time = bool(_TIME_MARKERS.search(sentence))
    has_version = bool(_VERSION_RE.search(sentence))
    has_year = bool(_YEAR_RE.search(sentence))
    has_money = bool(_MONEY_RE.search(sentence))
    has_entity = bool(_ENTITY_RE.search(sentence))

    signals = sum([has_time, has_version, has_year, has_money])
    if signals >= 2 or has_money:
        return ("high", True)
    if has_time or has_version or has_year:
        return ("high" if has_entity else "medium", True)
    if has_entity:
        return ("medium", False)
    return ("low", False)


def alias_in_text(alias: str, text: str) -> bool:
    alias = normalize(alias)
    if not alias:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None
