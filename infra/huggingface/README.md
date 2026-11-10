---
title: StaleCheck API
colorFrom: indigo
colorTo: red
sdk: docker
app_port: 8000
pinned: false
---

# StaleCheck API (Hugging Face Space)

This Space runs the StaleCheck FastAPI service from the repository's root `Dockerfile`.

## Deploy

1. Create a new Docker Space on Hugging Face.
2. Copy the contents of this repository into the Space repository, then replace the Space
   `README.md` with this file (the YAML header is required for Docker Spaces).
3. In **Settings → Variables and secrets**, add:
   - `TAVILY_API_KEY` (secret, free tier)
   - `LLM_API_KEY` (secret; Groq/Gemini/OpenAI key)
   - `LLM_PROVIDER` (variable: `groq`, `gemini` or `openai`; omit for `mock`)
   - `API_KEY` (optional secret to require `x-api-key`)
   - `CORS_ORIGINS` (variable, e.g. `https://your-dashboard.pages.dev`)
4. The Space exposes the API at `https://<user>-<space>.hf.space`.

Free Spaces use ephemeral disk: run history resets on restart. That is fine for a demo.
For durable storage, mount a volume (paid) or move to Turso/Postgres (roadmap v0.2).
