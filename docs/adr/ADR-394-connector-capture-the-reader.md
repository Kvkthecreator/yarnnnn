# ADR-394 — Connector Capture: making a connected platform actually READ

> **Status**: **Accepted** (2026-07-01) — ratified by the operator; implementation lands in the §5 sequence. This ADR closes the reader gap left open after ADR-392 (the connector lane) + ADR-393 (the capture pipeline): a connected Slack/Notion/GitHub *has a full UI and a capture lane, but nothing pulls its content into substrate*. It resolves the two remaining forks (fan-out mechanism + capture-declaration authoring), ratifies the derive placement **by reference** (no new derive step), and wires the retention GC.
> **Date**: 2026-07-01
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: the Phase-C scoping of the connector arc (memory `project-connector-phasec`). The five verified gaps (file:line receipts below) are: (1) the watch→capture bridge has no consumer, (2) Slack doesn't fit the single-tool-result capture shape, (3) there is no per-workspace capture-declaration authoring path, (4) the derive step is unbuilt, (5) the retention GC is not scheduler-wired.
> **Builds on / ratified framing**: [ADR-392](ADR-392-the-connector-lane.md) (the four-phase connector lane: Connect · Select · **Capture** · Derive; §5 steps 4/5/8 are the unbuilt limbs this ADR builds) + [ADR-393](ADR-393-the-perception-capture-pipeline.md) (the capture lane `services.capture` — deterministic, outside the wake funnel; connector captures are its first real per-channel volume) + [ADR-389](ADR-389-principal-vs-peripheral-and-the-steward-shaped-envelope.md)/[ADR-335](ADR-335-perception-field.md) (a connector is a **peripheral** — driver-class, intent-free, `system:`-attributed, judged for health-not-honesty; its selected slices are a **declared watch**, DP27).
> **Preserves**: [ADR-376](ADR-376-ledger-intake-raw-observation-vs-derived-substrate.md) (`retain + attribute + cite` — connector capture is the *retain-and-attribute* half; **derive stays the separate seat act ADR-376 line 77 already defines**, NOT a new cadence), [ADR-209](ADR-209-authored-substrate.md) (`write_revision` single write path — connector raw is an ordinary attributed revision, `system:sync-platform-state`), [ADR-286](ADR-286-single-writer-per-path.md) (single-writer — `_captures.yaml` has one writer; the seed act is idempotent), [ADR-254](ADR-254-file-format-discipline.md) (`_`-prefixed yaml is machine-parsed), [ADR-264](ADR-264-substrate-canonical-world-and-syncplatformstate.md) (`SyncPlatformState` is unchanged — connector fan-out is a *new sibling primitive*, not an overload of the state-mirror primitive).
> **Amends**: nothing. This is additive — it builds the three unbuilt ADR-392 §5 limbs (4, 5, 8) without changing any decided contract.
> **Dimensional classification** (Axiom 0): **Substrate** (Axiom 1 — how connector context enters: raw retained in `inbound/`, understanding derived-and-citing) + **Trigger** (Axiom 4 — the connector capture is periodic/mechanical, wakes no one). The load-bearing separation: **capture is mechanical and cadenced; derive is judgment and on-engagement — they are two cells and must not collapse into "a scheduled thing that pulls-and-summarizes."**

---

## 1. Why this ADR — the connector reads nothing

