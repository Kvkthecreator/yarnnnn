# Supervision Dashboard — Route Restructure & Autonomous Surfacing

**Date:** 2026-03-16
**Status:** Archived — Phases 1-3 implementation was superseded by successive ADRs. Composer (ADR-111) deleted by ADR-156. ADR-092 five-mode taxonomy dissolved into pulse model (ADR-126) then invocation model (ADR-231). `/activity` page deleted by ADR-163. Current activity surfacing: workspace events in Chat briefing, per-task in /work, per-agent in /agents. Retained as design-intent record.
**Related:**
- [Agent Presentation Principles](AGENT-PRESENTATION-PRINCIPLES.md) — source-first mental model, grouping
- [Surface-Action Mapping](SURFACE-ACTION-MAPPING.md) — directive vs configuration surfaces
- [ADR-111: Agent Composer](../adr/ADR-111-agent-composer.md) — lifecycle progression, maturity signals
- [ADR-092: Agent Intelligence & Mode Taxonomy](../adr/ADR-092-agent-intelligence-mode-taxonomy.md) — five agent modes
- [FOUNDATIONS.md](../FOUNDATIONS.md) — two-layer intelligence model

---

## Problem

YARNNN's current route structure places the TP chat at `/dashboard` (the landing page) and the agent list at `/agents`. This reflected the original product model: users converse with TP, who creates and directs agents on their behalf.

With ADR-111 (Agent Composer), agents now have autonomous lifecycle:
- **Composer** auto-creates agents from substrate assessment
- **Heartbeat** monitors agent health on every scheduler tick
- **Lifecycle progression** pauses underperformers, suggests expansions, detects cross-agent patterns
- **Maturity signals** classify agents as nascent / developing / mature

None of this work requires user input — it happens in the background. But the user has no ambient awareness of what the system is doing. The landing page waits for the user to type, while meaningful autonomous work goes unseen.

---

## Design Principle

**The home page should reflect what's happening, not wait for input.**

As YARNNN's autonomy matures, the user's role shifts from **directing** to **supervising**. The landing page should answer: "What has my system done, and does anything need my attention?"

This aligns with FOUNDATIONS.md's two-layer model:
- **TP (meta-cognitive layer)** → the Orchestrator, a tool for directing
- **Agents (domain-cognitive layer)** → autonomous workers producing outputs

The supervision dashboard is the meta-cognitive *view* — the same layer TP operates on, rendered as a surface instead of a conversation.

---

## Route Restructure

### Current → Proposed

| Current route | Current purpose | Proposed route | Proposed purpose |
|---------------|----------------|----------------|------------------|
| `/dashboard` | TP chat (landing page) | `/dashboard` | **Supervision dashboard** (landing page) |
| `/agents` | Agent list + detail | `/agents` | Agent list + detail (unchanged) |
| — | — | `/orchestrator` | **TP chat** (moved from /dashboard) |

### Why `/orchestrator` not `/chat` or `/tp`

- **Industry alignment**: "Orchestrator" is the standard term for a meta-cognitive agent that directs other agents (A2A, AutoGen, CrewAI). "Thinking Partner" is YARNNN-specific branding — valuable in marketing, but the route should use the technical term.
- **Future-proof**: If YARNNN supports multiple orchestrators or A2A protocols, `/orchestrator` generalizes cleanly. `/chat` is too generic (agents may have chat interfaces too). `/tp` is opaque.
- **Internal consistency**: ADR-092 and CLAUDE.md already use "Orchestrator / TP" as the canonical reference.

### Navigation

- **Sidebar**: "Dashboard" (home icon) + "Orchestrator" (message icon) + "Agents" + "Context" + "Activity"
- **Quick-access**: Dashboard includes a prominent "Ask Orchestrator" entry point (button or input) that navigates to `/orchestrator`
- **Deep links**: `/orchestrator?agent_id=X` opens Orchestrator scoped to a specific agent (existing behavior, new route)

---

## Dashboard: What It Shows

The supervision dashboard answers three questions:

### 1. "What's happening?" — Agent Health Grid

