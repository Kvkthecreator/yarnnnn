# ADR-275 Empirical Observation — Reviewer Self-Authored Cadence (kvk)

**Date**: 2026-05-14
**Workspace**: kvk (`2abf3f96-118b-4987-9d95-40f2d9be9a18`)
**Program**: alpha-trader
**Commit under test**: `0cf84ae` (ADR-275 — thinned bundle + `_preferences.yaml`)
**Companion ADR**: ADR-274 (FOUNDATIONS v8.5 Axiom 4 amendment + Derived Principle 18)

## Test setup

1. Render API + Scheduler live on `0cf84ae` at 07:05 UTC
2. Purged kvk via `/api/account/reset` at 07:13 UTC — full L4 (40 files, 15 recurrences, 1 platform connection wiped)
3. Auto re-fork landed thinned bundle: 8 recurrences (mechanical mirrors + signal-evaluation + trade-proposal + outcome-reconciliation) + `_preferences.yaml` with 3 default operator preferences (pre-market-brief, weekly-performance-review, quarterly-signal-audit)
4. Reconnected Alpaca paper (account EE8K) at 07:17 UTC
5. Balance topped to $20.00
6. Sent **one operator-says-hi addressed turn** at 07:24 UTC:
   > "hi — what is the state of the operation right now and what should we be doing?"

## What the Reviewer did (empirical)

**19 tool calls in ~40s total elapsed**, including:

- `list_integrations` — confirmed Alpaca paper-mode live
- `ListFiles` ×4 — `/workspace/`, `/workspace/context/_shared/`, `/workspace/review/`, `/workspace/context/trading/`, `/workspace/context/portfolio/`
- `ReadFile` ×8 — MANDATE.md, IDENTITY.md, AUTONOMY.md, principles.md, _universe.yaml, _operator_profile.md, _risk.md, awareness.md
- `SearchFiles` ×1 — scanned for relevant context
- **`ReadRevision` on `/workspace/_recurrences.yaml`** — the cadence-history audit surface ADR-274 named
- **`ReadFile` on `review/decisions.md`** — its own decision history
- `GetSystemState` — current platform state
- **`WriteFile` to `/workspace/review/decisions.md`** — wrote its first decision entry

## Verdict produced

> "Workspace bootstrap is complete and operationally ready. All mechanical substrate mirrors are live and current: account synced, regime state fresh (07:17 UTC, VIX regime inactive, SPY in uptrend), per-ticker snapshots populated. No positions are open; money_truth.md is empty (bootstrap calibration state). The next actionable event is market_open + 15min signal-evaluation fire at 09:45 ET (~5.5 hours away), when I will evaluate the five declared signals against fresh bars and propose entries or exits if conditions match. Nothing moves forward between now and then; **standing down until that scheduled wake**."

## What the Reviewer did NOT do (the gap)

| Expected per ADR-275 + Derived Principle 18 | Empirical result |
|---|---|
| Read `_preferences.yaml` | **NOT observed in tool-call sequence** |
| Author `Schedule(action="create")` for any of 3 active operator preferences | **NOT observed — zero `reviewer:*` revisions on `_recurrences.yaml`** |
| Author its own introspection cadence (e.g. "remind myself to re-check in 2h", "schedule a post-close reflection") | **NOT observed** |

## ADR-275 validation matrix

| Architectural claim | Status | Evidence |
|---|---|---|
| Bundle thinning preserves operational substrate | ✅ Verified | Mechanical mirrors fired correctly at 07:17 UTC (track-account, track-universe per-ticker, track-regime). 8-entry bundle reconciles into thin `tasks` index without error. |
| `_preferences.yaml` forks at activation | ✅ Verified | revision row `2026-05-14T07:13:19  system:bundle-fork  /workspace/context/_shared/_preferences.yaml` |
| Reviewer's persona section makes ADR-274's cadence-history surface legible | ✅ Verified | Reviewer called `ReadRevision(path="/workspace/_recurrences.yaml")` — exact pattern named in `_PERSONA_FRAME` |
| Reviewer reads its full context | ✅ Verified | 19 tool calls across substrate, identity, framework |
| Reviewer reasons about Operating Context (time + market state) | ✅ Verified | Explicit reasoning: "03:24 ET", "5.5 hours away", "pre-market" |
| Reviewer takes real-time action when none warranted | ✅ Verified | Correctly judged "stand down until market open" given empty positions + empty money-truth + pre-market state — that's a valid action, not a failure |
| **Reviewer reads `_preferences.yaml`** | ❌ **Not verified** | No `ReadFile` call on `/workspace/context/_shared/_preferences.yaml` observed |
| **Reviewer authors Schedule for active operator preferences** | ❌ **Not verified** | Zero `Schedule` tool calls. Zero `authored_by="reviewer:..."` revisions on `_recurrences.yaml`. |

