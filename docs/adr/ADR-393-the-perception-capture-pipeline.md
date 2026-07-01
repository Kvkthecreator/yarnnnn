# ADR-393 — The Perception/Capture Pipeline: mechanical intake is its own lane, not a wake carve-out

> **Status**: **Proposed** (2026-07-01, doc-first). No code in this commit; each implementation limb is gated to its own follow-on. **Trigger + Mechanism dimensions** — it separates deterministic upstream *capture* (Trigger: periodic, Mechanism: pure Python) from judgment *wakes* (Trigger: escalation-shaped, Mechanism: LLM). It changes **no** substrate paths, **no** write gate, **no** attribution, and adds **no** new primitive — it re-homes the dispatch of an existing one.
> **Date**: 2026-07-01
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: the operator's read while scoping ADR-392 Phase B — *"I'm uncomfortable using recurrences as the same pipeline now that context and connections are no longer part of the integrated agent architecture. It's now independent, actually more upstream and mechanical. In the past a separate pipeline wasn't warranted because everything was handled by LLM calls — is it warranted now?"* This ADR answers: **yes**, and names the lane.
> **Builds on / ratified framing**: [ADR-389](ADR-389-principal-vs-peripheral-and-the-steward-shaped-envelope.md) + [ADR-335](ADR-335-perception-field.md) (peripherals are driver-class transports with **no intent**, judged for **health not honesty**, mechanical, `system:`-attributed — the framing that makes capture NOT judgment-agent work) + [ADR-392](ADR-392-the-connector-lane.md) (the connector lane whose Phase-3 Capture this pipeline runs).
> **Amends**: [ADR-263](ADR-263-recurrence-mode-mechanical-vs-judgment.md) + [ADR-296](ADR-296-continuous-judgment-cycle.md) — the `mode: mechanical` recurrence carve-out inside the wake funnel is superseded for the **capture** class by a dedicated pipeline; recurrences narrow toward **judgment-only**. [ADR-264](ADR-264-substrate-canonical-world-and-syncplatformstate.md) — `SyncPlatformState` is unchanged as a primitive; only its *dispatch home* moves from `_dispatch_mechanical` (inside `wake.py`) to the capture scheduler.
> **Preserves**: [ADR-209](ADR-209-authored-substrate.md) (`write_revision` single write path + `system:sync-platform-state` attribution — capture writes are unchanged), [ADR-291](ADR-291-unified-cost-ledger.md) (`execution_events` stays the ledger — capture rows still land there, just written by the new lane), [ADR-376](ADR-376-ledger-intake-raw-observation-vs-derived-substrate.md) (`retain + attribute + cite` — capture is the retain-and-attribute half; derive stays a separate act).
> **Dimensional classification** (Axiom 0): **Trigger** (Axiom 4 — capture is periodic/heartbeat, not escalation-shaped) + **Mechanism** (Axiom 5 — capture sits at the fully-deterministic end; the wake funnel is the judgment end). The load-bearing claim: these are two different cells and the current code conflates them.

---

## 1. Why this ADR — the "theatre" comment is the smell

Today a mechanical capture runs through the **wake/Reviewer funnel** and escapes via a bypass. The receipt, verbatim from `api/services/wake.py::dispatch()`:

```python
if recurrence.mode == "mechanical":
    return await _dispatch_mechanical(...)   # line 370
    # "NO Reviewer invocation, NO LLM session, NO balance gate
    #  (mechanical work has zero LLM cost so the balance check would be theatre)."
```

The path a capture takes today:

```
scheduler tick
  → get_due_recurrences (thin `tasks` index)
  → cron_tick.dispatch_recurrence
  → submit_wake_proposal   ← the WAKE GATEWAY (the Reviewer-invocation funnel)
  → wake_evaluation.evaluate (Tier 1 / Tier 2 — built for judgment escalation)
  → dispatch()
  → EARLY RETURN to _dispatch_mechanical   ← capture bypasses everything above
```

Capture passes *through* the judgment funnel only to bypass it. When the code itself calls a gate "theatre" for a whole class of work, that class wants out of that pipeline. This is an **Axiom 0 dimensional conflation**: capture (Trigger = periodic, Mechanism = deterministic) is riding the wake machinery (Trigger = escalation, Mechanism = LLM) that it structurally never uses.

**Why it was correct before, and isn't now.** Pre-perception-field, *everything the system did on a cadence was an LLM call* — a single "wake → maybe-escalate-to-LLM" funnel was the right one pipeline, and ADR-263/264 bolted mechanical recurrences on as the deterministic exception. Then **ADR-335 + ADR-389 ratified that perception is upstream, mechanical, intent-free, and NOT part of the judgment-agent architecture** — peripherals are "driver-class transports … judged for health not honesty." The framing moved; the plumbing didn't. This ADR moves the plumbing.

