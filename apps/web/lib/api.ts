export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export type Verdict = "fresh" | "stale" | "unverifiable";
export type Mode = "annotate" | "auto_refresh" | "block";
export type Action = "allow" | "annotate" | "refresh" | "block";

export interface Evidence {
  title: string;
  url: string;
  snippet: string;
  published_at?: string | null;
}

export interface Claim {
  id: string;
  text: string;
  volatility: "high" | "medium" | "low";
  time_sensitive: boolean;
  verdict: Verdict;
  confidence: number;
  reason: string;
  evidence: Evidence[];
  suggested_fix?: string | null;
}

export interface CheckResponse {
  run_id: string;
  verdict: Verdict;
  staleness_score: number;
  action: Action;
  claims: Claim[];
  mode: Mode;
  cached: boolean;
  provider: string;
  latency_ms: number;
  created_at: string;
}

export interface RunDetail extends CheckResponse {
  input_text: string;
  context?: string | null;
}

export interface RunSummary {
  run_id: string;
  verdict: Verdict;
  staleness_score: number;
  action: Action;
  claims_total: number;
  claims_stale: number;
  mode: Mode;
  provider: string;
  preview: string;
  created_at: string;
}

export interface Stats {
  runs: number;
  claims: number;
  stale_claims: number;
  stale_rate: number;
  avg_latency_ms: number;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body.slice(0, 200)}`);
  }
  return (await res.json()) as T;
}

export function checkAnswer(body: {
  text: string;
  context?: string;
  mode: Mode;
  use_web: boolean;
}): Promise<CheckResponse> {
  return request<CheckResponse>("/v1/check", {
    method: "POST",
    body: JSON.stringify({
      text: body.text,
      context: body.context,
      mode: body.mode,
      use_web: body.use_web,
      metadata: {},
    }),
  });
}

export function listRuns(limit = 25): Promise<RunSummary[]> {
  return request<RunSummary[]>(`/v1/runs?limit=${limit}`);
}

export function getRun(id: string): Promise<RunDetail> {
  return request<RunDetail>(`/v1/runs/${encodeURIComponent(id)}`);
}

export function getStats(): Promise<Stats> {
  return request<Stats>("/v1/stats");
}
