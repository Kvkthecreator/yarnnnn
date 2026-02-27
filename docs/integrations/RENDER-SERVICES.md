# Render Services Infrastructure

> Backend infrastructure documentation for YARNNN services deployed on Render.
> **Last updated**: 2026-02-27 (ADR-083: removed worker + Redis)

## Service Overview

| Service | Type | Runtime | Region | Schedule |
|---------|------|---------|--------|----------|
| yarnnn-api | Web Service | Python 3 (FastAPI) | Oregon | Always on |
| yarnnn-unified-scheduler | Cron Job | Python 3 | Singapore | `*/5 * * * *` |
| yarnnn-platform-sync | Cron Job | Python 3 | Singapore | `*/5 * * * *` |
| yarnnn-mcp-server | Web Service | Python 3 (FastAPI) | Oregon | Always on |

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
│  ├── /api/chat         - TP conversation                          │
│  ├── /api/deliverables - Recurring reports                        │
│  ├── /api/integrations - Platform connections + on-demand sync    │
│  ├── /api/context      - User context & memories                  │
│  ├── /api/work         - Work tickets (inline execution)          │
│  ├── /api/documents    - Document uploads                         │
│  ├── /api/account      - User account                             │
│  ├── /api/admin        - Admin endpoints                          │
│  ├── /webhooks/slack   - Slack events                             │
│  └── /webhooks/lemon   - Billing webhooks                         │
└──────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                   yarnnn-unified-scheduler                        │
│                      (Cron: every 5 min)                          │
│                                                                   │
│  Subsystems:                                                      │
│  ├── Deliverables  - Check & trigger due deliverables             │
│  ├── Work Tickets  - Check & trigger recurring work               │
│  ├── Signals       - Hourly signal processing (Starter+)          │
│  ├── Digests       - Send weekly digests (hour boundary only)     │
│  ├── Import Jobs   - Process pending platform imports             │
│  ├── Memory        - Nightly fact extraction                      │
│  └── Cleanup       - Expire ephemeral context (hour boundary)     │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                   yarnnn-platform-sync                             │
│                      (Cron: every 5 min)                          │
│                                                                   │
│  Checks tier-based schedules, dispatches sync_platform() inline   │
│  Free=2x/day, Starter=4x/day, Pro=hourly                         │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                    yarnnn-mcp-server                               │
│                   (FastAPI, ADR-075)                               │
│                                                                   │
│  Exposes YARNNN data to Claude.ai/Claude Desktop via MCP          │
│  Auth: OAuth 2.1 (auto-approve) + static bearer token fallback   │
└───────────────────────────────────────────────────────────────────┘
```

## Environment Variable Matrix

**Critical**: API and Schedulers must share integration-related env vars. The API handles OAuth and stores encrypted tokens; Schedulers decrypt and use them for sync.

| Env Var | API | Sync Cron | Unified Sched | MCP Server |
|---------|-----|-----------|---------------|------------|
| `SUPABASE_URL` | yes | yes | yes | yes |
| `SUPABASE_SERVICE_KEY` | yes | yes | yes | yes |
| `INTEGRATION_ENCRYPTION_KEY` | yes | yes | yes | — |
| `GOOGLE_CLIENT_ID/SECRET` | yes | yes | yes | — |
| `SLACK_CLIENT_ID/SECRET` | yes | yes | yes | — |
| `NOTION_CLIENT_ID/SECRET` | yes | yes | yes | — |
| `ANTHROPIC_API_KEY` | yes | — | yes | — |
| `RESEND_API_KEY` | yes | — | yes | — |
| `MCP_BEARER_TOKEN` | — | — | — | yes |
| `MCP_USER_ID` | — | — | — | yes |

## Deployment

All services deploy automatically on push to `main` branch via Render's GitHub integration.

## Health Checks

| Service | Endpoint | Expected |
|---------|----------|----------|
| yarnnn-api | `GET /health` | `{"status": "ok"}` |
| yarnnn-mcp-server | `GET /health` | `{"status": "ok"}` |

## Troubleshooting

### Scheduler not running
1. Check cron job logs in Render dashboard
2. Verify schedule is `*/5 * * * *`
3. Check for startup errors in logs

### Platform sync not working
1. Check `INTEGRATION_ENCRYPTION_KEY` is set on sync cron
2. Check OAuth client credentials match API service
3. Review `sync_registry.last_error` for per-source failures

### Deliverables not generating
1. Check unified-scheduler logs for errors
2. Verify deliverable is `status=active`
3. Review `deliverable_versions` table for failed entries

## Related Documentation

- [Backend Orchestration](../architecture/backend-orchestration.md) — canonical reference for all background features
- [ADR-083](../adr/ADR-083-remove-rq-worker.md) — decision to remove RQ/Redis worker
- [ADR-075](../adr/ADR-075-mcp-server.md) — MCP Server architecture
- [ADR-076](../adr/ADR-076-direct-api-consolidation.md) — decision to delete MCP Gateway
