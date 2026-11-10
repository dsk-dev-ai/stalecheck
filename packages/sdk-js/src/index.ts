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

export interface CheckResult {
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

export interface Stats {
  runs: number;
  claims: number;
  stale_claims: number;
  stale_rate: number;
  avg_latency_ms: number;
}

export interface CheckOptions {
  text: string;
  context?: string;
  mode?: Mode;
  useWeb?: boolean;
  metadata?: Record<string, unknown>;
}

export class StaleCheckError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "StaleCheckError";
  }
}

export class StaleAnswerError extends StaleCheckError {
  readonly result: CheckResult;

  constructor(result: CheckResult) {
    const stale = result.claims
      .filter((c) => c.verdict === "stale")
      .slice(0, 3)
      .map((c) => c.text)
      .join("; ");
    super(`Blocked stale answer: ${stale}`);
    this.name = "StaleAnswerError";
    this.result = result;
  }
}

const DEFAULT_URL = "http://localhost:8000";

export class StaleCheck {
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly fetcher: typeof fetch;

  constructor(options: { baseUrl?: string; apiKey?: string; fetch?: typeof fetch } = {}) {
    const env = (
      globalThis as { process?: { env?: Record<string, string | undefined> } }
    ).process?.env;
    this.baseUrl = (options.baseUrl ?? env?.STALECHECK_URL ?? DEFAULT_URL).replace(/\/$/, "");
    this.apiKey = options.apiKey ?? env?.STALECHECK_API_KEY;
    this.fetcher = options.fetch ?? fetch;
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    let response: Response;
    try {
      response = await this.fetcher(`${this.baseUrl}${path}`, {
        ...init,
        headers: {
          "content-type": "application/json",
          ...(this.apiKey ? { "x-api-key": this.apiKey } : {}),
          ...(init?.headers ?? {}),
        },
      });
    } catch (error) {
      throw new StaleCheckError(
        `Could not reach StaleCheck at ${this.baseUrl}: ${String(error)}`,
      );
    }
    if (!response.ok) {
      const body = await response.text();
      throw new StaleCheckError(`StaleCheck API ${response.status}: ${body.slice(0, 300)}`);
    }
    return (await response.json()) as T;
  }

  check(options: CheckOptions): Promise<CheckResult> {
    return this.request<CheckResult>("/v1/check", {
      method: "POST",
      body: JSON.stringify({
        text: options.text,
        context: options.context,
        mode: options.mode ?? "annotate",
        use_web: options.useWeb ?? true,
        metadata: options.metadata ?? {},
      }),
    });
  }

  stats(): Promise<Stats> {
    return this.request<Stats>("/v1/stats", { method: "GET" });
  }
}

export interface GuardedAnswer {
  text: string;
  result: CheckResult;
  refreshed: boolean;
}

export async function guardAnswer(
  checker: StaleCheck,
  answer: string,
  options: {
    mode?: Mode;
    refresh?: (result: CheckResult) => Promise<string> | string;
  } = {},
): Promise<GuardedAnswer> {
  const mode = options.mode ?? "annotate";
  const result = await checker.check({ text: answer, mode });
  if (result.verdict !== "stale") {
    return { text: answer, result, refreshed: false };
  }
  if (mode === "block") {
    throw new StaleAnswerError(result);
  }
  if (mode === "auto_refresh" && options.refresh) {
    return { text: await options.refresh(result), result, refreshed: true };
  }
  return { text: answer, result, refreshed: false };
}
