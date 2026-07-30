# YARNNN

**Your true AI-first workspace — co-work like never before.**

One shared workspace for you, your people, and the AI you already use. Nothing to set up — connect, co-work on shared files and documents, share with a link. And every change signed by whoever made it, human or not.

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
│   ├── agents/          # Agent implementations (TP, Deliverables)
│   ├── services/        # Business logic (memory, signals, primitives)
│   └── main.py          # Entry point
├── web/                 # Next.js frontend
│   ├── app/             # App router pages
│   ├── components/      # React components
│   └── lib/             # Utilities
├── supabase/            # Database
│   └── migrations/      # SQL migrations
└── docs/                # Documentation
    ├── ESSENCE.md       # Canonical product narrative
    ├── architecture/FOUNDATIONS.md   # First-principles cognitive architecture
    ├── architecture/agent-framework.md # Scope × Role × Trigger
    └── adr/             # Architecture Decision Records
```

## Core Concepts

- **YARNNN**: The system surface — conversation, supervision, and orchestration of all agent work
- **Persistent Agents**: Domain specialists with their own memory, workspace, directives, and run history
- **Compounding Context**: Synced platform data, workspace memory, prior outputs, and user feedback all improve future runs
- **Recurring Work Products**: Agents produce summaries, briefs, monitoring outputs, research, and richer rendered artifacts when the job requires them

## Documentation

Start with:

- [docs/ESSENCE.md](docs/ESSENCE.md)
- [docs/architecture/FOUNDATIONS.md](docs/architecture/FOUNDATIONS.md)
- [docs/architecture/agent-framework.md](docs/architecture/agent-framework.md)
- [docs/adr/ADR-118-skills-as-capability-layer.md](docs/adr/ADR-118-skills-as-capability-layer.md)
- [docs/adr/ADR-119-workspace-filesystem-architecture.md](docs/adr/ADR-119-workspace-filesystem-architecture.md)
