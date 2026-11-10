from stalecheck.client import CheckResult


def test_check_result_from_dict_and_properties():
    result = CheckResult.from_dict(
        {
            "run_id": "sc_1",
            "verdict": "stale",
            "staleness_score": 0.5,
            "action": "annotate",
            "mode": "annotate",
            "claims": [
                {
                    "id": "c1",
                    "text": "GPT-4o is the latest model",
                    "verdict": "stale",
                    "evidence": [{"title": "x", "url": "https://example.com"}],
                },
                {"id": "c2", "text": "Water boils at 100C", "verdict": "fresh"},
            ],
        }
    )
    assert result.is_stale
    assert len(result.stale_claims) == 1
    assert result.claims[0].evidence[0].url == "https://example.com"
    assert result.to_dict()["claims"][0]["verdict"] == "stale"
