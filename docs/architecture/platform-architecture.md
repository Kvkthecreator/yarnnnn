# Architecture: Data Platform + Surfaces

**Status:** Canonical
**Date:** 2026-02-25
**Related:**
- [Four-Layer Model](four-layer-model.md) — Data model (Memory / Activity / Context / Work)
- [Backend Orchestration](backend-orchestration.md) — Pipeline: Sync → Signal → Deliverable → Memory
- [Agent Execution Model](agent-execution-model.md) — TP vs Orchestrator execution paths
- [MCP Connectors](../integrations/MCP-CONNECTORS.md) — MCP product rationale
- [ADR-075](../adr/ADR-075-mcp-connector-architecture.md) — MCP technical implementation
- [ADR-072](../adr/ADR-072-unified-content-layer-tp-execution-pipeline.md) — Unified Content Layer

---

## The Core Thesis

YARNNN is a **data platform** with interchangeable consumption surfaces.

The platform syncs content from work tools (Slack, Gmail, Notion, Calendar), accumulates it over time with retention semantics, extracts memory and signals, and executes recurring workflows over that accumulated data. This is the moat.

The intelligence is commoditized. LLMs — Claude, ChatGPT, Gemini — are already capable reasoners. What they lack is the user's accumulated work context. YARNNN has it because it does the unglamorous work of syncing, retaining, and compounding it.

> **The accumulated context is not replaceable. The reasoning layer is.**

Surfaces — the Thinking Partner, MCP connectors, the scheduler, the REST API — are interchangeable ways to access and act on the platform's data. They are not the product.

---

## Platform vs Surfaces

```
                    ┌─────────────────────────────────────────┐
                    │          Consumption Surfaces            │
                    │                                         │
                    │  TP Agent     MCP Server    Scheduler   │
                    │  (Claude      (A2A:         (Cron)      │
                    │   AgentSDK)   Claude.ai,                │
                    │               ChatGPT,     REST API     │
                    │               Gemini)      (Web UI)     │
                    └──────────────────┬──────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────┐
                    │         Service Layer (44 modules)       │
                    │                                         │
                    │  execute_deliverable_generation()        │
                    │  search_platform_content()               │
                    │  build_working_memory()                  │
                    │  extract_signal_summary()                │
                    │  process_signal()                        │
                    │  ...                                     │
                    └──────────────────┬──────────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────────┐
                    │            Data Platform                 │
                    │                                         │
                    │  platform_content  (accumulation)        │
                    │  user_context      (memory)              │
                    │  activity_log      (provenance)          │
                    │  deliverables      (workflow config)     │
                    │  deliverable_versions (generated work)   │
                    │  signal_history    (detected patterns)   │
                    └─────────────────────────────────────────┘
```

**Convergence proof:** `execute_deliverable_generation()` — the central deliverable execution function — is called from 7+ locations across all surfaces: REST routes, TP primitives, MCP tools, scheduler phases, signal processing, and event triggers. No surface has its own execution logic. All consume the same service layer.

For pipeline detail, see [backend-orchestration.md](backend-orchestration.md). For data model, see [four-layer-model.md](four-layer-model.md).

---

## Four Surfaces

| Surface | Entry Point | Character |
|---------|-------------|-----------|
| **REST API** | `api/routes/` | Thin CRUD wrappers consumed by the Next.js frontend |
| **Thinking Partner** | `api/agents/thinking_partner.py` | Conversational agent — Claude AgentSDK with primitives and working memory |
| **MCP Server** | `api/mcp_server/server.py` | Agent-to-Agent protocol — external LLMs access YARNNN data via 6 tools |
| **Unified Scheduler** | `api/jobs/unified_scheduler.py` | Cron-driven autonomous orchestration — signal processing, deliverable execution, memory extraction |

### TP is a surface, not the product

The Thinking Partner is a Claude AgentSDK wrapper customized with YARNNN-specific primitives (Search, Read, Execute, etc.) and working memory injection. It brings YARNNN's accumulated context to one specific Claude model instance.

This is architecturally equivalent to the MCP server: both are mechanisms for an LLM to access YARNNN's data. The difference is packaging — TP runs inside YARNNN's infrastructure with custom prompt engineering; MCP lets external LLMs bring their own.

For TP execution detail, see [agent-execution-model.md](agent-execution-model.md).

### MCP connectors are Agent-to-Agent communication

When Claude.ai calls YARNNN's `search_content` tool, it is one agent (Claude) delegating data retrieval to another agent (YARNNN) via the MCP protocol. The host LLM brings its own reasoning, its own context window, and its own conversation with the user. YARNNN provides the accumulated work context that the host LLM cannot access on its own.

This is fundamentally different from Slack or Gmail integration. Those are data sources flowing inward. MCP connectors are consumption interfaces flowing outward.

For MCP product rationale, see [MCP-CONNECTORS.md](../integrations/MCP-CONNECTORS.md). For technical implementation, see [ADR-075](../adr/ADR-075-mcp-connector-architecture.md).

### The scheduler is the autonomous surface

It is the only surface that creates new work without external stimulus — detecting behavioral signals, creating signal-emergent deliverables, executing scheduled workflows, and extracting memory. It runs on a 5-minute cron cycle.

---

## Two Tiers of Integration

YARNNN has two fundamentally different types of external connections:

**Inbound — Data Sources:**
Slack, Gmail, Notion, Calendar feed content INTO the platform via the sync worker. These are infrastructure. They populate `platform_content` with the raw material that makes everything else valuable. The user connects them once; the platform accumulates continuously.

**Outbound — Consumption Surfaces:**
TP, MCP, Scheduler, REST consume data FROM the platform. These are how value reaches the user or their tools. They are interchangeable — adding a new consumption surface (a Gemini connector, a Slack bot, a webhook) requires only wiring to existing service functions.

MCP connectors sit at the top of funnel. They are the lowest-friction path for a user to get value from YARNNN's accumulated context — no new app to learn, no new UI to navigate. The user stays in their existing LLM. YARNNN goes to where they already work.

---

## The Full-Stack as Proof of Concept

YARNNN builds the TP, the web UI, and the deliverable system even though the data platform is the moat. Why?

The full-stack is a **proof of concept** that the data platform works. It demonstrates end-to-end value: sync data → accumulate context → produce useful output. Without it, the platform is an invisible backend with no way to show users what accumulated context enables.

Deliverable execution must live in the platform because the raw data lives there. Workflows are bound to data residency — you can't run a cross-platform status report from an external tool that doesn't have access to all four platforms' accumulated content. This is why YARNNN is both a data layer for external agents (via MCP) AND the go-to place for recurring workflows.

The TP is the most accessible surface for new users — it requires zero external tooling. But it is not privileged architecturally. It consumes the same service layer as every other surface.

---

## Strategic Implications

1. **Platform improvements compound across all surfaces.** Better content accumulation, smarter signal processing, or richer memory extraction improves TP, MCP, and scheduler simultaneously. No surface-specific work needed.

2. **New surfaces are cheap to build.** Adding a consumption surface requires wiring to existing service functions — the 6 MCP tools were ~200 lines of code wrapping existing services. No new business logic.

3. **TP prompt engineering is one surface's optimization.** It matters for the YARNNN web experience but does not affect MCP consumers. The host LLM does its own reasoning.

4. **The moat deepens with tenure.** 90 days of accumulated context across four platforms is irreplaceable — regardless of which surface accesses it. This is true for TP users, MCP consumers, and autonomous scheduled workflows alike.
