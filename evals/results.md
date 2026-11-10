# StaleCheck evaluation

Generated: 2026-11-10T15:03:15+00:00
Mode: offline (mock + snapshot)

**Accuracy:** 0.886 (39/44)
**Avg latency:** 0 ms

| Label | Precision | Recall | F1 | TP | FP | FN |
|---|---|---|---|---|---|---|
| fresh | 1.000 | 0.929 | 0.963 | 13 | 0 | 1 |
| stale | 1.000 | 0.778 | 0.875 | 14 | 0 | 4 |
| unverifiable | 0.706 | 1.000 | 0.828 | 12 | 5 | 0 |

## Mismatches

| ID | Expected | Predicted | Text | Reason |
|---|---|---|---|---|
| hard-001 | stale | unverifiable | GPT-4 Turbo remains OpenAI's top model. | Known topic, but the claim is not specific enough to confirm freshness. |
| hard-002 | fresh | unverifiable | OpenAI has moved past GPT-4o to GPT-5. | Known topic, but the claim is not specific enough to confirm freshness. |
| hard-003 | stale | unverifiable | Anthropic's newest model is Claude Sonnet 4. | Known topic, but the claim is not specific enough to confirm freshness. |
| hard-004 | stale | unverifiable | The Bitcoin block subsidy is 6.25 BTC. | Known topic, but the claim is not specific enough to confirm freshness. |
| hard-008 | stale | unverifiable | The newest Python release is 3.10. | No freshness source covers this claim yet. |
