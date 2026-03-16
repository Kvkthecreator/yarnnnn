# User Flow: Two-Path Onboarding (v4)

> **Status**: Current
> **Date**: 2026-03-16
> **Supersedes**: [Onboarding V3](archive/USER_FLOW_ONBOARDING_V2.md) (2026-02-26)
> **Related**: ADR-057 (Streamlined Onboarding), ADR-072 (Unified Content Layer), ADR-109 (Agent Framework), ADR-110 (Onboarding Bootstrap), ADR-111 (Agent Composer), [Supervision Dashboard](SUPERVISION-DASHBOARD.md), [Agent Presentation Principles](AGENT-PRESENTATION-PRINCIPLES.md)

---

## What Changed Since V3

V3 assumed a single path: connect platforms → select sources → accumulate context → use TP. This reflected the original product model where platform connections were the engine.

With ADR-111 (Agent Composer) and the Supervision Dashboard, YARNNN's model is now:

1. **Platforms are the onramp, not the engine.** They provide the fastest time-to-first-value (connect → auto-created agent → first delivery in minutes). But the long-term product is autonomous agents — not platform sync.

2. **The Orchestrator is always available.** Users can create agents for topics, research, or tasks without any platform connection. Platform-less agents (research, knowledge, task) are first-class.

3. **The dashboard is the landing page.** Users land on a supervision view, not a chat interface. The home page reflects "what's happening" rather than waiting for input.

These changes require a **two-path onboarding** design: platform connection as the default recommended path, and Orchestrator as the alternative for users who want topic/task-based work immediately.

---

## User Personas

| Type | Description | Optimal path |
|------|-------------|--------------|
| **Platform-first** | Has Slack/Gmail/Notion/Calendar; wants recurring summaries from existing work data | Connect platforms → auto-created agents → refine |
| **Topic-first** | Has a research question or monitoring need; doesn't need platform data | Ask Orchestrator → describe intent → agent created via chat |
| **Explorer** | Curious about AI agents; wants to see what's possible before committing | Browse dashboard → connect one platform → see first result |

---

## User Journey

```
OPEN  →  CHOOSE PATH  →  FIRST AGENT  →  FIRST DELIVERY  →  SUPERVISION
 │           │                │                │                │
 ▼           ▼                ▼                ▼                ▼
Dashboard   Platform CTA    Auto-created     Output in        Dashboard
empty       OR Orchestrator  (bootstrap)     inbox/channel    shows health
state       chat             OR chat-created  or in-app       + activity
```

---

## Stage 1: First Open (Dashboard Empty State)

### User state
- Authenticated via Supabase Auth
- No connected platforms
- No agents

### Experience

Dashboard shows a clean welcome with **two paths**:

```
┌──────────────────────────────────────────────────────┐
│              Welcome to YARNNN                       │
│                                                      │
│  Connect your work platforms and YARNNN will create  │
│  agents that deliver recurring insights.             │
│                                                      │
│  ┌─────────────┐  ┌─────────────┐                    │
│  │ [Slack]      │  │ [Gmail]      │                   │
│  │  Slack       │  │  Gmail       │                   │
│  ├─────────────┤  ├─────────────┤                    │
│  │ [Notion]     │  │ [Calendar]   │                   │
│  │  Notion      │  │  Calendar    │                   │
│  └─────────────┘  └─────────────┘                    │
│                                                      │
│  ──────────────── or ────────────────                │
│                                                      │
│  [💬] Ask the Orchestrator                           │
│       Create agents for topics, research, or tasks   │
│       — no platform needed                           │
└──────────────────────────────────────────────────────┘
```

### Design decisions

- **Platform cards are primary** because they lead to the fastest time-to-value (connect → auto-bootstrap → first delivery). Most users have at least one platform.
- **Orchestrator is secondary but visible** for topic-first users who don't want to commit platforms yet.
- **No "skip" button** — both paths are productive. There's no empty "I'll figure it out later" state.
- **No tier info at this stage** — don't frontload pricing before the user sees value.

---

## Stage 2a: Platform Path (Connect → Bootstrap → Supervise)

### Flow

1. **User clicks platform card** → OAuth redirect → returns to `/context/{platform}?status=connected`
2. **Source selection** on context page (unchanged from v3: landscape discovery, smart defaults, recommended grouping)
3. **Import prompt** → sources sync
4. **Onboarding Bootstrap** (ADR-110): post-sync, system auto-creates matching digest agent with `origin=system_bootstrap`
5. **First run** executes immediately → user sees first delivery
6. **User returns to Dashboard** → sees agent in health grid with status

### What the user sees after connecting

Dashboard transitions from empty state to **transitional state**:

```
┌──────────────────────────────────────────────────────┐
│              Dashboard                                │
│                                                      │
│  Your platforms are connected. Agents will appear     │
│  here once they're created.                          │
│                                                      │
│      [✓ slack]  [✓ gmail]                            │
│                                                      │
│  [🔌] Select sources to sync                         │
│       Choose channels, labels, or pages              │
│                                                      │
│  [💬] Ask the Orchestrator                           │
│       Create or configure agents through conversation │
└──────────────────────────────────────────────────────┘
```

This transitional state appears between platform connection and agent creation. Once onboarding bootstrap creates the first agent, the dashboard shows the full supervision view.

