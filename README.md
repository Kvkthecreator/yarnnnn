# YARNNN

**Context-aware AI work platform**

Your AI agents understand your world because they read from your accumulated context.

## Quick Start

```bash
# Backend
cd api && pip install -r requirements.txt && uvicorn main:app --reload

# Frontend
cd web && npm install && npm run dev
```

## Structure

```
yarnnn/
├── api/                 # FastAPI backend
│   ├── routes/          # API endpoints
│   ├── agents/          # Agent implementations
│   ├── services/        # Business logic
│   └── main.py          # Entry point
├── web/                 # Next.js frontend
│   ├── app/             # App router pages
│   ├── components/      # React components
│   └── lib/             # Utilities
├── supabase/            # Database
│   └── migrations/      # SQL migrations
└── docs/                # Documentation
    └── ESSENCE.md       # Core specification
```

## Core Concepts

- **Projects**: Your work containers
- **Blocks**: Atomic knowledge units
- **Agents**: AI workers (Research, Content, Reporting, Chat)
- **Outputs**: Deliverables from agent work

## Documentation

See [docs/ESSENCE.md](docs/ESSENCE.md) for full specification.