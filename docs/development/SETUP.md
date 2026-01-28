# Local Development Setup

## Prerequisites

- Python 3.9+
- Node.js 18+
- pnpm or npm

## Environment Variables

### API (`api/.env`)

```bash
# Supabase
SUPABASE_URL=https://noxgqcwynkzqabljjyon.supabase.co
SUPABASE_ANON_KEY=<see docs/database/ACCESS.md>
SUPABASE_SERVICE_KEY=<see docs/database/ACCESS.md>

# AI Providers
ANTHROPIC_API_KEY=<your-key>

# App
ENVIRONMENT=development
```

### Web (`web/.env.local`)

```bash
NEXT_PUBLIC_SUPABASE_URL=https://noxgqcwynkzqabljjyon.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<see docs/database/ACCESS.md>
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Running Locally

### API

```bash
cd api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API available at: http://localhost:8000
Docs at: http://localhost:8000/docs

### Web

```bash
cd web
pnpm install
pnpm dev
```

Web available at: http://localhost:3000

## Database

### Direct SQL Access

```bash
psql "postgresql://postgres.noxgqcwynkzqabljjyon:yarNNN%21%21%40%40%23%23%24%24@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
```

### Run Migrations

```bash
psql "<connection-string>" -f supabase/migrations/001_initial_schema.sql
```

See [database/ACCESS.md](../database/ACCESS.md) for full connection details.

## Deployments

| Service | URL | Auto-deploy |
|---------|-----|-------------|
| Vercel (Web) | yarnnnn.vercel.app | On push to main |
| Render (API) | yarnnn-api.onrender.com | On push to main |
