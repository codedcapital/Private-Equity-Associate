# AI-Driven PE Investment Platform — Backend

## Quick Start

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with real API keys
   ```

2. **Start Docker services:**
   ```bash
   docker compose up -d
   ```

3. **Install Python dependencies:**
   ```bash
   cd backend
   uv pip install -e ".[dev]"
   # or: pip install -e ".[dev]"
   ```

4. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

5. **Seed dummy data:**
   ```bash
   python -m db.seed
   ```

6. **Start the API:**
   ```bash
   uvicorn api.main:app --reload
   ```

7. **Open API docs:** http://localhost:8000/docs

## Project Structure

```
backend/
├── api/           # FastAPI routers & main app
├── agents/        # LangGraph agent graphs (sourcing, research, LBO, etc.)
├── core/          # Shared services (LLM, embeddings, vector search, LBO engine)
├── db/            # SQLAlchemy models, sessions, CRUD, migrations
├── ingest/        # Data ingestion pipelines (SEC, Companies House, yfinance)
├── schemas/       # Pydantic request/response schemas
└── tests/         # pytest suite
```

## Testing

```bash
pytest tests/ -v
```

## Data Sources

| Source | Type | Key Required |
|--------|------|-------------|
| SEC EDGAR | US public filings | Free (user agent only) |
| Companies House | UK company data | Yes (free API key) |
| Yahoo Finance | Financial metrics | Free (no key) |
| Tavily | Web search | Yes |
| Crunchbase | Competitor data | Yes |
| PitchBook | Competitor data | Yes |
