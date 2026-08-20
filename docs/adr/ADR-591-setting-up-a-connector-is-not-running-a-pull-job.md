# ADR-591: Setting Up a Connector Is Not Running a Pull Job

> **Status**: Proposed 2026-08-20. **Supersedes [ADR-582](ADR-582-the-connector-is-a-writer-not-a-pipeline.md) D4**
> (the direct scheduler walk) and retires cadence as a connector concept.
>
> **Disposition (declared first, per intake-pipeline.md §5)**: **INTAKE** —
> this is the durable capture lane. The decision is about its *trigger*:
> what causes a capture to happen. No new reach, no change to what a
> capture writes or how it is attributed.
>
> **Dimensional classification (Axiom 0)**: **Trigger** (what causes a
> capture) + **Boundary** (what a deploy flag is permitted to gate).

---

## 1. The question

The operator, asked to flip `CONNECTOR_CAPTURE_ENABLED` on API + Scheduler
so connectors could be *configured* for downstream use:

> *"those for the scheduler sound like legacy approaches and i'd argue we
> shouldn't even have actual jobs for those in the pipeline. thus, what i
> really wanted was the enabled to be 'able to be set-up' for future,
> downstream connector use by headless when the time comes, hence, we need
> actual front end and APPs to be able to use them."*

And, when this ADR's first draft proposed keeping the cadence dial as
stored intent:

> *"are you sure this also isn't legacy concept? connectors is just
> connectors, the architecture i thought we decided to clean cut."*

## 2. What was actually there (measured, 2026-08-20)

`CONNECTOR_CAPTURE_ENABLED` has exactly three live call sites:

| # | Site | What it gates | Kind |
|---|---|---|---|
| 1 | `jobs/unified_scheduler.py:336` | `drain_due_connector_captures` — the cron walk | **JOB** |
| 2 | `routes/integrations.py:356` | the capture-signal endpoint's flag field | **SURFACE** |
| 3 | `routes/integrations.py:1662` | the same field on the detail payload | **SURFACE** |

One flag, two unrelated questions: *may a cron walk fire?* and *may an
operator see and set this connection's configuration?* Fusing them made
"configure a connector" reachable only by starting a pull job.

**An honest correction to this ADR's own first draft**: it argued the walk
was unexamined residue predating the recut. That is false. ADR-582 D4
("Capture is a direct scheduler walk") **deliberately kept** it one day
earlier, listing "selection-as-aperture + cadence" under *Kept (axioms)*.
The walk is not a survival; it is a ratified decision. This ADR therefore
supersedes it rather than tidying after it.

**Stale documentation, recorded**: `connector_capture_gating.py`'s docstring
names a third cut site — seed-at-select (`seed_connector_capture`). ADR-582
deleted that machinery; the docstring outlived what it described.

## 3. Why D4 no longer holds

ADR-582 D4 was ratified **before** ADR-585 demonstrated the alternative.
Turn reach reads platforms with no scheduler, no cadence, and no walker,
because **presence of a principal replaced the tick** — and it needed
nothing from the scheduler to do it.

That reframes the cadence. A cadence answers "how often should we read
when nobody asked?" — a question that only exists because the trigger is
time. Once a trigger can be *a consumer wanting the data*, the cadence is
not a setting the operator tunes; it is a parameter of a mechanism we no
longer want.

ADR-582's own ruling points the same way: **"consumers are separate
concerns."** Every consumer was separated out — the digest opt-in, Strings
reading landed files, radar a named follow-on — except the walker, which
was not a consumer at all but a *clock* standing in for one.

**What this costs, stated plainly**: nothing lands before someone asks, so
there is no automatic back-history. A member cannot open Slack history from
a Tuesday nobody was present for. This is accepted: it is the ADR-404
commons-first posture (automatic capture de-emphasized) carried to its
conclusion, and the durable-record property comes from what consumers
*land and cite*, not from a clock filling a folder in advance.

## 4. Decisions

### D1 — Cadence is retired as a connector concept

`CONNECTOR_CADENCE_CHOICES`, `_CADENCE_SECONDS`, `_cadence_due`, and the
`cadence` key in `settings["connector"]` are **deleted**, along with the
FE cadence dial and the `cadence_choices` payload field. A connector is
credential + selection + destination. There is no "how often".

`last_capture_at` survives as an **observation** — when this connection was
last captured — not as a clock to compare a cadence against.

### D2 — The scheduler walk is deleted

`drain_due_connector_captures` and its scheduler block are **deleted**, not
left dormant (Singular Implementation: a dormant walker is a second way to
do the thing D3 defines). The scheduler holds no connector job.

`run_connector_capture(client, user_id, row, observed_at=…)` — the actual
**writer** — is untouched. It was always invocation-shaped; the walker was
a loop around it. Attribution, destination grammar, diff-awareness, and the
health signal are all unchanged.

### D3 — Capture is consumer-invoked (the seam, named and left open)

A capture fires because a consumer asked: an app, a headless caller, a
member's turn. The writer already accepts exactly that call.

This ADR **names the seam and does not build the caller**. Which surface
invokes it, under what authorization, and how it meters are a separate
design conversation — and building a caller speculatively is the mistake
ADR-582 made with the walker. D2 is safe to land before D3 exists because
the lane is dormant today: deleting a walker that is switched off removes
no capability anyone currently has.

### D3.a — The digest's walker goes with it

`drain_due_connector_derives` (ADR-580) is the same shape as the capture
walker: a clock (6h floor + new-raw gate) standing in for a consumer that
wants a digest. It is **deleted** on D3's logic. The derive writer
(`derive_turn`) survives and is invocable, exactly as the capture writer is.

No connection has ever opted in (`settings["connector"]` is NULL on all
three live rows, measured 2026-08-20), so nothing running stops running.

### D3.b — The connector raw-lane GC goes with the lane

`prune_raw_lane` + `gather_cited_raw_paths` and their scheduler block are
**deleted**. The GC existed to age out what a 15-minute clock accumulated;
with no clock filling `inbound/{platform}/`, consumer-invoked captures land
what someone asked for, and those files follow ordinary member-managed
lifecycle like any other file in the commons.

This is the ADR-582 D3 posture already stated for custom destinations
("a custom destination opts its files into ordinary member-managed
lifecycle") applied to the default lane too, now that the default lane is
no longer machine-filled.

### D4 — The configuration surface is always live

Selection and destination are durable operator intent in
`landscape.selected_sources` and `settings["connector"]`. They are visible
and editable regardless of any execution lane — configuring a connector is
not running one.

The **digest toggle goes with its walker** (D3.a): a dial whose only
consumer was a deleted clock is not configuration, it is a control for
nothing. When a digest caller exists (D3), whether it is opt-in per
connection is that design's decision to make, on evidence — not a switch
inherited from the lane it replaced.

### D5 — The flag becomes what it always described

With the walk gone, `CONNECTOR_CAPTURE_ENABLED` has no job to gate. It is
**deleted** along with `connector_capture_gating.py`; the surfaces that
reported it stop reporting a flag that gates nothing.

The operator-facing statement follows: the page states what a connector
holds (selection, destination) and that captures happen when something
asks — never a paused-schedule fiction.

## 5. What this explicitly does not change

- The consent rule (ADR-582 §1): selection starts empty; nothing
  machine-fills it.
- Attribution (`system:capture-{platform}` + `revision_kind='observation'`),
  the destination grammar, raw-ness as a ledger fact (ADR-423/582 D3).
- The writer itself, the health signal, and the digest's opt-in default.
- Turn reach (ADR-585): orthogonal — read-only, transient, no writes.
- The `services/capture/` lane, which has other tenants.
