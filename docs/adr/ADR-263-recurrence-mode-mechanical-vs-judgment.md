# ADR-263: Recurrence Mode — Mechanical vs Judgment, Authoring-Intent as the Wake Signal

**Status**: Proposed 2026-05-10 (rewrite of original ADR-263 draft titled "Significance Vocabulary as Kernel Grammar"; the original draft was set aside after stress-test discourse revealed it solved a problem with a simpler authoring-time answer — see §10 "Why this rewrite" for the trace).

**2026-05-14 bundle-compliance note (ADR-271 Thread A)**: §1 named `track-universe` as the canonical mechanical-vs-judgment mismatch case. The deterministic Python executor for it was originally shipped by ADR-253 + ADR-254, then accidentally swept by ADR-261 Phase B's back-office cleanup, leaving the alpha-trader bundle with judgment-mode prompts for pure indicator math. ADR-271 Thread A restored the deterministic path via new `TrackUniverse` + `TrackRegime` primitives (`api/services/primitives/track_universe.py` + `track_regime.py`) and migrated both alpha-trader bundle recurrences to `mode: mechanical` with one-line `@primitive: ...` prompts. The ADR-263 thesis is now bundle-compliant on these two recurrences.

**Companion ADRs (atomic together — same architectural arc as 260/261/262)**:
- ADR-260 — Real-Time Reviewer Loop: Cron is a Nudge, Continuation is Not a Trigger
- ADR-261 — Recurrences as Prompts: Single Execution Shape
- ADR-262 — Output Topology and Specs: Filesystem-Native Output Without Registries

