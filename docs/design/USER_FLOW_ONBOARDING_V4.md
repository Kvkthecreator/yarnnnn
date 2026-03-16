# User Flow: Two-Path Onboarding (v5)

> **Status**: Current
> **Date**: 2026-03-16
> **Supersedes**: [Onboarding V4](archive/) (2026-03-16), [Onboarding V3](archive/USER_FLOW_ONBOARDING_V2.md) (2026-02-26)
> **Related**: ADR-057 (Streamlined Onboarding), ADR-072 (Unified Content Layer), ADR-109 (Agent Framework), ADR-110 (Onboarding Bootstrap), ADR-111 (Agent Composer), ADR-113 (Auto Source Selection), [Supervision Dashboard](SUPERVISION-DASHBOARD.md), [Agent Presentation Principles](AGENT-PRESENTATION-PRINCIPLES.md)

---

## What Changed Since V4

V4 required manual source selection as a prerequisite after platform connection: OAuth → context page → pick sources → sync → bootstrap. This created friction at the moment of highest user intent.

With ADR-113 (Auto Source Selection), the flow is now:

1. **Sources are auto-selected at connection time.** `compute_smart_defaults()` picks the highest-signal sources (busiest Slack channels, INBOX/SENT for Gmail, recently-edited Notion pages, all calendars) up to tier limits.

2. **Sync starts immediately.** No manual step between connecting and syncing. The OAuth callback discovers landscape, applies defaults, and kicks off the first sync as a background task.

3. **Users land on the dashboard, not a context page.** Post-OAuth redirect goes to `/dashboard` where users see their platform connected and syncing. Source curation is optional refinement, not a gate.

4. **Context pages are for refinement, not setup.** Users can still add/remove sources at any time from `/context/{platform}`, but this is an escape hatch — not the first-time entry point.

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
OPEN  →  CONNECT  →  AUTO-SYNC  →  FIRST AGENT  →  FIRST DELIVERY  →  SUPERVISION
 │          │           │              │                │                │
 ▼          ▼           ▼              ▼                ▼                ▼
Dashboard  OAuth      Smart defaults  Bootstrap        Output in        Dashboard
empty      (direct)   + background    (automatic)      inbox/channel    shows health
state                 sync starts                      or in-app        + activity
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
│  │ [Slack]      │  │ [Gmail]      │  ← OAuth direct  │
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

- **Platform cards trigger OAuth directly** (ADR-113). No intermediate context page. One click starts the entire flow.
- **Orchestrator is secondary but visible** for topic-first users who don't want to commit platforms yet.
- **No "skip" button** — both paths are productive. There's no empty "I'll figure it out later" state.
- **No tier info at this stage** — don't frontload pricing before the user sees value.

---

## Stage 2a: Platform Path (Connect → Auto-Sync → Bootstrap → Supervise)

### Flow

1. **User clicks platform card** → OAuth redirect → callback auto-discovers landscape + auto-selects sources (ADR-113) → kicks off first sync → redirects to `/dashboard?provider={platform}&status=connected`
2. **Dashboard shows transitional state**: platform connected, sync in progress, "agents will appear automatically"
3. **Onboarding Bootstrap** (ADR-110): post-sync, system auto-creates matching digest agent with `origin=system_bootstrap`
4. **First run** executes immediately → user sees first delivery
5. **Dashboard transitions to active state** → agent appears in health grid

### What the user sees after connecting

Dashboard transitions from empty state to **transitional state**:

```
┌──────────────────────────────────────────────────────┐
│              Dashboard                                │
│                                                      │
│  Your platforms are syncing. Agents will appear      │
│  here automatically.                                 │
│                                                      │
│      [✓ slack]  [✓ gmail]                            │
│                                                      │
│  ┌ Connect more platforms ─────────────────────────┐ │
│  │  [notion]  [calendar]                           │ │
│  └─────────────────────────────────────────────────┘ │
│                                                      │
│  [+] Customize synced sources                        │
│      Add or remove specific channels, labels, pages  │
│                                                      │
│  [💬] Ask the Orchestrator                           │
│       Create or configure agents through conversation │
└──────────────────────────────────────────────────────┘
```

### Key differences from V4

- **No source selection step.** Sources auto-selected by `compute_smart_defaults()` at OAuth callback time.
- **User lands on dashboard**, not context page. They see progress, not a form.
- **"Customize synced sources"** is an optional refinement link, not a prerequisite CTA.
- **"Connect more platforms"** is surfaced directly in the transitional state.

### Source curation (optional)

Users who want to change which sources are synced can visit `/context/{platform}` at any time. The context page shows auto-selected sources with checkboxes to add/remove. This is the same UI as before — just no longer the first-time entry point.

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
| **Empty** | No platforms, no agents | Two-path welcome (platform OAuth cards + Orchestrator) |
| **Transitional** | Platforms connected, no agents | Connected platforms + syncing message + connect more + customize sources (optional) |
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
| Context pages | `web/app/(authenticated)/context/` | Source refinement (no longer first-time entry point) |
| `PlatformIcons` | `web/components/ui/PlatformIcons.tsx` | Platform icon rendering |

### Backend

| Endpoint | Purpose |
|----------|---------|
| `GET /api/dashboard/summary` | Dashboard payload: agents, Composer actions, attention, connected platforms, stats |
| `GET /integrations/{provider}/callback` | OAuth callback: stores tokens + auto-discovers landscape + auto-selects sources + kicks off sync (ADR-113) |
| `GET /integrations/{provider}/landscape` | Discover resources + recommended flag (also auto-selects if no prior selection) |
| `PUT /integrations/{provider}/sources` | Save selected sources (for manual refinement) |
| `POST /integrations/{provider}/sync` | Trigger on-demand sync |
| Onboarding bootstrap | Auto-creates digest agent post-sync (ADR-110) |
| Composer heartbeat | Assesses substrate, suggests/creates agents (ADR-111) |

### Data flow

```
Dashboard (empty state)
  ├─ Path A: Platform → OAuth → callback auto-discovers + auto-selects + starts sync
  │    → /dashboard (transitional) → sync completes → bootstrap → first agent + first run
  │    → dashboard (active) → Composer heartbeat → additional agents
  │
  └─ Path B: Orchestrator → /orchestrator → chat → CreateAgent
       → agent created → dashboard (active) → first run on schedule
```

---

## Differences from V4

| Aspect | V4 | V5 (ADR-113) |
|--------|----|----|
| Post-OAuth redirect | `/context/{platform}` → manual source selection | `/dashboard` → see progress |
| Source selection | Prerequisite (manual) | Auto (smart defaults), manual = optional refinement |
| First sync trigger | After user saves source selection | Immediately at OAuth callback |
| Dashboard platform cards | Navigate to context page | Trigger OAuth directly |
| Transitional state CTA | "Select sources to sync" | "Customize synced sources" (optional) |
| Time-to-first-sync | User-dependent (requires manual action) | Seconds after OAuth callback |

---

## References

- [Supervision Dashboard](SUPERVISION-DASHBOARD.md)
- [Agent Presentation Principles](AGENT-PRESENTATION-PRINCIPLES.md)
- [ADR-057: Streamlined Onboarding](../adr/ADR-057-streamlined-onboarding-gated-sync.md)
- [ADR-110: Onboarding Bootstrap](../adr/ADR-110-onboarding-bootstrap.md)
- [ADR-111: Agent Composer](../adr/ADR-111-agent-composer.md)
- [ADR-113: Auto Source Selection](../adr/ADR-113-auto-source-selection.md)
