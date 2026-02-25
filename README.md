# YARNNN

**A context accumulation platform for AI — syncs your work tools, accumulates intelligence over time, and serves it to any AI surface.**

YARNNN connects to your work platforms (Slack, Gmail, Notion, Calendar) and accumulates context over time. This accumulated intelligence powers multiple surfaces: a built-in Thinking Partner agent, autonomous deliverable generation, and MCP connectors that let Claude.ai, ChatGPT, and other LLMs access your accumulated context directly. The platform is the product — surfaces are interchangeable.

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
│   ├── services/        # Core platform logic (44 modules)
│   ├── routes/          # API endpoints (REST surface)
│   ├── agents/          # Thinking Partner agent (Claude AgentSDK)
│   ├── mcp_server/      # MCP server (A2A surface for external LLMs)
│   ├── jobs/            # Scheduler (autonomous surface)
│   └── main.py          # API entry point
├── web/                 # Next.js frontend
│   ├── app/             # App router pages
│   ├── components/      # React components
│   └── lib/             # Utilities
├── supabase/            # Database
│   └── migrations/      # SQL migrations
└── docs/                # Documentation
    ├── architecture/    # Architecture specs (platform, execution, data model)
    ├── adr/             # Architecture Decision Records
    └── ESSENCE.md       # Foundation document
```

## Architecture

YARNNN is a **data platform with interchangeable consumption surfaces**. The platform syncs, accumulates, and processes context from work tools. Surfaces consume the platform's services.

### Platform
- **Platform Sync**: Continuous synchronization with Slack, Gmail, Notion, Calendar
- **Content Accumulation**: Retention-based accumulation — content that proves significant is retained indefinitely ([four-layer model](docs/architecture/four-layer-model.md))
- **Deliverable Execution**: Autonomous report/digest/brief generation with type-specific strategies
- **Memory & Signals**: Implicit memory extraction, behavioral signal processing, compounding learning loops

### Surfaces
- **Thinking Partner (TP)**: Built-in conversational agent (Claude AgentSDK) with primitive-based tools and working memory injection
- **MCP Server**: Agent-to-Agent protocol — Claude.ai, ChatGPT, and other LLMs access YARNNN data via 6 MCP tools ([ADR-075](docs/adr/ADR-075-mcp-connector-architecture.md))
- **Unified Scheduler**: Cron-driven autonomous orchestration — signal processing, deliverable execution, memory extraction
- **REST API**: Thin endpoint layer consumed by the Next.js frontend

## Documentation

- [Platform Architecture](docs/architecture/platform-architecture.md) — Why the data platform is the moat, and how surfaces consume it
- [Four-Layer Model](docs/architecture/four-layer-model.md) — Memory, Activity, Context, Work data model
- [Backend Orchestration](docs/architecture/backend-orchestration.md) — Pipeline: Sync → Signal → Deliverable → Memory
- [ESSENCE.md](docs/ESSENCE.md) — Foundation document
- [Architecture Decision Records](docs/adr/) — All architectural decisions
