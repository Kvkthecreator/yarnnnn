# ADR-594: The connection is a rail — fixed landing grammar, and the string reaches through it

> **Status**: **Accepted** (2026-08-21, operator-ratified — "yes, aligned in full.
> would like to delegate implementation details as we're aligned" — closing the
> Strings-audit discourse of the same day; the audit measured the state this ADR
> re-cuts). **BUILT** with this ratification.
> **Date**: 2026-08-21
> **Dimension (Axiom 0)**: **Mechanism** (capture becomes consumer-invoked in
> fact, not only in principle) + **Substrate** (the landing grammar fixes;
> the settings store empties) primary; **Identity** (the credential posture of
> machinery executing standing intent) secondary.
> **Supersedes / amends**: ADR-582 **D1's "operator-chosen destination" clause
> and D3** (the destination dial) — the writer thesis itself is untouched;
> ADR-591 **D3** (the named, unbuilt consumer seam — this ADR builds its first
> caller); ADR-580 (the digest — superseded as a special case of an md string,
> the ADR-569 generalization applied a second time); ADR-569 D4 (connector
> sources go from declared-but-starved to live).
> **Relates to**: ADR-423 (raw-ness is the `revision_kind`, never the address —
> the receipt this ADR completes), ADR-401 (connection = peripheral), ADR-576
> (doors, never rooms), ADR-585 (turn reach — the sibling disposition,
> untouched), ADR-577 (credential custody — the posture §D2 decides), ADR-588
> (folders are derived — why the raw layer must not carry meaning).

---

## 1. Context — the dial that outlived both of its reasons

ADR-582 ratified two things in one sentence: *"a connector is a writer of
attributed observation files to an operator-chosen destination."* The writer
half is proven and stays. The destination half was already semantically inert
when ratified — ADR-582's own D3 re-keyed raw-visibility to the ledger
(`revision_kind='observation'`, never embedded, **wherever it lands**), so the
path stopped carrying meaning the same day it became choosable. Its one
remaining *behavioral* differential — a custom destination opted out of the
retention GC — was deleted by ADR-591 with the GC itself. What remained was a
wiring-time dial whose entire effect was which folder raws visually appear in.

Measured 2026-08-21 (production): 3 connections, **zero** custom destinations
ever set. The dial was never used.

The operator's architectural statement, ratifying this re-cut: at 10s–100s of
connections, per-connection folder designation "creates way too much slop …
what we're really looking for architecturally on connections is purer and
closer to conventional chats — **connection is just the set-up and rail that
ALLOWS the access**," with consumption driven **intent-first** by whatever
reads (an ephemeral chat turn, a string's standing declaration).

Meanwhile ADR-591 had deleted the capture clock and named its replacement — a
consumer-invoked seam — without building the caller. The Strings audit (same
day) measured the consequence: `run_connector_capture` had **zero production
callers**, so ADR-582 D6's `{connector, selector}` string sources were inert
end-to-end — a declared source metering `no_sources_fetched` forever against
snapshots nothing lands.

These are one decision, not two: fix the landing grammar (the rail carries no
placement choice) and give the seam its first caller (the string's run reaches
through the rail and retains a receipt).

## 2. Decisions

### D1 — The landing grammar is FIXED; the destination dial is deleted

`inbound/{platform}/{selector}/{stamp}.{ext}` — the intake grammar, now a law
for this lane rather than a default. Deleted outright: `_validate_destination`,
the `destination` key, `connector_settings()` and `update_connector_settings()`
(with the dial gone the settings object had no remaining reader — `cadence` and
`digest` died with ADR-591, `last_capture_at` lost its writer with the walker),
`PUT /integrations/{provider}/connector-settings` and its FE control/binding.
`platform_connections.settings["connector"]` becomes an unread fossil; no
migration (rewriting rows to tidy a fossil is churn, and a future tenant may
claim the key).

The principle, stated once: **the raw layer is addressed by mechanism; meaning
lives at the consumer layer.** A deal folder does not collect its Slack raws —
the deal's *maintained file* cites them from the fixed lane. (ADR-588 is the
kernel-side echo: folders are derived views; making the raw address
meaning-shaped was decorating a layer that cannot hold meaning.)

Existing substrate stays put: 48 landed snapshots already sit in the default
lanes (zero elsewhere — measured), and attributed chains are never re-homed.

### D2 — The seam's first caller: a string's run reaches through the connection

`run_connector_capture` gains a `selectors=` narrowing: the effective capture
set is the **intersection** of the caller's ask with the connection's aperture
(`landscape.selected_sources`) — a consumer can narrow the operator's consent,
never widen it. A declared-but-unselected selector captures nothing and reads
nothing: the honest empty, now with the aperture as the stated reason.

A string run with connector sources invokes capture for its declared selectors
(grouped per platform, one invocation each), then reads the newest landed
snapshot exactly as before — **reach with a receipt**. Guards, in order:

