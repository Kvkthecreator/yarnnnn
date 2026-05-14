# ADR-275: Introspection Cadence is Reviewer-Authored, Not Bundle-Scaffolded

**Status**: **Proposed 2026-05-14** — closes the structural gap ADR-274 named but didn't finish.

**Authors**: KVK + Claude (discourse session 2026-05-14, continued from ADR-274)

**Companion canon**: FOUNDATIONS v8.5 Axiom 4 amendment + Derived Principle 18 ("Standing intent implies Trigger-authoring authority"). ADR-274 enabled the primitives (Operating Context block + Schedule attribution + persona cadence-authoring section). ADR-275 enacts the structural cleanup by removing pre-scheduled judgment recurrences from program bundles.

**Amends**:
- ADR-261 D2 — the `_recurrences.yaml` shape stays, but bundles ship only substrate-maintenance + reactive entries; judgment-cadence entries dissolve into Reviewer-authored cadence.
- ADR-262 D1 — operator-facing deliverable specs (`/workspace/specs/*.md`) remain the canonical capability library, but they are no longer paired with bundle-scheduled judgment recurrences.
- ADR-268 — market-context-aware schedules survive on substrate-maintenance mirrors + signal-evaluation; the deliverable cadences they previously anchored (pre-market-brief at `@market_open - 30min`) move to operator-authored preferences.

**Preserves**:
- FOUNDATIONS Axioms 1–8 unchanged.
- ADR-209 Authored Substrate model unchanged.
- ADR-264 substrate-canonical world axiom unchanged (mechanical mirrors stay).
- Schema unchanged (no new tables / no new columns).
- Primitive surface unchanged (no new primitives — `Schedule` already exists per ADR-261 D4 + ADR-274).
- Cron scheduler unchanged.

**Dimensional classification**: **Trigger** (Axiom 4) primary; **Identity** (Axiom 2) secondary; **Substrate** (Axiom 1) tertiary.

---

## 1. The structural gap

FOUNDATIONS v8.5 + Derived Principle 18 (shipped via ADR-274) canonized that the Trigger dimension is authored by Identity layers — the Reviewer holds standing intent, therefore the Reviewer authors its own operating cadence. The bundle's initial recurrence entries are *scaffolds* (`authored_by="system:bundle-fork"`), not the Reviewer's permanent rhythm.

ADR-274 shipped the **enabling primitives**:
- Reviewer perceives Operating Context (now + timezone + market state + tenure) on every wake
- Reviewer's persona frame names cadence-authoring as its responsibility
- Schedule primitive fails fast on missing `authored_by`; dispatch-layer auto-attribution
- Reviewer can call `Schedule(action="create" | "update" | "pause" | "resume" | "archive")` mid-loop

ADR-274 did **not** finish the structural cleanup: the alpha-trader bundle still ships **9 pre-scheduled judgment recurrences** (`morning-reflection`, `morning-calibration`, `narrative-digest`, `proposal-cleanup`, `pre-market-brief`, `weekly-performance-review`, `quarterly-signal-audit`) as if cadence were the bundle's responsibility. This contradicts the axiom: the bundle should ship the *capability library* (specs at `/workspace/specs/`), not the *cadence* the Reviewer should self-author.

The Reviewer's first-wake guardrail in ADR-274's persona frame says: "*Observe operation against [the scaffold cadence] for several cycles before authoring substantial cadence changes — don't over-engineer.*" With 9 pre-scheduled introspection rituals shipping daily/weekly, the Reviewer never has the structural pressure to author its own cadence — infrastructure does it for it. The axiom never gets exercised.

## 2. Skills-library analog

The bundle's `/workspace/specs/*.md` files are the **capability library** — they describe what each kind of output looks like (schema, sections, quality criteria, references). This is exactly the architectural shape of Claude Code's `SKILL.md` convention (ADR-118): a folder ships a capability declaration; the runtime decides when to invoke it.

| Concern | Where it lives | Shape |
|---|---|---|
| **What** the output looks like | `/workspace/specs/{slug}.md` | Capability spec (skills.md analog) |
| **When** to produce it | Reviewer's judgment, authored via `Schedule` | Trigger dimension, owned by Identity (Axiom 4 v8.5) |
| **Operator's cadence preferences** | `/workspace/context/_shared/_preferences.yaml` | Operator-authored substrate the Reviewer reads |

The bundle ships the first; the Reviewer authors the second; the operator declares the third. Three orthogonal concerns, three substrate locations, one canonical write path each.

## 3. The operator preferences distinction

