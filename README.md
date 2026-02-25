# YARNNN

**Autonomous AI that works on your behalf — powered by accumulated context from your real work platforms.**

Yarn connects to the tools you already use (Slack, Gmail, Notion, Calendar), accumulates understanding of your work world over time, and works autonomously: producing deliverables, surfacing signals, and operating as a thinking partner that already knows your context.

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
    ├── ESSENCE.md       # Core thesis & architecture
    ├── GTM_POSITIONING.md  # Go-to-market messaging
    └── adr/             # Architecture Decision Records
```

## Core Concepts

- **Thinking Partner (TP)**: Context-aware AI agent with primitive-based tools, sub-agent delegation, and web search — it knows your work world before you say a word
- **Deliverables**: Autonomous, scheduled work outputs (reports, digests, briefs) that improve over time through feedback loops
- **Platform Sync**: Continuous synchronization with Slack, Gmail, Notion, Calendar — the raw material for context accumulation
- **Memory & Context**: Four-layer model (Memory → Activity → Context → Work) with bidirectional learning — generation flows down, learning flows up

## Documentation

See [docs/ESSENCE.md](docs/ESSENCE.md) for the core thesis and architecture.