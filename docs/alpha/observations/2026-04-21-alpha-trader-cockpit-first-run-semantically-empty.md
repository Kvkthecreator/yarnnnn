# 2026-04-21 — alpha-trader — Cockpit-first-run is semantically empty, not structurally empty

## Classification
- **Objective:** both (A-system primary; B-product secondary — an operator who can't tell what to do won't make money)
- **Within-A scope:** ui-ux, qualitative-agent-behavior
- **FOUNDATIONS dimension:** Channel (Axiom 6) primary — Channel legibility per Derived Principle 12; Identity (Axiom 2) secondary — operator-vocabulary vs system-vocabulary mismatch
- **Severity:** cognitive-load (not dead-stop; operator can navigate but can't tell what action produces value)
- **Resolution path:** ADR-candidate (pattern spans multiple surfaces) + component-patch (empty states + tile copy) + prompt-tweak (YARNNN should onboard proactively on Overview)
- **Money impact:** decision-impact (forward-looking — alpha operator can't form an opinion about YARNNN's utility from a cold-start cockpit)

## Context
KVK logged into alpha-trader (Mode 2, via browser) for the first time post-setup. Harness had shipped 23/23 green the day before — workspace is structurally complete per Objective-A invariants (12 agents, 5 essential tasks active, platform connected, core files scaffolded, context domains seeded). Opened `/overview` (HOME_ROUTE) and `/context?path=/workspace/context/portfolio/summary.md`.

## What happened
**Overview `/overview` rendered:**
- NEEDS ME → "Nothing needs you right now."
- SINCE LAST LOOK → "Quiet past 24h. 5 tasks active across 0 agents."
- SNAPSHOT → three tiles: Book (—), Workforce (0 agents · 5 active tasks), Context (Competitors)

**Files `/context` rendered:**
- Left tree: Context / Portfolio / Trading / Reports / Uploads / Settings
- Opened `portfolio/summary.md` — shows three empty section headers (Account State / Position Mix / Performance & Attribution), no content under any
- File metadata: *"File · Directory scaffold: portfolio · Updated Apr 21, 2026"*

## Friction
Three distinct gaps, same root cause:

### Gap 1 — Day-zero detection threshold is too strict

`OverviewEmptyState` fires only when **zero agents AND zero active tasks AND zero pending proposals**. But the alpha-trader workspace has 12 agents (scaffolded at signup per ADR-189) and 5 active tasks (all back-office system tasks + daily-update heartbeat). Day-zero UX never activates — even though the workspace is *semantically* at day-zero (no operator-authored work, no signals fired, no trades reviewed).

The detector conflates **structurally empty** (no rows) with **semantically empty** (no operator-originated work). They're different.

### Gap 2 — Surfaces speak system-vocabulary, not operator-vocabulary

"0 agents · 5 active tasks" reads as contradictory to a non-engineer operator. *How can 5 tasks run with 0 agents?* The architectural truth (back-office tasks are owned by YARNNN + platform bots which are authored at signup, not by the operator) requires ADR-189 + ADR-164 familiarity to parse.

"Context: Competitors" in the Snapshot tile is accurate per `SnapshotPane.tsx` logic (richest domain by entity count, alphabetical tiebreaker), but has no operator-intent. KVK is a trader; Competitors isn't their primary domain. The tile should surface trading or portfolio first, or at minimum explain *why Competitors*.

"Book —" (em-dash) is Snapshot's honest "no performance data yet" rendering, but gives the operator no affordance to understand *when or how* the Book will populate.

### Gap 3 — Scaffolded files render as if the operator is supposed to fill them

`portfolio/summary.md` shows three empty headers with no body. The file metadata tag says "Directory scaffold: portfolio" — a file existence marker that's legible to engineers (*"this file was auto-scaffolded as part of directory creation"*) but ambiguous to operators (*"is this waiting for me to write something? or will something fill it?"*).

The surface doesn't distinguish:
- **Empty because waiting for agent population** (correct mental model: leave it alone; `signal-evaluation` will populate)
- **Empty because you need to do something** (wrong mental model here, but the UI doesn't rule it out)

## Root cause (one sentence)

**Post-cockpit transition, no surface owns the first-run guidance moment.** Pre-cockpit, TP opened a workspace-state modal on `/chat` landing and emitted a `lead=context` marker (per `docs/design/ONBOARDING-TP-AWARENESS.md` v4). When `HOME_ROUTE` moved to `/overview` (ADR-199), the marker-based onboarding never fires because nobody is on `/chat` at cold-start. Overview has `OverviewEmptyState` for the *completely empty* case, but no guidance for the *semantically empty but structurally scaffolded* case — which is what every single new YARNNN signup now looks like.

## Hypothesis
Three coordinated changes resolve this:

### H1 — Redefine day-zero for semantic emptiness
Detection triggers when **zero non-system tasks AND zero non-scaffolded agents AND zero platform connections beyond the billing one**. Back-office tasks + scaffolded YARNNN/Specialist agents don't count toward "active" for UX purposes. They exist at the structural layer; they don't constitute operator activity.

Component-patch on `OverviewSurface.detectDayZero()`. Read from persona-appropriate signals (recent operator-originated proposals / approved decisions / connected non-YARNNN platforms) rather than raw row counts.

### H2 — Overview is the cold-start surface; rail opens by default when semantically empty

When day-zero (semantic) is true, the YARNNN rail opens with a pre-seeded first-session prompt from YARNNN, and the main pane renders operator-facing empty-state content (not "NEEDS ME / SINCE LAST LOOK / SNAPSHOT" panes that read as empty monitors).

This replaces the pre-cockpit `/chat`-modal onboarding pattern with `/overview`-rail onboarding — same intent (TP drives first-run), new home (cockpit's landing destination). Supersedes ONBOARDING-TP-AWARENESS.md v4 cold-start flow.

### H3 — Operator-vocabulary copy on all tile + empty-state surfaces

- "0 agents · 5 active tasks" → "Your workforce: YARNNN + 11 specialists on standby. No authored agents yet."
- "Book —" → "Book: no trades yet. Fires when you approve your first signal trigger."
- "Context: Competitors" → context tile should rank by *persona relevance* (trading domains for alpha-trader) or show "Your richest context: `{domain}` · N entities — or add yours via Files"
- Scaffolded file headers (e.g., `portfolio/summary.md`) should render a persistent info-banner: *"This file is maintained by the portfolio-summary task. It'll populate after your first reconciliation cycle."*

Prompt-tweak: YARNNN onboarding prompt (`api/agents/yarnnn_prompts/onboarding.py`) extended with cockpit-first-run guidance — "when user lands on `/overview` with semantically-empty workspace, introduce yourself, point at Overview's structure briefly, and offer the three concrete first moves."

## Counterfactual (Objective B)

Without this fix, an external alpha operator (friend, not KVK) lands on the cockpit and sees a system reporting "Nothing needs you right now" despite the entire purpose of the product being to tell them what to do. They get no signal that (a) they need to talk to YARNNN first, (b) the workspace is idle but ready, or (c) what the first concrete action is.

**Probability this silences a real alpha friend within 60 seconds of landing: high.** Probability they form an opinion about YARNNN's utility before they've even authored their first agent: also high, and the opinion is "this doesn't seem to know what it's for."

Money impact is indirect but real — every alpha friend lost to cold-start confusion is an ICP-validation signal we fail to collect. ADR-191's polymath-operator alpha thesis requires at least several alpha operators to form opinions. Any of them bouncing from a legibility gap is a research-cost we eat.

## Links
- Screens observed: `/overview` + `/context?path=%2Fworkspace%2Fcontext%2Fportfolio%2Fsummary.md` on `seulkim88@gmail.com` workspace
- `web/components/overview/OverviewSurface.tsx` — `detectDayZero()` threshold
- `web/components/overview/OverviewEmptyState.tsx` — current two-CTA empty state
- `web/components/overview/SnapshotPane.tsx` — tile copy + domain-selection logic
- `docs/design/ONBOARDING-TP-AWARENESS.md` — pre-cockpit onboarding flow (now orphaned)
- `api/agents/yarnnn_prompts/onboarding.py` — prompt guidance that still assumes `/chat` entry
- ADR-199 (Overview surface) + ADR-198 v2 (cockpit nav) — the transition that created the gap
- Related future: ADR-203 candidate — First-Run Guidance Layer
