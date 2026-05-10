# ADR-264: Substrate-Canonical-World — External State Mediation as Mechanical Primitives

**Status**: Proposed 2026-05-10

**Companion ADR**:
- ADR-263 — Recurrence Mode: Mechanical vs Judgment, Authoring-Intent as the Wake Signal

**Amends**:
- FOUNDATIONS Axiom 1 (Substrate — Filesystem Is the Persistence Layer) — extends the persistence commitment to cover external-system state. The workspace's substrate is the canonical model of *every* piece of state the Reviewer reasons about, including state that originates in external systems.

**Preserves**:
- FOUNDATIONS Axioms 0, 2, 4, 5, 6, 7, 8, 9.
- ADR-194 v2 Reviewer substrate.
- ADR-195 v2 money-truth substrate (which is the canonical example of external-state mediation already in place).
- ADR-209 Authored Substrate — every revision attributed and retained, including substrate revisions written by mechanical primitives.
- ADR-247 three-party narrative model.
- ADR-258 (revised) curated `REVIEWER_PRIMITIVES`.
- ADR-261 unified recurrence shape.
- ADR-263 recurrence-mode field — the dispatch layer this ADR's primitives ride on.

---

## 1. Why this ADR

ADR-263 committed the recurrence-mode field (`judgment | mechanical`) and the `@primitive: ...` dispatch convention for mechanical recurrences. It deliberately deferred the question: *what primitives do mechanical recurrences invoke?*

YARNNN's substrate today represents the workspace's *internal* state coherently — operator-authored declarations (MANDATE, principles, IDENTITY, _operator_profile, _risk), accumulated narrative (decisions.md, reflections.md, _performance.md), domain context entities. But state that originates in external systems (broker positions, order fills, commerce revenue, customer churn signals, news arrivals) is **not** in substrate. It lives in the LLM's context window during a Reviewer session, fetched ad-hoc via platform tools.

This is the same Axiom 1 violation as `platform_content` before ADR-153, or `action_outcomes` SQL before ADR-195: external data living in a parallel substrate (LLM context) instead of where it belongs (filesystem). The Reviewer has no persistent "what is true about the world right now" — only what was last fetched within an LLM session.

The corrective move is the same one ADR-153 and ADR-195 made: **mirror external state into substrate continuously, by deterministic Python, on a cadence the operator declares.** The substrate becomes the canonical "what is true about the world right now." Judgment reads it.

This is not a future optimization. It is what Axiom 1 demands when honored consistently for external systems.

---

## 2. The single principle

> **The workspace's substrate is the canonical model of every piece of state the Reviewer reasons about — internal AND external. External-system mediation (API → substrate) is mechanical work performed by deterministic primitives invoked through `mechanical`-mode recurrences (per ADR-263). LLM judgment reads substrate, not external APIs directly. Platform tools survive as judgment-time conveniences for ad-hoc lookups, but they are not the primary mediation layer — `SyncPlatformState` is.**

Three consequences:

1. **Axiom 1 extension**: substrate represents both internal and external state. The boundary "internal vs external" is operationally invisible to the Reviewer — both are files at known paths.
2. **One new primitive**: `SyncPlatformState` — the canonical mechanical-recurrence-friendly primitive that wraps `(platform tool call → substrate write → diff-awareness)` as one atomic deterministic operation.
3. **Platform tool / Substrate sensor duality**: the same underlying API client serves two consumption patterns. Platform tools (LLM-callable, return to context) are unchanged. `SyncPlatformState` is the substrate-mirror surface, called by mechanical recurrences, writing to substrate.

---

## 3. Decision

### D1 — FOUNDATIONS Axiom 1 amendment: substrate is canonical for internal AND external state

Axiom 1 currently says *"What persists lives in files. Nothing else persists."* It speaks implicitly about YARNNN's *internal* semantic state (entities, theses, decisions, identities). This ADR extends it explicitly:

> **Every piece of state the Reviewer reasons about lives in the substrate, regardless of whether it originates internally or externally. External-system state (broker positions, fills, account state, commerce revenue, news arrivals) is mirrored into substrate by deterministic Python primitives invoked through mechanical recurrences. The substrate is the workspace's complete model of the world. Judgment reads substrate; it does not read external APIs as primary perception.**

This is an Axiom 1 *clarification*, not a new axiom. It makes explicit what was implicit but inconsistently honored: external state was *de facto* allowed to live in LLM context windows because there was no mechanism to mirror it into substrate. ADR-264 supplies the mechanism.

