# ADR-110: Onboarding Bootstrap

**Status:** Implemented (Phase 1 + Phase 2 + inline first-run: backend bootstrap + OAuth redirect + dashboard UX + immediate execution)
**Date:** 2026-03-13
**Supersedes:** None
**Related:** ADR-057 (Streamlined Onboarding), ADR-088 (Trigger Dispatch), ADR-109 (Agent Framework), ADR-111 (Agent Composer)

---

## Context

YARNNN's time-to-first-value is too long. After signup, the path to a user's first agent output is:

```
Signup → /dashboard → Connect platform (OAuth, ~30s) → /context page
  → manually select sources → wait for sync → navigate back
  → click template OR chat with TP → 2-3 chat turns → agent created
  → TP offers "generate first draft?" → user says yes → ~20s generation
```

**Best case: ~2-3 minutes.** Realistic: 5-10+ minutes. This is the difference between retention and churn.

Five friction points exist between signup and magic moment:

1. Post-OAuth redirect goes to `/context/{platform}`, not back to dashboard — breaks momentum
2. Source selection is manual and on a separate page — cognitive load
3. Agent creation requires 2-3 TP chat turns (Clarify loops) — unnecessary for obvious cases
4. No auto-creation based on connected platform — user must initiate everything
5. First draft requires explicit "yes" or waiting for scheduler — value delayed

## Decision

Implement a **deterministic bootstrap service** that fires on platform lifecycle events and auto-creates the matching digest agent. No LLM involved. Lookup table, not intelligence.

### Trigger Points

| Event | Action | Timing |
|-------|--------|--------|
| Platform connection + first source sync complete | Create matching digest agent | Inline in sync completion handler |
| All sources synced for a platform | Execute first run immediately | Inline after agent creation |

**Why "sync complete" not "OAuth complete":** An agent with no synced content produces an empty first run. Wait until at least one source has content, then fire.

### Template Mapping (Deterministic)

| Platform Connected | Agent Created | Scope | Skill | Trigger |
|-------------------|---------------|-------|-------|---------|
| Slack | Slack Recap | platform | digest | recurring |
| Gmail | Gmail Digest | platform | digest | recurring |
| Notion | Notion Summary | platform | digest | recurring |
| Calendar | *(none — Calendar feeds into Meeting Prep which requires multi-platform)* | — | — | — |

Calendar is excluded because a calendar-only recap has low value. Meeting Prep (the natural calendar agent) requires cross-platform context (Slack, Gmail) to be useful. This is a Composer-tier decision (ADR-111), not a bootstrap decision.

### Agent Defaults

- `origin`: `"system_bootstrap"` (new value, distinct from `user_configured` and `coordinator_created`)
- `schedule`: `{frequency: "daily", time: "09:00", timezone: <user's timezone or UTC>}`
- `sources`: ALL synced sources for that platform (matches existing digest command behavior)
- `status`: `"active"`
- `agent_instructions`: Platform-specific default from `DEFAULT_INSTRUCTIONS["digest"]`

### First Run Behavior

After bootstrap agent creation, immediately call `execute_agent_generation()` inline (same path as the Execute primitive's `agent.generate` action). The user sees their first output generating on the dashboard when they return from OAuth.

### Idempotency

- Before creating, check if a digest agent already exists for that platform (query `agents` where `skill=digest` and sources overlap). If yes, skip.
- Disconnect + reconnect does not re-create if agent still exists (even if paused).

### Tier Interaction

- Free tier: 2 agent limit. Bootstrap respects this. If user already has 2 agents, skip bootstrap creation. Don't silently fill their slots.
- If bootstrap would exceed limit, show a notification: "Connected Slack! You can create a Slack Recap from the dashboard."

### Post-OAuth Redirect

Change OAuth callback redirect from `/context/{platform}?status=connected` to `/dashboard?provider={platform}&status=connected&bootstrapped=true`. The dashboard detects `bootstrapped=true` and shows the generating agent inline rather than the template picker.

## Implementation

### Phase 1: Bootstrap Service (backend)

New file: `api/services/onboarding_bootstrap.py`

```python
async def maybe_bootstrap_agent(client, user_id: str, platform: str) -> Optional[str]:
    """
    Check conditions and create a bootstrap digest agent if appropriate.
    Returns agent_id if created, None if skipped.

    Conditions: no existing digest for this platform, under tier agent limit,
    at least one synced source with content.
    """
```

Call site: `platform_worker.py` after successful source sync, or `platform_sync_scheduler.py` after first sync cycle completes.

### Phase 2: Redirect + Dashboard UX (frontend)

- OAuth callback returns to `/dashboard` with bootstrap params
- Dashboard detects params, shows "Your Slack Recap is generating..." inline
- Template picker hides the template for the bootstrapped platform

### Phase 3: Bootstrap as Composer Bounded Context (ADR-111 revised)

Bootstrap is one of three bounded contexts within TP's Composer capability (ADR-111 revised 2026-03-16):

- **Bootstrap**: Deterministic, zero-LLM fast-path for highest-confidence agents (this ADR — preserved)
- **Heartbeat**: TP's periodic self-assessment of agent workforce health (new)
- **Composer**: The compositional judgment that creates/adjusts/dissolves agents (new)

Bootstrap is not "superseded" — it remains the fast-path for platform-connect events where the right agent is obvious. Composer extends coverage to non-obvious agent types (knowledge, cross-platform, research) and adds the Heartbeat cadence for ongoing assessment. The three contexts are architecturally cohesive but independently tier-gatable.

## Consequences

### Positive
- First value in <60 seconds post-connection (sync time + generation time)
- Zero chat turns required for first agent
- Deterministic — no LLM cost, no latency variability
- Clean `origin=system_bootstrap` provenance for analytics

### Negative
- May create an agent the user doesn't want (mitigated: they can delete/pause it)
- Fills a tier slot automatically (mitigated: tier check + notification)
- Calendar has no bootstrap path (deferred to Composer)
- Doesn't help users who upload files without connecting platforms (deferred to Composer)

### Neutral
- Bootstrap agents are identical to user-created agents after creation — same editing, same scheduling, same deletion
- `origin` field is the only differentiator

## References

- [ADR-057: Streamlined Onboarding](ADR-057-streamlined-onboarding.md)
- [ADR-088: Trigger Dispatch](ADR-088-trigger-dispatch.md)
- [ADR-109: Agent Framework](ADR-109-agent-framework.md)
- [ADR-111: Agent Composer](ADR-111-agent-composer.md)
