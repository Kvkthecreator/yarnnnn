# ADR-428 — Retire the Eager Foreign-Write Derive Wake

> **Status**: **Accepted** (2026-07-09, operator-ruled "retire the wake, keep the raw write"). Small, additive-by-subtraction: removes one per-write seat invocation and its prompt; changes no schema, no axiom, no reader. The ledger-intake invariant (ADR-376/DP32) is **preserved** — only a demoted mechanism is retired.
> **Date**: 2026-07-09
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimension**: Identity/Trigger (Axiom 2/4 — *when* the seat is woken) + Substrate (Axiom 1 — the invariant's carrier moves from a wake to a column)
> **Relates to**: ADR-376/DP32 (the ledger-intake axiom — `retain + attribute + cite`; this retires its MCP-slice derive *mechanism*, preserves the invariant), ADR-310 (Judged Substrate Served Everywhere — the "foreign write judged async" framing this walks back to "foreign write retained + attributed + tagged, derived on demand"), ADR-423 (`revision_kind` — the column that now carries `retain + attribute`; its §7 reserves the derive step this ADR confirms is not-yet-code), ADR-384 / the Files-model note §5 (which demote the derive step to "reserved, not the justification"), ADR-296 (the wake architecture whose `substrate_event` source this stops feeding on `remember`)
> **Amends**: ADR-376 (its "derive-and-cite placement wake IMPLEMENTED" status — the wake is retired; the invariant's `retain + attribute` half is carried by `revision_kind='observation'` per ADR-423, the `cite` half is deferred to a real derive step)
> **Preserves**: ADR-376/DP32 invariant (raw retained + attributed + cited — the raw still lands immutably in `inbound/mcp/{client}/`, attributed `yarnnn:mcp:{client}`, tagged `revision_kind='observation'`), ADR-209 (the authored substrate + revision chain — unchanged), ADR-423 (`revision_kind` column + `trace`'s `derived_from` walk — unchanged, ready for a real derive producer), the external MCP surface (three verbs — `remember`/`recall`/`trace` — behave the same to the caller; only the invisible follow-on wake is gone)

---

## 1. Context — a prompt-only mechanism for a demoted step

ADR-376 (DP32) ratified the ledger-intake invariant: every contribution enters
as an attributed **raw observation**; what the workspace derives from it is a
separate attributed **derived act** that cites its source; the raw is never
rewritten (`retain + attribute + cite`).

The MCP `remember` slice implemented the `cite` half as an **eager per-write
wake**: after a foreign LLM's `remember` landed a raw observation in
`inbound/mcp/{client}/`, `mcp_composition.submit_foreign_write_wake` enqueued a
`substrate_event` wake (slug `mcp-foreign-write-review`) whose entire payload was
a `hook.prompt` instructing the seat to **derive-and-cite** the understanding
into `operation/` with a `derived_from` line.

Two ratifications since then demoted that mechanism, without anyone retiring the
wake:

- **ADR-423 §1** states plainly: for the `remember` lane, *"no live code
  produces a derived file at all — the 'derive-and-cite' step is an LLM prompt
  contract, never deterministic code."* It moved the `retain + attribute` half
  onto a **`revision_kind` column** (`observation`), and **reserved**
  `'derivation'` "for when a derive step is real."
- **The Files-model note §5** (2026-07-09) makes the demotion explicit: the
  derive step is *"reserved, not the justification."* The value of the intake
  reframe is the `Downloads/` category move (provenance-as-column), **not** the
  derive loop.

So the wake persisted as a **prompt-only contract asking the seat to do a thing
the architecture had stopped requiring.**

## 2. Evidence — mostly ceremony, occasionally real work

Receipts from the live kvk workspace (`d5b9029b`), reading `execution_events` +
`workspace_file_versions` across the wake's recent firings:

- **1 genuine derivation**: 2026-07-08 10:32 the seat authored
  `operation/yarnnn-product/product-notes/2026-07-08-architecture-direction.md`
  with `derived_from`, message *"derive: Claude MCP observation → …"*. The
  mechanism working as designed.
- **2 no-ops at ~$0.22 each** (2026-07-08 23:37, 2026-07-09 00:02): the seat
  read the observation, judged nothing to derive, and its only output was an
  edit to `persona/standing_intent.md` logging *"observation evaluated, no
  derivation needed."* — paying a Sonnet invocation to write "I looked,
  nothing to do."

And the trigger population is not "foreign": every `inbound/mcp/claude/` write
was the **operator's own** Claude MCP session (`yarnnn:mcp:Claude`), not a
low-context third-party agent. The wake's own premise — *"the contributing LLM
did not understand this workspace's structure, which is why the derivation is
yours"* — does not hold when the writer is the operator dropping a note they
fully understand.

The interop-first future in which a genuinely-foreign agent floods raw writes
that the seat must metabolize is **deferred** (the connector capture lane is
dormant behind `CONNECTOR_CAPTURE_ENABLED`, ADR-404; multi-principal foreign
writers are ADR-373/382 direction, not launch state).

## 3. The decision in one sentence

**The eager per-write foreign-write derive wake is retired: `remember` no longer
enqueues a `mcp-foreign-write-review` `substrate_event`; the raw observation is
still retained + attributed + tagged `revision_kind='observation'` (the invariant's
live half, carried by the ADR-423 column); the `cite` half re-attaches
deliberately when a real, deterministic derive step ships (ADR-423 §7 deferred).**

## 4. Decisions

### D1 — Remove the call site
`mcp_server/server.py` (`remember` handler): drop the
`submit_foreign_write_wake(...)` call after the raw write. The raw already
committed, is attributed, and carries `revision_kind='observation'` — nothing
downstream is owed a wake.

### D2 — Delete the seam (Singular Implementation)
`services/mcp_composition.py`: delete `submit_foreign_write_wake` (its only live
caller was D1's). It was the single MCP site touching the wake contract; the MCP
tools are now fully wake-agnostic. A tombstone comment records the retirement +
the re-attachment contract for a future derive step.

### D3 — The invariant's carrier is the column, not the wake
The `retain + attribute` half of DP32 is satisfied by the raw write itself:
immutable revision (ADR-209), `authored_by='yarnnn:mcp:{client}'`, and
`revision_kind='observation'` (ADR-423). No wake required. `trace`'s
`derived_from` walk (`compose_trace`) is unchanged and works the day a real
derivation producer exists.

### D4 — The `cite` half is deferred, not deleted
When a deterministic derive step ships (ADR-423 §7), it writes
`revision_kind='derivation'` + `derived_from` as its own mechanism — not a
per-write prompt-only wake. This ADR does not design that step; it removes the
placeholder that stood in for it.

## 5. What this is NOT

- **Not a DP32 walk-back.** The invariant holds exactly; only a mechanism for
  one half moves from "eager prompt wake" to "the column + a future real step."
- **Not a change to the external MCP surface.** `remember`/`recall`/`trace`
  behave identically to the caller. Only the invisible follow-on invocation is
  gone.
- **Not `inbound/` dissolution.** The raw still lands in `inbound/mcp/{client}/`
  this pass (the directory→`Downloads/` fold is ADR-423's tree-reshape, separate).

## 6. Consequences

- **Cost/ceremony removed**: `remember` over MCP stops firing a ~$0.22
  derive-or-log seat invocation per write. At the operator's own note-taking
  cadence this is the dominant recurring cost of the memory surface, spent
  mostly on "nothing to derive" logs.
- **Legibility improved**: the Activity/cost surface no longer shows a
  `mcp-foreign-write-review` per `remember`, which read as "the system did
  something" when it usually didn't.
- **Reversible**: a real derive step re-introduces the derive act as deterministic
  code; the reader side (`trace`) already supports it.

## 7. Gates

- `api/test_adr376_ledger_intake.py` **11/11** — check #5 rewritten to assert
  the surviving truth (raw tagged `observation` + eager wake retired). A
  pre-existing stale `fake_write_revision` mock that rejected the ADR-423
  `revision_kind` kwarg is fixed with `**_kwargs` (unblocked #11 — unrelated to
  this ADR, fixed in passing).
- `api/probe_mcp_memory_surface.py` R3/R3b — updated to the post-retirement
  assertions (raw carries `observation`; the eager wake seam is gone).
- CHANGELOG `[2026.07.09.3]`.