A compact grid of all active agents, showing at-a-glance health:

```
┌─────────────────────────────────────────────────────┐
│  [Slack] Weekly Recap          ● Mature   ✓ 2h ago  │
│  [Gmail] Email Digest          ● Developing  ✓ 1d  │
│  [Notion] Project Tracker      ○ Paused    ⚠ auto   │
│  [🌐] Market Research          ● Nascent   ✓ 3d ago │
└─────────────────────────────────────────────────────┘
```

| Element | Source | Notes |
|---------|--------|-------|
| Platform icon | `sources[].provider` | Same as agent cards (Principle 1) |
| Title | `agent.title` | |
| Maturity indicator | Computed from run count + approval rate | nascent / developing / mature |
| Last delivery | `agent.last_run_at` | Relative time |
| Auto-paused flag | `status === 'paused'` + origin context | Distinguishes manual vs auto-pause |

Clicking an agent navigates to `/agents/[id]`.

### 2. "What did the system do?" — Composer Activity Feed

Recent autonomous actions, reverse-chronological:

```
┌─────────────────────────────────────────────────────┐
│  ✨ Created "Cross-Platform Weekly"                  │
│     Composer detected 3 mature platform digests      │
│     12 hours ago                                     │
│                                                      │
│  ⏸  Paused "Daily Standup Notes"                    │
│     8 runs, 25% approval — below threshold           │
│     1 day ago                                        │
│                                                      │
│  💡 Suggestion: Track #design-system channel         │
│     New active channel detected in Slack landscape   │
│     2 days ago                                       │
└─────────────────────────────────────────────────────┘
```

Data sources:
- `activity_log` where `event_type = 'composer_heartbeat'` — lifecycle actions stored in metadata
- `agents` where `origin = 'composer'` — auto-created agents
- Future: `agent_suggestions` table for pending suggestions (not yet implemented)

### 3. "Does anything need attention?" — Attention Banner

A dismissible banner at the top when something warrants user review:

- Agent auto-paused (user should review or archive)
- Composer suggestion pending (user should approve/dismiss)
- Agent with declining edit trend (convergence stalling)
- Failed runs requiring investigation

This is intentionally minimal — 0-2 items at most. The dashboard should feel calm when things are healthy.

### Summary Stats (Optional, Low Priority)

Compact row of counts:
- Active agents / Total
- Runs this week
- Average approval rate
- Mature / Developing / Nascent distribution

---

## What the Dashboard Does NOT Show

- **Full agent management** — that stays at `/agents`. Dashboard links into it.
- **Agent output/content** — that's in the agent detail view's Runs tab.
- **Platform sync status** — that stays at `/context`. Dashboard doesn't duplicate sync health.
- **Full activity history** — that stays at `/activity`. Dashboard shows only Composer-specific actions.

---

## Data Requirements

### New API Endpoint: `GET /api/dashboard/summary`

Returns the supervision dashboard payload in a single call:

```typescript
interface DashboardSummary {
  agents: {
    id: string;
    title: string;
    status: AgentStatus;
    origin: string;
    role: string;
    sources: Source[];
    last_run_at: string | null;
    maturity: 'nascent' | 'developing' | 'mature';
    approval_rate: number | null;
    edit_trend: number | null;  // negative = improving
  }[];
  composer_actions: {
    type: 'created' | 'paused' | 'suggestion' | 'observation';
    summary: string;
    agent_id?: string;
    agent_title?: string;
    created_at: string;
    metadata: Record<string, unknown>;
  }[];
  attention: {
    type: 'auto_paused' | 'suggestion' | 'declining' | 'failed';
    message: string;
    agent_id: string;
    agent_title: string;
  }[];
  stats: {
    total_agents: number;
    active_agents: number;
    runs_this_week: number;
    maturity_distribution: { nascent: number; developing: number; mature: number };
  };
}
```

This endpoint reuses `heartbeat_data_query()` logic from `composer.py` — the maturity signals are already computed there. The dashboard endpoint surfaces the same data the Composer uses internally.

### No New Tables

