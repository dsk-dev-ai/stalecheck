"use client";

import { useEffect, useState } from "react";
import { ClaimList, ScoreMeter, VerdictBadge, formatDate } from "../../components/ui";
import { getRun, listRuns, type RunDetail, type RunSummary } from "../../lib/api";

export default function RunsPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<RunDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    listRuns(50)
      .then(setRuns)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, []);

  async function open(runId: string) {
    setDetailLoading(true);
    setError(null);
    try {
      setSelected(await getRun(runId));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <>
      <section className="hero">
        <h1>Run history</h1>
        <p>
          Every check is stored with claim-level verdicts, evidence and suggested fixes so you
          can audit drift over time.
        </p>
      </section>

      <div className="card">
        {loading ? (
          <div className="empty">
            <span className="spin" /> Loading runs…
          </div>
        ) : runs.length === 0 ? (
          <div className="empty">No runs yet. Run a check from the home page.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>Verdict</th>
                <th>Claims</th>
                <th>Stale</th>
                <th>Preview</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.run_id}>
                  <td className="mono">{formatDate(run.created_at)}</td>
                  <td>
                    <VerdictBadge verdict={run.verdict} />
                  </td>
                  <td>{run.claims_total}</td>
                  <td>{run.claims_stale}</td>
                  <td className="muted">{run.preview}</td>
                  <td>
                    <button className="ghost" onClick={() => open(run.run_id)}>
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {error ? <div className="error">{error}</div> : null}
      </div>

      {selected ? (
        <section style={{ marginTop: 22 }}>
          <div className={`verdict ${selected.verdict}`}>
            <div>
              <VerdictBadge verdict={selected.verdict} />
              <div className="muted" style={{ marginTop: 4 }}>
                {selected.run_id} · {selected.provider} · {selected.latency_ms}ms ·{" "}
                {formatDate(selected.created_at)}
              </div>
            </div>
            <ScoreMeter score={selected.staleness_score} />
            <span className="pill">{selected.action}</span>
          </div>
          <div className="card" style={{ marginBottom: 16 }}>
            <h2>Input</h2>
            <div className="mono" style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
              {detailLoading ? "Loading…" : selected.input_text}
            </div>
          </div>
          <div className="card">
            <h2>Claims</h2>
            <ClaimList claims={selected.claims} />
          </div>
        </section>
      ) : null}
    </>
  );
}