The operator may have hard-cadence preferences for operator-facing deliverables — "I want a pre-market brief 30min before market open every weekday." This is a *preference*, not a mandate. It can change without re-authoring MANDATE.md. It's the *what* and *when* the operator wants honored; the *how* (Reviewer judgment about content) stays delegated.

Per ADR-254 File Format Discipline, machine-parsed structured data lives in `.yaml`. Operator's cadence preferences are exactly machine-parsed structured data: the Reviewer reads them at every wake and authors cadence accordingly.

**New operator-authored substrate file**: `/workspace/context/_shared/_preferences.yaml`. Bundle ships a template with the program's typical deliverables declared with reasonable defaults the operator can edit. Default-lock policy (ADR-258 D9) extends to include this file — Reviewer reads but does not write.

## 4. Decisions

### D1. Bundle ships capability + maintenance + reactive; not judgment cadence.

Program bundles `docs/programs/{slug}/reference-workspace/_recurrences.yaml` ship only:
- **Mechanical substrate-maintenance recurrences** (no LLM, deterministic, sensor infrastructure)
- **Reactive triggers** (`schedule: null`, fire on events like proposal arrival or signal fire)
- **Optional**: `signal-evaluation`-shape entries when the program's trading-business heartbeat is operator-declared in `_operator_profile.md` (these are operator's trading strategy fires, not Reviewer introspection)

Bundles do **NOT** ship judgment-mode recurrences for introspection, calibration, housekeeping, or operator-facing deliverables on cadence. Those are Reviewer-authored.

### D2. Alpha-trader bundle thinning.

Delete from `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml`:

| Slug | Reason for deletion |
|---|---|
| `morning-reflection` | Reviewer introspection — Reviewer-authored cadence |
| `morning-calibration` | Reviewer introspection — Reviewer-authored cadence |
| `narrative-digest` | Housekeeping — Reviewer-authored cadence |
| `proposal-cleanup` | Housekeeping — Reviewer-authored cadence |
| `pre-market-brief` | Operator-facing deliverable cadence — operator declares preference, Reviewer authors cadence |
| `weekly-performance-review` | Operator-facing deliverable cadence — operator declares preference, Reviewer authors cadence |
| `quarterly-signal-audit` | Operator-facing deliverable cadence — operator declares preference, Reviewer authors cadence |

Net: 15 entries → 8 entries.

**Preserved entries**:
- `track-positions` / `track-account` / `track-orders` (mechanical mirrors, ADR-264)
- `track-regime` / `track-universe` (mechanical, ADR-271 Thread A)
- `signal-evaluation` (operator-declared trading-business heartbeat, market-event-anchored)
- `outcome-reconciliation` (post-close substrate-maintenance — judgment-mode but invokes the deterministic reconciler; the wake is the trigger-vehicle for substrate write, not introspection)
- `trade-proposal` (reactive only, fires on signal events)

### D3. Specs (capability library) are preserved.

The seven spec files in `docs/programs/alpha-trader/reference-workspace/specs/` (pre-market-brief.md, weekly-performance-review.md, quarterly-signal-audit.md, falsify-signals.md, performance-rollup.md, regime-state.md, ticker-snapshot.md) remain in the bundle. They fork into the operator's workspace at activation as the canonical capability library — what each kind of output looks like.

The Reviewer reads `/workspace/specs/{slug}.md` when it decides to produce that kind of output; the spec is the capability contract. This is the Claude Code skills.md analog.

### D4. New operator-authored substrate: `_preferences.yaml`.

Path: `/workspace/context/_shared/_preferences.yaml`. Machine-parsed `.yaml` per ADR-254 file-format discipline. Lives next to AUTONOMY.md and MANDATE.md — operator-authored substrate.

Schema:
```yaml
# /workspace/context/_shared/_preferences.yaml
#
# Operator-authored cadence preferences. Reviewer reads this every wake
# and authors scheduled recurrences via Schedule(action="create"|"update"|
# "archive") to honor declared preferences. Reviewer does NOT write to
# this file (default-locked per ADR-258 D9 extended).
#
# Each entry declares: a deliverable the operator wants on cadence, the
# spec it conforms to (from /workspace/specs/), and the cadence pattern
# the operator wants honored. The Reviewer authors actual scheduled
# recurrences from these declarations.

deliverable_preferences:
  - slug: pre-market-brief
    spec: /workspace/specs/pre-market-brief.md
    cadence: "@market_open - 30min"   # ADR-268 semantic schedule
    description: "Pre-market brief 30min before RTH open weekdays"
    active: true

  - slug: weekly-performance-review
    spec: /workspace/specs/weekly-performance-review.md
    cadence: "0 18 * * 0"             # Sunday 18:00 UTC
    description: "Weekly performance synthesis"
    active: true

  - slug: quarterly-signal-audit
    spec: /workspace/specs/quarterly-signal-audit.md
    cadence: "0 18 31 3,6,9,12 *"     # quarter-end 18:00 UTC
    description: "Quarter-end signal discipline ritual"
    active: true
```

