"use client";

import { useEffect, useState } from "react";
import { ClaimList, ScoreMeter, VerdictBadge, formatDate } from "../components/ui";
import {
  checkAnswer,
  getStats,
  type CheckResponse,
  type Mode,
  type Stats,
} from "../lib/api";

const SAMPLES = [
  {
    label: "Stale: model",
    text: "GPT-4o is the latest OpenAI model. It is the most capable model available today.",
  },
  {
    label: "Stale: versions",
    text: "Python 3.11 is the latest version of the language. Node 18 is the LTS release for production.",
  },
  {
    label: "Fresh",
    text: "GPT-5 is the latest OpenAI model. Python 3.14 is the latest stable release.",
  },
  { label: "Unknown", text: "The Zorblax API costs $42 per call." },
];

const SAMPLE_TEXT = SAMPLES[0].text;

export default function HomePage() {
  const [text, setText] = useState(SAMPLE_TEXT);
  const [mode, setMode] = useState<Mode>("annotate");
  const [useWeb, setUseWeb] = useState(true);
  const [context, setContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CheckResponse | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    getStats()
      .then(setStats)
      .catch(() => setStats(null));
  }, []);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await checkAnswer({ text, context, mode, use_web: useWeb });
      setResult(res);
      getStats().then(setStats).catch(() => undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <section className="hero">
        <h1>Catch stale answers before your users do.</h1>
        <p>
          Paste any AI answer. StaleCheck decomposes it into claims, scores time-sensitivity,
          verifies the volatile ones against fresh evidence, and tells you what is outdated —
          with a corrected statement you can ship.
        </p>
      </section>

      <div className="grid">
        <div className="card">
          <h2>Check an answer</h2>
          <form onSubmit={onSubmit}>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste an AI answer or RAG output…"
            />
            <textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Optional RAG context / sources (grounded facts, docs)…"
              style={{ minHeight: 90, marginTop: 10 }}
            />
            <div className="samples">
              {SAMPLES.map((sample) => (
                <button
                  type="button"
                  key={sample.label}
                  onClick={() => setText(sample.text)}
                >
                  {sample.label}
                </button>
              ))}
            </div>
            <div className="row">
              <select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
                <option value="annotate">annotate</option>
                <option value="auto_refresh">auto_refresh</option>
                <option value="block">block</option>
              </select>
              <label className="check">
                <input
                  type="checkbox"
                  checked={useWeb}
                  onChange={(e) => setUseWeb(e.target.checked)}
                />
                live web (Tavily)
              </label>
              <button className="primary" type="submit" disabled={loading || !text.trim()}>
                {loading ? <span className="spin" /> : "Run check"}
              </button>
            </div>
          </form>
          {error ? <div className="error">{error}</div> : null}
        </div>

        <div className="card">
          <h2>Live stats</h2>
          <div className="stats">
            <div className="stat">
              <div className="k">Runs</div>
              <div className="v">{stats?.runs ?? "—"}</div>
            </div>
            <div className="stat">
              <div className="k">Claims</div>
              <div className="v">{stats?.claims ?? "—"}</div>
            </div>
            <div className="stat">
              <div className="k">Stale rate</div>
              <div className="v">
                {stats ? `${(stats.stale_rate * 100).toFixed(0)}%` : "—"}
              </div>
            </div>
            <div className="stat">
              <div className="k">Avg latency</div>
              <div className="v">
                {stats ? `${stats.avg_latency_ms.toFixed(0)}ms` : "—"}
              </div>
            </div>
          </div>
          <p className="muted" style={{ marginTop: 14, lineHeight: 1.6 }}>
            Pipeline: extract claims → classify volatility → snapshot pre-filter → Tavily for
            unknowns → LLM judge → policy.
          </p>
        </div>
      </div>

      {result ? (
        <section style={{ marginTop: 22 }}>
          <div className={`verdict ${result.verdict}`}>
            <div>
              <VerdictBadge verdict={result.verdict} />
              <div className="muted" style={{ marginTop: 4 }}>
                run {result.run_id} · {result.provider} · {result.latency_ms}ms ·{" "}
                {result.cached ? "cached · " : ""}
                {formatDate(result.created_at)}
              </div>
            </div>
            <ScoreMeter score={result.staleness_score} />
            <span className="pill">{result.action}</span>
          </div>
          <div className="card">
            <h2>Claims</h2>
            <ClaimList claims={result.claims} />
          </div>
        </section>
      ) : null}
    </>
  );
}