All data is already in existing tables:
- `agents` — health, status, origin, maturity (computed from agent_runs)
- `agent_runs` — approval rate, edit trend
- `activity_log` — Composer heartbeat events with lifecycle metadata

---

## Interaction with Existing Surfaces

### Orchestrator (`/orchestrator`, was `/dashboard`)

Unchanged functionally. Same TP chat with full primitive access. The route moves and the sidebar label changes from "Dashboard" to "Orchestrator."

The Orchestrator page retains its agent-scoped mode: when accessed from an agent detail page, the chat is scoped to that agent.

### Agent List (`/agents`)

Unchanged. Source-affinity grouping, agent cards with platform icons, detail view with tabs. The dashboard links into this for full management.

One small addition: agent cards could show a maturity dot (matching the dashboard) for consistency. This is optional — the agent list already shows status (active/paused) and delivery status.

### Activity (`/activity`)

Already updated — `composer_heartbeat` and `agent_bootstrapped` events now render with proper icons and origin badges. The dashboard's Composer activity feed is a filtered subset of what `/activity` shows.

---

## Naming: "Thinking Partner" vs "Orchestrator"

| Context | Use "Thinking Partner" | Use "Orchestrator" |
|---------|------------------------|-------------------|
| Marketing / landing page | Yes — it's the brand differentiator | No |
| In-app route / sidebar | No | Yes — `/orchestrator` |
| CLAUDE.md / ADRs | Keep dual reference: "Orchestrator / TP" | Continue using both |
| User-facing tooltip | "Your Orchestrator (Thinking Partner)" | Transition gradually |
| API routes | No change needed (`/chat` stays `/chat`) | Internal naming only |

The rename is cosmetic in the UI layer — no backend changes. The TP system prompt, primitives, and API routes continue using their current names.

---

## Implementation Phases

### Phase 1: Route Restructure (Minimal) -- IMPLEMENTED
- [x] Move TP chat from `/dashboard` to `/orchestrator`
- [x] Update sidebar navigation (Dashboard + Orchestrator + Agents primary)
- [x] Update all internal links (5 hardcoded refs + OAuth default)
- [x] Add `/orchestrator` to middleware protected routes + robots.txt
- [x] Update ADR-110 test assertions for new OAuth redirect path

### Phase 2: Dashboard MVP -- IMPLEMENTED
- [x] `GET /api/dashboard/summary` endpoint (maturity, Composer actions, attention, stats)
- [x] Agent health grid (status dot, maturity badge, edit trend, approval rate)
- [x] Composer activity feed (lifecycle actions + bootstraps from activity_log)
- [x] "Ask Orchestrator" quick-access button
- [x] Summary stats row (active agents, runs/week, maturity distribution)

### Phase 3: Attention System -- IMPLEMENTED
- [x] Attention banner for auto-paused agents
- [x] Attention banner for recently failed runs
- [x] Deep links to agent detail pages from all items

### Phase 4: Refinement (Future)
- [ ] Dismissible attention items (localStorage or user preferences)
- [ ] Maturity trend sparklines (if data warrants)
- [ ] Customizable dashboard layout (user can hide sections)

---

## Open Questions

1. **Should the dashboard be the default landing page immediately, or should we A/B test?** Users accustomed to chat-first might find the change jarring. A feature flag could help.

2. **Should Orchestrator keep the sidebar chat panel on the agents page?** Currently the TP chat appears as a slide-over panel from agent detail. If Orchestrator gets its own route, should the panel remain as a quick-access mode?

3. **How prominent should maturity indicators be?** Nascent/developing/mature is meaningful for power users but might confuse new users with 1-2 agents. Progressive disclosure (show maturity only after N agents or M total runs) could help.

4. **Should Composer suggestions be interactive on the dashboard?** E.g., "Approve" / "Dismiss" buttons inline, vs. navigating to agent detail. Inline actions are faster but add complexity.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-16 | Initial proposal — route restructure, supervision dashboard, Orchestrator rename |
| 2026-03-16 | Implemented Phases 1-3: route restructure, dashboard MVP, attention system |
