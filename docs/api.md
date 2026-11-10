# API reference

Base URL: `http://localhost:8000` in development.

Interactive docs are served at `/docs` (Swagger) and `/redoc`.

## Authentication

Auth is off by default. If the API is started with `API_KEY=<secret>`, every `/v1/*` request
must include `x-api-key: <secret>`. `/health` and `/` stay public.

## `POST /v1/check`

Check a block of text for stale claims.

```bash
curl -s http://localhost:8000/v1/check \
  -H 'content-type: application/json' \
  -d '{"text": "GPT-4o is the latest OpenAI model.", "mode": "annotate", "use_web": true}'
```

Request fields:

| Field | Type | Default | Notes |
|---|---|---|---|
| `text` | string | required | 1–20,000 chars |
| `context` | string \| null | null | Optional RAG context / sources |
| `mode` | `annotate` \| `auto_refresh` \| `block` | `annotate` | Drives `action` |
| `use_web` | boolean | `true` | Allow Tavily for unknown claims |
| `metadata` | object | `{}` | Free-form caller metadata |

Response:

```json
{
  "run_id": "sc_4f2a1c9d8e7b6a50",
  "verdict": "stale",
  "staleness_score": 1.0,
  "action": "annotate",
  "mode": "annotate",
  "provider": "mock",
  "cached": false,
  "latency_ms": 4,
  "created_at": "2026-11-10T12:00:00Z",
  "claims": [
    {
      "id": "c1",
      "text": "GPT-4o is the latest OpenAI model.",
      "volatility": "high",
      "time_sensitive": true,
      "verdict": "stale",
      "confidence": 0.92,
      "reason": "Contradicts a dated fact (snapshot as of 2026-11-01).",
      "suggested_fix": "GPT-5 is OpenAI's flagship model (released August 2025), succeeding GPT-4o.",
      "evidence": [
        {
          "title": "Introducing GPT-5",
          "url": "https://openai.com/index/introducing-gpt-5/",
          "snippet": "GPT-5 is OpenAI's flagship model...",
          "published_at": "2026-11-01"
        }
      ]
    }
  ]
}
```

`action` values: `allow` (nothing stale), `annotate`, `refresh`, `block` (derived from `mode`).

## `GET /v1/runs?limit=25&offset=0`

Returns recent runs, newest first.

## `GET /v1/runs/{run_id}`

Returns the full run, including `input_text` and all claims. `404` when unknown.

## `GET /v1/stats`

```json
{"runs": 12, "claims": 31, "stale_claims": 9, "stale_rate": 0.29, "avg_latency_ms": 8.4}
```

## `GET /health`

```json
{"status": "ok", "version": "1.0.0", "provider": "mock", "live_web": false, "auth": false}
```

## Errors

| Status | Meaning |
|---|---|
| `401` | `API_KEY` is set and `x-api-key` is missing/wrong |
| `404` | Unknown run id |
| `422` | Request validation failed (e.g. empty `text`) |
| `500` | Unhandled server error |