A workspace can connect Slack, see the connection in the Channels → Connections pane, open the per-connection Manage subsurface, pick channels to watch, and set a retention window (all shipped: ADR-392 Phase B, PR #18). The freshness column shows **"not reading yet"** on every channel — honestly, because **nothing pulls the channels' content into substrate.** The four-phase connector lane (ADR-392 D1) is:

```
1 Connect  — OAuth                          ✅ (platform_connections)
2 Select   — an operator watch declaration  ✅ (operation/_connectors/{platform}/_watch.yaml)
3 Capture  — pull selected slices' raw       ❌ THE GAP
             into inbound/{platform}/{selector}/
4 Derive   — distil into operation/, citing   — inherits the seat's existing act (ADR-376)
```

Phase 3 is the hole. Three structural reasons it doesn't run today, each with a receipt:

**(a) The watch declaration has a writer and a reader, but no consumer.** `services/connector_watch.py::read_selected_ids` (line 137) is documented as "the consumer surface: SyncPlatformState's capture recurrence reads these" — but `sync_platform_state.py` never imports it. Its only live callers are the FE selection route (`routes/integrations.py`) + tests. The bridge from *what the operator selected* to *what gets captured* does not exist.

**(b) Slack doesn't fit the capture shape.** `SyncPlatformState` (the only connector-capable capture primitive) iterates **one tool result as a list** (`sync_platform_state.py:326`, `result[iterate_field]`). That fits the trader: `platform_trading_get_positions` returns a `positions` list, iterated per-symbol in one call. But `platform_slack_get_channel_history` (`platform_tools.py:1806`) takes a **single `channel_id`** — capturing N selected channels means **looping N tool calls**, which `SyncPlatformState` structurally cannot do. It can fan out over *items in one result*, not over *a declaration of read targets*.

**(c) No per-workspace capture-declaration authoring.** `_captures.yaml` exists **only via `fork_reference_workspace`** (`programs.py:568,778` — materializes the capture index from a *forked* bundle file). `walk_workspace_captures` reads one canonical `/workspace/_captures.yaml`. A **bare workspace** (no bundle) that connects Slack has no `_captures.yaml` at all, and `services/capture/` has **no declaration write path** — only `write_capture_signal` (health), never a *what-to-capture* writer. Connectors are kernel-universal (`orchestration.py::CAPABILITIES` `read_slack`; ADR-353 §15.2), so their capture cannot depend on a program.

And two downstream limbs are un-wired:

**(d) Derive is unbuilt** (but its *placement is already decided* — §4). **(e) The retention GC** (`connector_retention.py::prune_raw_lane`, line 115) is called only by tests; the scheduler tick (`unified_scheduler.py:355`) drains captures but never prunes.

---

## 2. The decision

### D1 — A new `CaptureConnector` primitive fans out over the watch declaration

`SyncPlatformState` stays exactly what it is (ADR-264): a **state mirror** (one tool call → one result → substrate, `write_to`-direct) plus the single-shot connector-capture case it already supports. Connector **fan-out** — looping a per-selector read tool over a *declared* watch — is a **new sibling primitive**, `CaptureConnector`, not an overload.

```
@primitive: CaptureConnector(
  platform="slack",
  read_tool="platform_slack_get_channel_history",
  selector_arg="channel_id",           # the tool arg each selected id fills
  tool_args={"limit": 50},             # static args merged into every call
  ext="md"                             # raw-lane file extension (default md)
)
```

Behavior (deterministic, zero LLM):

1. Read `operation/_connectors/{platform}/_watch.yaml` via `connector_watch.read_selected_ids` — **giving the reader its consumer** (closes gap (a)).
2. For each selected id: call `handle_platform_tool(auth, read_tool, {**tool_args, selector_arg: id})`.
3. Write each raw result to `inbound/{platform}/{id}/{observed_at}.{ext}` via `resolve_capture_path` (reused from `sync_platform_state.py` — the raw-lane path convention is not duplicated) through `write_revision`, attributed `system:sync-platform-state` (the peripheral is the mechanism, not a principal — ADR-288).
4. Diff-aware: an unchanged channel's snapshot is skipped (no revision noise), same as `SyncPlatformState`.
5. Return `{success, paths_written, paths_skipped, items_processed}` — the shape the capture lane already reads for its health signal.

**Why a new primitive, not an extension of `SyncPlatformState` (the fork, resolved):** the fan-out concern (loop a read tool over a *declaration of targets*) is a different job from the state-mirror concern (mirror *one call's result* into substrate). Overloading `SyncPlatformState` with `iterate_from_declaration=true` would make one primitive mean three things (state mirror / single capture / watch-fanned capture) and bleed the connector-watch dependency into the ground-truth state-mirror primitive. Singular-implementation is *one honest job per primitive*, so the fan-out is its own primitive. `CaptureConnector` depends on `connector_watch`; `SyncPlatformState` stays free of it. `observed_at` is caller-stamped by the capture lane (Axiom 1 / resume safety — the primitive never reads the clock).

`CaptureConnector` registers in `HANDLERS` + `HEADLESS_PRIMITIVES` + `FREDDIE_PRIMITIVES` (NOT `CHAT_PRIMITIVES` — operators don't invoke capture directly; same policy as `SyncPlatformState`, ADR-264 D3). The capture lane's platform-capability gate (`lane.py::_required_platform_for_primitive`) is extended to derive the required platform from `CaptureConnector`'s `platform=` arg (today it only reads `SyncPlatformState.tool`), so a capture on a disconnected platform skips (health-signals) rather than fires-and-fails.

### D2 — The connector capture declaration is seeded at select-time

When the operator saves a watch selection with **≥1 channel selected**, the existing selection write path (`routes/integrations.py` PUT selection → `connector_watch.write_selection`) **also idempotently ensures a kernel-universal capture entry** in `/workspace/_captures.yaml` and materializes the capture index. Deterministic Python, zero LLM, no new primitive — the selection UI already exists (Phase B).

```
On PUT selection (selected_count ≥ 1):
  ensure /workspace/_captures.yaml contains, upserted by slug:
    - slug: capture-slack                       # capture-{platform}
      schedule: "@every 15min"                  # kernel default; operator-tunable later
      primitive: |
        @primitive: CaptureConnector(
          platform="slack",
          read_tool="platform_slack_get_channel_history",
          selector_arg="channel_id",
          tool_args={"limit": 50}
        )
      display_name: "Slack Channel Capture"
  materialize_capture_index(client, user_id)

On PUT selection (selected_count == 0):
  pause the capture-{platform} entry (paused: true) — the declaration stays
  legible ("this platform is watched but nothing is selected"), but the
  scheduler leaves next_run_at None so it never fires.
```

The seed is a **single write path** into `_captures.yaml` (ADR-286 single-writer: the connector-seed is the sole writer of `capture-{platform}` slugs; a bundle that also captures a connector would be an authoring conflict the operator owns — same rule ADR-393 §7 states for recurrence↔capture slug collisions). The upsert reads the current `_captures.yaml` (empty for a bare workspace, or a forked bundle's file), replaces/inserts *only* the `capture-{platform}` entry, and re-writes via `write_revision`. Bundle entries are never touched.

The **per-platform read-tool binding** (`read_tool` / `selector_arg`) is a kernel-universal table keyed on platform (Slack → `get_channel_history`/`channel_id`; the Notion/GitHub bindings land when those connectors get a selection UI — Slack is the first). It lives beside the existing `orchestration.py::CAPABILITIES` connector table, not in a bundle.

**Why seed-at-select, not a captures-authoring primitive (the fork, resolved):** connectors are kernel-universal and their capture is fully determined by (platform, selected ids) — there is no judgment in *whether* to capture a selected channel, so no actor needs to author the declaration. A general `ManageCapture` primitive (a `Schedule`-analogue) would be the right shape *if* arbitrary actors authored arbitrary captures, but that is a broader model with its own gate + surface, and the connector case does not need it. Seed-at-select keeps the connector's capture declaration a **deterministic function of the operator's selection** — the same shape the watch declaration itself has. The captures-authoring primitive stays a **named-but-unbuilt** option for a future where the steward authors non-connector captures; the connector case does not force it.

### D3 — Derive is the seat's existing act, ratified by reference (no new step)

**This is the decision the operator sharpened, and it is the load-bearing separation-of-concerns of this ADR.** ADR-393 §7-6 *leaned* derive wake-side but deferred ratification "to when it's built." It is now built-adjacent, so this ADR ratifies it — **and ratifies that Phase C builds no derive step of its own.**

Derive is **not** a scheduled LLM job. Framing it as "a derive recurrence that fires on a cadence and summarizes the channel" reintroduces exactly the wake-vs-capture conflation ADR-393 killed for capture. The disciplined framing, already canon in ADR-376 line 77 and **already built for the MCP slice** (`mcp_composition.py` — read raw → author a *new* `operation/…` object carrying `derived_from` → raw stays immutable → `trace` walks it → `recall` reads derived-first):

- **Capture** (mechanical, cadenced, wakes no one) lands raw in `inbound/slack/{channel}/{ts}.md`.
- The raw **sitting un-derived in `inbound/`** *is the legible state* — "captured, not yet distilled" (ADR-376 line 77: *"'leave in inbox' becomes 'no derived object yet'"*).
- **Derive** is the seat's **derive-and-cite placement act**, performed **when its judgment engages that raw** — not on a cadence, not as a new primitive, not connector-specific. It authors a new `operation/…` object with `derived_from: [inbound/slack/…]`, attributed `reviewer:ai`.

```
CAPTURE  (mechanical · cadenced · wakes no one · CaptureConnector)
   → inbound/slack/{channel}/{ts}.md          [raw, immutable, system:sync-platform-state]
          │  (raw sits un-derived — this IS the legible "not distilled yet" state)
          ▼
DERIVE   (seat judgment · on engagement · NOT scheduled · NO new code)
   seat reads the raw when its judgment engages it
   → authors NEW operation/… with derived_from: [inbound/slack/…]   attributed reviewer:ai
   = the SAME derive-and-cite act MCP `remember` placement already performs
   = zero new connector code; the connector raw inherits the built path
```

So **gap 4 collapses**: Phase C builds *nothing* for derive. It ratifies (by reference to ADR-376) that connector raw is engaged by the same seat act as MCP raw, and that the FE "derived understanding" view + the `trace` raw↔derived chain light up for connectors the moment the seat derives — no connector-specific derive wiring. This is the separation of concerns paying off: capture is a Trigger/Mechanism-periodic-deterministic cell; derive is a Purpose/Mechanism-judgment cell; they do not share a pipeline.

### D4 — The retention GC wires into the capture lane's maintenance phase

`connector_retention.prune_raw_lane(cited_paths=...)` (built, ADR-392 §5 step 5) runs in the scheduler tick's maintenance phase, **as a sibling to the capture drain** (`unified_scheduler.py:355`, after `drain_due_captures`). `cited_paths` is computed from a `GROUP BY`-shaped read over `derived_from` metadata (the raw paths the seat has already cited) — a cited raw is **evidence** and is never pruned; only un-cited raw past the workspace's `retention_days` window (`connector_retention.resolve_retention_days`) is dropped. This keeps the raw lane **evidence, not a crawl archive** (ADR-376 line 70). GC runs per-workspace, best-effort, logged — a prune failure never blocks a capture.

---

## 3. What this fixes (validation)

| Gap (receipt) | Closed by |
|---|---|
| (a) watch reader has no consumer (`connector_watch.py:137`) | D1 — `CaptureConnector` reads `read_selected_ids` |
| (b) Slack doesn't fit the capture shape (`sync_platform_state.py:326` vs `platform_tools.py:1806`) | D1 — fan-out primitive loops the per-selector read tool |
| (c) no capture-declaration authoring (`programs.py:568` fork-only) | D2 — seed-at-select-time into kernel-universal `_captures.yaml` |
| (d) derive unbuilt | D3 — **inherits the seat's existing derive-and-cite act (ADR-376); nothing to build** |
| (e) GC not wired (`prune_raw_lane` test-only) | D4 — scheduler maintenance-phase wiring |

**The honest gap this closes on the FE:** the Phase-B freshness column ("not reading yet") starts showing real observed-at timestamps the moment `capture-slack` runs its first cadence — **no FE change needed for the basics.** The only FE additions are the "derived understanding" view + the `trace` chain, which light up when the seat derives (D3) — those are follow-on, not Phase C.

---

## 4. Anti-conflation summary (Axiom 0 dimensional check)

| Concern | Cell | Where it lives | Does NOT bleed into |
|---|---|---|---|
| Pull selected channels' raw | Trigger=periodic · Mechanism=deterministic | `CaptureConnector` (capture lane) | the state-mirror primitive (`SyncPlatformState` stays free of the watch) |
| Decide what to capture | (no judgment — a function of the operator's selection) | seed-at-select (deterministic Python) | a captures-authoring primitive / an LLM |
| Distil raw → understanding | Purpose=judgment · Mechanism=LLM · **on engagement, not cadence** | the seat's derive-and-cite act (ADR-376, already built) | the capture lane / any new scheduled step |
| Bound the raw lane | Trigger=periodic · Mechanism=deterministic | `prune_raw_lane` (capture-lane maintenance) | the derive act (cited raw is evidence, never pruned) |

The one line: **capture is mechanical and cadenced; derive is judgment and on-engagement; the operator's selection is deterministic; retention is mechanical GC over un-cited raw.** Four cells, four homes, no conflation.

---

## 5. Implementation sequence (each limb its own commit, gated on ratification)

1. **Ratify** this ADR. No code until then.
2. **`CaptureConnector` primitive** (D1) — new `api/services/primitives/capture_connector.py`; reuse `resolve_capture_path` from `sync_platform_state.py`; register in `HANDLERS` + `HEADLESS_PRIMITIVES` + `FREDDIE_PRIMITIVES`; extend `lane.py::_required_platform_for_primitive` to read `CaptureConnector.platform`. Test gate: watch with 2 selected channels → 2 `handle_platform_tool` calls → 2 raws in `inbound/slack/{id}/{ts}.md`; diff-aware skip on unchanged; disconnected-platform skip. CHANGELOG (new primitive).
3. **Seed-at-select** (D2) — the kernel read-tool binding table + the idempotent `_captures.yaml` upsert on the PUT-selection route + `materialize_capture_index`; pause-on-empty. Test gate: bare workspace, select 1 channel → `_captures.yaml` gains `capture-slack` + index row; deselect all → paused; re-select → resumed; a forked bundle's captures untouched.
4. **GC wiring** (D4) — `prune_raw_lane` in the scheduler maintenance phase with `cited_paths` from a `derived_from` read. Test gate: un-cited raw past window pruned; cited raw kept; prune failure non-fatal.
5. **Derive** — **nothing to build** (D3). A doc note + a `trace` round-trip test proving connector raw → seat derive-and-cite → `derived_from` chain walks, using the *existing* MCP-slice path (no connector-specific code). This is validation, not construction.

**Bundle conformance:** D2 seeds a `capture-{platform}` entry only into a *live workspace's* `_captures.yaml`, never a bundle reference-workspace. The bundle-conformance tests (`test_adr287_bundle_conformance.py`, `test_adr230/268/269`) pin the *bundle* `_captures.yaml` shapes — untouched by this ADR. Confirm they stay green (no bundle file changes).

---

## 6. What this ADR deliberately does NOT do

- **No derive cadence, no derive primitive, no derive recurrence** (D3) — the separation of concerns the operator hardened. Derive is the seat's engagement act.
- **No `SyncPlatformState` change** (D1) — the state-mirror primitive is untouched; fan-out is a sibling.
- **No captures-authoring primitive** (D2) — named-but-unbuilt; the connector case doesn't force it.
- **No new gate / table / attribution** — connector raw is an ordinary `write_revision` (ADR-209); the capture lane + `execution_events` are unchanged (ADR-393).
- **No Notion/GitHub bindings yet** — the read-tool table has one entry (Slack, the first connector with a selection UI); the others land with their UIs.