**Amends**:
- ADR-260 D2 (three-trigger taxonomy `addressed | reactive | scheduled`) — collapses to two (`addressed | reactive`). The `scheduled` trigger dissolves; cron is part of the environment that produces substrate revisions; the wake mechanism is uniformly reactive, with the recurrence's own `mode` field declaring whether the recurrence is itself a Reviewer wake or pure mechanical work.
- ADR-261 D1 (recurrence shape `{slug, schedule, prompt}`) — extended with one new field: `mode: judgment | mechanical`. Default is `judgment` (today's behavior is preserved for all existing recurrences).

**Preserves**:
- FOUNDATIONS Axiom 0 (six dimensions), Axiom 1 (Substrate, with ADR-209 Authored Substrate clause), Axiom 2 (Identity layers), Axiom 4 (Trigger — refined here), Axiom 5 (Mechanism spectrum), Axiom 6 (Channel), Axiom 9 (Invocation and Narrative).
- ADR-194 v2 Reviewer substrate.
- ADR-195 v2 money-truth substrate.
- ADR-209 Authored Substrate.
- ADR-247 three-party narrative model.
- ADR-258 (revised) curated `REVIEWER_PRIMITIVES`.
- ADR-261 unified recurrence shape (extended with `mode` field).
- ADR-262 filesystem-native output topology.

---

## 1. Why this ADR

ADRs 260/261/262 ratified the substrate-native real-time loop, the unified recurrence shape, and filesystem-native output. The remaining unresolved question — surfaced through alpha-trader scenario walk-throughs (operator: *"help me put in a trade and make money"*) — is **how the Reviewer perceives that something requires its judgment without inviting either (a) constant-cadence LLM polling or (b) an ungoverned proliferation of trigger types.**

The ADR-260 three-trigger model (`addressed | reactive | scheduled`) named the right shapes at the API level but left two structural ambiguities:

1. **`scheduled` was doing two unrelated jobs.** Some `scheduled` recurrences exist to do mechanical work (refresh tickers, reconcile fills); some exist to wake judgment on a clock (morning reflection, weekly review). The trigger name didn't distinguish, and operators authored both shapes as Reviewer prompts by default — paying LLM cost on every cron tick regardless of whether judgment was required.
2. **Today's recurrences invoke the Reviewer for every fire**, including pure-mechanical work the LLM has no judgment to add to (e.g., `track-universe` is currently a Reviewer prompt asking the Reviewer to "fetch fresh bars and write snapshots" — pure deterministic work expressed as an LLM prompt).

Pulled to first principles, both ambiguities collapse to one observation: **the recurrence's author already knows whether the work it scheduled is judgment-needing or mechanical.** Asking the dispatcher to derive that from substrate writes after the fact (via post-write hooks, message-vocabulary parsing, or any other read-site mechanism) is over-complicated. The wake decision belongs at the *authoring site*, encoded as a single property of the recurrence record.

This ADR commits the recurrence-mode field. It does so by **adding one field to the recurrence schema** (`mode: judgment | mechanical`) and by **amending ADR-260's three-trigger taxonomy down to two**.

---

## 2. The single principle

> **A recurrence's author declares at authoring time whether the recurrence runs as judgment work (invokes the Reviewer with its prompt) or as mechanical work (deterministic Python, writes substrate, never wakes the Reviewer). The dispatcher honors the author's declaration. The Reviewer also wakes from operator addressing (always) and from specialized reactive handlers (proposal arrival, future webhook handlers). There is no derived-from-substrate wake mechanism. Authoring intent is the wake signal.**

Three consequences:

1. **One new field on recurrences**: `mode: judgment | mechanical`. Default is `judgment` (today's behavior preserved for all existing recurrences in `_recurrences.yaml`).
2. **One trigger-axis collapse**: ADR-260 D2 narrows from three (`addressed | reactive | scheduled`) to two (`addressed | reactive`). Judgment-mode recurrences fire the Reviewer reactively (the recurrence itself is the reactive event from the Reviewer's perspective). Mechanical-mode recurrences run Python, write substrate, never invoke the Reviewer. Cron is part of the environment, not a trigger taxonomy.
3. **One cost lever for operators**: cost is a function of how many `judgment` recurrences fire per period, plus operator addressing rate, plus reactive-handler events. Operators tune cost by editing the mode field on existing recurrences (flipping a recurrence from `judgment` to `mechanical` instantly stops it from waking the Reviewer) and by adding/removing recurrences.

---

## 3. Decision

### D1 — Recurrence schema gains `mode: judgment | mechanical`

The recurrence record gains exactly one new field:

```yaml
- slug: morning-reflection
  schedule: "0 7 * * *"
  mode: judgment
  prompt: |
    Reflect on yesterday's decisions against your principles. Look at
    decisions.md and _performance.md. If patterns warrant adjustment,
    ProposeAction with full revised file content.

- slug: track-positions
  schedule: "* * 9-16 * 1-5"
  mode: mechanical
  prompt: |
    @primitive: SyncPlatformState(
      tool: platform_trading_get_positions,
      write_to: "context/portfolio/positions/{symbol}.yaml"
    )
```

`mode` is required for all new recurrences. The default at parse time, when the field is absent on legacy entries, is `judgment` — preserving today's behavior for every existing recurrence in `_recurrences.yaml`.

`judgment` recurrences invoke the Reviewer with the recurrence's `prompt` as the message envelope. The Reviewer's real-time loop runs (per ADR-260 D1).

`mechanical` recurrences are dispatched to deterministic Python execution. The `prompt` for a mechanical recurrence is expected to name a primitive invocation (e.g., `@primitive: SyncPlatformState(...)`); the dispatcher parses the invocation and runs it. No LLM session.

### D2 — `scheduled` trigger collapses into `reactive`; ADR-260 D2 amended

Per ADR-260, the three-trigger model was `addressed | reactive | scheduled`. Under D1 above, `scheduled` is no longer a distinct trigger:

- A `judgment`-mode recurrence firing wakes the Reviewer reactively. From the Reviewer's perspective, the trigger is `reactive` — a substrate-driven event (the cron firing produced the wake). Operator authoring intent is encoded in the recurrence's `mode` field, not in a separate trigger sub-shape.
- A `mechanical`-mode recurrence firing does not wake the Reviewer. It runs Python and writes substrate. There is no Reviewer trigger.

The Reviewer's `trigger` parameter collapses to two values:

```python
trigger: Literal["addressed", "reactive"]
```

**Note: this is a structural amendment to ADR-260 D2.** It does not contradict ADR-260's deeper commitment (real-time loop, mid-loop continuation is not a trigger). It refines ADR-260 in light of the recurrence-mode principle: cron's role is to fire recurrences; whether a recurrence wakes the Reviewer is a property of the recurrence's mode, not a separate trigger shape.

### D3 — Three wake sources, each with a known authoring intent

Under this ADR, the Reviewer wakes from exactly three sources, and each source declares its wake intent at authoring time:

| Source | Wake decision | Authoring site |
|---|---|---|
| **Recurrence fires** | Recurrence's `mode` field — `judgment` wakes; `mechanical` doesn't. | Operator (via YARNNN), Reviewer (mid-loop), or bundle activation (system fork). |
| **Operator addresses** | Always wakes (operator's feed message is itself the wake signal). | Operator types into the feed surface. |
| **Reactive event handler** | Specialized handlers (`on_proposal_created`, future webhook handlers) decide per their policy. Existing path; unchanged by this ADR. | The handler's source code (e.g., `services/review_proposal_dispatch.py`). |

Each wake has a clear authorship origin. The dispatcher does not derive wake-worthiness from substrate writes; it honors the declared intent at the source.

### D4 — Schedule primitive: who can author/edit recurrences

Per ADR-247 three-party narrative model + ADR-258 revised + ADR-261 D4: the `Schedule` primitive (which authors and modifies recurrences) is available to:

- **Operator via YARNNN orchestration surface** (Schedule is in `CHAT_PRIMITIVES`) — operator authors recurrences in conversation; YARNNN dispatches Schedule. Operator declares the `mode` field; YARNNN may infer it from the prompt and confirm with the operator.
- **Reviewer mid-loop** (Schedule is in `REVIEWER_PRIMITIVES` per ADR-258 revised) — the Reviewer authors its own future wake-ups. The Reviewer declares the `mode` field per the work it's scheduling.
- **System bundle-fork at activation** (`authored_by="system:bundle-fork"`) — bundle templates declare the `mode` field per recurrence; fork copies the declaration verbatim.

Three authoring sites, each declaring mode at its source. **System Agent does not independently author recurrences** — System Agent is the deterministic executor (per ADR-257) that dispatches what the Reviewer or YARNNN directs. It does not have standing intent to create recurrences on its own. (Once a Schedule call is issued by YARNNN or the Reviewer, the System Agent executes it deterministically — but the *intent* originates with YARNNN or the Reviewer.)

### D5 — Mechanical recurrence dispatch convention

A `mechanical`-mode recurrence's prompt is expected to name a primitive invocation. The convention: the prompt body matches the pattern `@primitive: <PrimitiveName>(<args>)`. The dispatcher parses the invocation, looks up the handler in the primitive registry, executes it, and writes substrate via the primitive's normal write path.

The same primitives used in mechanical recurrences are also available to the LLM as ordinary tools — they are not a separate registry. A primitive is a primitive; it can be invoked by an LLM during a session OR by the dispatcher during a mechanical recurrence fire. Singular implementation.

The first concrete mechanical-recurrence-friendly primitive — **`SyncPlatformState`**, which wraps a platform-tool call + substrate write + diff-awareness — is **scoped to ADR-264** (a follow-on ADR specifying the substrate-canonical-world commitment and the primitive's contract). ADR-263 commits the recurrence-mode field and the dispatch convention; ADR-264 commits the first primitive that uses them.

### D6 — Operator-facing surfacing of mode

When operator authors a recurrence in chat (via YARNNN), YARNNN infers the appropriate mode from the prompt and surfaces it in the confirmation:

> *"I'll schedule `track-positions` to run every minute during market hours as a mechanical recurrence — Python sync of broker positions to substrate, no Reviewer wake. Sound right?"*

vs

> *"I'll schedule `morning-reflection` at 7am daily as a judgment recurrence — wakes the Reviewer to look at yesterday's decisions. Sound right?"*

Operator can override. The mode is visible at edit time in the operator's view of `_recurrences.yaml` (and in the Phase 3 FE schedule surface).

---

## 4. The kernel housing

Per Derived Principle 16 (ADR-222, OS framing), kernel grammar is housed by a consistent pattern. Recurrence mode follows the same pattern:

| Layer | Authored-by taxonomy (ADR-209) | Recurrence mode (this ADR) |
|---|---|---|
| **Schema field** | `authored_by` (every revision) | `mode` (every recurrence) |
| **Code constant** | `VALID_AUTHOR_PREFIXES` in `api/services/authored_substrate.py` | `RECURRENCE_MODES = ("judgment", "mechanical")` in `api/services/recurrence.py` |
| **Validation function** | `is_valid_author()` | `is_valid_mode()` (or schema validation in YAML parser) |
| **Axiom anchor** | Axiom 1 (Substrate) — Authored clause | Axiom 4 (Trigger) — refined here |

No new registry concept invented — the existing housing pattern applies.

---

## 5. Implementation surface

### Modified files

| File | Change |
|---|---|
| `api/services/recurrence.py` | Add `mode` field to recurrence schema parser. Default to `"judgment"` when absent (legacy entries). Validation: `mode in ("judgment", "mechanical")`. |
| `api/services/invocation_dispatcher.py` | `dispatch()` branches on `recurrence.mode`. `judgment` → existing Reviewer-invocation path. `mechanical` → new path: parse `@primitive: ...` prompt, look up handler, execute, write substrate via primitive's write path. |
| `api/services/primitives/schedule.py` | `Schedule(action="create"/"update")` accepts `mode` parameter. YARNNN and Reviewer pass it explicitly; bundle activation reads from bundle templates. |
| `api/agents/reviewer_agent.py` | `trigger` Literal narrows from three to two values: `Literal["addressed", "reactive"]`. `_TRIGGER_FRAMING` dict shrinks to two keys. |
| `api/agents/prompts/base.py` (or `tp_prompts/`) | YARNNN's recurrence-authoring guidance: explain `mode` field, guide operator confirmation pattern (D6). |
| `docs/architecture/FOUNDATIONS.md` | Axiom 4 amended (collapse `scheduled` into `reactive`; reference recurrence-mode authoring as the wake signal). |
| `docs/architecture/GLOSSARY.md` | New entry: **Recurrence mode**. Updated **Pulse** entry: three sub-shapes collapse to two. |
| `docs/adr/ADR-260-real-time-reviewer-loop.md` | Status header note: "D2 amended by ADR-263 — three triggers collapse to two; recurrence mode encodes wake intent." |
| `docs/adr/ADR-261-recurrences-as-prompts.md` | Status header note: "D1 extended by ADR-263 — `mode` field added to recurrence schema." |
| `api/prompts/CHANGELOG.md` | Entry for the YARNNN recurrence-authoring guidance update + Reviewer trigger Literal narrowing. |
| `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` | Existing recurrences remain `mode: judgment` (no behavior change at this ADR). The `track-universe`, `signal-evaluation`, `outcome-reconciliation` recurrences that should be `mechanical` migrate as part of ADR-264's implementation alongside `SyncPlatformState`. |

### Deletions (Singular Implementation)

| Existing path | Removed by | Rationale |
|---|---|---|
| `Literal[..., "scheduled"]` in `invoke_reviewer` | This ADR (D2) | Three-trigger taxonomy collapses to two. |
| `_TRIGGER_FRAMING["scheduled"]` key | This ADR (D2) | Same. |

The recurrence walker in `invocation_dispatcher.py` is **preserved** — it still walks `_recurrences.yaml` and fires recurrences on schedule. What changes is the per-recurrence dispatch: `judgment` mode → existing Reviewer path; `mechanical` mode → new direct primitive-execution path.

`on_proposal_created` in `review_proposal_dispatch.py` is **preserved** as the proposal-arrival reactive handler with its specialized policy gate (context_domain resolution + observe-only fallback). It is one of the "specialized reactive handlers" named in D3.

`_emit_workspace_activity` in `services/primitives/workspace.py` is **preserved** — it's a separate concern (activity-log emission for two canonical paths); the original ADR-263 draft proposed dissolving it into a substrate wake hook, but under the simplified architecture there is no such hook. `_emit_workspace_activity` lives or dies on its own merits.

### What does NOT need to change

- The Authored Substrate (`write_revision`) — no post-write hook added.
- The five-verb significance vocabulary — never introduced.
- The `SIGNIFICANCE_POSTURES` prompt block — never introduced.
- The `should_wake_reviewer(authored_by, message)` predicate — never introduced.
- Sensor message-vocabulary discipline — never introduced.
- A `wake_paths.yaml` or `_significance.yaml` sibling file — never introduced.

These were all proposed in the original ADR-263 draft as mechanisms for *deriving* wake-worthiness from substrate writes after the fact. Under the simplified architecture, wake intent is declared at authoring time on the recurrence; there is nothing to derive.

---

## 6. What this fixes (validation)

### 6.1 The alpha-trader screenshot

Operator: *"help me put in a trade and make money"*

Under ADR-263 + the existing 260/261/262 stack + ADR-264 (forthcoming):

1. Operator's feed message wakes Reviewer with `addressed` posture (operator addressing → always wakes).
2. Reviewer reads MANDATE, principles, recent substrate. Sees no recent signal-fire substrate; sees no `track-positions` recurrence scheduled; decides infrastructure scaffold needed.
3. Reviewer calls `Schedule(slug="track-positions", schedule="* * 9-16 * 1-5", mode="mechanical", prompt="@primitive: SyncPlatformState(...)")` — System Agent executes. New mechanical recurrence lands in `_recurrences.yaml`.
4. Reviewer calls `Schedule(slug="signal-evaluation", schedule="0 * 9-16 * 1-5", mode="judgment", prompt="Evaluate signals against...")` — System Agent executes. New judgment recurrence lands.
5. Reviewer calls `FireInvocation(slug="signal-evaluation")` to run it once now.
6. Signal-evaluation runs as judgment recurrence; Reviewer evaluates conditions against fresh data (which `track-positions` has populated); decides to ProposeAction.
7. Loop closes within the original `addressed` session.

### 6.2 Position lifecycle (the gap from earlier audit)

Under ADR-263 + ADR-264:
1. `track-positions` (mechanical) runs every minute during market hours. Python reads broker, writes `/workspace/context/portfolio/positions/{symbol}.yaml`. No Reviewer wake. Quiet days produce zero LLM cost.
2. `signal-evaluation` (judgment) runs every hour during market hours. Reviewer wakes, reads fresh position state (already in substrate from `track-positions`), evaluates exit conditions per `_operator_profile.md` rules. On day 21 of NVDA, Reviewer notices max-hold reached, proposes `close_position`.
3. Loop closes.

The exit path closes through scheduled judgment cadence + mechanical state mirroring. Operator authored both at recurrence-creation time; the system honors the authored intent.

### 6.3 Cost discipline

Under ADR-263:
- `judgment` recurrences cost: number of fires × Reviewer-session cost. Predictable. Operator-tunable by editing `mode` field or schedule.
- `mechanical` recurrences cost: zero LLM. Bounded by Python execution time + API call rate.
- Addressed wakes: operator-message-rate × Reviewer-session cost.
- Reactive-handler wakes: proposal-arrival-rate × Reviewer-session cost.

Each cost component is observable and operator-controllable. The pricing surface is honest: workspace cost ≈ judgment-recurrence-fires + addressed-wakes + reactive-handler-wakes, all multiplied by Reviewer-session cost.

---

## 7. What this preserves (compatibility)

- **ADR-209 substrate model unchanged.** Revisions still carry `(authored_by, message, parent_version_id)`. No post-write hook; no significance-vocabulary discipline.
- **ADR-261 recurrence shape preserved with one added field.** `{slug, schedule, prompt}` becomes `{slug, schedule, mode, prompt}`. Existing recurrences default to `mode: judgment` at parse time.
- **ADR-258 (revised) `REVIEWER_PRIMITIVES` unchanged.** Schedule remains in the curated set; Reviewer can still author its own recurrences mid-loop.
- **ADR-194 v2 Reviewer substrate unchanged.** `/workspace/review/` paths preserved.
- **ADR-247 three-party narrative model unchanged.** Operator + System Agent + Reviewer remain the visible participants; recurrence-mode authoring respects the three-party authority split (D4).
- **`on_proposal_created` reactive handler unchanged.** Proposal arrival continues to wake the Reviewer with its specialized policy gate.

---

## 8. Out of scope (deferred to follow-on ADRs)

- **`SyncPlatformState` primitive contract.** The first primitive designed for use in mechanical recurrences. ADR-264 specifies its contract, the substrate-canonical-world axiom amendment to FOUNDATIONS Axiom 1, and the migration of alpha-trader's mechanizable recurrences (`track-universe`, signal-evaluation's data-fetching half, `outcome-reconciliation`'s reconciliation half) to mechanical mode using this primitive.
- **Operator-authored significance rules.** If/when operators want to declare structured numeric/content rules that mechanical recurrences evaluate, the question of where those rules live (YAML siblings to existing prose like `_risk.yaml` per ADR-254 pattern, vs hand-coded sensors) is part of ADR-264's scope.
- **External-action recurrences.** Templated cron-driven sends (e.g., "post yesterday's P&L summary to Slack at 5pm") that don't require Reviewer judgment. Today these route through `ProposeAction` + Reviewer + autonomy-gate. A future ADR may specify a primitive shape for templated direct-execution sends.
- **Operator-facing significance dashboard.** Phase 3 FE reshape includes a `/schedule`-adjacent surface that renders recurrence-fire history grouped by mode. UX shape and interaction model are downstream of this ADR.
- **Operator-facing interruption gestures.** Pause/halt/steer/override/question gestures are FE-posture decisions; deferred to Phase 3.
- **Mid-loop async resume.** ADR-260 D7 committed to synchronous-only sessions for alpha; deferred for the same reason.

---

## 9. Sequence of implementation (Phase 1 → 4)

1. **Phase 1 (Documentation, this commit set)**
   1. ADR-263 (this file — rewrite of original significance-vocabulary draft)
   2. FOUNDATIONS Axiom 4 re-amendment (collapse `scheduled` into `reactive`; reference recurrence-mode authoring)
   3. GLOSSARY entries: drop Significance verb / Wake rule / Significance posture entries; add **Recurrence mode** entry; update **Pulse** entry
   4. `api/prompts/CHANGELOG.md` reservation entry (Phase 2 will land the implementation alongside its own CHANGELOG entry)
   5. The original `docs/architecture/significance-vocabulary.md` canonical doc is **deleted** (the architecture it described is not adopted)

2. **Phase 2 (Implementation, singular)**
   1. `api/services/recurrence.py` — schema parser gains `mode` field; validation
   2. `api/services/invocation_dispatcher.py::dispatch()` — branches on `recurrence.mode`
   3. Mechanical-mode dispatch path: parses `@primitive: ...` prompt, looks up handler, executes
   4. `api/services/primitives/schedule.py` — `Schedule(action="create"/"update")` accepts `mode` parameter
   5. Reviewer trigger Literal narrowed; `_TRIGGER_FRAMING["scheduled"]` key removed
   6. YARNNN recurrence-authoring guidance updated (operator confirmation pattern per D6)
   7. Test gate `api/test_adr263_recurrence_mode.py` — schema validation, dispatch branching, no-wake on mechanical, wake on judgment, Schedule primitive accepts mode

3. **Phase 3 (FE reshape)** — unchanged scope from earlier sequencing
   1. `/schedule` surface displays each recurrence's mode visibly
   2. Compositor reshape off `task.output_kind` / `task.shape` (deferred ADR-261 follow-up)
   3. Mid-loop human interruption surface

4. **Phase 4 (Operator persona refresh — alpha-trader and System Agent)** — depends on ADR-264
   1. Alpha-trader MANDATE / IDENTITY / principles / CONVENTIONS / _autonomy.yaml / AUTONOMY.md / MANIFEST.yaml updates per the audit
   2. Mechanical-mode recurrences (`track-positions`, `track-fills`, `track-account`) added to alpha-trader bundle using `SyncPlatformState` (per ADR-264)
   3. Existing mechanical-shaped recurrences (`track-universe`, `outcome-reconciliation`'s reconciliation half) migrated from `judgment` to `mechanical` mode

---

## 10. Why this rewrite — design history

The original ADR-263 draft (titled "Significance Vocabulary as Kernel Grammar") proposed a five-verb canonical vocabulary (`occurred | crossed | flagged | cued | addressed`) leading substrate revision messages, with a `should_wake_reviewer(authored_by, message)` predicate evaluated by a post-write hook in `write_revision()` that determined whether each substrate revision invoked the Reviewer reactively.

**Stress-test discourse revealed the original architecture solved a problem with a simpler answer.** The wake decision was being *derived* from the substrate write at the read site (verb in message + author class), when the same decision was already known at the *authoring site* (the recurrence's author knew at create-time whether the work warranted judgment). Deriving downstream what was knowable upstream was the over-complication.

The original draft also assumed deterministic mechanical sensors that don't yet exist in YARNNN's codebase — every today's "mechanical-shaped" recurrence is currently a Reviewer prompt asking the Reviewer to do mechanical work. The original draft would have shipped a wake mechanism whose cost benefits couldn't materialize until mechanical sensors landed (a follow-on commitment).

The simplified architecture in this rewrite:
- **Authoring-intent is the wake signal.** No derivation, no vocabulary, no post-write hook.
- **One new field on recurrences.** `mode: judgment | mechanical`.
- **Composes cleanly with ADR-264.** Mechanical recurrences need primitives to invoke; ADR-264 specifies the first one (`SyncPlatformState`) and the substrate-canonical-world axiom amendment that motivates it.
- **No half-shipped state.** Phase 2 adds the field, the dispatch branch, and the Reviewer trigger Literal collapse — all atomic. ADR-264 adds the first mechanical primitive in its own atomic commit. Each ADR ships singular.

The discourse trace is preserved in this section so future readers can see why "significance vocabulary" was considered and rejected; the simpler authoring-time answer is the architecturally correct call.

---

## 11. Anti-conflation summary (Axiom 0 dimensional check)

This ADR's primary dimension: **Trigger** (Axiom 4) — refines the trigger taxonomy via a recurrence-record property.

Secondary dimensions touched and explicitly preserved:
- **Substrate** (Axiom 1): no new substrate; the `mode` field lives on the existing recurrence record (`/workspace/_recurrences.yaml`).
- **Identity** (Axiom 2): three authoring sites for recurrences (operator-via-YARNNN, Reviewer-mid-loop, System-bundle-fork), each declaring `mode` per its own intent. System Agent does not author independently.
- **Mechanism** (Axiom 5): `mechanical` recurrences sit at fully-deterministic; `judgment` recurrences invoke the Reviewer at fully-judgment. The `mode` field is the explicit boundary between the two ends of the spectrum.
- **Channel** (Axiom 6): `/schedule` Phase 3 FE surface renders the mode field visibly per recurrence; the operator can see their workspace's cost-shape at a glance.

No dimension is inadvertently spanning. The ADR's load-bearing claim is in one cell (Trigger), and the new property (`mode`) lives on the existing recurrence record.

---

## 12. Amendment 2026-05-12 — Capability gate at mechanical dispatch

**Triggered by**: alpha-trader workspace observation — a workspace with the alpha-trader bundle activated (which scaffolds `track-positions` / `track-account` / `track-orders` mechanical recurrences) but no Trading platform connected produced ~1 narrative entry per minute (`SyncPlatformState failed: Failed to get trading credentials`), wallpapering the Feed surface and obscuring meaningful events.

**Decision**: `_dispatch_mechanical` gains a capability gate that runs *before* the primitive handler is invoked. The gate is convention-based, no schema bump:

1. **Derivation**: a small helper `_required_platform_for_primitive(name, args)` returns the required `platform_connections.platform` value derived from primitive args. For `SyncPlatformState`, the `tool="platform_<name>_..."` arg names the platform 1:1 with the connection record. Returns `None` for primitives that don't depend on a platform connection. Future platform-bound mechanical primitives extend this helper, not the gate structure.
2. **Check**: `_platform_connection_active(client, user_id, platform)` is a single `platform_connections` lookup (`status='active'`). Fail-closed (DB error → treated as missing).
3. **Skip path on miss**: `record_execution_event(status="skipped", error_reason="capability_missing")`, return `_result_failed(...)`. The scheduler advances `next_run_at` normally — the recurrence is not paused at the substrate level (operator can pause via `Schedule(action="pause")` if they want).
4. **Transition-only narrative**: `_last_skip_reason(client, user_id, slug)` reads the most-recent `execution_events.error_reason`. If the prior reason was *not* `capability_missing`, emit one `_emit_system_narrative` entry naming the missing platform and the two operator paths (reconnect or pause). Subsequent firings stay silent until either action transitions the prior reason to something else.

**Companion change in the same commit (singular implementation discipline)**: the per-fire `_emit_system_narrative` call at the bottom of `_dispatch_mechanical` was firing on **every** mechanical run regardless of `success`. This was the actual spam source — failed credentialled mirrors emitted both the failure summary AND the housekeeping per-fire entry. Per-fire narrative is now `if success` only. Failed runs land an `execution_events` row but no Feed entry. The capability gate handles the operator-facing transition signal for the missing-credentials case; transient/unexpected failures remain visible via `execution_events` (and the upcoming observability surface) without flooding the Feed.

**What this preserves**: FOUNDATIONS Axiom 9 (every invocation emits a narrative entry) is honored at the *audit* layer (`execution_events`); the *feed* layer applies a weight-and-suppression policy on top, which Axiom 9's commentary explicitly permits ("rendering weight (material / routine / housekeeping) is UI policy, logging is complete"). The capability gate's transition entry is itself a narrative entry — Axiom 9 isn't bypassed, repeated identical entries are suppressed.

**What this does NOT do** (deferred):
- No schema field on `Recurrence` for `requires_platform`. Auto-derive from primitive args is sufficient today; explicit declaration becomes pressure-driven if a non-derivable case appears.
- No corresponding gate on judgment-mode recurrences. Judgment recurrences read substrate (not platform APIs) as primary perception per ADR-264; when they do call a platform tool the Reviewer's prompt already says "stand down quietly" and the surface_reviewer_actions narration handles operator-facing surfacing. If judgment-mode platform-API failures become a noise source, this gate generalizes trivially.
- No `Schedule(action="pause", reason="capability_missing")` auto-pause. The recurrence stays scheduled so it resumes naturally when the operator connects the platform; auto-pausing would require operator intervention to un-pause and creates a parallel state to track.

**Implementation surface**: `api/services/invocation_dispatcher.py` only. ~80 LOC added (3 helpers + gate block + `if success` guard on the per-fire narrative). Zero schema, zero new ADR, zero test_recent_commits.py impact.

**Operational follow-up**: a one-shot DB delete pruned the existing 2,328 stale `SyncPlatformState failed:` narrative rows in alpha-trader-2 / kvkthecreator workspaces. Going forward the gate prevents the spam at source.