**Why now specifically.** Only ~2 bundles use mechanical recurrences today (trader/author state-mirrors), so the carve-out was tolerable. **ADR-392 connectors introduce high-frequency per-channel capture** (a chatty Slack channel, minute-cadence) — the first real volume through this path. The forcing input is connectors; the instinct surfaced now because now is when it bites.

---

## 2. The decision

### D1 — A distinct perception/capture pipeline, outside the wake funnel

Capture becomes its **own mechanical lane**, not a recurrence and not a wake. Its shape:

```
capture scheduler tick (mechanical; sibling to the wake scheduler, not inside it)
  → walk each workspace's capture declarations
      (connector _watch.yaml selections [ADR-392 D7] + the trader/author
       state-mirror declarations migrated out of _recurrences.yaml)
  → for each due capture: run its primitive (SyncPlatformState / TrackWebSources /
      TrackRegime / …) deterministically — pure Python, zero LLM
  → write inbound/ (or the state-mirror target) via write_revision (unchanged)
  → write a per-declaration HEALTH signal (the peripheral-field substrate)
  → record execution_events (mechanical class; NOT funnel_decision-stamped)
  NO submit_wake_proposal, NO wake_evaluation, NO Tier 1/2, NO balance theatre.
```

The Reviewer wake funnel (`wake.py`) narrows to what it is *for*: **judgment**. `mode` on a recurrence stops being the discriminator that routes past a funnel; the pipeline a unit runs on IS its class.

### D2 — Recurrences become judgment-only (ADR-263 amendment)

`_recurrences.yaml` and the wake funnel serve **judgment** work exclusively. The `mode: mechanical` field is retired from the recurrence schema; mechanical work relocates to **capture declarations** (a new declaration substrate, D4). This is the singular-implementation payoff: one abstraction (recurrence) stops meaning two things (a judgment prompt OR a bypassed primitive call).

`_dispatch_mechanical` + `_parse_primitive_directive` + `_required_platform_for_primitive` + `_platform_connection_active` + the transition-guarded capability-missing narration — all currently *inside* `wake.py` — **move to the capture pipeline module** (`services/capture/…`). They are capture machinery living in the judgment module; the move is a re-home, not a rewrite.

### D3 — The health signal is the pipeline's first-class output (ADR-389 peripheral field)