A new Axiom 1 sub-section names this:

```
### External-system state lives in substrate too

External APIs are not the persistence layer; substrate is. State observed
from external systems (Alpaca, Lemon Squeezy, GitHub, Slack, Notion, etc.)
is mediated into substrate by mechanical primitives (per ADR-264) running
on operator-declared cadences. The Reviewer perceives the world by reading
substrate, never by directly calling external APIs as primary perception.

Platform tools (api/services/platform_tools.py) survive as judgment-time
conveniences — when the Reviewer needs an ad-hoc lookup not yet mirrored,
it can call a platform tool. But the primary mediation layer is
SyncPlatformState (ADR-264), invoked by mechanical recurrences.
```

### D2 — `SyncPlatformState` primitive contract

A new primitive at `api/services/primitives/sync_platform_state.py`:

```python
SyncPlatformState(
    tool: str,                          # platform tool name, e.g. "platform_trading_get_positions"
    tool_args: dict = {},               # input arguments to the tool (channel, query, ticker, etc.)
    write_to: str,                      # substrate path template, e.g. "context/portfolio/positions/{symbol}.yaml"
    iterate_field: str | None = None,   # if set, iterate over result[iterate_field] and write per-item
    item_key: str | None = None,        # template-variable name for per-item iteration (e.g. "symbol")
    diff_aware: bool = True,            # only write substrate if content meaningfully changed since prior revision
)
```

Behavior:

