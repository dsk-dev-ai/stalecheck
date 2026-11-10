import asyncio

from stalecheck_api.config import get_settings
from stalecheck_api.llm import get_llm
from stalecheck_api.pipeline import Pipeline
from stalecheck_api.schemas import CheckRequest
from stalecheck_api.store import Store
from stalecheck_api.verifier import get_verifier


def _pipeline(tmp_path):
    settings = get_settings()
    return Pipeline(
        settings,
        Store(tmp_path / "test.db"),
        get_llm(settings),
        get_verifier(settings),
    )


def test_stale_claim_is_flagged_with_fix(tmp_path):
    pipeline = _pipeline(tmp_path)
    result = asyncio.run(pipeline.check(CheckRequest(text="GPT-4o is the latest OpenAI model.")))
    assert result.verdict == "stale"
    assert result.staleness_score == 1.0
    assert result.action == "annotate"
    assert result.claims[0].suggested_fix


def test_fresh_claim_passes(tmp_path):
    pipeline = _pipeline(tmp_path)
    result = asyncio.run(pipeline.check(CheckRequest(text="GPT-5 is the latest OpenAI model.")))
    assert result.verdict == "fresh"
    assert result.action == "allow"


def test_unknown_claim_is_unverifiable(tmp_path):
    pipeline = _pipeline(tmp_path)
    result = asyncio.run(pipeline.check(CheckRequest(text="The Zorblax API costs $42 per call.")))
    assert result.verdict == "unverifiable"


def test_block_mode_action(tmp_path):
    pipeline = _pipeline(tmp_path)
    result = asyncio.run(
        pipeline.check(CheckRequest(text="Python 3.11 is the latest version.", mode="block"))
    )
    assert result.verdict == "stale"
    assert result.action == "block"


def test_cache_hit(tmp_path):
    pipeline = _pipeline(tmp_path)
    req = CheckRequest(text="Node 18 is the LTS release.")
    first = asyncio.run(pipeline.check(req))
    second = asyncio.run(pipeline.check(req))
    assert first.cached is False
    assert second.cached is True
    assert first.run_id == second.run_id
