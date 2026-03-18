# Agent Presentation Principles

**Date:** 2026-03-13
**Status:** Active
**Related:**
- [Agent Framework: Scope × Role × Trigger](../architecture/agent-framework.md) — backend taxonomy
- [Surface-Action Mapping](SURFACE-ACTION-MAPPING.md) — directive vs configuration surfaces
- [Workspace Layout & Navigation](WORKSPACE-LAYOUT-NAVIGATION.md) — layout structure
- [ADR-105: Instructions to Chat Surface](../adr/ADR-105-instructions-chat-surface-migration.md) — chat-first creation

---

## Core Insight

The backend taxonomy (Scope × Role × Trigger) is an execution framework — it answers how the system builds and runs agents. The frontend must answer a different question: **how does a user think about, find, and manage their agents?**

Users don't think in skills or scopes. They think:

- "What's happening on Slack?" — **source-first**
- "Am I prepared for tomorrow?" — **job-first**
- "What's that thing that emails me on Mondays?" — **routine-first**

The agent's identity in the user's mind is formed by the intersection of **what it watches** (platform/sources) and **what it produces** (output on a cadence). Not the role taxonomy.

---

## Principle 1: Source-First Mental Model

**The user's primary cognitive anchor for an agent is where it reads, not what role it uses.**

A user with 3 Slack agents thinks "my Slack stuff" — not "my digest, my monitor, and my synthesizer." The platform/source is the stable anchor; the role is a behavioral detail.

This means:

- **Grouping**: When the agent list grows, group by source affinity (platform icons), not by role
- **Creation**: Start with "what do you want to stay on top of?" (source selection), then "how should I help?" (role selection contextual to the sources)
- **Visual identity**: Platform icons are the primary visual signal on agent cards, not role badges

### Source affinity tiers

| Tier | Visual | Meaning |
|------|--------|---------|
| Single platform | Platform icon (Slack, Gmail, Notion, Calendar) | Reads from one platform |
| Multi-platform | Stacked/overlapping platform icons | Reads from 2+ connected platforms |
| Knowledge | Brain/library icon | Reads from accumulated knowledge, no live platform |
| Web/Research | Globe icon | Primarily web-driven, no platform sources |

These tiers map cleanly to scope, but the user sees icons, not scope labels.

### Why not role-first?

Roles describe *what the agent does* with information — but users don't primarily categorize by processing verb. Consider: you don't think of your email inbox as "a digest role applied to Gmail." You think "my email." The processing (summarize, alert, prep) is secondary to the source.

Exception: the `research` role with no platform sources. Here the job-to-be-done *is* the identity, because there's no platform anchor. Research agents are source-less — their identity comes from the topic/instructions.

---

## Principle 2: Progressive Disclosure Over Exhaustive Selection

**Show users what's natural for their setup. Don't enumerate every possible agent type.**

The current 8 skills × 5 scopes matrix yields ~20 natural combinations. Presenting these as a flat grid overwhelms. Instead:

### Creation flow: Source → Job → Configure

```
Step 1: "What do you want to stay on top of?"
  → Show connected platforms as cards (Slack, Gmail, Notion, Calendar)
  → Plus: "Everything" (cross-platform), "A topic" (research/knowledge)

Step 2: "How should I help?" (contextual to Step 1)
  → If Slack selected: Recap (digest), Watch (monitor), Summary (synthesize)
  → If Calendar selected: Meeting Prep (prepare)
  → If "Everything": Work Summary (synthesize), Proactive Insights (synthesize+proactive)
  → If "A topic": Research (research), Domain Tracker (monitor)

Step 3: Schedule + Destination (drawer/configuration)
```

Step 2 options are **filtered by source selection** — the user never sees irrelevant combinations. This is the "template" layer from agent-framework.md, but presented as a progressive flow rather than a matrix.

### Alternatively: Chat-first creation (ADR-105 aligned)

The creation flow above can also be expressed as conversation starters:

```
"Catch me up on Slack every morning"     → digest, platform(slack), recurring(daily)
"Prep me for tomorrow's meetings"        → prepare, cross_platform, recurring(daily)
"Summarize my week across platforms"     → synthesize, cross_platform, recurring(weekly)
"Track AI agent market developments"     → research, research, recurring(weekly)
```

The starter cards become **prompt suggestions**, not type selectors. TP infers role + scope + trigger from the natural language and creates the agent. The user refines in the agent workspace.

### The two paths coexist

- **Quick-start cards**: Curated prompt suggestions for the 4-6 most common agent setups. These cover 80% of creation scenarios.
- **"Create custom agent"**: Opens source → job → configure flow for users who want explicit control. This is the progressive disclosure path.
- **Chat freeform**: User describes what they want; TP figures out the rest. This is the power-user path (and the long-term default as TP improves).

