# Cognerd Hackathon

Monorepo for an AI visibility and content platform with three main parts:
- `brand-monitor-service`: primary Next.js app (auth, dashboards, APIs, brand analysis, file generation)
- `frontend`: secondary Next.js dashboard/client app
- `pycode`: Python services for content generation, knowledge workflows, and agent pipelines

## Repository Structure

```text
Cognerd Hackathon/
├── brand-monitor-service/   # Main Next.js 16 TypeScript app
├── frontend/                # Additional Next.js 16 frontend
├── pycode/                  # Python services and agent workflows
├── n8n-workflow/            # n8n workflow JSON exports
└── .gitignore
```

## Tech Stack

- TypeScript, React 19, Next.js 16
- Node.js package managers: npm/pnpm (lockfiles present)
- Python (LLM, vector DB, workflow tooling)
- PostgreSQL, MongoDB, Qdrant (used by app/services)
- Drizzle ORM migrations in `brand-monitor-service`

## Prerequisites

- Node.js 20+
- npm 10+ (or pnpm if you prefer it)
- Python 3.10+
- `pip` and virtual environment tooling (`venv`)
- Local/remote access to:
  - PostgreSQL
  - MongoDB (for file and profile data paths)
  - Qdrant (for vector workflows in Python service)

## Quick Start

### 1. Clone and enter project

```bash
git clone <your-repo-url>
cd "Cognerd Hackathon"
```

### 2. Setup `brand-monitor-service`

```bash
cd brand-monitor-service
npm install
cp .env.example .env.local  # if available; otherwise create .env.local manually
npm run dev
```

App runs on `http://localhost:3000` by default.

### 3. Setup `frontend`

Open a new terminal:

```bash
cd frontend
npm install
# create frontend/.env if needed
npm run dev
```

### 4. Setup `pycode`

Open another terminal:

```bash
cd pycode
python -m venv .venv
# Windows PowerShell:
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
python src/main.py
```

## Environment Variables

Use separate env files per service (`brand-monitor-service/.env.local`, `frontend/.env`, `pycode/.env`).

### `brand-monitor-service` (required)

- `DATABASE_URL`
- `BETTER_AUTH_SECRET`
- `NEXT_PUBLIC_APP_URL`
- `AUTUMN_SECRET_KEY`

### `brand-monitor-service` (commonly used)

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `OPENROUTER_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_GENERATIVE_AI_API_KEY`
- `PERPLEXITY_API_KEY`
- `DEEPSEEK_API_KEY`
- `XAI_API_KEY`
- `FIRECRAWL_API_KEY`
- `MONGODB_URI`
- `MONGODB_DB`
- `MONGODB_COLLECTION`
- `DATAFORSEO_LOGIN`
- `DATAFORSEO_PASSWORD`
- `GMAIL_USER`
- `GMAIL_PASS`
- `GMAIL_APP_PASSWORD`
- `EMAIL_FROM`
- `SUPERUSER_EMAILS`
- `WEBHOOK_URL`
- `FILES_WEBHOOK_SECRET`

### `frontend` (from current usage)

- `NEXT_PUBLIC_BRAND_MONITOR_URL`
- `NEXT_PUBLIC_PYTHON_SERVICE_BASE_URL`
- `JWT_SECRET`

### `pycode` (important)

- `DATABASE_URL`
- `OPENAI_API_KEY`
- `OPENROUTER_API_KEY`
- `GEMINI_API_KEY` (or `GOOGLE_API_KEY`)
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `COLLECTION_NAME`
- `BRAND_COLLECTION_NAME`
- `MONGODB_URI`
- `MONGODB_DB`
- `MONGODB_COLLECTION`
- `DEFAULT_LLM_PROVIDER`
- `RESEARCHER_PROVIDER`, `PLANNER_PROVIDER`, `WRITER_PROVIDER`, `OPTIMIZER_PROVIDER`, `QA_PROVIDER`
- `OLLAMA_BASE_URL` (if using Ollama)

## Common Commands

### `brand-monitor-service`

```bash
npm run dev
npm run build
npm run start
npm run lint
npm run setup
npm run db:generate
npm run db:migrate
npm run db:push
npm run db:studio
npm run seed:brands
```

### `frontend`

```bash
npm run dev
npm run build
npm run start
npm run lint
```

### `pycode`

```bash
pytest
python src/main.py
python src/api.py
```

## Database and Migrations

- SQL migrations live in:
  - `brand-monitor-service/migrations/`
  - `brand-monitor-service/drizzle-generated/`
- Drizzle config: `brand-monitor-service/drizzle.config.ts`
- Run migration flow from `brand-monitor-service`:

```bash
npm run db:generate
npm run db:migrate
```

## n8n Workflow

- Exported workflow file:
  - `n8n-workflow/Product-to-UGC.json`

Import this into your n8n instance to reproduce the automation flow.

## Troubleshooting

### `DATABASE_URL` errors

- Confirm `DATABASE_URL` is set in the correct service env file.
- Confirm database is reachable from your machine.

### Auth issues

- Verify `BETTER_AUTH_SECRET` and `NEXT_PUBLIC_APP_URL`.
- Recheck Google OAuth values if social login fails.

### Python import/module errors

- Ensure the virtual environment is activated.
- Reinstall dependencies:

```bash
pip install -r requirements.txt
```

### Frontend cannot reach APIs

- Verify `NEXT_PUBLIC_BRAND_MONITOR_URL` and `NEXT_PUBLIC_PYTHON_SERVICE_BASE_URL`.
- Confirm backend services are running.

## Notes

- Keep secrets out of git.
- Use `.env.local` for local development in Next.js services.
- This repository contains multiple apps; run each service from its own folder.
