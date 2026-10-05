# Requirements Impact Radar

Requirements Impact Radar is a small B2B web app for comparing two versions of a requirements register and reviewing likely downstream impacts.

## Architecture

- Frontend: React, TypeScript, Vite, Tailwind, TanStack Query.
- Backend: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL.
- Analysis: deterministic ID matching, field diffs, relationship extraction, identifier references, and RapidFuzz lexical similarity.
- Optional services: AI, billing, analytics, and Sentry are feature-flagged or no-op by default.

## Run Locally

```powershell
docker compose up --build
```

If Docker Hub DNS is unavailable but the common base images are already cached locally, run:

```powershell
$env:PYTHON_BASE_IMAGE="python:3.11-slim-bookworm"
$env:NODE_BASE_IMAGE="node:20-alpine"
docker compose up --build
```

Use the default Python 3.12 and Node 24 images again once Docker Hub access is healthy.

Open:

- Frontend: http://localhost:5173
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

Local development uses `DEV_AUTH_BYPASS=true`, which creates a fixed development user and workspace. The backend refuses to start with `DEV_AUTH_BYPASS=true` when `APP_ENV=production`.

## Demo Workflow

1. Create a project.
2. Upload `sample-data/requirements-v1.csv` as `V1`.
3. Upload `sample-data/requirements-v2.csv` as `V2`.
4. Click Compare versions.
5. Open a changed requirement, confirm or dismiss findings, then export CSV or PDF.

## Backend Commands

```powershell
cd backend
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
pytest
```

## Frontend Commands

```powershell
cd frontend
npm install
npm run typecheck
npm run test
npm run build
```

## Environment

Copy `.env.example` to `.env` for local overrides. AI runs with `AI_PROVIDER=none` by default. To use Ollama, set `AI_PROVIDER=ollama`, `AI_MODEL`, and `OLLAMA_BASE_URL`. To use OpenAI, set `AI_PROVIDER=openai`, `AI_MODEL`, and `OPENAI_API_KEY`.

## Deployment

See `docs/DEPLOYMENT.md`.
