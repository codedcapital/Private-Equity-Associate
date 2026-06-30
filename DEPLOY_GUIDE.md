# Deployment Guide — PE Associate (all free tiers)

This deploys the **full app** (Next.js frontend + FastAPI backend + AI) on free services and gives you a public shareable link.

## The stack we're using and why

| Piece | Service | Free? | Why this one |
|-------|---------|-------|--------------|
| Frontend (Next.js 16) | **Vercel** | ✅ Yes | Native Next.js host, zero-config, gives you the public link |
| Backend (FastAPI + Celery) | **Render** | ✅ Yes (sleeps when idle) | Runs Docker; the one free host that fits this Python app |
| Database (Postgres + pgvector) | **Supabase** | ✅ Yes | Has the `pgvector` extension the app needs, built in |
| Redis (Celery queue) | **Upstash** | ✅ Yes | Serverless Redis, generous free tier |
| AI (GPT-4o) | **OpenAI** | ❌ **Paid** | No free equivalent — see note below |

> **Cloudflare note:** Cloudflare Pages/Workers can't run this Python backend (FastAPI + Celery + a real Postgres connection), so it isn't the right fit here. Vercel + Render is the equivalent all-free path.

> **The one unavoidable cost — OpenAI.** Every AI feature calls GPT-4o, which bills per use. Put ~$5 on an OpenAI key to start (typically lasts a long time for demo use). Everything *else* here is free. Without a working OpenAI key the app deploys and loads, but pipeline/memo features will error.

> **Render free tier behavior:** the backend sleeps after 15 min idle and takes ~50 seconds to wake on the first request. Normal for a free demo link — just expect a slow first load.

---

## Step 0 — Push the deploy fixes to GitHub

