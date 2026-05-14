# ADR-277: Feed Emission Policy — Each Event Has One Canonical Home

**Status**: Implemented (2026-05-15 — commits `97c9529` + `2815964` + this commit)
**Date**: 2026-05-15
**Dimensional classification**: **Channel** (Axiom 6) primary — defines what the feed surface contains; **Mechanism** (Axiom 5) secondary — emission policy at source vs filter-on-read.

**Supersedes**: ADR-219 D5's `housekeeping` weight tier and the retired narrative_digest roll-up mechanism (which was deleted by the ADR-260/261/262 back-office package cleanup but whose emissions kept firing without their intended consumer).

**Amends**: ADR-219 (weight enum), ADR-263 amendment 2026-05-12 (per-fire success suppression — now extended from "failure-only" to "success-and-failure-only-on-judgment-or-operator-actionable-events").

**Preserves**: ADR-258 revised (Reviewer-action narration via `surface_reviewer_actions` — these are NOT `_emit_system_narrative` calls and are unaffected). ADR-260 real-time Reviewer loop. ADR-261 recurrence model. ADR-265 execution_events as canonical forensic substrate.

---

## 1. Context

Production audit on kvk's workspace surfaced **478 system rows in 24 hours** on the feed surface. ~196 per minute for `track-positions` + `track-orders` during regular trading hours. Every row was a mechanical-mirror-success notification:

```
SYSTEM   SyncPlatformState: 0 written, 1 unchanged    04:54 AM
SYSTEM   SyncPlatformState: 0 written, 0 unchanged    04:54 AM
SYSTEM   SyncPlatformState: 0 written, 1 unchanged    04:55 AM
SYSTEM   SyncPlatformState: 0 written, 1 unchanged    04:56 AM
... (repeating every 60s during RTH)
SYSTEM   TrackRegime: 1 items processed               05:30 AM
```

The operator's actual chat content drowned in mechanical telemetry. The feed surface — meant to be the central conversational substrate that surfaces throughout the cockpit — had effectively become a duplicate of `/activity` (the execution-lens forensic log).

### Why this happened — a design intent that never finished migrating

ADR-219 D5 originally specified three render shapes:

| Weight | Intent | Render shape |
|---|---|---|
| material | Operator must see | Full bubble |
| routine | Context if reading the feed | Collapsed slim line |
| housekeeping | **Hidden by default — rolled into daily digest** | (digest card was the curated surface) |

A `services/back_office/narrative_digest.py` job was supposed to roll housekeeping rows up into one daily curated card. **That job was deleted entirely along with the rest of the `back_office/` package in the ADR-260/261/262 cleanup (~3,142 LOC)**. The housekeeping emissions kept firing, but their intended consumer no longer existed.

FE drift in `MessageRow.tsx` papered over the missing roll-up — `HousekeepingRow` rendered at `opacity-50` as a "dim row so the operator can scroll past." For low-volume workspaces this was tolerable. For an alpha-trader workspace running mechanical mirrors every minute during RTH, the feed became unusable.

### Why the audit-trail rationale was never load-bearing

Every successful mechanical fire was already captured in **`execution_events`** with `mode`, `status`, `duration_ms`, and `cost_usd`. That's the canonical forensic substrate per ADR-265, surfaced via `/activity`. The narrative-row emission was pure duplication — same data, second home, no operator-relevant judgment added.

The same was true of every other audit-shaped event being narrated: skip rows, paused-recurrence rows, no-op success rows. **None of them carry operator-relevant judgment the substrate row doesn't already have.**

---

## 2. Decision

### D1 — Feed emission policy

**The feed is for events the operator chose to be told about, not events the system happened to do.**

Concretely:

> Before adding a narrative emission for a system event, ask: is there already a substrate row (`execution_events`, `workspace_file_versions`, `action_proposals`, `agent_runs`) that captures this event? If yes, the narrative emission only earns its place when it carries operator-relevant judgment or context the substrate row doesn't carry.

Two emission tiers survive:

| Tier | Definition | Render |
|---|---|---|
| **Material** | Operator-actionable or genuinely material events (Reviewer verdicts, hard stops, capability transitions, real failures, decisions the operator should know about even when not actively reading the feed) | Full bubble |
| **Routine** | Context if the operator's already reading the feed; not notification-worthy on their own (warn-but-proceed events, stand-down verdicts, mode transitions) | Slim collapsed line |

The third tier (`housekeeping`) is retired. Events that would have been tagged housekeeping should now **emit nothing at all** — their canonical home is the substrate row, accessible via `/activity` or `/context` file detail.

### D2 — Application to existing call sites

The 6 `_emit_system_narrative` call sites in `api/services/invocation_dispatcher.py` classified:

| Line | Event | Action | Weight |
|---|---|---|---|
| 145 | balance_exhausted | KEEP | material |
| 175 | spend_ceiling reactive skip | KEEP | material |
| 195 | spend_ceiling manual warn-but-proceed | KEEP | routine |
| 275 | reviewer_invocation exception | KEEP | material |
| 608 | capability_transition (first-detection) | KEEP | material |
| 707 | mechanical_fire success | **DELETE** | (retired) |