`active: false` lets the operator pause a preference without deleting it. Setting `active: false` is the operator's signal to the Reviewer that the corresponding scheduled recurrence (if it exists) should be paused or archived.

### D5. Reviewer authors cadence from preferences + judgment.

Every wake, the Reviewer:
1. Reads `_preferences.yaml` (operator's declared cadence preferences for deliverables)
2. Reads `_recurrences.yaml` revision history via `ListRevisions(path="/workspace/_recurrences.yaml")` to know what's currently scheduled
3. Compares declared preferences against currently-scheduled recurrences
4. Authors new cadences (`Schedule(action="create")`) for active preferences not yet honored
5. Updates / pauses / archives cadences when preferences changed
6. Also authors its own *introspection* cadence (reflection, calibration, housekeeping) from first-principled judgment — there is no operator-declared introspection preference; the Reviewer decides when to reflect based on outcome accumulation, market regime, decision density, etc.

Every Reviewer-authored Schedule write is attributed `reviewer:ai:reviewer-sonnet-v8` per ADR-274's dispatch-layer injection. The audit trail is the existing two-table pair: `workspace_file_versions` (intent) + `execution_events` (outcome).

### D6. Default-lock policy extended.

`DEFAULT_REVIEWER_WRITE_LOCKS` in `api/services/workspace_paths.py` (per ADR-258 D9) extends to include `/workspace/context/_shared/_preferences.yaml`. The Reviewer reads operator preferences but never writes them — preferences are the operator's declaration.

### D7. E2E playbook canonized.

The testing harness's seed event is **one operator-addressed chat turn** ("hi" / "what's the state" / similar) after activation. From there, the Reviewer must self-author all judgment cadence. The empirical test of Derived Principle 18 is whether the Reviewer:

1. Reads Operating Context block (time + market state + tenure) — observable in the prompt
2. Reads `_preferences.yaml` and `_recurrences.yaml` — observable via tool calls
3. Reasons about what's needed now vs later given mandate + preferences + market state — observable in narrative
4. Takes real-time action (FireInvocation for substrate refresh, INLINE research, WriteFile to its own substrate) — observable in workspace_file_versions
5. Authors `Schedule(action="create")` for at least one declared preference (if any are active) — observable in `_recurrences.yaml` revision chain with `authored_by="reviewer:..."`
6. Optionally authors its own introspection cadence — observable in same revision chain

The system itself ships pure axiom — no infrastructure scaffolds the first Reviewer wake. The harness provides the seed.

### D8. Discipline rule for future bundles.

A new program bundle (alpha-commerce, alpha-defi, etc.) ships `_recurrences.yaml` with only substrate-maintenance + reactive + operator-declared-trading-business-heartbeat entries. Judgment cadence for introspection / housekeeping / operator-facing deliverables is **never** pre-scheduled in a bundle. Specs go in `/workspace/specs/`. Operator preferences for deliverable cadence go in `/workspace/context/_shared/_preferences.yaml`.

## 5. What this ADR does NOT do

- **No new primitives.** `Schedule` already exists per ADR-261 D4. Reading `_preferences.yaml` uses existing ReadFile primitive.
- **No schema changes.** No new tables, no new columns. Substrate is filesystem per Axiom 1.
- **No changes to Reviewer's `_PERSONA_FRAME`.** ADR-274 already added the cadence-authoring discipline section. We extend it with one paragraph naming `_preferences.yaml` as the operator's preference declaration the Reviewer honors.
- **No backwards-compatibility shim.** Per Singular Implementation: the 7 deleted recurrences are removed atomically from the bundle. Existing operator workspaces with those recurrences in their `_recurrences.yaml` are unaffected (revision chain preserved); future activations and re-forks ship the thinned bundle.
- **No removal of `/workspace/specs/`.** Specs are the capability library — they stay.

## 5b. Refinement (2026-05-14, post-run-1 e2e)

Run-1 e2e on commit `0cf84ae` showed the Reviewer reading 19 tool calls of substrate but **never reading `_preferences.yaml`** — verdict stood down with no Schedule authoring for the operator's 3 active preferences. Diagnosis: `_preferences.yaml` was prose-named in `_PERSONA_FRAME` ("remember to read this file") instead of pre-loaded into the wake envelope alongside MANDATE / IDENTITY / principles / AUTONOMY. The architectural pattern that ADR-274 used for the Operating Context block (assemble at wake, inject into envelope, every wake perceives without a tool call) is the right pattern for `_preferences.yaml`.

**Refinement decisions** (Singular Implementation; no new ADR — this is ADR-275 implementation refinement):

- (R1) `ReviewerContext` TypedDict gains `preferences_yaml: str` field. Same shape as `mandate_md`, `autonomy_md`, etc.
- (R2) `_build_user_message` injects `## _preferences.yaml — Operator's deliverable cadence preferences` block after AUTONOMY. Reviewer perceives operator cadence preferences at every wake without a tool call.
- (R3) `_PERSONA_FRAME` collapses the long `_preferences.yaml` paragraph + "ADR-275 in plain terms" paragraph + "first-wake bootstrap" paragraph into ~10 lines. The instruction is structural ("pre-loaded above; for each `active: true` preference not yet honored, Schedule"), not narrative.
- (R4) `routes/feed.py` (addressed trigger) — adds `SHARED_PREFERENCES_PATH` to the `_asyncio.gather` pre-load, passes `preferences_yaml` in the context bag.
- (R5) Audit finding: `routes/feed.py` was also not pre-loading `SHARED_AUTONOMY_PATH` — fixed in the same commit (closes a pre-existing gap surfaced by this audit; addressed-trigger Reviewer was operating without AUTONOMY context).

**Out of scope at ADR-275 refinement time**: `services/invocation_dispatcher.py` (reactive trigger — recurrence fires + proposal arrivals) passed only `recurrence_prompt + recurrence_slug + recurrence_required_capabilities + options + operating_context_block` to the Reviewer. MANDATE / IDENTITY / principles / AUTONOMY / `_preferences.yaml` were NOT pre-loaded on reactive wakes — the Reviewer's reactive wake reasoned only from the recurrence's own prompt + Operating Context, relying on tool calls to fetch governance substrate.

**RESOLVED by ADR-276** ([docs/adr/ADR-276-reactive-trigger-envelope-governance-preload.md](ADR-276-reactive-trigger-envelope-governance-preload.md)): the addressed-trigger and reactive-trigger envelopes share a single canonical assembly helper at `services/reviewer_envelope.py::load_reviewer_governance_envelope`. Both `routes/feed.py` (addressed) and `services/invocation_dispatcher.py` (reactive) call the helper and dict-spread the result into the context bag passed to `invoke_reviewer()`. Singular Implementation: one helper, two callers, identical envelope shape for both trigger paths. The Reviewer perceives full governance substrate at every wake regardless of trigger shape. Derived Principle 18 (FOUNDATIONS v8.5) now lands operationally across the entire trigger surface.

## 6. Implementation scope

- `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` — delete 7 entries
- `docs/programs/alpha-trader/reference-workspace/context/_shared/_preferences.yaml` — new file with three deliverable preferences
- `api/services/workspace_paths.py` — extend `DEFAULT_REVIEWER_WRITE_LOCKS` with `_preferences.yaml`
- `api/agents/reviewer_agent.py` — extend `_PERSONA_FRAME` with one paragraph naming `_preferences.yaml` + the Reviewer's authoring contract
- `api/test_adr275_introspection_cadence.py` — regression gate (~15 assertions)
- `docs/adr/ADR-275-introspection-cadence-reviewer-authored.md` — this file
- `CLAUDE.md` — ADR-275 entry in summary
- `api/prompts/CHANGELOG.md` — `[2026.05.14.7]` entry
- `docs/architecture/FOUNDATIONS.md` — no new amendment (v8.5 axiom already covers this); add a one-line cross-ref under Derived Principle 18

Net: ~150 LOC across 9 files (mostly doc-edits + the 1-paragraph persona extension).

## 7. Empirical test (post-deploy)

1. Purge kvk workspace
2. Reactivate alpha-trader program (auto-forks thinned bundle)
3. Operator-says-hi addressed turn from chat surface
4. Observe whether Reviewer:
   - Reads Operating Context + preferences + current schedule state
   - Takes appropriate action given pre-market state + empty findings + active preferences
   - Authors at least one scheduled recurrence via `Schedule(action="create")`
   - Attribution on the resulting `_recurrences.yaml` revision is `reviewer:ai:reviewer-sonnet-v8`

If the Reviewer takes those actions, Derived Principle 18 lands operationally. If it stands down silently or asks the operator what to do, ADR-275 needs refinement (likely in the persona-frame guidance, not the axiom).
