# Connectors — a connector is a writer

> **Status**: canon, ratified with [ADR-582](../adr/ADR-582-the-connector-is-a-writer-not-a-pipeline.md)
> (2026-08-19). Supersedes the connector-specific machinery of ADR-392/394
> (the watch mirror, seed-at-select, `CaptureConnector`); composes with
> [intake-pipeline.md](intake-pipeline.md) (the cross-lane contract) and
> [ADR-580](../adr/ADR-580-the-connector-derive-step.md) (the digest, now
> opt-in).

The axiomatic core, in two sentences:

> **A connector is a writer of attributed observation files to an
> operator-chosen destination. Anything built from them cites them.**

## 1. The base feature

Connect (OAuth) → select slices → attributed observation files land at the
destination on a cadence. That is the whole feature — zero LLM, zero
judgment, $0 on the critical path. "Connect Slack" produces files a member
can open immediately.

**A selection is consent, never a default** (2026-08-19; deletes ADR-079/113
auto-selection): the selection is the capture writer's mandate and, for
github, a reach bound (ADR-576) — so nothing machine-fills it. It starts
empty; only the operator checks a box; the smart-default scoring survives
solely as the `recommended` badge. The walk already skips honestly on empty
(`nothing_selected`). Gate: `test_adr582_connectors.py` §7p.

| Fact | Where it lives |
|---|---|
| Credential | `platform_connections` — the human's ACCOUNT object (ADR-425), never readable by an agent (ADR-577) |
| Selection (which slices) | `platform_connections.landscape.selected_sources` — the ONE store |
| Settings (cadence · destination · digest) | `platform_connections.settings["connector"]` |
| Owner record | `platform_connections.connected_by` (ADR-580 D5) |
| Per-platform specifics | one row in `services/connectors.py::CONNECTOR_CAPTURE_BINDINGS` |
| The walk | `services/connectors.py::drain_due_connector_captures` — scheduler tick, behind `CONNECTOR_CAPTURE_ENABLED` (ADR-404 D2) |

Disconnect deletes the row — and with it selection and settings. Credential
gone means aperture gone; a fresh connect is a fresh selection.

## 2. Placement

Destination is a per-connection setting. Unset → the intake grammar default:

```
inbound/{platform}/{selector}/{stamp}.{ext}
```

Set → `{destination}/{selector}/{stamp}.{ext}`. Filing WITHIN the destination
is always deterministic — a peripheral has no judgment to place with;
flexibility is the operator's at wiring time, never the writer's at write
time.

**Raw-ness is a ledger fact, not an address** (ADR-423, finished for this
lane by ADR-582 D3): a snapshot is raw because `revision_kind='observation'`,
wherever it sits. The writer never embeds, so raw is never ranked into
recall. The retention GC sweeps the default lane; a custom destination opts
its files into ordinary member-managed lifecycle instead.

## 3. Attribution (axioms, unchanged)

- Snapshots: `authored_by = "system:capture-{platform}"` +
  `revision_kind='observation'`. The peripheral is machinery, never a
  principal (ADR-401 D1). (Historical rows signed
  `system:sync-platform-state` keep their string — the ledger records what
  happened.)
- Anything derived from them cites them (`derived_from`) and carries the
  owner via `author_identity_uuid = connected_by`, displayed as the ratified
  "on behalf of" sentence (ADR-580 D4).

## 4. Consumers — separate concerns, by design

The connector never knows who reads its files. Current consumers:

| Consumer | Opt-in | What it does |
|---|---|---|
| **The digest** (ADR-580) | `settings.connector.digest = true` (default off) | one bounded turn per selector maintains `operation/_connectors/{platform}/{selector}.md`, citing the raw |
| **Strings** (ADR-582 D6) | a `connector:` source in `_string.yaml` | Keeper folds the newest landed snapshot into the designated file, citing the landed path |
| **Agent reach aperture** (ADR-576 D2) | automatic | the github selection bounds which repos platform tools answer about |
| **Radar** | *named follow-on* | the same source form in `_radar.yaml`; its intake runs inside `TrackWebSources` |

The app-side rule: an app consumes **landed files** — never a platform API,
never a credential. The connection-level aperture (what is captured at all)
stays the operator's consent setting; app opt-in selects within it. An app
naming an un-captured selector gets the same honest empty as a dead feed.

## 5. The operator surface

The per-connection detail page (`web/components/settings/
ManageConnectionSubsurface.tsx`, the drill-in from Settings → Connectors)
has **two strata** (2026-08-19 recut): CONNECTION-level facts, then the
capture writer's configuration as one consumer block.

| Stratum | Block | What it states | Where the truth lives |
|---|---|---|---|
| CONNECTION | **Access** | granted OAuth scopes + the validate probe | `metadata.scope`; the probe is the only liveness signal (ADR-401 D6) |
| CONNECTION | **What this connection does** | reads / writes / agents — capability FACTS | derived server-side: the capture binding's `reads` · the exporter registry · the ADR-577 refusal (`connector_does()`) |
| CONNECTION | **What this connection does** → the `chat` row | whether a chat turn may read through this connection, and — when it may — that what it reads goes to the member-chosen engine (ADR-585 D5, the engine disclosure) | derived from `TURN_REACH_ENABLED` in `connector_does()`; the disclosure rides the same flag as the capability |
| CAPTURE | **Capture** | the writer's config as ONE block: the selection (consent — never auto-filled; `Suggested` badge only) + cadence + destination + digest; collapsed to one honest line while dormant | selection: `landscape.selected_sources`; dials: `settings["connector"]` via `PUT /integrations/{provider}/connector-settings` → `update_connector_settings` (the validation chokepoint) |
| CAPTURE | **Yield** | freshness + landed-files link (flag-gated) | `_capture_signal.yaml` |

Facts, not controls: there is no per-tool enforcement point on the outbound
side to bind permission dials to — the OAuth scope is the platform's control
and agent exclusion is species-level (ADR-577) — so the page states
capabilities and never renders a per-tool grid. (The per-verb grain exists
only on the INBOUND side, where ADR-563 scope tiers are enforced per call.)
Discovery failures RAISE and render scoped inside Scope; an empty landscape
is only ever the honest success case.

## 6. What this is not

**Turn reach** — an LLM calling a platform live inside a conversation turn
(the conventional-MCP shape) — is a different disposition
(intake-pipeline.md §5), still not built. It now has a PROPOSED decision:
[ADR-585](../adr/ADR-585-turn-reach-the-members-own-connections.md) (draft,
awaiting ratification) — the member's OWN connections inside their OWN turn,
on the principal-presence cut line; agents/apps stay landed-files-only. Any
proposal touching platform reach declares its disposition in its first
paragraph.

## 7. Gates

`test_adr582_connectors.py` (the writer's contract, driven) ·
`test_adr580_connector_derive.py` (the digest) ·
`test_adr576_github_connector.py` (the aperture) ·
`test_adr404_capture_dormancy.py` (the flag) ·
`test_intake_pipeline_contract.py` (the cross-lane grammar + observation law).
