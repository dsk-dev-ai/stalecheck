import type { Claim, Verdict } from "../lib/api";

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const label =
    verdict === "fresh" ? "Fresh" : verdict === "stale" ? "Stale" : "Unverifiable";
  return <span className={`badge ${verdict}`}>{label}</span>;
}

export function Pill({ verdict }: { verdict: Verdict }) {
  return <span className={`pill ${verdict}`}>{verdict}</span>;
}

export function ScoreMeter({ score }: { score: number }) {
  return (
    <div className="meter" title={`staleness ${(score * 100).toFixed(0)}%`}>
      <span style={{ width: `${Math.max(4, Math.min(100, score * 100))}%` }} />
    </div>
  );
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const pad = (n: number) => String(n).padStart(2, "0");
  const d = new Date(date.toISOString());
  return (
    `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ` +
    `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`
  );
}

export function ClaimList({ claims }: { claims: Claim[] }) {
  if (!claims.length) {
    return <div className="empty">No checkable claims were extracted.</div>;
  }
  return (
    <div className="claims">
      {claims.map((claim) => (
        <div className="claim" key={claim.id}>
          <div className="top">
            <span className="text">{claim.text}</span>
            <span className="row" style={{ marginTop: 0 }}>
              <span className="pill">{claim.volatility} volatility</span>
              <Pill verdict={claim.verdict} />
            </span>
          </div>
          <div className="why">
            {claim.reason}
            {claim.confidence ? ` · confidence ${(claim.confidence * 100).toFixed(0)}%` : ""}
          </div>
          {claim.suggested_fix ? (
            <div className="fix">Suggested fix: {claim.suggested_fix}</div>
          ) : null}
          {claim.evidence.length ? (
            <div className="evidence">
              {claim.evidence.map((ev, i) => (
                <div key={`${claim.id}-ev-${i}`}>
                  <a href={ev.url} target="_blank" rel="noreferrer">
                    {ev.title || ev.url}
                  </a>
                  {ev.snippet ? <div className="muted">{ev.snippet.slice(0, 220)}</div> : null}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
