# Deliverable Types — Feature Reference

**Status:** Living document
**Date:** 2026-03-06
**Related:** [ADR-093: Deliverable Type Taxonomy](../adr/ADR-093-deliverable-type-taxonomy.md), [Quality Testing Framework](../development/deliverable-quality-testing.md)

Each deliverable type maps to a job-to-be-done. This document captures the validated output format, execution details, and design decisions per type. Types are added here as they go through quality validation (see testing framework).

---

## Sequencing model

```
Acquisition wedge:     Work Summary (cross-platform synthesis)
Trust builder:         Auto Meeting Prep (daily calendar-driven prep)
Retention foundation:  Recap (daily/weekly platform catchup)
Deepening hooks:       Deep Research, Watch, Coordinator
```

---

## Work Summary (type: `status`)

**Validated:** 2026-03-06 (Pass 1)
**Prompt version:** v4 — tracked in `api/prompts/CHANGELOG.md`

### What it does

Synthesizes activity across all connected platforms into a structured work summary for a specific audience — daily, weekly, or on any schedule. The value scales with each platform connected — no single-platform tool can produce this.

### Output format: two-part structure

**Part 1 — Cross-Platform Synthesis** (intelligence layer):
- TL;DR executive summary
- Key accomplishments (drawn from all platforms)
- Blockers and risks
- Next steps with owners
- Cross-platform connections — cause-and-effect chains across platforms

**Part 2 — Platform Activity** (evidence layer):
- Separate `## Section` per connected platform
- Slack: grouped by channel
- Gmail: notable emails, action items
- Notion: document updates, changes
- Calendar: upcoming events (when present)

**Design rule:** Every platform with data gets a section. No update is still news — low activity is reported briefly to confirm nothing was missed.

### Why two parts

- Part 1 = what YARNNN thinks matters (the intelligence)
- Part 2 = what actually happened where (the evidence)
- Recipients get both narrative and source attribution

### Execution details

- **Binding:** `cross_platform` (CrossPlatformStrategy)
- **Default mode:** `recurring` (weekly)
- **Headless agent:** 3 tool rounds max
- **Delivery:** Email via Resend (ADR-066)

---

## Auto Meeting Prep (type: `brief`)

**Validated:** 2026-03-06 (Pass 3)
**Prompt version:** v3 — tracked in `api/prompts/CHANGELOG.md`
**Full details:** [docs/features/meeting-prep.md](meeting-prep.md)

### What it does

Every morning, reads the user's Google Calendar and sends a prep briefing for the day's meetings — with context pulled from Slack, Gmail, and Notion for each meeting.

### Key features

- **Daily batch:** runs once per morning, covers today + tomorrow morning (no gap between deliveries)
- **Meeting classification:** adapts prep depth per meeting type (recurring internal, external/new, large group, low-stakes)
- **Cross-platform context:** surfaces attendee mentions from Slack, recent email threads, Notion docs
- **Requires Google Calendar** — explicit dependency

### Constraints

- One per user
- Daily frequency only
- Google Calendar must be connected

### Execution details

- **Binding:** `cross_platform` (CrossPlatformStrategy)
- **Default mode:** `recurring` (daily)
- **Sources:** Calendar + all connected platforms
- **Delivery:** Email via Resend (ADR-066)

---

## Recap (type: `digest`)

**Validated:** 2026-03-06 (Pass 2 — in progress)
**Prompt version:** v2 — tracked in `api/prompts/CHANGELOG.md`

### What it does

Catches the user up on everything across a single connected platform. Platform-wide — covers all synced sources (channels, labels, pages), not just one.

### Output format: highlights + by-source breakdown

**Highlights** — top 3-5 things that happened across the entire platform. Decisions, problems surfaced, progress on key work.

**By Source** — subsection per source with `###` headers:
- Slack: by channel (`### #engineering`, `### #daily-work`)
- Gmail: by category or sender (`### Infrastructure Alerts`)
- Notion: by page or database (`### Architecture Docs`)
- Calendar: by timeframe (`### This Week`)

**Design rule:** Every source with data gets a subsection. Low activity noted briefly.

### Constraints

- One recap per platform per user (enforced at creation time)
- Title set dynamically: "Slack Recap", "Gmail Recap", etc.
- Frequency: daily or weekly (user chooses)

### Execution details

- **Binding:** `platform_bound` (PlatformBoundStrategy)
- **Default mode:** `recurring`
- **Headless agent:** 3 tool rounds max
- **Delivery:** Email via Resend (ADR-066)

---

## Deep Research (type: `deep_research`)

**Validated:** Not yet

---

## Hidden pre-launch (2026-03-06)

The following types are implemented in the backend (type keys, strategies, prompts) but hidden from the creation UI. They can be restored when their prerequisites are met.

| Type | Reason hidden | Restore when |
|------|--------------|--------------|
| **Watch** (`watch`) | Promises real-time monitoring but architecture is polling-based (1-24hr sync). Misleading UX. | Sub-5-minute sync or webhook infrastructure in place |
| **Coordinator** (`coordinator`) | Power-user meta-feature. Not needed for initial adoption. | User base has power users creating 5+ deliverables |
| **Custom** (`custom`) | Adds ambiguity. Users should choose from validated types pre-launch. | Post-launch, if users request flexibility beyond the 4 active types |

---

## Key files (shared across all types)

| Concern | Location |
|---------|----------|
| Type prompts | `api/services/deliverable_pipeline.py` (TYPE_PROMPTS) |
| Execution strategies | `api/services/execution_strategies.py` |
| Content fetching | `api/services/platform_content.py` |
| Generation pipeline | `api/services/deliverable_execution.py` |
| Quality testing | `docs/development/deliverable-quality-testing.md` |