A wake that fails is a judgment miss. A capture that fails is a **health** signal — ADR-389: "the only judgment a peripheral invites is about its *health* … is the feed live? is the connection expired? is the data stale?" The capture pipeline writes a per-declaration health/freshness record (`_capture_signal.yaml` sibling, mirroring `TrackWebSources`'s `_watch_signal.yaml`). This is:

- the substrate the steward's **peripheral-field fact** (ADR-389, `freddie_envelope.py::_peripheral_field_fact`) should read (today it reads bare `platform_connections.status` — this gives it real freshness);
- **the data source for ADR-392 Phase B** (the "observed" half of the selection surface's declared × observed). Phase B was blocked on exactly this signal; this pipeline produces it.

The health signal is NOT `execution_events` (that's the cost/audit ledger, ADR-291 — capture rows still land there for spend/debug). Health is *substrate* (Axiom 1), operator- and steward-readable, per-declaration.

### D4 — Capture declarations: one substrate for "what to mechanically pull"

Capture is declared, never crawled (DP27). The declaration substrate:

- **Connectors**: the ADR-392 D7 `operation/_connectors/{platform}/_watch.yaml` (selected channels/pages) — already built; the capture pipeline reads it directly (this is the consumer ADR-392 D3 named).
- **State mirrors** (trader positions/account/orders, author web/regime): migrated out of `_recurrences.yaml` mechanical entries into capture declarations. Same primitives, new home.
- **Cadence**: each declaration carries its own schedule (the state mirrors are minute/5-minute; connectors carry the operator's chosen cadence). The capture scheduler walks these; the thin scheduling index (`tasks`, ADR-231) generalizes to index capture declarations too, or a sibling index — an implementation call (§4).

### D5 — What the wake funnel KEEPS (the boundary is sharp)

Not everything mechanical leaves. **Substrate-event hooks** (`_hooks.yaml`, ADR-296) stay wake-side: a hook fires *because substrate changed* and its purpose is *to wake judgment* — it is escalation-shaped by construction. Capture is the opposite: it runs on cadence to *make* substrate fresh, and wakes no one. The line: **does it exist to feed judgment (wake) or to mirror the world (capture)?** Hooks feed judgment; captures mirror the world.

---

## 3. What this fixes (validation)

1. **Dimensional purity** — capture stops riding a funnel it bypasses. Trigger + Mechanism cells no longer conflated (Axiom 0).
2. **The peripheral-field fact gets real data** — freshness/health per declaration, not bare connection status (ADR-389's envelope gap).
3. **ADR-392 Phase B unblocks** — the "observed" freshness signal now has a producer.
4. **Connector volume is handled in its own lane** — a minute-cadence chatty channel doesn't touch the judgment scheduler, `wake_queue` dedup-for-judgment, or the balance gate.
5. **Recurrences get singular meaning** — a recurrence is a judgment prompt, full stop. `mode` stops overloading it.
6. **The derive step (ADR-392) clarifies** — capture (this pipeline, mechanical) and derive (a judgment act reading inbound/, wake-side) are now cleanly on opposite sides of the line, exactly as ADR-376's retain-vs-derive split wants.

---

## 4. Open questions (for the ratification / build)

1. **Scheduler topology** — one process that ticks both lanes (capture walk + wake walk, sequentially) vs two Render Crons vs `pg_cron`. The *architectural* guarantee (capture runs independent of and upstream of judgment) is what ratifies; deployment shape is a code-PR call (mirrors the ADR-296 §scheduler open question).
2. **Scheduling index** — extend the thin `tasks` index to carry capture declarations, or a sibling `captures` index. `tasks` is already a reconstructable scheduling projection (ADR-231 D4); reuse is likely cleaner than a parallel table.
3. **Health signal schema** — `_capture_signal.yaml` per-platform (mirroring `_watch_signal.yaml`) vs one workspace-level capture-health file. Per-platform matches the connector-watch topology + Phase B's per-channel need.
4. **State-mirror migration** — trader/author mechanical recurrences move to capture declarations. Byte-for-byte behavior preserved (same primitives, same cadence); the migration is bundle-scoped (re-author `_recurrences.yaml` mechanical entries → capture declarations). Sequencing: after the pipeline exists, before `mode: mechanical` is deleted.
5. **`execution_events` shape** — capture rows keep landing there (spend/audit) but `funnel_decision` is meaningless for them (there was no funnel). Drop the field for capture rows, or stamp a sentinel. Cosmetic; decide at build.
6. **Does the derive step ride this pipeline or the wake side?** Derive reads inbound/ and writes operation/ *with judgment* (what's worth distilling). Leaning: derive is a **judgment recurrence** (wake-side) that reads the capture pipeline's output — capture and derive stay on opposite sides of the line (D5). But a purely-mechanical derive (template distillation, no judgment) could ride capture. Decide when the derive step is built (ADR-392 §5 step 8).

---

## 5. Implementation sequence (each limb its own commit, gated on ratification)

1. **Ratify** this ADR + the model (distinct lane) + the open-question calls that block build (scheduler topology, index, health schema).
2. **Extract** `_dispatch_mechanical` + helpers out of `wake.py` into `services/capture/` — a re-home, no behavior change, with the existing mechanical recurrences still pointed at it (temporary bridge).
3. **Build the capture scheduler + declaration walk** — reads capture declarations, runs primitives, writes the health signal.
4. **Migrate** connector `_watch.yaml` (already built) + trader/author state-mirrors into capture declarations.
5. **Retire** `mode: mechanical` from the recurrence schema + delete the `wake.py` carve-out (Singular Implementation — the bypass is gone, not left as a fallback).
6. **Wire** the peripheral-field fact to read the health signal (ADR-389 envelope upgrade) — this is also ADR-392 Phase B's data source.

---

## 6. Anti-conflation summary (Axiom 0 dimensional check)

Primary dimensions: **Trigger** (Axiom 4 — capture is periodic/heartbeat, a distinct trigger shape from the escalation-funnel wake) + **Mechanism** (Axiom 5 — capture is fully-deterministic Python; the wake funnel is the LLM-judgment end). The ADR's whole thesis is that these two cells were conflated in one pipeline and the fix is to separate them.

Secondary and explicitly preserved: **Substrate** (Axiom 1 — capture writes are unchanged `write_revision` calls; the new thing is the health *signal*, which is substrate not a table); **Identity** (Axiom 2 — capture stays `system:`-attributed, the mechanism is the author of record per ADR-389). No dimension spans without necessity: the split is precisely along the Trigger/Mechanism seam that the "theatre" bypass was papering over.
