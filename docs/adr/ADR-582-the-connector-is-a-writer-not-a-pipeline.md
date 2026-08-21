# ADR-582: The Connector Is a Writer, Not a Pipeline

> **Amended by [ADR-594](ADR-594-the-connection-is-a-rail.md)** (2026-08-21): D1's
> "operator-chosen destination" clause and D3 (the destination dial) are
> SUPERSEDED — the landing grammar is fixed; D5's digest opt-in dissolved with
> the digest itself (ADR-594 D3). The writer thesis and D2/D6 stand.
>
> **Status**: Implemented 2026-08-19 (operator-directed re-cut; the thesis was
> the operator's, tested from the axioms in the 2026-08-19 discourse: *"the
> architecture is over-engineered and holding us hostage to an old conceptual
> framing… in the purest sense of a file system, attribution native — the
> connector just needs to adhere to those principles; where and how we utilize
> this infra is a separate concern"*).
>
> **Dimensional classification (Axiom 0)**: **Mechanism** (the capture path
> re-cut) + **Substrate** (destination flexibility; quarantine re-keyed to the
> ledger) + **Trigger** (cadence as a connection setting).
>
> **Amends**: ADR-392 (the four-phase lane; the `_watch.yaml` declaration),
> ADR-394 (CaptureConnector; seed-at-select), ADR-401 Phase 4 (the cadence
> dial's home), ADR-569 D4 (Strings' HTTP-only source rule), ADR-580 (derive
> demoted from lane stage to opt-in consumer). **Finishes** ADR-423's stated
> direction for this lane (raw is a `revision_kind`, not a directory).

---

## 1. The thesis, tested

The connector architecture accreted across ADR-392→394→401→404→580: a watch
declaration mirrored to substrate, a capture declaration seeded into
`_captures.yaml`, a primitive (`CaptureConnector`) whose only caller was a
directive string parsed at runtime, a path-quarantine, and a derive step that
became the mandatory door out of it. Tested against the axioms, the genuinely
axiom-derived core is two sentences:

> **A connector is a writer of attributed observation files to an
> operator-chosen destination. Anything built from them cites them.**

Everything else was framing-era machinery. The receipt that the framing was
already obsolete is internal: ADR-423 (`write_revision`'s own docstring)
declared that `revision_kind` "is what lets the `inbound/` directory
dissolve — a raw arrival is distinguished by its revision_kind, not its
path." The ledger and the namespace encoded the same fact twice; canon had
already named the ledger as the survivor.

The hostage mechanism, named precisely: **quarantine → derive-is-mandatory →
LLM spend on the critical path.** Because raw was unreachable-by-design, a
paid judgment turn was the only way "connect Slack" produced anything a
member could see. Under this re-cut, connecting produces files — immediately,
mechanically, at $0 — and every LLM consumer is optional value on top.

Measured before cutting (2026-08-19): production `_captures.yaml` is
`captures: []` (the seeding machinery has ZERO live rows); three `_watch.yaml`
mirrors exist (slack · notion · github), and every live selection they carry
is already in `platform_connections.landscape.selected_sources` — the store
the selection UI wrote FIRST, to which ADR-392 added the substrate mirror
(slack: 3 channels; github: 1 repo; notion: none). `settings` is `{}` on all
three rows — a clean namespace for the connector settings object.

## 2. Decisions

### D1 — The connector is a base product feature: a writer

Connect (OAuth) → select slices → attributed observation files land at the
destination on a cadence. That is the whole feature. Zero LLM, zero judgment,
zero derive obligation on this path. Everything downstream — digests, radar,
Strings, future chat turn-reach — is a **consumer**, wired separately (the
operator's "separate concern").

### D2 — One selection store; the mirror layer is deleted

`platform_connections.landscape.selected_sources` — the store the UI always
wrote — is the ONLY selection store. Deleted outright:

- `services/connector_watch.py` (the `_watch.yaml` mirror + read/write,
  seed-at-select, cadence-in-captures-yaml, teardown) — the whole module.
- `services/primitives/capture_connector.py` (`CaptureConnector`) — a
  primitive whose only production caller was a seeded directive string; its
  registry rows and the capture lane's special-cases go with it.
- The route-side mirror + seed blocks in `update_selected_sources`.

Per-connection knobs move to `platform_connections.settings["connector"]`:
`{cadence, destination, digest, last_capture_at}` — one JSON object on the
row that already owns the connection. `CONNECTOR_CAPTURE_BINDINGS` (which
read-tool per platform — the entire per-platform "architecture") and
`CONNECTOR_CADENCE_CHOICES` move to the new `services/connectors.py`.

**Behavior change, deliberate**: selection now dies with the connection
(disconnect deletes the row). The old `_watch.yaml` survived disconnect so
reconnect restored perception; under the re-cut a fresh connect is a fresh
selection — credential gone means aperture gone, which is the honest shape.
The three production `_watch.yaml` mirrors are left in place as substrate
history (deleting them would churn attributed chains to tidy fossils).

### D3 — Destination is a connection setting; the grammar is the default

`settings.connector.destination` names the folder where snapshots land;
unset → the intake grammar `inbound/{platform}/{selector}/{stamp}.{ext}`
(zero data migration; existing raw stays put). Filing WITHIN the destination
stays deterministic — stamped snapshots, slugified selectors, one segment per
selector — because a peripheral has no judgment to place with; flexibility is
the operator's at wiring time, never the writer's at write time.

Raw-visibility policy re-keys from the path to the ledger, finishing ADR-423
for this lane: a snapshot is raw because `revision_kind='observation'`, not
because of where it sits. The writer NEVER embeds (already true of the whole
write path — `UserMemory.write` does not embed), so raw is not ranked into
recall wherever it lands. The retention GC continues to sweep the default
lane; a custom destination opts its files into ordinary member-managed file
lifecycle instead (stated, not hidden).

### D4 — Capture is a direct scheduler walk

`services/connectors.py::drain_due_connector_captures(client)` — walks active
connections with a capture binding, checks the per-connection cadence
(`last_capture_at` on settings), loops the selected ids through the platform
read tool, and writes diff-aware snapshots attributed
**`system:capture-{platform}`** (the mechanism string ADR-401 D1 already
named), `revision_kind='observation'`. The per-declaration health signal
keeps being written (the steward envelope's reader is unchanged). Still
behind `CONNECTOR_CAPTURE_ENABLED` (ADR-404 D2 stands; the flag now gates a
$0 mechanical walk plus whatever consumers are opted in).

No `_captures.yaml` entry, no directive parsing, no primitive dispatch. The
capture LANE (`services/capture/`) survives untouched for its other tenants
(state mirrors, bundle captures) — only the connector's use of it ends.

### D5 — The digest is an opt-in consumer (demotes ADR-580's stage framing)

`settings.connector.digest = true` (default **false**) is what turns on the
ADR-580 derive step for a connection. The machinery survives exactly as
built — the shared bounded turn, the pace law, the attribution encoding, the
living digest at `operation/_connectors/{platform}/{selector}.md` — but it is
now one consumer among several, not the lane's mandatory stage 2. "Connect
Slack" no longer has LLM spend anywhere on its critical path.

### D6 — Apps opt in by consuming landed files

The app-side half of the operator's framing: an app declares a connector
slice as a **source**, reads the LANDED snapshots (substrate only — never a
platform API, never a credential), and places its own output per its own
declaration. Implemented now in **Strings** (the slot its schema reserved
since ADR-569: "connector sources wait for the ADR-404 re-light"):

```yaml
sources:
  - id: standup
    connector: slack        # the platform
    selector: C0A6P2WS4HL   # the slice (a selected id)
```

A connector source resolves to the newest landed snapshot at the connection's
destination; the string's write cites that path as its raw (no re-retain —
capture already retained it). Selection layering is explicit: the
**connection-level aperture** (which slices are captured at all — consent,
cost, privacy) stays an operator setting; the **app-level opt-in** consumes
within it. An app naming an un-captured selector gets the same honest empty
as a dead feed.

**Radar follow-on, named**: the same source form belongs in `_radar.yaml`;
radar's intake runs inside `TrackWebSources`, so it is its own contained
change. Nothing in this ADR blocks it.

### D7 — The ADR-576 D2 reach aperture holds

The github selection still binds agent tool reach — re-pointed to the one
selection store. Same fail-open posture (the aperture is a declared
narrowing; OAuth scope is the security control).

## 3. Kept / demoted / deleted

| | |
|---|---|
| **Kept (axioms)** | attributed observation writes · `derived_from` citation · `revision_kind` vocabulary · the two-dispositions rule (intake vs turn reach) · ADR-577 (no credential near an LLM) · selection-as-aperture + cadence · the health signal · the dormancy flag |
| **Demoted** | the path grammar → the DEFAULT destination · ADR-580's derive → an opt-in consumer · intake-pipeline.md's connector rows → described by `connectors.md` |
| **Deleted** | `connector_watch.py` (the `_watch.yaml` mirror + seeding + captures-yaml cadence) · `primitives/capture_connector.py` + registry rows + lane special-cases · the route-side mirror/seed blocks · `test_adr394_capture_connector.py` (gated deleted machinery; superseded by `test_adr582_connectors.py`) |

## 4. Verification

```
cd api && python3 test_adr582_connectors.py            # the new contract, driven
cd api && python3 test_adr580_connector_derive.py      # digest machinery unchanged
cd api && python3 test_adr569_strings.py               # strings over connector sources
cd api && python3 test_intake_pipeline_contract.py
cd api && python3 test_adr576_github_connector.py      # aperture re-pointed
cd api && python3 test_adr404_capture_dormancy.py      # flag still gates the walk
```
