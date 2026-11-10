# Deploy everything on free tiers

The whole product can run at **$0** for a hackathon demo:

| Piece | Service | Free tier (check current limits) |
|---|---|---|
| API (Docker) | Hugging Face Spaces **or** Render | Free CPU Space / free web service |
| Dashboard (static) | Cloudflare Pages **or** Vercel Hobby | Static hosting + build minutes |
| Freshness search | Tavily | 1,000 searches/month |
| LLM (extract + judge) | Groq or Gemini API | Free, rate-limited |
| Database | SQLite inside the API container | included |
| CI | GitHub Actions (public repo) | free minutes |
| Domain | `*.pages.dev` / `*.hf.space` / `*.onrender.com` | free |

> Verify each provider's current free-tier limits before relying on them. Numbers change.

The API is a single container with a file-based SQLite database. That is deliberate: it removes
the need for a managed database, a queue, or a GPU.

---

## 1. Get the two API keys (free)

1. **Tavily** — create an account and copy the API key. Free tier: 1,000 searches/month.
   StaleCheck only searches for claims the offline snapshot cannot resolve, so a demo usually
   consumes a handful of credits.
2. **LLM** — either:
   - **Groq**: `LLM_PROVIDER=groq`, key from the Groq console; default model
     `llama-3.1-8b-instant`.
   - **Gemini**: `LLM_PROVIDER=gemini`, key from Google AI Studio; default model
     `gemini-2.0-flash`.
   - **OpenAI** or any OpenAI-compatible endpoint: `LLM_PROVIDER=openai` / `custom`.

Without keys the API still runs in **mock mode** (offline snapshot, rule-based extraction).
That is enough for the dashboard and the eval suite.

---

## 2. Deploy the API

### Option A — Hugging Face Spaces (recommended: more RAM, stays warm)

1. Create a **Docker** Space.
2. Push this repository to the Space repo.
3. Replace the Space `README.md` with `infra/huggingface/README.md` (the YAML header tells
   Spaces to use the root `Dockerfile` and port 8000).
4. In **Settings → Variables and secrets**:
   - `TAVILY_API_KEY` (secret)
   - `LLM_API_KEY` (secret)
   - `LLM_PROVIDER` = `groq` (variable, optional)
   - `API_KEY` (optional secret)
   - `CORS_ORIGINS` = your dashboard origin (or `*` for the demo)
5. Wait for the build. Your API is at `https://<user>-<space>.hf.space`. Check `/health`.

Free Spaces use ephemeral disk, so run history resets when the Space restarts. Fine for a demo;
see the roadmap for durable storage.

### Option B — Render (blueprint included)

1. Push the repo to GitHub.
2. Render → **New → Blueprint** → select the repo. It reads `render.yaml`.
3. Add the secret env vars (`TAVILY_API_KEY`, `LLM_API_KEY`) in the dashboard.
4. Deploy. Free services sleep after inactivity, so the first request may take ~30s.

### Option C — Fly.io (not free, but persistent volume)

`fly.toml` is included with a `/data` volume and auto-stop machines. This is the cheapest path to
durable run history if you are willing to pay a few cents.

### Option D — your own machine

```bash
docker build -t stalecheck-api .
docker run --rm -p 8000:8000 -v "$PWD/data:/data" --env-file .env stalecheck-api
```

---

## 3. Deploy the dashboard (Cloudflare Pages)

The dashboard is a static Next.js export (`output: "export"`), so it needs no server.

1. Cloudflare Pages → **Create project** → connect the repo.
2. Build settings:
   - **Root directory:** `apps/web`
   - **Build command:** `pnpm install --no-frozen-lockfile && pnpm build`
   - **Build output directory:** `out`
3. Environment variable (production):
   - `NEXT_PUBLIC_API_URL` = your API URL from step 2.
4. Deploy. Add the resulting `*.pages.dev` origin to the API's `CORS_ORIGINS`.

Vercel works too: import the repo, set **Root Directory** to `apps/web`, framework Next.js, and
the same `NEXT_PUBLIC_API_URL` env var.

> The dashboard is public. Do **not** set `API_KEY` on a public demo API unless you put a
> server-side proxy in front of it — a static site cannot keep a secret. For production, put the
> API behind your own authenticated backend.

---

## 4. Smoke test

```bash
curl -s https://YOUR-API/health
curl -s https://YOUR-API/v1/check \
  -H 'content-type: application/json' \
  -d '{"text":"GPT-4o is the latest OpenAI model."}' | jq
```

Expected: `verdict: "stale"`, with a `suggested_fix`.

---

## Cost control

- **Cache aggressively.** Identical checks return cached verdicts for 24h by default
  (`CACHE_TTL_SECONDS`).
- **Snapshot first.** Tavily is only called for unknown claims.
- **Cap the work.** `MAX_CLAIMS` and `MAX_JUDGED_CLAIMS` bound extraction and verification.
- **Cheap model.** Groq's small Llama model is enough for extraction and judging.
