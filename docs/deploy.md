# Deploying Interviu

Interviu is a monorepo with two deployable parts:

- **`apps/web`** — a Next.js 15 app. **Vercel-native** (`next build` passes; ~113 kB first load).
- **`apps/api`** — a FastAPI (Python) service. **Not** Vercel-native as-is; host it
  separately and point the web app at it.

## 1. Deploy the web app to Vercel

In the Vercel dashboard → **Add New… → Project → import this repo**, then:

- **Root Directory:** `apps/web` (Vercel auto-detects Next.js; no `vercel.json` needed).
- **Build Command:** `next build` (default) · **Install:** `npm install`.
- **Environment Variable:** `NEXT_PUBLIC_API_BASE_URL = https://<your-api-host>`
  (the public URL of the deployed API from step 2). This is the only public var —
  never put server secrets in `NEXT_PUBLIC_*`.

CLI alternative:

```bash
cd apps/web
npx vercel            # first deploy / link
npx vercel --prod     # production
```

## 2. Host the API

The API holds server-only secrets (`OPENAI_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`,
`TRACERAZOR_BIN`) and runs a long-lived process, so deploy it on a Python host
(Render, Railway, Fly.io, Azure App Service, a VM, etc.):

```bash
python -m uvicorn interviu_api.main:app --app-dir apps/api --host 0.0.0.0 --port $PORT
```

Set these env vars on the API host (server-only):

- `INTERVIU_DB_BACKEND=supabase`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
- `OPENAI_API_KEY` (optional — enables the OpenAI research/extraction layer)
- CORS: `apps/api/interviu_api/main.py` currently allow-lists `localhost:30xx`.
  Add your Vercel domain to `allow_origins` / `allow_origin_regex` before going live.

> Vercel-only alternative for the API: port the FastAPI routes to Vercel Python
> Serverless Functions under `api/`. That's a follow-up — the long-running
> `uvicorn` process + the spawned TraceRazor binary fit a container host better.

## 3. Database

Supabase is already provisioned (`interviu_*` tables, RLS + service-role grants).
No build step needed; just supply the env vars above. SQLite is the local fallback
when Supabase vars are absent.
