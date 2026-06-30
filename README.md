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
└── vercel.json        # Vercel deployment configuration
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

## Deployment

### Frontend → Vercel
1. Push this repo to GitHub
2. Import the repo in [Vercel](https://vercel.com/new)
3. Set environment variable: `NEXT_PUBLIC_API_URL=https://your-api-domain.com`
4. Deploy

### Backend → Separate Host (Railway / Render / Fly.io / AWS)
The backend requires:
- Python 3.11+
- PostgreSQL 15+ with pgvector
- Redis

**Required env vars:**
- `DATABASE_URL`
- `DATABASE_URL_SYNC`
- `OPENAI_API_KEY`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`

See `.env.example` for full configuration.

## License

MIT
# Private-Equity-Associate