### Composer follow-up (ADR-111)

After bootstrap creates the initial agent, the Composer assesses the full substrate on the next heartbeat and may:
- Suggest additional agents (shown in Composer Activity feed)
- Auto-create high-confidence agents (with "Auto" badge)
- Surface these actions on the Dashboard's Composer Activity section

---

## Stage 2b: Orchestrator Path (Chat → Create → Supervise)

### Flow

1. **User clicks "Ask the Orchestrator"** → navigates to `/orchestrator`
2. **User describes intent** in natural language: "Track AI agent market developments weekly"
3. **TP infers** skill + scope + trigger from the prompt → creates agent via `CreateAgent` primitive
4. **Agent appears on Dashboard** → health grid shows the new agent
5. **First run** executes on schedule (or immediately if user requests)

### When to suggest platforms

If a user creates a platform-dependent agent via chat (e.g., "summarize my Slack channels") but has no platforms connected, TP should:
- Explain that the agent needs Slack access to read channels
- Offer to connect Slack (link to `/context/slack`)
- Create the agent in `paused` state pending platform connection

This is a natural conversation — not a modal or blocker.

---

## Stage 3: Supervision (Returning User)

### Dashboard states (progressive)

| State | Condition | Display |
|-------|-----------|---------|
| **Empty** | No platforms, no agents | Two-path welcome (platform cards + Orchestrator) |
| **Transitional** | Platforms connected, no agents | Connected platforms summary + source selection CTA + Orchestrator CTA |
| **Active** | 1+ agents | Full supervision dashboard (health grid, stats, Composer activity, attention) |

### What the active dashboard shows

See [SUPERVISION-DASHBOARD.md](SUPERVISION-DASHBOARD.md) for full specification:
- **Agent Health Grid**: maturity badges, edit trend arrows, approval rates, last run time
- **Summary Stats**: active agents, runs this week, maturity distribution
- **Composer Activity Feed**: auto-created agents, paused agents, observations
- **Attention Banners**: auto-paused agents, failed runs

### Origin labeling

All non-user-created agents show a single **"Auto"** badge regardless of internal origin (`system_bootstrap`, `composer`, `coordinator_created`). This keeps the UI clean — users don't need to know the internal mechanism that created an agent.

---

## Technical Components

### Frontend

| Component | Location | Purpose |
|-----------|----------|---------|
| Dashboard page | `web/app/(authenticated)/dashboard/page.tsx` | Empty state + transitional + supervision views |
| Orchestrator page | `web/app/(authenticated)/orchestrator/page.tsx` | TP chat (moved from /dashboard in v3) |
| Context pages | `web/app/(authenticated)/context/` | Platform connection + source selection (unchanged) |
| `PlatformIcons` | `web/components/ui/PlatformIcons.tsx` | Platform icon rendering |

### Backend

| Endpoint | Purpose |
|----------|---------|
| `GET /api/dashboard/summary` | Dashboard payload: agents, Composer actions, attention, connected platforms, stats |
| `GET /integrations/{provider}/landscape` | Discover resources + recommended flag |
| `PUT /integrations/{provider}/sources` | Save selected sources |
| `POST /integrations/{provider}/import` | Start foreground import |
| Onboarding bootstrap | Auto-creates digest agent post-sync (ADR-110) |
| Composer heartbeat | Assesses substrate, suggests/creates agents (ADR-111) |

### Data flow

```
Dashboard (empty state)
  ├─ Path A: Platform → OAuth → /context/{platform} → source selection
  │    → import → bootstrap → first agent + first run → dashboard (active)
  │    → Composer heartbeat → additional agents → dashboard updates
  │
  └─ Path B: Orchestrator → /orchestrator → chat → CreateAgent
       → agent created → dashboard (active) → first run on schedule
```

---

## Differences from V3

| Aspect | V3 | V4 |
|--------|----|----|
| Landing page | TP chat (`/dashboard`) | Supervision dashboard (`/dashboard`) |
| TP location | `/dashboard` | `/orchestrator` |
| Onboarding entry | Platform cards only | Two paths: platforms + Orchestrator |
| Empty state | PlatformSyncStatus component | Purpose-built welcome with two-path design |
| Post-connect | Return to TP chat | Return to context page → dashboard shows transitional state |
| Agent creation | User drives via TP chat | Auto (bootstrap/Composer) + manual (Orchestrator chat) |
| Agent visibility | Agent list page only | Dashboard health grid + agent list page |
| Origin display | Per-type labels (bootstrap, composer, etc.) | Unified "Auto" badge |

---

## Archived Components

These v3 components are no longer part of the primary onboarding flow:
- `PlatformSyncStatus` as dashboard landing — replaced by dashboard empty states
- Dashboard = TP chat assumption — dashboard is now supervision, TP is at `/orchestrator`

---

## References

- [Supervision Dashboard](SUPERVISION-DASHBOARD.md)
- [Agent Presentation Principles](AGENT-PRESENTATION-PRINCIPLES.md)
- [ADR-057: Streamlined Onboarding](../adr/ADR-057-streamlined-onboarding-gated-sync.md)
- [ADR-110: Onboarding Bootstrap](../adr/ADR-110-onboarding-bootstrap.md)
- [ADR-111: Agent Composer](../adr/ADR-111-agent-composer.md)