L707 was the only true audit-only emission. The L608 transition guard (which fires at most once per platform-disconnect event, not per per-minute fire) covers the only operator-actionable mechanical state change. The L145/175/195/275 sites are operator-relevant and stay.

### D3 — Weight enum collapse

FE `NarrativeWeight` type union: `'material' | 'routine'` (was `'material' | 'routine' | 'housekeeping'`).

`HousekeepingRow` component, `dedupeBackOfficeEvents` heuristic (60-second-window content-match for system+system_agent duplicate pairs — paper-cover for the mechanical-fire emission), and all `'housekeeping'` filter values DELETED. Singular Implementation — one render path per weight value, no parallel paths.

### D4 — Legacy data tolerance

Pre-ADR-277 stored `session_messages` rows in the database still carry `metadata.weight = 'housekeeping'`. These are not deleted (operator data preservation). Read-side tolerance:

- `MessageRow.tsx`: any weight value other than `'material'` falls through to `RoutineRow` (the legacy housekeeping rows render as routine).
- `FeedPanel.tsx::narrativeFilterMatches`: legacy `'housekeeping'` value coerces to `'routine'` at the filter-comparison site so pre-ADR-277 data still appears under the routine filter.

Coercion is a single-site read-time adapter, not a parallel third render path. The wire type and component type unions both reflect current vocabulary.

### D5 — Where deleted information lives instead

No information loss. The canonical homes for what used to be feed-rendered:

| What was in feed | Canonical home post-ADR-277 |
|---|---|
| Mechanical-fire success notifications | `execution_events` (visible at `/activity` filtered to `mode=mechanical`) |
| Per-fire substrate write detail | `workspace_file_versions` revision chain (ADR-209) — visible per-file in `/context` |
| Reviewer's recent activity | `/agents?agent=reviewer&tab=activity` (post-2026-05-14 rewrite) |
| Full recurrence schedule + cadence | `/work?tab=schedule` |
| Workspace-wide execution forensics | `/activity` |

All four surfaces existed already. The feed cleanup just stops duplicating them.

---

## 3. The rule of thumb (canon)

For future emission decisions — surface design, downstream data-type handling, anywhere an event might be considered for the feed:

> **Each event has one canonical home. The feed is for events whose canonical home is conversation.**
>
> If the same event is already captured in `execution_events` / `workspace_file_versions` / `action_proposals` / `agent_runs`, the feed only earns a parallel narrative emit when it carries **operator-relevant judgment or context the substrate row doesn't carry.**
>
> Density (material vs routine) is determined by *whether the operator should see this when not actively reading the feed*, not by event frequency. Frequency is a different question: high-frequency events should usually emit nothing (their canonical home is the substrate), not "emit at routine density."

This is the lens-sharpening discipline canonized in WORKSPACE.md (Schedule vs /activity declaration-vs-execution split, Autonomy vs Activity tab config-vs-supervision split) applied at the **emission policy** layer rather than the surface layer. Each event has exactly one canonical home; the feed is its conversational layer when one exists.

---

## 4. What this is not

- **Not a hide-at-render filter.** Filter-on-read mechanisms accumulate forever; the underlying rows still cost storage, indexing, and query time. Emission policy is at source.
- **Not a roll-up resurrection.** ADR-260/261/262 deleted the back_office package including the narrative_digest job. Rebuilding it would re-introduce the surface we already decided to retire. This ADR makes emissions intentional at source so no roll-up is needed.
- **Not a Reviewer-narration change.** `services/reviewer_chat_surfacing.py::surface_reviewer_actions` (Reviewer's tool-use loop narration per ADR-258 revised) is a separate emission path — unaffected. Reviewer fired track-universe / wrote to decisions.md / proposed action X all still render in the feed exactly as before.

---

## 5. Implementation

Three commits, atomic on `main`:

1. `97c9529` — backend `invocation_dispatcher.py`: delete L707 mechanical-fire emission, tighten weights on L145/175/195/275/608, delete dead `_summarize_mechanical_result` helper.
2. `2815964` — FE collapse: delete `HousekeepingRow`, delete `dedupeBackOfficeEvents`, update `NarrativeWeight` type union to 2-value, update wire types in `api/client.ts`, update `FeedFilterBar` WEIGHTS array, add legacy-tolerance coercion in `narrativeFilterMatches`.
3. (this commit) — ADR-277 + WORKSPACE.md Tab: Chat emission policy bullet.

### Validation

Net behavioral impact on kvk's alpha-trader workspace:

- Feed volume: **478 system rows / 24h → ~10 system rows / 24h** (only operator-relevant events emit).
- All forensic data preserved in `execution_events`; `/activity` page unchanged.
- Reviewer narration (`surface_reviewer_actions`) unchanged.
- Operator chat experience: chat content no longer drowns in mechanical telemetry; feed reads as a conversation again.

### Acceptance criteria

- [x] No `_emit_system_narrative` call site emits for mechanical-fire success.
- [x] FE `NarrativeWeight` type union is 2-value.
- [x] `HousekeepingRow` component does not exist.
- [x] `dedupeBackOfficeEvents` heuristic does not exist.
- [x] Pre-ADR-277 stored rows with `weight='housekeeping'` render correctly (coerced to routine).
- [x] Type-check clean; Python parse clean.