1. **Call the platform tool** via `handle_platform_tool(auth, tool, tool_args)`. Returns `{success, result}` envelope.
2. **Resolve write target(s)**:
   - If `iterate_field` is None: single substrate write to `write_to` (templates resolved against caller context — `{date}`, `{user}`, etc.).
   - If `iterate_field` is set: iterate over `result[iterate_field]`, write one substrate file per item. The `item_key` names the template variable (e.g., `{symbol}` resolves to each position's symbol field).
3. **Diff-aware write**: when `diff_aware=True` (default), compute SHA-256 of new content; compare to head revision's content hash; skip write if unchanged. (The Authored Substrate already has dedup via content-addressed blobs per ADR-209; `diff_aware` skips even creating a new revision-row when nothing changed, avoiding noise in the revision chain.)
4. **Write substrate** via `services.authored_substrate.write_revision()` with `authored_by="system:sync-platform-state"` and `message="synced {tool} → {path}"`.
5. **Return** `{success: True, paths_written: [...], paths_skipped: [...], items_processed: N}`.

The primitive does **one job**: mirror external state into substrate. It does not evaluate significance. It does not emit canonical verbs. It does not invoke the Reviewer. It writes substrate; what happens next is determined by the recurrence's mode (per ADR-263) — and the recurrence is `mechanical`, so nothing wakes the Reviewer. If the substrate written by `SyncPlatformState` later needs to be perceived by the Reviewer, that happens through a *separate* `judgment`-mode recurrence that reads the mirrored substrate (the existing pattern: read context, evaluate, decide).

### D3 — `SyncPlatformState` is registered in three primitive registries

Per the existing primitive-registration discipline (ADR-258 revised, ADR-168):

- **`HEADLESS_PRIMITIVES`** — the LLM may call `SyncPlatformState` during a headless session if it needs to refresh substrate before reasoning. Rare in practice; the typical pattern is mechanical recurrences keep substrate fresh.
- **`REVIEWER_PRIMITIVES`** — the Reviewer may call `SyncPlatformState` mid-loop in the rare case it wants to refresh substrate before judging. Same rationale as headless.
- **NOT in `CHAT_PRIMITIVES`** — operators don't directly invoke `SyncPlatformState` from the feed surface. Operators author *recurrences* (via Schedule) that invoke `SyncPlatformState` mechanically. The primitive is dispatch-callable but not operator-direct-callable.

The dispatcher's `@primitive: ...` parser (per ADR-263 D5) recognizes `SyncPlatformState` invocations in mechanical-mode recurrence prompts and executes them via the same handler.

### D4 — Platform tool / Substrate sensor duality

The same underlying platform-tool handler (`handle_platform_tool`) serves two consumption patterns:

| Surface | Consumer | Output | Caller-side effect |
|---|---|---|---|
| **Platform tool** (LLM-callable) | LLM during a session (Reviewer, headless specialist) | Returns to LLM context | LLM reads result; may judge or write substrate as a *separate* tool call |
| **`SyncPlatformState`** (substrate sensor) | Cron-driven mechanical recurrence | Substrate write | Atomic mediation: API call → substrate revision in one operation |

Same API client. Same auth resolution. Different consumption pattern. Both surfaces survive — they are complementary, not competing.

The principle: **platform tools are for ad-hoc lookups during judgment; `SyncPlatformState` is for systematic substrate mirroring**. If a piece of external state is referenced often by the Reviewer, the operator authors a `SyncPlatformState` recurrence and the Reviewer reads the mirrored substrate thereafter, never calling the platform tool directly.

### D5 — Migration of alpha-trader's mechanizable recurrences

Three of alpha-trader's existing recurrences are structurally mechanical work expressed as Reviewer prompts. Migration plan:

1. **`track-universe`** — currently a Reviewer prompt that says "fetch fresh bars and write snapshots." Migrate to:
   ```yaml
   - slug: track-universe
     schedule: "0 8,11,15 * * 1-5"
     mode: mechanical
     prompt: |
       @primitive: SyncPlatformState(
         tool: "platform_trading_get_market_data",
         tool_args: { tickers_from_path: "context/trading/_universe.yaml" },
         write_to: "context/trading/{ticker}.yaml",
         iterate_field: "tickers",
         item_key: "ticker"
       )
   ```
   (`tickers_from_path` is a small extension — sensor-side resolves the universe file before iterating. If the platform tool already accepts a list of tickers, this becomes simpler.)

2. **`track-positions`** (new — does not exist today, but is the gap from earlier audit) — adds substrate-native position monitoring:
   ```yaml
   - slug: track-positions
     schedule: "* * 9-16 * 1-5"
     mode: mechanical
     prompt: |
       @primitive: SyncPlatformState(
         tool: "platform_trading_get_positions",
         write_to: "context/portfolio/positions/{symbol}.yaml",
         iterate_field: "positions",
         item_key: "symbol"
       )
   ```

3. **`outcome-reconciliation`** — the daily reconciliation already exists (ADR-195 v2). The mirror half (read fills from broker) is mechanizable; the reconciliation half (compute P&L, fold into `_performance.md`) is more complex but largely deterministic. Migrate the mirror half to `SyncPlatformState` writing raw fills to `/workspace/context/portfolio/fills/{date}/{order_id}.yaml`; keep the reconciliation half as a `judgment` recurrence (or mechanical with a dedicated `ReconcileFills` primitive — deferred to a follow-on ADR if/when the reconciliation logic warrants its own primitive).

`signal-evaluation` stays `judgment`-mode for now. The signal-evaluation work (apply boolean rules to fresh ticker bars, decide if a signal fires, ProposeAction if so) is a hybrid — the boolean rule application is deterministic, but the judgment about *whether to act* on a fired signal is the Reviewer's job. Migration to mechanical mode requires a separate primitive (e.g., `EvaluateSignalRules`) that applies the boolean rules and writes signal-fire substrate revisions; the Reviewer then wakes only on signal-fire substrate (via the `judgment`-mode ProposeAction-pipeline). This is structurally clean but is its own design call — deferred to a follow-on ADR or implementation discretion.

### D6 — System Agent attribution for mechanical recurrence writes

Per ADR-247 three-party model + ADR-209 attribution: when `SyncPlatformState` writes substrate, the `authored_by` field is `"system:sync-platform-state"`. This makes the revision attribution truthful — the System Agent (deterministic executor per ADR-257) is what actually wrote the substrate, not the Reviewer.

The revision message is `"synced {tool} → {path}"` (e.g., `"synced platform_trading_get_positions → context/portfolio/positions/NVDA.yaml"`). This makes the substrate revision log self-describing for operator audit.

---

## 4. The kernel housing

Per Derived Principle 16 (ADR-222, OS framing), `SyncPlatformState` follows the existing primitive housing pattern:

| Layer | Existing pattern | This ADR |
|---|---|---|
| **Code** | `api/services/primitives/{name}.py` per primitive | `api/services/primitives/sync_platform_state.py` |
| **Registry** | `HEADLESS_PRIMITIVES`, `CHAT_PRIMITIVES`, `REVIEWER_PRIMITIVES`, `HANDLERS` | Add to `HEADLESS_PRIMITIVES` + `REVIEWER_PRIMITIVES` + `HANDLERS`. Not in `CHAT_PRIMITIVES`. |
| **Doc** | `docs/architecture/primitives-matrix.md` | New row added. |
| **Tool definition** | `*_TOOL = {...}` constant | `SYNC_PLATFORM_STATE_TOOL` |

No new registry concept. No new directory. No new convention. Standard primitive shape.

---

## 5. Implementation surface

### New files

| File | Purpose | Approx LOC |
|---|---|---|
| `api/services/primitives/sync_platform_state.py` | `SyncPlatformState` primitive — handler + tool definition | ~150 LOC |
| `api/test_adr264_sync_platform_state.py` | Test gate (call platform tool, write substrate, diff-aware skip, iterate over results, attribution correctness) | ~120 LOC |

### Modified files

| File | Change |
|---|---|
| `api/services/primitives/registry.py` | Add `SYNC_PLATFORM_STATE_TOOL` to `HEADLESS_PRIMITIVES` + `REVIEWER_PRIMITIVES`; add handler to `HANDLERS` dict |
| `docs/architecture/FOUNDATIONS.md` | Axiom 1 amendment per D1 (new sub-section: external-system state lives in substrate too) |
| `docs/architecture/primitives-matrix.md` | New row for `SyncPlatformState` (Substrate × Mechanism cells) |
| `docs/architecture/GLOSSARY.md` | New entries: **Substrate sensor** (the dispatch shape), **Substrate-canonical world** (the axiomatic property) |
| `api/prompts/CHANGELOG.md` | Entry — primitive registry change |
| `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml` | `track-universe` migrated to `mode: mechanical` per D5; new `track-positions` mechanical recurrence added |

### Deletions

None directly required by this ADR. The existing platform-tool handlers stay (D4 dual surface). The existing Reviewer-driven `track-universe` prompt is replaced by the mechanical equivalent (singular implementation — one recurrence per slug).

---

## 6. What this fixes (validation against scenarios)

### 6.1 Position lifecycle (the gap from earlier audit)

Before ADR-264: `track-positions` doesn't exist. The Reviewer has no continuous awareness of position state. Stop hits, max-hold-reached events go unnoticed until the operator addresses or a separate signal evaluation happens to read positions.

After ADR-264: `track-positions` runs every minute during market hours as a mechanical recurrence. Substrate at `/workspace/context/portfolio/positions/{symbol}.yaml` is fresh every minute. Whatever recurrence-driven judgment process eventually reads positions (a new `position-review` `judgment` recurrence, or `signal-evaluation` extending its scope) sees current state without needing to call the platform tool.

The exit path closes substrate-natively. Operator authors `track-positions` once at workspace activation; the substrate stays fresh thereafter; judgment recurrences read the substrate.

### 6.2 The "alpha-trader's substrate is incomplete" structural gap

Before: `_performance.md` exists (per ADR-195) and is the only piece of external-state mediation. Positions, fills, account state, market data — none of them are in substrate. The Reviewer compensates by calling platform tools every session.

After: `_performance.md` is one of many substrate files reflecting external state. Positions, fills, account state, market data all live in substrate. The Reviewer reads substrate; rare ad-hoc needs still hit platform tools (D4 duality).

### 6.3 Cost shape

Before: every Reviewer session incurs platform-tool calls in the LLM context. Every call burns context tokens; the LLM has to re-fetch state it could have read from substrate.

After: mechanical recurrences fetch external state at zero LLM cost (Python only). Reviewer sessions read mirrored substrate; context tokens spend on judgment, not perception. Net cost down meaningfully.

---

## 7. What this preserves (compatibility)

- **Platform tools unchanged.** `handle_platform_tool` and all 40+ existing tool definitions stay. They serve the LLM-judgment-time consumption pattern.
- **ADR-209 substrate model unchanged.** `SyncPlatformState` writes via `write_revision`; revisions carry `(authored_by="system:sync-platform-state", message, parent_version_id)`.
- **ADR-261 recurrence shape preserved.** Recurrences stay `{slug, schedule, mode, prompt}`. Mechanical-mode recurrences invoke `SyncPlatformState` (or other mechanical primitives) via the `@primitive: ...` convention.
- **ADR-263 dispatch convention unchanged.** Mechanical-mode dispatch parses `@primitive: ...` and routes to the named primitive's handler.
- **ADR-247 three-party model preserved.** System Agent executes `SyncPlatformState`; attribution is `"system:sync-platform-state"`; the operator and Reviewer read the resulting substrate.

---

## 8. Out of scope (deferred to follow-on ADRs)

- **`EvaluateSignalRules` primitive** (or equivalent) — for migrating signal-evaluation's deterministic-rule-application half to mechanical mode while keeping the judgment half (whether to act on fired signals) as Reviewer work. Implementation discretion or separate ADR.
- **`ReconcileFills` primitive** — for migrating outcome-reconciliation's reconciliation half from Reviewer-driven to mechanical. Same shape consideration.
- **External-action primitive shape** — templated cron-driven sends (post-Slack-summary at 5pm) that don't require Reviewer judgment. ADR-263 §8 already noted this as out of scope; remains so.
- **Operator-authored significance rules** — if/when operators want structured numeric-threshold-vs-content-predicate rule declarations in YAML siblings to existing prose (the `_risk.yaml` pattern per ADR-254), that is its own design call. Today's mechanical recurrences don't need it because operator authors recurrences directly with the threshold values inline.
- **Sensor message escalation discipline** — for `flagged: ...` messages that fire repeatedly, occurrence-count discipline could be useful but is not required. Deferred until pattern emerges.
- **Sensor failure handling** — when `SyncPlatformState` fails (API down, auth expired, rate-limited), it returns `{success: False, error}`. The recurrence's execution event records the failure. Operator-facing surfacing of repeated failures (auth re-prompt, etc.) is FE territory — Phase 3 and beyond.

---

## 9. Sequence of implementation (Phase 1 → 4)

1. **Phase 1 (Documentation, this commit set)**
   1. ADR-264 (this file)
   2. FOUNDATIONS Axiom 1 amendment per D1
   3. GLOSSARY entries: Substrate sensor, Substrate-canonical world
   4. primitives-matrix.md row for `SyncPlatformState`
   5. CHANGELOG entry chained to ADR-263 [2026.05.10.3] reservation

2. **Phase 2 (Implementation, atomic with ADR-263)**
   1. `api/services/recurrence.py` — `mode` field per ADR-263
   2. `api/services/invocation_dispatcher.py::dispatch()` — branch on `recurrence.mode`; mechanical-mode parses `@primitive: ...` and routes
   3. `api/services/primitives/sync_platform_state.py` — `SyncPlatformState` handler + tool definition
   4. `api/services/primitives/registry.py` — add to HEADLESS + REVIEWER registries + HANDLERS
   5. `api/services/primitives/schedule.py` — accept `mode` parameter (per ADR-263)
   6. `api/agents/reviewer_agent.py` — `_TRIGGER_FRAMING` shrink + Literal collapse (per ADR-263)
   7. YARNNN recurrence-authoring guidance updated (per ADR-263 D6)
   8. Test gates `api/test_adr263_recurrence_mode.py` + `api/test_adr264_sync_platform_state.py`

3. **Phase 3 (FE reshape)**
   1. `/schedule` surface displays each recurrence's mode visibly
   2. Compositor reshape (deferred ADR-261 follow-up)
   3. Mid-loop human interruption surface
   4. New: surface for inspecting `SyncPlatformState` substrate writes (revision log filtered by `authored_by="system:sync-platform-state"`)

4. **Phase 4 (Operator persona refresh — alpha-trader and System Agent)**
   1. Alpha-trader bundle updates per the audit (MANDATE / IDENTITY / principles / etc.)
   2. New mechanical recurrences in `_recurrences.yaml`: `track-positions`, `track-fills`, `track-account` (using `SyncPlatformState`)
   3. `track-universe` migrated from `judgment` to `mechanical` mode per D5
   4. `outcome-reconciliation` mirror-half migrated; reconciliation-half stays as today (or moves to `ReconcileFills` per future ADR)

---

## 10. Anti-conflation summary (Axiom 0 dimensional check)

This ADR's primary dimension: **Substrate** (Axiom 1) — extends the persistence commitment to cover external-system state.

Secondary dimensions touched and explicitly preserved:
- **Identity** (Axiom 2): `SyncPlatformState` writes are attributed `"system:sync-platform-state"`; the System Agent is the executor. No new identity class; the existing `system:*` prefix pattern is honored.
- **Mechanism** (Axiom 5): `SyncPlatformState` sits at fully-deterministic. Pure Python; no LLM. The platform tool surface (LLM-callable) sits at the same Mechanism end (deterministic API call), just different consumption surface (LLM-context return vs substrate write).
- **Trigger** (Axiom 4): `SyncPlatformState` is invoked by mechanical-mode recurrences (per ADR-263). It does not introduce a new trigger shape.
- **Channel** (Axiom 6): `SyncPlatformState` writes substrate at operator-declared paths. The substrate is then readable by the Reviewer through the same compact-index + ReadFile surfaces it already uses.

No dimension is inadvertently spanning. The ADR's load-bearing claim is in one cell (Substrate), and the new primitive lives at one address in the existing primitive housing pattern.
