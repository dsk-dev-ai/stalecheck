# Evaluation

`dataset.jsonl` is a labeled freshness suite: 44 examples across `fresh`, `stale`, and
`unverifiable`, grouped by topic (models, runtimes, OS, hardware, crypto, web, brand, unknown).

```bash
uv run python evals/run_eval.py                 # offline: mock LLM + snapshot
uv run python evals/run_eval.py --json          # machine-readable summary
uv run python evals/run_eval.py --min-accuracy 0.8
uv run python evals/run_eval.py --live          # Tavily + configured LLM
```

The offline run is deterministic and free, so CI uses it as a regression gate. It measures the
heuristic + snapshot layer, not the live LLM. The `--live` run measures the full pipeline and
requires `TAVILY_API_KEY` and `LLM_*` credentials.

## Current offline baseline

| Label | Precision | Recall | F1 |
|---|---|---|---|
| fresh | 1.000 | 0.929 | 0.963 |
| stale | 1.000 | 0.778 | 0.875 |
| unverifiable | 0.706 | 1.000 | 0.828 |

Accuracy: **0.886** (39/44). Full report, including mismatches, is written to `results.md`.

## Known limitations (the `hard-*` cases)

These are intentionally kept in the dataset so the gaps are visible instead of hidden:

- **No marker, no decision.** "GPT-4 Turbo remains OpenAI's top model." has no
  `latest/current/newest` marker, so it falls back to `unverifiable`.
- **Version separated from entity.** "The newest Python release is 3.10." does not contain the
  contiguous phrase `python 3.10`.
- **Fine-grained model versions.** "Claude Sonnet 4" vs "Claude Sonnet 4.5" is not in the alias
  map.
- **Synonyms.** "block subsidy" bypasses the explicit phrase `block reward`.
- **Transitions.** "OpenAI has moved past GPT-4o to GPT-5." mentions both an outdated and a
  current alias without a freshness marker.

Most of these are resolved by the live LLM judge, which is exactly why the pipeline escalates
unknown claims to Tavily + an LLM in production mode.

## Adding cases

Append a JSON line with `id`, `category`, `text`, `expected` and `note`. Keep each example to one
sentence so extraction is unambiguous. If you add a new topic, add the corresponding fact to
`apps/api/stalecheck_api/data/snapshot.json` so offline mode can resolve it.
