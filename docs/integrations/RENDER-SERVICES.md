# Render Services Infrastructure

> Backend infrastructure documentation for YARNNN services deployed on Render.
> **Last updated**: 2026-03-17 (ADR-118: added output gateway)

## Service Overview

| Service | Type | Runtime | Region | Schedule | Render ID |
|---------|------|---------|--------|----------|-----------|
| yarnnn-api | Web Service | Python 3 (FastAPI) | Singapore | Always on | `srv-d5sqotcr85hc73dpkqdg` |
| yarnnn-unified-scheduler | Cron Job | Python 3 | Singapore | `*/5 * * * *` | `crn-d604uqili9vc73ankvag` |
| yarnnn-platform-sync | Cron Job | Python 3 | Singapore | `*/5 * * * *` | `crn-d6gdvi94tr6s73b6btm0` |
| yarnnn-mcp-server | Web Service | Python 3 (FastAPI) | Singapore | Always on | `srv-d6f4vg1drdic739nli4g` |
| yarnnn-render | Web Service | Docker (Python 3.11 + pandoc) | Singapore | Always on | `srv-d6sirjffte5s73f90pfg` |

**Removed services** (ADR-083, 2026-02-27):
- `yarnnn-worker` — RQ background worker (all execution now inline)
- `yarnnn-redis` — Valkey 8 key-value store (no longer needed)

**Previously removed** (ADR-076, 2026-02-25):
- `yarnnn-mcp-gateway` — Node.js MCP protocol adapter (replaced by Direct API clients)

## Architecture

```
                              ┌─────────────────┐
                              │    Frontend     │
                              │    (Vercel)     │
                              └────────┬────────┘
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                         yarnnn-api                                │
│                        (FastAPI)                                  │
│                                                                   │
│  Routers:                                                         │
│  ├── /api/chat         - Composer/TP conversation                 │
│  ├── /api/agents       - Agent CRUD + execution                   │
│  ├── /api/integrations - Platform connections + on-demand sync    │
│  ├── /api/context      - User context & memories                  │
│  ├── /api/documents    - Document uploads                         │
│  ├── /api/account      - User account                             │
│  ├── /api/admin        - Admin endpoints                          │
│  ├── /api/dashboard    - Supervision dashboard summary            │
│  ├── /webhooks/slack   - Slack events                             │
│  └── /webhooks/lemon   - Billing webhooks                         │
└──────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                   yarnnn-unified-scheduler                        │
│                      (Cron: every 5 min)                          │
│                                                                   │
│  Subsystems:                                                      │
│  ├── Agents        - Check & trigger due agent runs               │
│  ├── Composer      - Heartbeat assessment (ADR-111)               │
│  ├── Memory        - Nightly fact extraction + feedback distill   │
│  └── Cleanup       - Expire ephemeral context (hour boundary)     │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                   yarnnn-platform-sync                             │
│                      (Cron: every 5 min)                          │
│                                                                   │
│  Checks tier-based schedules, dispatches sync_platform() inline   │
│  Free=limited, Pro=hourly (ADR-100 2-tier model)                  │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                    yarnnn-mcp-server                               │
│                   (FastAPI, ADR-075)                               │
│                                                                   │
│  Exposes YARNNN data to Claude.ai/Claude Desktop via MCP          │
│  Auth: OAuth 2.1 (auto-approve) + static bearer token fallback   │
│  9 tools (ADR-116 Phase 4): get_agent_card, search_knowledge,    │
│  discover_agents, query_knowledge, + 5 more                       │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│               yarnnn-render (Output Gateway)                      │
│              (Docker, ADR-118 Phase B)                             │
│                                                                   │
│  Capability filesystem: render/skills/{name}/SKILL.md + scripts/  │
│  POST /render — skill registry routes to entry points             │
│  Skills: pptx, pdf, xlsx, chart (+ future: diagram, video, etc.) │
│  Supabase Storage upload for binary outputs                       │
└───────────────────────────────────────────────────────────────────┘
```

## Environment Variable Matrix

**Critical**: API and Schedulers must share integration-related env vars. The API handles OAuth and stores encrypted tokens; Schedulers decrypt and use them for sync.

| Env Var | API | Sync Cron | Unified Sched | MCP Server | Output Gateway |
|---------|-----|-----------|---------------|------------|----------------|
| `SUPABASE_URL` | yes | yes | yes | yes | yes |
| `SUPABASE_SERVICE_KEY` | yes | yes | yes | yes | yes |
| `INTEGRATION_ENCRYPTION_KEY` | yes | yes | yes | — | — |
| `GOOGLE_CLIENT_ID/SECRET` | yes | yes | yes | — | — |
| `SLACK_CLIENT_ID/SECRET` | yes | yes | yes | — | — |
| `NOTION_CLIENT_ID/SECRET` | yes | yes | yes | — | — |
| `ANTHROPIC_API_KEY` | yes | — | yes | — | — |
| `RESEND_API_KEY` | yes | — | yes | — | — |
| `MCP_BEARER_TOKEN` | — | — | — | yes | — |
| `MCP_USER_ID` | — | — | — | yes | — |
| `RENDER_SERVICE_URL` | yes | — | yes | — | — |

**Common mistake**: Adding an env var to the API service but forgetting Schedulers. The API handles OAuth and stores tokens; Schedulers decrypt and use them for sync. The output gateway only needs Supabase credentials for storage uploads.

## Deployment

All services deploy automatically on push to `main` branch via Render's GitHub integration.

## Health Checks

| Service | Endpoint | Expected |
|---------|----------|----------|
| yarnnn-api | `GET /health` | `{"status": "ok"}` |
| yarnnn-mcp-server | `GET /health` | `{"status": "ok"}` |
| yarnnn-render | `GET /health` | `{"status": "ok"}` |

## Troubleshooting

### Scheduler not running
1. Check cron job logs in Render dashboard
2. Verify schedule is `*/5 * * * *`
3. Check for startup errors in logs

### Platform sync not working
1. Check `INTEGRATION_ENCRYPTION_KEY` is set on sync cron
2. Check OAuth client credentials match API service
3. Review `sync_registry.last_error` for per-source failures

### Agents not generating
1. Check unified-scheduler logs for errors
2. Verify agent is `status=active`
3. Review `agent_runs` table for failed entries

### Output gateway not rendering
1. Check `RENDER_SERVICE_URL` is set on API + unified-scheduler
2. Check yarnnn-render service is running (health check)
3. Check `SUPABASE_SERVICE_KEY` is set on yarnnn-render for storage uploads
4. Review workspace_files for missing `content_url` (indicates upload failure)

## Related Documentation

- [Backend Orchestration](../architecture/backend-orchestration.md) — canonical reference for all background features
- [ADR-083](../adr/ADR-083-remove-rq-worker.md) — decision to remove RQ/Redis worker
- [ADR-075](../adr/ADR-075-mcp-connector-architecture.md) — MCP Server architecture
- [ADR-076](../adr/ADR-076-eliminate-mcp-gateway.md) — decision to delete MCP Gateway
- [ADR-118](../adr/ADR-118-skills-as-capability-layer.md) — output gateway + skills as capability layer
