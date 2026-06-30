# AI-Driven PE Investment Platform

An AI-powered Private Equity investment platform for deal sourcing, financial analysis, LBO modeling, and IC memo generation.

## Architecture

- **Frontend**: Next.js 16 + React 19 + Tailwind CSS + Recharts
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL + pgvector + Redis + Celery
- **AI**: LangChain + LangGraph + OpenAI GPT-4o
- **Data**: SEC EDGAR, Yahoo Finance, Tavily Web Search, Companies House

## Project Structure

```
PE ASSOCIATE/
├── frontend/          # Next.js frontend application
├── backend/           # FastAPI backend application
├── docker-compose.yml # Docker services (Postgres, Redis)
├── .env.example       # Environment configuration template
├── vercel.json        # Vercel deployment configuration
└── railway.json       # Railway deployment configuration
```

## Quick Start (Local Development)

### 1. Start Docker Services
```bash
docker compose up -d
```

### 2. Start Backend
```bash
cd backend
source .venv/bin/activate
alembic upgrade head
uvicorn api.main:app --reload
```

### 3. Start Frontend
```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Production Deployment

### Frontend → Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. Import your GitHub repo (`codedcapital/Private-Equity-Associate`)
3. **Framework Preset**: Next.js (auto-detected)
4. **Root Directory**: `.` (leave as default)
5. **Environment Variables** — add:
   ```
   NEXT_PUBLIC_API_URL=https://your-railway-backend-url.com
   ```
   *(Get this URL after deploying the backend below)*
6. Click **Deploy**

---

### Backend → Railway (Recommended)

Railway is the best choice because it natively supports PostgreSQL with `pgvector` and Redis.

#### Step 1: Create Railway Project
1. Go to [railway.app](https://railway.app) and log in
2. Click **New Project** → **Deploy from GitHub repo**
3. Select `Private-Equity-Associate`

#### Step 2: Add PostgreSQL Database
1. In your Railway project, click **New** → **Database** → **Add PostgreSQL**
2. Once created, click on the PostgreSQL service → **Variables**
3. Copy the `DATABASE_URL` value
4. Add it as an environment variable to your **backend service** (see Step 4)
5. **Enable pgvector extension**:
   - Go to your PostgreSQL service → **Connect** tab
   - Use any PostgreSQL client to connect
   - Run: `CREATE EXTENSION IF NOT EXISTS vector;`

#### Step 3: Add Redis
1. Click **New** → **Database** → **Add Redis**
2. Copy the `REDIS_URL` (or `REDIS_PUBLIC_URL`)
3. Add it as an environment variable to your backend service

#### Step 4: Configure Environment Variables
Go to your **backend service** → **Variables** tab and add these:

| Variable | Value | Source |
|----------|-------|--------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | From Railway PostgreSQL |
| `DATABASE_URL_SYNC` | `postgresql+psycopg2://...` | Same as above but swap `asyncpg` → `psycopg2` |
| `REDIS_URL` | `redis://...` | From Railway Redis |
| `CELERY_BROKER_URL` | `redis://...` | Same as `REDIS_URL` |
| `CELERY_RESULT_BACKEND` | `redis://...` | Same as `REDIS_URL` |
| `OPENAI_API_KEY` | `sk-...` | Your OpenAI API key |
| `ENVIRONMENT` | `production` | Hardcoded |
| `ALLOWED_ORIGINS` | `https://your-vercel-app.vercel.app` | From Vercel dashboard |
| `TAVILY_API_KEY` | `tvly-...` | *(Optional)* Your Tavily API key |
| `SEC_USER_AGENT` | `PE Platform (your@email.com)` | Your contact info for SEC |

> **Note**: The `ALLOWED_ORIGINS` must be your actual Vercel frontend URL (e.g., `https://private-equity-associate-xxx.vercel.app`). You can update this after deploying the frontend.

#### Step 5: Deploy
1. Railway will auto-detect the `railway.json` and use the `backend/Dockerfile`
2. Click **Deploy** on your backend service
3. Wait for the build to complete (2-3 minutes)
4. Once deployed, copy the **backend public URL** from the service dashboard

#### Step 6: Connect Frontend to Backend
1. Go back to your **Vercel project** → **Settings** → **Environment Variables**
2. Update `NEXT_PUBLIC_API_URL` to your Railway backend URL
3. Vercel will auto-redeploy with the new API URL

---

### Backend → Render (Alternative)

Render has a generous free tier but requires manual pgvector setup. If you prefer Render:

1. **Create a PostgreSQL database** on Render (or use Supabase for pgvector)
2. **Create a Redis instance** on Render
3. **Create a Web Service** → Deploy from GitHub repo
4. Set **Root Directory** to `backend`
5. Set **Build Command** to `pip install -e ".[dev]"`
6. Set **Start Command** to `./start.sh`
7. Add all environment variables as shown in the Railway section above

---

## Required Environment Variables (Production)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL with asyncpg driver |
| `DATABASE_URL_SYNC` | ✅ | Same DB with psycopg2 driver (for Alembic) |
| `OPENAI_API_KEY` | ✅ | Powers all AI agents |
| `REDIS_URL` | ✅ | Celery broker + result backend |
| `ENVIRONMENT` | ✅ | Set to `production` |
| `ALLOWED_ORIGINS` | ✅ | Vercel frontend URL (CORS) |
| `TAVILY_API_KEY` | ⚪️ | Web search (agents fall back gracefully) |
| `EXPLORIUM_API_KEY` | ⚪️ | Competitor enrichment |
| `COMPANIES_HOUSE_API_KEY` | ⚪️ | UK company data |
| `SEC_USER_AGENT` | ✅ | Contact info for SEC EDGAR |

---

## License

MIT