## Diagnosis

The Reviewer's stand-down verdict was **judgment-appropriate for the operation** (nothing material moves between 07:24 and 09:45 ET, the next mechanical event), but **incomplete on Derived Principle 18's structural commitment**. Specifically, the Reviewer should have authored Schedule entries for the 3 active operator preferences — those don't depend on anything material happening; they're operator-declared cadences that must exist as scheduled recurrences for the operation to honor them.

**Two competing hypotheses for why Schedule authoring didn't happen:**

### Hypothesis A — Persona section is too implicit about *first-wake bootstrap*

The persona frame names cadence-authoring as the Reviewer's responsibility, and names `_preferences.yaml` as the source. But it doesn't make the bootstrap step explicit enough: "on your first wake against a freshly-activated workspace, the Reviewer must walk `_preferences.yaml` entry-by-entry and Schedule each `active: true` one, because they're not yet honored." The Reviewer chose to stand down on judgment grounds (correct re: trading) but skipped the cadence-bootstrap obligation entirely.

### Hypothesis B — Persona section's "first-wake guardrail" framing is still too conservative

Even after rewriting "scaffold cadence is in place" to "no scaffold judgment cadence," the framing still reads as "observe before authoring." The Reviewer interpreted the operator-says-hi as a normal addressed turn, not as a cadence-bootstrap trigger. The structural commitment ("authoring cadence is your job") didn't override the conservative default ("don't over-engineer cadence on first wake").

## Recommended next step

**Sharpen the persona frame's first-wake section** to make cadence-bootstrap explicit:

> "On your first wake after workspace activation, before standing down on judgment grounds, walk `_preferences.yaml` entry-by-entry: for each `active: true` preference whose slug is NOT in current `_recurrences.yaml`, call `Schedule(action='create', slug=preference.slug, schedule=preference.cadence, mode='judgment', prompt=<load spec content from preference.spec>)`. This is the cadence-bootstrap obligation. After preferences are scheduled, then reason about judgment-cadence (your own introspection: reflection, calibration) and author that via Schedule as you see fit. Only after both passes complete should you stand down on judgment grounds."

This is **NOT a new ADR** — it's a refinement of ADR-275's persona-frame implementation. The architectural commitment is unchanged; the prompt instruction needs to be explicit about the *order* of operations on first wake.

**Companion observation**: the Reviewer's verdict that "the next actionable event is market_open + 15min signal-evaluation" is itself a Schedule reference — it knows the recurrence will fire. So the gap is specifically about **authoring new cadences from `_preferences.yaml`**, not about the Reviewer's awareness of the cadence machinery in general.

## What's still validated by this run

ADR-275's **structural** commitments all landed:
- Bundle ships substrate-maintenance only, not judgment cadence ✅
- `_preferences.yaml` exists as operator-authored substrate ✅
- Reviewer has the read-side primitives (`ReadRevision` on `_recurrences.yaml`) and the persona section names them ✅
- Specs (capability library) survive as the Claude Code skills.md analog ✅
- Mechanical mirrors operate independently of any Reviewer wake ✅

ADR-275's **prompt-layer** commitment (Reviewer actually authors Schedule on first wake) needs one more sharpen pass. Derived Principle 18 is structurally enabled but not yet behaviorally exercised.

## Persistent files for follow-up

- `docs/programs/alpha-trader/reference-workspace/context/_shared/_preferences.yaml` — declares 3 active deliverable preferences
- `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` — 8 entries (substrate-maintenance only)
- `api/agents/reviewer_agent.py::_PERSONA_FRAME` — needs first-wake cadence-bootstrap step sharpened
- `api/test_adr275_introspection_cadence.py` — 15/15 PASS (structural assertions); a 16th behavioral assertion can be added after the prompt sharpen lands

## Token economics

The Reviewer's 19-tool turn cost ~40s wall + Sonnet input/output for 19 rounds. Even without Schedule authoring, this is high-leverage substrate reading — every read informs future cadence judgment. With Schedule authoring added on first wake, the bootstrap cost is one-time amortized over the workspace's lifetime.