---

## Principle 3: Agent Cards Show Source + Routine, Not Taxonomy

**An agent card's visual hierarchy should match the user's mental model: what it watches → what it does → when it runs.**

### Card anatomy (list/sidebar)

```
┌─────────────────────────────────────────────┐
│ [Slack icon]  Weekly Slack Recap             │
│               Recap · Mon 9:00am → email     │
│               ✓ Delivered 2d ago             │
└─────────────────────────────────────────────┘
```

| Element | Priority | Source |
|---------|----------|--------|
| **Platform icon(s)** | Primary visual anchor | Derived from `sources[].provider` |
| **Title** | Primary text | `agent.title` |
| **Role label + schedule** | Secondary text | `ROLE_LABELS[role]` + schedule summary |
| **Destination** | Tertiary | `→ email` / `→ #channel` |
| **Delivery status** | Status indicator | Latest run status |

### Platform icon derivation

```typescript
function getAgentPlatformIcons(agent: Agent): PlatformIcon[] {
  const providers = new Set(
    agent.sources
      ?.filter(s => s.provider)
      .map(s => s.provider === 'google' ?
        (s.resource_id?.startsWith('label:') ? 'gmail' : 'calendar') :
        s.provider
      ) ?? []
  );

  if (providers.size === 0) {
    // Research/knowledge agents — use role-derived icon
    return [agent.role === 'research' ? 'globe' : 'brain'];
  }
  return [...providers]; // ['slack'], ['slack', 'notion'], etc.
}
```

### Sidebar panel (compact)

The sidebar `AgentsPanel` uses a tighter layout but maintains the same hierarchy:

```
┌────────────────────────────────────┐
│ [▶] [Slack] Weekly Slack Recap     │
│              Delivered             │
├────────────────────────────────────┤
│ [▶] [🌐]   Market Research        │
│              Delivered             │
└────────────────────────────────────┘
```

Platform icon replaces the generic play/pause as the leading visual element. Active/paused status moves to a subtle indicator (green dot vs. muted).

---

## Principle 4: Grouping Emerges From Source Affinity

**As the agent count grows, natural groups form around source affinity — not role categories.**

### Threshold behavior

| Agent count | Display | Rationale |
|-------------|---------|-----------|
| 1-5 | Flat list, no grouping | Grouping adds overhead with few items |
| 6-12 | Source-affinity sections | Visual sections: "Slack agents", "Cross-platform", "Research" |
| 13+ | Collapsible groups + search | Groups default-collapsed except most recently active |

### Source-affinity groups

| Group label | Criteria | Icon |
|-------------|----------|------|
| **Slack** | All sources are `provider: "slack"` | Slack icon |
| **Gmail** | All sources are `provider: "gmail"` or `provider: "google"` (gmail) | Gmail icon |
| **Notion** | All sources are `provider: "notion"` | Notion icon |
| **Calendar** | All sources are `provider: "calendar"` or `provider: "google"` (calendar) | Calendar icon |
| **Cross-platform** | Sources from 2+ providers | Stacked icons |
| **Research & Knowledge** | No platform sources, or knowledge-scope | Globe/brain icon |

Agents with mixed sources (e.g., Slack + Notion) go into "Cross-platform." An agent with only Slack sources goes into "Slack" regardless of role.

### Sorting within groups

1. Active before paused
2. Most recently delivered first
3. Alphabetical as tiebreaker

---

## Principle 5: Roles Are Behavioral, Not Taxonomic

**Role labels describe behavior ("Recap", "Meeting Prep") — they are not categories users navigate by.**

Roles appear as:
- **Secondary label** on agent cards (after the title)
- **Filter chips** on the agents list page (for power users with 10+ agents)
- **Contextual options** in the creation flow (Step 2, filtered by source selection)

Roles do NOT appear as:
- Primary grouping dimension
- Navigation categories
- Tab labels
- First-level creation choices

### Role label guidelines

| Role | User-facing label | Verb-form (for prompts) |
|-------|-------------------|-------------------------|
| digest | Recap | "catch me up on..." |
| prepare | Meeting Prep | "prep me for..." |
| synthesize | Summary | "summarize..." |
| monitor | Watch | "track..." / "alert me when..." |
| research | Research | "research..." / "investigate..." |
| orchestrate | Coordinator | "manage my agents..." |
| act | Action | "reply to..." / "post..." |
| custom | Custom | (freeform) |

---

## Principle 6: Presentation Must Survive Taxonomy Expansion

**The frontend presentation layer must not break when new skills, scopes, or capabilities are added.**

### Design for unknown futures

1. **No hardcoded role grids**: The creation flow derives available options from the backend, filtered by connected sources. Adding a new role doesn't require frontend changes if it follows the template pattern.

