# Render Services Infrastructure

> Backend infrastructure documentation for YARNNN services deployed on Render.

## Service Overview

| Service | Type | Runtime | Region | Schedule |
|---------|------|---------|--------|----------|
| yarnnn-api | Web Service | Python 3 (FastAPI) | Singapore | Always on |
| yarnnn-worker | Background Worker | Python 3 (RQ) | Singapore | Always on |
| yarnnn-unified-scheduler | Cron Job | Python 3 | Singapore | `*/5 * * * *` |
| yarnnn-mcp-gateway | Web Service | Node.js (Express) | Oregon | Always on |
| yarnnn-redis | Key-Value Store | Valkey 8 | Singapore | Always on |

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
│  ├── /api/integrations - Platform connections                     │
│  ├── /api/context      - User context & memories                  │
│  ├── /api/work         - Work tickets                             │
│  ├── /api/documents    - Document uploads                         │
│  ├── /api/domains      - Context domains                          │
│  ├── /api/account      - User account                             │
│  ├── /api/admin        - Admin endpoints                          │
│  ├── /api/skills       - Slash commands                           │
│  ├── /webhooks/slack   - Slack events                             │
│  └── /webhooks/lemon   - Billing webhooks                         │
└───────────────┬───────────────────────────────┬──────────────────┘
                │                               │
                ▼                               ▼
┌───────────────────────────┐     ┌─────────────────────────────────┐
│      yarnnn-redis         │     │      yarnnn-mcp-gateway         │
│    (Valkey 8 - Queue)     │     │    (MCP Protocol Adapter)       │
│                           │     │                                 │
│  Queue: "work"            │     │  Translates MCP calls to:       │
│  Used by: RQ worker       │     │  ├── Slack API                  │
│                           │     │  ├── Notion API                 │
└─────────────┬─────────────┘     │  ├── Gmail API                  │
              │                   │  └── Calendar API               │
              ▼                   └─────────────────────────────────┘
