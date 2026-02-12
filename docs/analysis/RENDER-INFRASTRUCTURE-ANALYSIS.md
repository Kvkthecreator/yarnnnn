# Render Infrastructure Analysis

**Date:** 2026-02-12
**Status:** Draft - pending review

## Current Services

| Service | Runtime | Region | Purpose | Status |
|---------|---------|--------|---------|--------|
| yarnnn-api | Python 3 | Singapore | Core FastAPI backend | Required |
| yarnnn-mcp-gateway | Node.js | Oregon | MCP protocol translator for platforms | Required |
| yarnnn-worker | Python 3 | Singapore | RQ job queue consumer | Required |
| yarnnn-unified-scheduler | Python 3 | Singapore | Consolidated cron (every 5 min) | Required |
| yarnnn-digest-scheduler | Python 3 | Singapore | Legacy digest processor | **Redundant** |
| yarnnn-redis | Valkey 8 | Singapore | Job queue backend | Required |

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  YARNNN v5 Service Architecture                             │
└─────────────────────────────────────────────────────────────┘

                         ┌──────────────┐
                         │   Frontend   │
                         │   (Vercel)   │
                         └──────┬───────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────┐
│                      yarnnn-api                            │
│                     (FastAPI + 12 routers)                 │
│  /api/chat, /api/deliverables, /api/integrations, etc.    │
└────────────────┬─────────────────────┬────────────────────┘
                 │                     │
                 ▼                     ▼
        ┌────────────────┐    ┌────────────────────┐
        │  yarnnn-redis  │    │ yarnnn-mcp-gateway │
        │   (Job Queue)  │    │  (Slack/Notion)    │
        └───────┬────────┘    └────────────────────┘
                │
       ┌────────┴────────┐
       ▼                 ▼
┌─────────────┐  ┌───────────────────────┐
│   worker    │  │  unified-scheduler    │
│ (RQ jobs)   │  │  (cron: */5 min)      │
└─────────────┘  └───────────────────────┘
```

## Service Details

### yarnnn-api (Required)

The core FastAPI backend serving all API endpoints:
- `/api/chat` - TP conversation handling
- `/api/deliverables` - Recurring report management
- `/api/integrations` - Platform connections (Slack, Gmail, Notion)
- `/api/context` - User context and memories
- `/api/work` - Work ticket management
- `/webhooks` - Slack events, Lemon Squeezy billing

### yarnnn-mcp-gateway (Required)

Node.js Express server implementing Model Context Protocol (MCP) for platform integrations (ADR-050). Acts as a translation layer between yarnnn and external platforms.

**Why separate from API:**
- Different runtime (Node.js vs Python)
- MCP protocol requires specific tooling
- Isolates platform-specific failures from core API

### yarnnn-worker (Required)

Redis Queue (RQ) worker that processes background jobs:
- Work ticket execution
- Async deliverable generation
- Import job processing

Configuration:
- Queue: `work`
- Timeout: 10 minutes per job
- Result TTL: 24 hours

### yarnnn-unified-scheduler (Required)

Consolidated cron job running every 5 minutes. Handles all scheduled tasks:

| Subsystem | Purpose | Timing |
|-----------|---------|--------|
| Deliverables | Generate recurring reports (ADR-018) | Every 5 min check |
| Work Tickets | Execute recurring work (ADR-017) | Every 5 min check |
| Weekly Digests | Send user activity summaries | Hour boundaries only |
| Import Jobs | Process platform data imports | Every 5 min check |
| Cleanup | Expire ephemeral context (ADR-031) | Hour boundaries only |

Source: `api/jobs/unified_scheduler.py`

### yarnnn-redis (Required)

Valkey 8 instance (Redis-compatible) used for:
- Job queue backend for RQ worker
- No caching or session storage currently

Plan: Starter (25MB) - sufficient for current queue depth.

### yarnnn-digest-scheduler (Redundant)

**Recommendation: Remove**

This is a legacy service from before the scheduler consolidation. All digest processing is now handled by `unified_scheduler.py` (lines 554-629).

Git history confirms migration: commit `7051e82` "Delete legacy work_scheduler, use unified_scheduler"

## Findings

### Issue 1: Redundant Scheduler

Two cron services are running for digest processing:
1. `yarnnn-unified-scheduler` - handles digests as part of consolidated scheduler
2. `yarnnn-digest-scheduler` - legacy standalone digest processor

**Impact:** Unnecessary cost (~$5/month) and potential duplicate processing.

**Resolution:** Remove `yarnnn-digest-scheduler` from Render dashboard.

### Issue 2: Region Mismatch

MCP Gateway is in Oregon while all other services are in Singapore. This adds latency for API-to-gateway calls.

**Recommendation:** Consider moving MCP Gateway to Singapore for consistency, unless there's a specific reason for Oregon (e.g., closer to Slack/Notion servers).

## Cost Optimization

| Action | Monthly Savings |
|--------|-----------------|
| Remove digest-scheduler | ~$5 |
| **Total** | ~$5/month |

## Service Necessity Matrix

| Service | Necessary | Can Consolidate? | Notes |
|---------|-----------|------------------|-------|
| yarnnn-api | Yes | No | Core backend |
| yarnnn-mcp-gateway | Yes | Maybe* | Could embed in API but requires Node→Python refactor |
| yarnnn-worker | Yes | Maybe* | Could use push model but significant refactor |
| yarnnn-unified-scheduler | Yes | No | Already consolidated |
| yarnnn-digest-scheduler | **No** | N/A | Remove - functionality in unified-scheduler |
| yarnnn-redis | Yes | No | Required for job queue |

*Future optimization opportunities, not recommended now.

## Action Items

- [ ] Remove `yarnnn-digest-scheduler` from Render dashboard
- [ ] Verify no duplicate digest emails after removal
- [ ] Consider moving MCP Gateway to Singapore region
- [ ] Monitor Redis queue depth over next month

## References

- ADR-017: Recurring Work Tickets
- ADR-018: Deliverables
- ADR-031: Ephemeral Context
- ADR-039: Platform Integrations
- ADR-050: MCP Gateway Architecture