- **Freshness floor** (the spend guard, succeeding `is_due` — see D3): if the
  selector's newest landed snapshot is younger than
  `_CONNECTOR_CAPTURE_MIN_INTERVAL_S` (600s), the run reads it and does not
  re-reach. Two strings sharing a selector cost one platform read per window.
- **Failure isolation**: a capture error degrades to the newest landed
  snapshot (stale-but-honest — the desk already states staleness); only a
  selector with *nothing* landed and *no* reach yields the empty.
- The string's own cadence, the CAS run claim, and diff-aware capture (an
  unchanged world writes nothing) bound everything else, as before.

**The credential posture, decided explicitly** (the question ADR-591 D3
deferred): capture executes under the **connection owner's** OAuth token via
the non-agent machinery identity `system:connector-capture`. This is not the
ADR-577 agent fall-through: no LLM holds or steers the credential at any point
— the tool, its arguments, and the write path are fixed by
`CONNECTOR_CAPTURE_BINDINGS`, and the invocation executes the composition of
two standing human declarations (the operator's aperture at the connection ×
the member's designation on the string). ADR-577's refusal of *agent* callers
is unchanged and still enforced at its chokepoint.

### D3 — The digest is superseded by the md string

`services/connector_derive.py` is DELETED, with its `system_calls` row. The
reason is the ADR-569 generalization applied a second time: radar was a
specialization of the maintained file, and so was the digest — a prose leaf
kept current from connector raws, with a hardcoded posture instead of a
member-authored CONTRACT, a fixed path instead of a designated leaf, a bare
system call instead of a resident, and no surface at all. An **md string with
connector sources** is that feature, generalized and already shipped. Keeping
both is a dual implementation (Core Discipline 2), and ADR-591 had already
reduced the digest to caller-less machinery whose opt-in toggle was gone.

This consciously overturns two survivals ADR-591 kept one week ago, with the
supersession recorded rather than relabeled as cleanup: the derive writer
("D3's seam has something to call" — the seam's real caller turned out to be
Strings, which routes judgment through its own resident per ADR-562, not
through a system call), and `is_due` (the spend guard survives **as a
concept** in D2's freshness floor; the function dies with its only would-be
consumer). The 3 existing digest files under `operation/_connectors/` remain
as ordinary attributed files — substrate is never deleted by a code re-cut;
a member who wants them maintained designates them as strings.

`derive_turn.py` (the shared bounded turn) survives with Strings as its
consumer — it was never digest-specific.

### D4 — Repairs riding this ADR (measured in the same audit)

- `GET /strings*` serves connector sources (the projection filtered on `url`
  and silently dropped them); the desk renders both source shapes.
- The desk's cadence line renders through the existing schedule humanizer
  (plain words beside a "change in chat" seed, not raw cron).
- Fetch health moves to the sources card header — it is per-string data and
  was painted per-source, implying truth the data does not carry.
- `test_adr580_connector_derive.py` re-cut (it iterated the deleted
  `services/radar.py` and crashed rather than reported); ADR-582/591 gates
  re-anchored to this ADR's contract; canon swept (connectors.md, GLOSSARY's
  Perceive row, CLAUDE.md pointer rows, `derive_turn.py`'s docstring).

## 3. What this ADR does NOT do

- **No change to turn reach** (ADR-585) — the sibling disposition: transient,
  member-present, excluded from app paths by construction. A string is the
  *standing* disposition and lands receipts precisely because nobody is
  present.
- **No change to the retention dial** (`governance/_retention.yaml`, its
  routes, `retention_max_days` as a tier axis). It configures a GC that no
  longer exists; but it is a live **pricing** surface (ADR-396 gate 1), so its
  disposition — rebuild a GC over the fixed lane, or retire the axis — is a
  pricing decision, named here as owed rather than folded in.
- **No change to the ADR-393 declaration lane** (`CAPTURE_LANE_ENABLED`, its
  drainer) — a different lane with different tenants.
- **No substrate migration** — snapshots, digests, and chains stay where the
  ledger put them.
- **No new axiom** — this composes ADR-423 + ADR-582's writer thesis +
  ADR-591's trigger re-cut; the one sentence above ("raw is addressed by
  mechanism; meaning lives at the consumer layer") is a restatement, not a law.

## 4. Gates

`test_adr582_connectors.py` (re-anchored: fixed grammar, `selectors=`
narrowing driven, no settings door) · `test_adr591_no_pull_job.py`
(re-anchored: the seam has its CALLER; the digest stays deleted) ·
`test_adr569_strings.py` (extended: the reach-with-receipt path driven, the
freshness floor, aperture intersection) · `test_adr580_connector_derive.py`
re-cut as the shared-derive-turn gate. Each new check falsified against a
broken shape before being trusted.