┌───────────────────────────┐
│      yarnnn-worker        │
│    (RQ Job Consumer)      │
│                           │
│  Processes:               │
│  ├── Work ticket exec     │
│  ├── Deliverable gen      │
│  └── Import jobs          │
└───────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│                   yarnnn-unified-scheduler                        │
│                      (Cron: every 5 min)                          │
│                                                                   │
│  Subsystems:                                                      │
│  ├── Deliverables  - Check & trigger due deliverables             │
│  ├── Work Tickets  - Check & trigger recurring work               │
│  ├── Digests       - Send weekly digests (hour boundary only)     │
│  ├── Import Jobs   - Process pending platform imports             │
│  └── Cleanup       - Expire ephemeral context (hour boundary)     │
└───────────────────────────────────────────────────────────────────┘
```

## Service Details

### yarnnn-api

**Purpose:** Core backend API serving all HTTP endpoints.

**Entry point:** `api/main.py`

**Key dependencies:**
- Supabase (database + auth)
- Anthropic API (Claude for TP)
- Resend (email delivery)

**Environment variables:**
```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
ANTHROPIC_API_KEY
RESEND_API_KEY
REDIS_URL (optional - graceful fallback if unavailable)
```

**Health check:** `GET /health`

---

### yarnnn-worker

**Purpose:** Background job processor using Redis Queue (RQ).

**Entry point:** `api/worker.py`

**Queue configuration:**
- Queue name: `work`
- Job timeout: 10 minutes
- Result TTL: 24 hours

**Job types processed:**
- `execute_work_ticket` - Run work ticket logic
- `generate_deliverable` - Generate deliverable content
- `process_import` - Process platform data imports

**Graceful degradation:** If Redis is unavailable (`REDIS_OPTIONAL=true`), jobs execute synchronously in the API process.

**Environment variables:**
```
REDIS_URL
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
ANTHROPIC_API_KEY
INTEGRATION_ENCRYPTION_KEY          # Required — decrypts OAuth tokens
GOOGLE_CLIENT_ID                    # Required — refreshes Google access tokens
GOOGLE_CLIENT_SECRET
NOTION_CLIENT_ID                    # Required — Notion API auth
NOTION_CLIENT_SECRET
```

> **Lesson learned (2026-02-23):** Worker was silently reporting `success=True` while syncing 0 items because `INTEGRATION_ENCRYPTION_KEY` was missing. The worker couldn't decrypt OAuth tokens but didn't raise — it just fetched nothing. Always ensure Worker has the same integration-related env vars as the API.

---

### yarnnn-unified-scheduler

**Purpose:** Consolidated cron job handling all scheduled tasks.

**Entry point:** `api/jobs/unified_scheduler.py`

**Schedule:** Every 5 minutes (`*/5 * * * *`)

**Subsystems:**

| Subsystem | Runs | Description |
|-----------|------|-------------|
| Deliverables | Every run | Check for due deliverables, enqueue generation |
| Work Tickets | Every run | Check for due recurring work, enqueue execution |
| Weekly Digests | Hour boundary | Send weekly activity digests to users |
| Import Jobs | Every run | Process pending platform import jobs |
| Cleanup | Hour boundary | Expire old ephemeral context records |
| Platform Sync | Every run | Check for users due for sync, enqueue to Worker |

**Logic flow:**
1. Initialize Supabase client with service role
2. Run deliverable checks → enqueue to Redis
3. Run work ticket checks → enqueue to Redis
4. If minute < 5: run digest processing
5. Run import job processing
6. If minute < 5: run cleanup tasks
7. Run platform sync checks → enqueue to Worker
8. Write per-user heartbeat to activity_log
9. Log summary stats

**Environment variables:**
```
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
REDIS_URL
RESEND_API_KEY
INTEGRATION_ENCRYPTION_KEY          # Same as Worker — needed for token checks
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
NOTION_CLIENT_ID
NOTION_CLIENT_SECRET
```

---

### yarnnn-redis

**Purpose:** Job queue backend for RQ worker.

**Runtime:** Valkey 8 (Redis-compatible)

**Plan:** Starter (25MB)

**Usage:**
- Primary: Job queue for background work
- No caching or session storage currently

**Connection:** Via `REDIS_URL` environment variable

## Environment Variable Parity

**Critical**: API, Worker, and Scheduler must share integration-related env vars. The API handles OAuth and stores encrypted tokens; the Worker decrypts and uses them for sync.

| Env Var | API | Worker | Scheduler |
|---------|-----|--------|-----------|
| `SUPABASE_URL` | Yes | Yes | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Yes | Yes |
| `ANTHROPIC_API_KEY` | Yes | Yes | No |
| `INTEGRATION_ENCRYPTION_KEY` | Yes | Yes | Yes |
| `GOOGLE_CLIENT_ID/SECRET` | Yes | Yes | Yes |
| `NOTION_CLIENT_ID/SECRET` | Yes | Yes | Yes |
| `REDIS_URL` | Yes | Yes | Yes |
| `RESEND_API_KEY` | Yes | No | Yes |

Use Render MCP tools to audit env vars across services when debugging sync failures.

---

## Deployment

### Automatic Deploys

All services deploy automatically on push to `main` branch via Render's GitHub integration.

### Manual Deploys

```bash
# Trigger deploy via Render API
curl -X POST "https://api.render.com/v1/services/{service_id}/deploys" \
  -H "Authorization: Bearer $RENDER_API_KEY"
```

### Rollback

Use Render dashboard to rollback to previous deploy.

## Monitoring

### Logs

Access via Render dashboard or CLI:
```bash
render logs --service yarnnn-api --tail
```

### Health Checks

| Service | Endpoint | Expected |
|---------|----------|----------|
| yarnnn-api | `GET /health` | `{"status": "ok"}` |
| yarnnn-mcp-gateway | `GET /health` | `{"status": "ok"}` |

### Key Metrics to Watch

- **API:** Response times, error rates
- **Worker:** Queue depth, job failure rate
- **Scheduler:** Successful runs, subsystem errors
- **Redis:** Memory usage, connection count

## Troubleshooting

### Worker not processing jobs

1. Check Redis connection: `redis-cli ping`
2. Check worker logs for errors
3. Verify `REDIS_URL` is set correctly
4. Check queue depth: `rq info --url $REDIS_URL`

### Scheduler not running

1. Check cron job logs in Render dashboard
2. Verify schedule is `*/5 * * * *`
3. Check for startup errors in logs

### MCP Gateway failures

1. Check platform API credentials are valid
2. Verify tokens haven't expired
3. Check rate limits on platform APIs

### Deliverables not generating

1. Check scheduler logs for errors
2. Verify deliverable is `status=active`
3. Check worker is processing jobs
4. Review `deliverable_versions` table for failed entries

## Related Documentation

- [ADR-017: Recurring Work Tickets](../adr/ADR-017-recurring-work-tickets.md)
- [ADR-018: Deliverables](../adr/ADR-018-deliverables.md)
- [ADR-031: Ephemeral Context](../adr/ADR-031-ephemeral-context.md)
- [ADR-050: MCP Gateway Architecture](../adr/ADR-050-mcp-gateway-architecture.md)
