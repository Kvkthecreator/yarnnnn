# ADR-275: Introspection Cadence is Reviewer-Authored, Not Bundle-Scaffolded

> **⚠ Preserved by [ADR-296 v2](ADR-296-continuous-judgment-cycle.md) (2026-05-20).** ADR-275's commitment that bundles ship capability + maintenance + reactive recurrences only (not judgment cadence) is preserved and **strengthened**. Under ADR-296 v2 D3, the Reviewer's authority is over cadence preference + substrate-event interest + standing intent — the natural extension of ADR-275's "Reviewer authors its own cadence." Reactive `schedule: null` recurrence pattern as the substrate-event vehicle is **superseded** by the sibling `_hooks.yaml` substrate per ADR-296 v2 D2 — the alpha-author `pre-ship-audit` migration from `_recurrences.yaml` to `_hooks.yaml` (Checkpoint 2) is the canonical example. Bundles continue to ship initial cadence as scaffolding; the Reviewer continues to author over them; the audit trail (D5 + D6) is unchanged.

> **⚠ Amended 2026-05-21 (D9–D11 below).** The 2026-05-20 substrate contract audit ([docs/observations/2026-05-20-235100-substrate-contract-audit/](../observations/2026-05-20-235100-substrate-contract-audit/findings.md)) surfaced a contract-shape mismatch: `_preferences.yaml` is operator-declaration-shape (operator names what they want), but ADR-275 D5 specified its honoring mechanism as Reviewer-judgment-shape (Reviewer reconciles every wake). Every other operator-declaration substrate file (MANDATE, IDENTITY, BRAND, `_risk.md`, `_operator_profile.md`, `_universe.yaml`) has its content honored at activation deterministically; `_preferences.yaml` alone was deferred to runtime Reviewer judgment. The kvk-vs-alpha-trader-2 cycle-1 asymmetry (alpha-trader-2's Reviewer authored 3 Schedule calls; kvk's Reviewer authored none on identical `_preferences.yaml`) was the predicted consequence. D9–D11 split deliverable-cadence (now bundle-fork-honored at activation) from introspection-cadence (still Reviewer-authored). ADR-275's original intent — operator authority over deliverable cadence; Reviewer authority over introspection — is preserved with sharper mechanism alignment.

**Status**: **Proposed 2026-05-14** — closes the structural gap ADR-274 named but didn't finish. **Amended 2026-05-21** (D9–D11) — split deliverable-cadence from introspection-cadence honoring mechanism; deliverable cadence becomes bundle-fork-honored.

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

## 4b. Amendment (2026-05-21) — D9–D11: split deliverable-cadence from introspection-cadence

The 2026-05-20 substrate contract audit walked 18 operator-relevant substrate files across four axes (authorship layer × document purpose × contract strength × prompt-text location). Step B output identified `_preferences.yaml` as the only file whose contract names a specific Reviewer ACTION but enforces that action through verbiage strength alone.

**Compound-axiom in the audit**: a substrate file's contract shape = authorship layer × document purpose. Separation of concerns must hold on both dimensions for prompting effectiveness.

**Single sharp finding**: `_preferences.yaml` is declaration-shape (operator names what they want) but its honoring mechanism is Reviewer-judgment-shape (Reviewer decides each wake whether to act). Every other operator-declaration file has shape symmetry between declaration and honoring. `_preferences.yaml` is the structural outlier.

The audit walked seven options across the spectrum (promote, hard-gate, strengthen text, reframe-bundle-fork-honors, dissolve into MANDATE, dissolve into `_recurrences.yaml`, delete entirely). Five eliminated on first-principles grounds. **Option 4 (reframe: bundle-fork honors first-time `_preferences.yaml` declarations at activation; Reviewer reconciles subsequent operator preference changes)** survived as the structurally correct move because it restores shape symmetry with every other operator-declaration file: each is honored at activation; subsequent changes propagate via existing mechanisms.

D5's original framing — "Every wake, the Reviewer reads `_preferences.yaml` ... authors new cadences ... for active preferences not yet honored" — conflated two distinct contract shapes: (a) initial honoring at activation (deterministic, structural), (b) reconciliation of operator-authored changes (Reviewer-judgment-quality). D5 treated both as Reviewer-judgment-shape, which is the source of the cycle-1 asymmetry. D9–D11 split them.

### D9. Bundle-fork honors deliverable-cadence preferences at activation.

When `_fork_reference_workspace` runs (program activation, or operator-initiated substrate update per ADR-292), it reads the operator's `_preferences.yaml` post-fork (which itself was just forked from the bundle template) and seeds `_recurrences.yaml` accordingly:

