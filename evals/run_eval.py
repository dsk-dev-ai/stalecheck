"""Evaluate StaleCheck against a labeled freshness dataset.

Usage:
    uv run python evals/run_eval.py
    uv run python evals/run_eval.py --min-accuracy 0.8 --output evals/results.md
    uv run python evals/run_eval.py --live   # use configured Tavily + LLM provider

Default mode is offline (mock provider + bundled snapshot) so it is
deterministic and free to run in CI.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = Path(__file__).parent / "dataset.jsonl"
DEFAULT_OUTPUT = Path(__file__).parent / "results.md"
LABELS = ["fresh", "stale", "unverifiable"]


def load_dataset(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


async def evaluate(rows: list[dict], live: bool) -> list[dict]:
    os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="stalecheck-eval-"))
    if not live:
        os.environ["LLM_PROVIDER"] = "mock"
        os.environ["TAVILY_API_KEY"] = ""

    if str(ROOT / "apps" / "api") not in sys.path:
        sys.path.insert(0, str(ROOT / "apps" / "api"))

    from stalecheck_api.config import get_settings
    from stalecheck_api.llm import get_llm
    from stalecheck_api.pipeline import Pipeline
    from stalecheck_api.schemas import CheckRequest
    from stalecheck_api.store import Store
    from stalecheck_api.verifier import get_verifier

    get_settings.cache_clear()
    settings = get_settings()
    tmp = Path(tempfile.mkdtemp(prefix="stalecheck-eval-db-"))
    pipeline = Pipeline(settings, Store(tmp / "eval.db"), get_llm(settings), get_verifier(settings))

    results = []
    for row in rows:
        result = await pipeline.check(CheckRequest(text=row["text"], mode="annotate", use_web=live))
        results.append(
            {
                **row,
                "predicted": result.verdict,
                "score": result.staleness_score,
                "claims": len(result.claims),
                "latency_ms": result.latency_ms,
                "reason": result.claims[0].reason if result.claims else "",
            }
        )
    return results


def summarize(results: list[dict]) -> dict:
    total = len(results)
    correct = sum(1 for r in results if r["predicted"] == r["expected"])
    metrics: dict = {
        "total": total,
        "accuracy": correct / total if total else 0.0,
        "scores": {},
    }
    for label in LABELS:
        tp = sum(1 for r in results if r["expected"] == label and r["predicted"] == label)
        fp = sum(1 for r in results if r["expected"] != label and r["predicted"] == label)
        fn = sum(1 for r in results if r["expected"] == label and r["predicted"] != label)
        precision, recall, f1 = prf(tp, fp, fn)
        metrics["scores"][label] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    metrics["avg_latency_ms"] = sum(r["latency_ms"] for r in results) / total if total else 0.0
    return metrics


def render_markdown(metrics: dict, results: list[dict], live: bool) -> str:
    mode = "live (Tavily + LLM)" if live else "offline (mock + snapshot)"
    lines = [
        "# StaleCheck evaluation",
        "",
        f"Generated: {datetime.now(UTC).isoformat(timespec='seconds')}",
        f"Mode: {mode}",
        "",
        f"**Accuracy:** {metrics['accuracy']:.3f} "
        f"({sum(1 for r in results if r['predicted'] == r['expected'])}/{metrics['total']})",
        f"**Avg latency:** {metrics['avg_latency_ms']:.0f} ms",
        "",
        "| Label | Precision | Recall | F1 | TP | FP | FN |",
        "|---|---|---|---|---|---|---|",
    ]
    for label, s in metrics["scores"].items():
        lines.append(
            f"| {label} | {s['precision']:.3f} | {s['recall']:.3f} | "
            f"{s['f1']:.3f} | {s['tp']} | {s['fp']} | {s['fn']} |"
        )

    mismatches = [r for r in results if r["predicted"] != r["expected"]]
    lines += ["", "## Mismatches", ""]
    if not mismatches:
        lines.append("None.")
    else:
        lines.append("| ID | Expected | Predicted | Text | Reason |")
        lines.append("|---|---|---|---|---|")
        for r in mismatches:
            reason = r["reason"].replace("|", "/")[:120]
            text = r["text"].replace("|", "/")[:100]
            lines.append(f"| {r['id']} | {r['expected']} | {r['predicted']} | {text} | {reason} |")
    lines.append("")
    return "\n".join(lines)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate StaleCheck")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--live", action="store_true", help="Use Tavily + configured LLM")
    parser.add_argument("--min-accuracy", type=float, default=0.0)
    parser.add_argument("--json", action="store_true", help="Print JSON summary")
    args = parser.parse_args()

    rows = load_dataset(args.dataset)
    results = await evaluate(rows, live=args.live)
    metrics = summarize(results)
    report = render_markdown(metrics, results, live=args.live)
    args.output.write_text(report, encoding="utf-8")

    if args.json:
        print(json.dumps({"metrics": metrics}, indent=2))
    else:
        print(report)

    if metrics["accuracy"] < args.min_accuracy:
        print(
            f"\nAccuracy {metrics['accuracy']:.3f} below threshold {args.min_accuracy:.3f}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