I made three fixes (pgvector extension in the migration, an in-container Celery worker so you don't pay for a second service, and a `.dockerignore`). Commit and push them from your terminal:

```bash
cd "/Users/aditya/Desktop/PE Associate/PE ASSOCIATE"
git add -A
git commit -m "Make app deploy-ready for free-tier hosting"
git push origin main
```

Repo: `https://github.com/codedcapital/Private-Equity-Associate`

---

## Step 1 — Database (Supabase)

1. Go to **https://supabase.com** → sign in with GitHub → **New project**.
2. Name it (e.g. `pe-associate`), set a **database password** (save it), pick a region near you, click **Create**.
3. Wait ~2 min for it to provision.
4. Go to **Project Settings → Database → Connection string → URI**. Copy the connection string. It looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxx.supabase.co:5432/postgres
   ```
5. **Convert it for this app** — change the scheme to the async driver. You'll use this as `DATABASE_URL`:
   ```
   postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.xxxxxxxx.supabase.co:5432/postgres
   ```
   (The app derives the sync URL for migrations automatically — you don't need `DATABASE_URL_SYNC`.)
6. pgvector: the app's migration runs `CREATE EXTENSION IF NOT EXISTS vector` automatically, so there's nothing to enable by hand. (If it ever complains, run that line in **Supabase → SQL Editor**.)

> **Which Supabase URL to use:** pick the **Session pooler** string (host looks like `aws-0-<region>.pooler.supabase.com`, port `5432`) — Render's free tier can't reach the direct `db.<ref>.supabase.co` host. If the string ends in `?pgbouncer=true`, that's fine: the app now strips that parameter automatically.

Keep the `DATABASE_URL` handy.

---

## Step 2 — Redis (Upstash)

1. Go to **https://upstash.com** → sign in with GitHub → **Create Database** (Redis).
2. Name it, pick a region close to your Render region, **Create**.
3. On the database page, copy the **`redis://` connection URL** (use the standard Redis URL, not the REST one). It looks like:
   ```
   rediss://default:xxxxxxxx@your-db.upstash.io:6379
   ```

Keep the Redis URL handy.

---

## Step 3 — OpenAI key

1. Go to **https://platform.openai.com/api-keys** → **Create new secret key** → copy it (`sk-...`).
2. Add a few dollars of credit under **Billing** if you haven't.

---

## Step 4 — Backend (Render)

1. Go to **https://render.com** → sign in with GitHub.
2. **New → Web Service** → connect the `Private-Equity-Associate` repo.
3. Configure:
   - **Language / Runtime:** Docker
   - **Root Directory:** *(leave blank)*
   - **Dockerfile Path:** `backend/Dockerfile`
   - **Instance Type:** Free
4. **Environment variables** — click **Advanced → Add Environment Variable** and add each:

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | your `postgresql+asyncpg://...` from Step 1 |
   | `REDIS_URL` | your `rediss://...` from Step 2 |
   | `OPENAI_API_KEY` | your `sk-...` from Step 3 |
   | `ENVIRONMENT` | `production` |
   | `ALLOWED_ORIGINS` | leave blank for now — you'll set it in Step 6 |
   | `SEC_USER_AGENT` | `PE Associate (adityashetty0205@gmail.com)` |
   | `PORT` | `8000` |

5. Click **Create Web Service**. First build takes ~3–5 min.
6. When it's live, copy the backend URL from the top of the page, e.g.:
   ```
   https://pe-associate-backend.onrender.com
   ```
7. Confirm it works: open `https://<your-backend>.onrender.com/docs` — you should see the FastAPI API docs.

---

## Step 5 — Frontend (Vercel)

1. Go to **https://vercel.com/new** → sign in with GitHub → **Import** the `Private-Equity-Associate` repo.
2. Configure:
   - **Framework Preset:** Next.js (auto-detected)
   - **Root Directory:** leave it **empty / repo root**. (Do NOT set it to `frontend` — the repo's `vercel.json` already does `cd frontend` itself, and setting both makes the build try to `cd frontend` from inside `frontend` and fail.)
3. **Environment Variables** — add:

   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | your Render backend URL from Step 4 (e.g. `https://pe-associate-backend.onrender.com`) |

4. Click **Deploy**. ~2 min.
5. Vercel gives you your **public shareable link**, e.g.:
   ```
   https://private-equity-associate.vercel.app
   ```

---

## Step 6 — Connect the two (CORS) and finish

1. Back in **Render → your backend service → Environment**, set:
   ```
   ALLOWED_ORIGINS = https://private-equity-associate.vercel.app
   ```
   (your exact Vercel URL, no trailing slash). Save — Render redeploys automatically.
2. Open your Vercel link. The app should load and talk to the backend.
   - First request may take ~50s while Render wakes up — that's the free tier.
   - Share the Vercel URL with anyone. That's your link.

---

## Troubleshooting

- **Frontend loads but data calls fail / CORS error:** `ALLOWED_ORIGINS` on Render must exactly match your Vercel URL (https, no trailing slash). Redeploy after changing.
- **Backend build/deploy crashes on start:** check **Render → Logs**. Most often a malformed `DATABASE_URL` (make sure it's `postgresql+asyncpg://...`) or a missing env var.
- **`invalid dsn: invalid connection option "pgbouncer"`:** caused by Supabase's pooler string ending in `?pgbouncer=true`. The app now strips this automatically — just push the latest code and redeploy. (Or remove `?pgbouncer=true` from the `DATABASE_URL` value in Render yourself.)
- **Can't connect to the database at all from Render:** you're probably using the direct `db.<ref>.supabase.co` host, which Render free can't reach. Switch `DATABASE_URL` to the **Session pooler** string (`aws-0-<region>.pooler.supabase.com:5432`).
- **Migration error mentioning `vector`:** open Supabase → SQL Editor → run `CREATE EXTENSION IF NOT EXISTS vector;` then redeploy the backend.
- **Backend runs out of memory** (Render free is 512 MB; the API + Celery worker share it): in Render env vars set `RUN_CELERY_WORKER=0` to drop the worker. The UI still works, but background agent jobs won't process until you run a worker elsewhere or upgrade the instance.
- **AI features error:** confirm `OPENAI_API_KEY` is set on Render and the OpenAI account has billing/credit.

## Seeding demo data (make it investor-ready)

The app ships empty. To populate it with a realistic investment universe — 66 real
public companies across sectors, three years of financials each, deals spread
across all five pipeline stages, LBO metrics on the underwritten deals, and two
full IC memos — use the built-in seeder. It needs no OpenAI and no external APIs.

Because Render's **free tier has no Shell/One-Off Jobs**, trigger it over HTTP:

1. On Render → backend service → **Environment**, add a variable:
   ```
   SEED_TOKEN = <any-random-string-you-choose>
   ```
   Save (the service redeploys).
2. Open your backend's API docs: `https://<your-backend>.onrender.com/docs`
3. Find **POST `/admin/seed-demo`** → **Try it out** → set `token` to your
   `SEED_TOKEN` value → **Execute**. (First call may take ~50s while the free
   instance wakes up.)
4. It returns `{"status":"ok","companies":66,"deals":66}`. Refresh the frontend —
   the pipeline board is now full.

Re-running is safe (it skips what already exists). To wipe and reseed, set the
`reset` parameter to `true`.

> Prefer the command line? You can instead run `python seed_demo.py` from the
> `backend/` directory locally with `DATABASE_URL` pointed at your Supabase
> session-pooler URL — same result.

## Replacing Explorium

Explorium (paid) is no longer required. The competitive agent now enriches
companies from **SEC EDGAR** (free, no key) for US public companies — industry,
HQ, exchange, ticker, and latest annual revenue — alongside the existing free
Wikidata, GLEIF, and OpenCorporates sources. Explorium remains optional and is
only used if `EXPLORIUM_API_KEY` is set; you can leave it unset.

## Cost summary

Everything is free except **OpenAI usage** (a few dollars of pay-as-you-go). Render/Supabase/Upstash/Vercel free tiers cover the rest for demo-level traffic.