- For each `active: true` deliverable preference whose `slug` is NOT yet a recurrence in `/workspace/_recurrences.yaml`, the fork appends a new recurrence entry with `mode: judgment`, `schedule: <preference.cadence>`, and a prompt block built from the spec at `preference.spec`.
- Attribution: `authored_by="system:bundle-fork-from-preferences"` (new ADR-209 actor sub-type per D9 + ADR-209 attribution taxonomy). Distinct from `system:bundle-fork` (which seeds the bundle's own recurrences) and `reviewer:...` (which authors Reviewer-judgment cadence).
- Idempotent: if the slug already exists as a recurrence (regardless of who authored it), the fork does NOT clobber. Operator-edited or Reviewer-authored recurrences for the same slug are preserved.
- The fork iterates declared preferences in order; revision messages name the preference declaration that drove each new entry.

**Why this honors ADR-275's original intent rather than violating it**: ADR-275's commitment is "Reviewer authors its own *introspection* cadence, not bundle-scaffolded judgment cadence." Deliverable cadence is NOT Reviewer introspection — it's operator-declared output cadence. The bundle ships *capability specs* (the spec library); the bundle-fork honors *operator declarations* of which capabilities to schedule at activation. The Reviewer's authority survives for: (a) introspection cadence (reflection, calibration, housekeeping) — first-principled judgment, always Reviewer-authored; (b) preference-change reconciliation — when operator updates `_preferences.yaml` post-activation, the Reviewer reads and authors Schedule(update|archive) per D10.

### D10. Reviewer reconciles operator preference CHANGES, not the initial set.

The persona-frame contract text simplifies from "every wake, read `_preferences.yaml` and author Schedule for declared preferences" to: **"Every wake, compare `_preferences.yaml` against current `_recurrences.yaml`. If a preference's `cadence` was edited or its `active` flag flipped, author `Schedule(action="update"|"pause"|"archive")` to honor the change."**

Initial honoring is structural (bundle-fork); ongoing reconciliation is Reviewer-judgment. The contract matches the action's appropriate enforcement layer.

### D11. Introspection cadence remains Reviewer-authored per first principles.

D1–D8 commitments around introspection cadence (Reviewer's reflection, calibration, housekeeping) are unchanged. The Reviewer authors these from first-principled judgment about outcome accumulation, decision density, market regime, etc. Bundles do NOT ship introspection cadence; operator `_preferences.yaml` does NOT declare introspection cadence. These are Reviewer's structural authority per Derived Principle 18.

The split is cleaner than ADR-275 originally drew it:

| Cadence class | Who declares | Who honors at activation | Who honors changes |
|---|---|---|---|
| **Introspection** (reflection / calibration / housekeeping) | Reviewer (first-principled judgment) | Reviewer (first wake) | Reviewer (every wake) |
| **Deliverable** (operator-facing outputs on cadence) | Operator (`_preferences.yaml`) | **bundle-fork** (D9, new) | Reviewer (D10) |
| **Substrate-maintenance** (mechanical mirrors) | Bundle author | Bundle-fork (existing) | Operator via Schedule or bundle update |
| **Operator-trading-business heartbeat** (signal-evaluation) | Bundle author + operator declaration in `_operator_profile.md` | Bundle-fork | Operator via Schedule |

### D9 Implementation: `_fork_reference_workspace` extension

```python
# In api/services/programs.py, post-existing-fork loop, before
# materialize_scheduling_index:

async def _seed_recurrences_from_preferences(
    client: Any,
    user_id: str,
    program_slug: str,
    files_written: list[str],
    files_skipped: list[str],
) -> int:
    """Seed _recurrences.yaml with operator-active deliverable preferences.

    Per ADR-275 D9 (2026-05-21 amendment). Idempotent: skips slugs that
    already exist as recurrences regardless of who authored them.

    Returns count of preference-derived recurrences seeded.
    """
    # Read post-fork _preferences.yaml + _recurrences.yaml
    # Parse preferences; for each active: true whose slug not in recurrences,
    # build a recurrence entry from spec template + cadence;
    # append to _recurrences.yaml with authored_by="system:bundle-fork-from-preferences"
    # ...
```

Attribution actor `system:bundle-fork-from-preferences` extends ADR-209 `is_valid_author` taxonomy (starts with `system:`, so the existing prefix check accepts it).

### D9 + D10 effect on the cycle-1 asymmetry

Post-D9, both kvk and alpha-trader-2 (and any future alpha-trader-program workspace) get all three deliverable cadences (`pre-market-brief`, `weekly-performance-review`, `quarterly-signal-audit`) seeded into `_recurrences.yaml` at activation. The Reviewer's first natural wake post-activation observes them already scheduled; no cadence-authoring action required for the initial set. The kvk-vs-alpha-trader-2 cycle-1 asymmetry dissolves structurally.

On operator-preference CHANGE (operator edits `_preferences.yaml`'s `cadence` for `weekly-performance-review` from Sunday 18:00 to Friday 22:00), the Reviewer's wake reads both files, observes the cadence drift, and authors `Schedule(action="update", slug="weekly-performance-review", schedule=<new>)`. The Reviewer-judgment contract (D10) survives at the layer where Reviewer judgment is genuinely appropriate.

---

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

### Original ADR-275 implementation (2026-05-14)

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

### D9–D11 amendment implementation (2026-05-21)

- `api/services/programs.py` — extend `fork_reference_workspace` with `_seed_recurrences_from_preferences` step (post-existing-fork, pre-materialize_scheduling_index). New attribution actor `system:bundle-fork-from-preferences`.
- `api/agents/reviewer_agent.py` — `_PERSONA_FRAME` cadence-authoring paragraph rewritten per D10. The contract simplifies from "every wake, read preferences and author Schedule" to "every wake, reconcile preference CHANGES (cadence edits, active flips) via Schedule(update|pause|archive); the initial set was bundle-fork-honored."
- `api/test_adr275_introspection_cadence.py` — extend regression gate with D9-D11 assertions (idempotency, attribution actor, persona-frame text shape).
- `api/prompts/CHANGELOG.md` — new `[2026.05.21.N]` entry naming the D9–D11 amendment.
- `docs/adr/ADR-275-introspection-cadence-reviewer-authored.md` — this amendment (D9–D11 + amendment banner + cross-reference to substrate contract audit observation).
- Re-fork all live workspaces (kvk, alpha-trader-2, yarnnn-author) idempotently via the existing apply_substrate_update path. Bumped-version bundles already present (alpha-trader v2026-05-20.1, alpha-author v2026-05-20.1) — no version bump needed since the per-workspace seeding is at the fork-helper layer.

Net: ~120 LOC across 5 files (1 code extension + 1 persona-frame edit + 3 doc/test).

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