2. **Graceful unknown handling**: If a new role appears that the frontend doesn't have an icon/label for, fall back to the `custom` treatment (generic icon + role name as label).

3. **Source affinity is stable**: Platform providers change slowly (new integration = new icon + group label). Roles change faster (new capability = new behavioral option). Grouping by the stable axis (source) means the UI structure survives role expansion.

4. **Template-driven creation**: The creation cards/prompts come from a `TEMPLATES` config that the backend can extend. The frontend renders whatever templates exist — it doesn't enumerate skills.

### Template config shape

```typescript
interface AgentTemplate {
  id: string;                          // "slack-recap", "meeting-prep"
  label: string;                       // "Slack Recap"
  description: string;                 // "Daily summary of your Slack channels"
  prompt: string;                      // "Set up a daily Slack recap"
  icon: PlatformIcon;                  // "slack" | "calendar" | "globe" | ...
  requiredPlatforms?: string[];        // ["slack"] — only show if connected
  defaults: {
    role: Role;
    trigger: Trigger;
    scope?: Scope;                     // Usually auto-inferred
  };
}
```

Templates are the **bridge** between the backend taxonomy and the user's mental model. They are the canonical way to add new agent creation options without modifying the presentation framework.

---

## Principle 7: Chat Is the Long-Term Creation Surface

**Agent creation through conversation is the target state. Structured flows are a scaffold.**

Per ADR-105 and Surface-Action Mapping:
- **Directives** (what the agent should do, how it should behave) flow through chat
- **Configuration** (schedule, sources, destination) lives in the drawer

Agent creation is a mix of both — it starts as a directive ("I want a weekly Slack recap") and finishes as configuration (select channels, set schedule). The ideal flow:

1. User expresses intent in chat (or picks a starter card that prefills the prompt)
2. TP creates the agent with inferred defaults (role, scope, trigger, sources)
3. User refines via chat ("focus on #engineering and #product only") or drawer (tweak schedule)

The structured creation flow (Source → Job → Configure) serves users who prefer explicit control, and covers cases where TP inference isn't confident enough. Both paths produce the same result — an agent with all three axes configured.

As TP improves at intent detection and configuration inference, the structured flow becomes less necessary. But the **presentation principles** (source-first grouping, platform icons, progressive disclosure) remain stable regardless of creation method.

---

## Anti-Patterns

| Anti-pattern | Why it fails | Correct approach |
|-------------|-------------|-----------------|
| Role-first picker grid (8+ cards) | Users don't think in processing verbs | Source-first, then contextual role options |
| Scope as user-visible label | "Platform scope" means nothing to users | Show platform icons; scope is system-internal |
| Flat list at 15+ agents | No visual anchoring, scanning becomes linear | Source-affinity grouping with threshold |
| Hardcoded creation options | Breaks when skills/templates expand | Template-driven creation from config |
| Separate page per role type | Over-engineering; agents are peers regardless of role | Flat list with source-affinity grouping |
| Trigger/mode as grouping | "My recurring agents" is useless — they're almost all recurring | Source affinity or role filter chips |

---

## Implementation Priorities

### Implemented
1. ~~Add platform icons to agent cards~~ — Dashboard agent health grid uses `getPlatformIcon()` derived from `sources[].provider` (2026-03-16)
2. ~~Agent portfolio dashboard~~ — Supervision Dashboard at `/dashboard` with agent health grid, maturity badges, edit trend arrows, approval rates, Composer activity feed, attention banners (2026-03-16)
3. ~~Origin badges~~ — All non-user origins (`system_bootstrap`, `composer`, `coordinator_created`) collapsed to unified "Auto" badge in dashboard + activity page (2026-03-16)
4. ~~Two-path onboarding~~ — Dashboard empty state shows platform connect cards (primary) + Orchestrator chat (alternative). See [USER_FLOW_ONBOARDING_V4.md](USER_FLOW_ONBOARDING_V4.md) (2026-03-16)

### Immediate
5. Update `STARTER_CARDS` to use correct ADR-109 role names and add platform context
6. Fix the "What type of work-agent?" modal to use template-style prompts

### Near-term
7. Source-affinity grouping when agent count ≥ 6
8. Template config (backend-driven, replaces hardcoded `STARTER_CARDS`)
9. Creation flow: Source → Job → Configure (for structured creation path)

### Future
10. Chat-first creation as default (TP infers everything from natural language)
11. Template bundles ("Slack Power User" → creates digest + monitor + responder)
12. Maturity trend sparklines on dashboard

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-13 | Initial principles — source-first mental model, progressive disclosure, platform icons, source-affinity grouping |
| 2026-03-16 | Updated priorities: platform icons on dashboard, supervision dashboard, origin badge collapse, two-path onboarding — all implemented |
