# Connectors — the connection is a rail

> **Status**: canon. Ratified with [ADR-582](../adr/ADR-582-the-connector-is-a-writer-not-a-pipeline.md)
> (2026-08-19, the writer thesis), amended by ADR-591 (no clock) and
> [ADR-594](../adr/ADR-594-the-connection-is-a-rail.md) (2026-08-21: fixed
> landing grammar, the seam's first caller, the digest folded into Strings).
> Composes with [intake-pipeline.md](intake-pipeline.md) (the cross-lane
> contract).

The axiomatic core, in two sentences:

> **A connection is the rail that allows access: consent, credential, and
> aperture. A capture is a consumer's act — it writes attributed observation
> files to the fixed intake lane, and anything built from them cites them.**

## 1. The base feature

Connect (OAuth) → select slices → attributed observation files land **when a
consumer asks**. That is the whole feature — zero LLM, zero judgment, $0 on
the critical path.

**A capture happens because something asked, never because time passed**
(ADR-591): there is no cadence, no scheduler walk, and no capture flag.
`run_connector_capture` is the writer; **its production caller is a string's
run** (ADR-594 D2 — "reach with a receipt"): a maintained file with
`connector:` sources invokes capture for its declared selectors, narrowed to
the intersection with the aperture, floored by snapshot freshness, then reads
and cites what landed. Nothing lands before someone asks, so there is no
automatic back-history.

**A selection is consent, never a default** (2026-08-19; deletes ADR-079/113
auto-selection): the selection is the aperture — the capture bound and, for
github, a reach bound (ADR-576) — so nothing machine-fills it. It starts
empty; only the operator checks a box; the smart-default scoring survives
solely as the `recommended` badge. The walk already skips honestly on empty
(`nothing_selected`). Gate: `test_adr582_connectors.py` §7p.

| Fact | Where it lives |
|---|---|
| Credential | `platform_connections` — the human's ACCOUNT object (ADR-425), never readable by an agent (ADR-577). Capture executes under the connection owner's token via the non-agent machinery identity `system:connector-capture` (ADR-594 D2 — fixed tool bindings, two composed human declarations; no LLM ever holds the credential) |
| Selection (the aperture) | `platform_connections.landscape.selected_sources` — the ONE store |
| Owner record | `platform_connections.connected_by` (ADR-580 D5) |
| Per-platform specifics | one row in `services/connectors.py::CONNECTOR_CAPTURE_BINDINGS` |
| The writer | `services/connectors.py::run_connector_capture(…, selectors=)` — invoked by a consumer (Strings), never by a clock |

There are **no per-connection settings** (ADR-594 D1): the destination dial
was the last one and is deleted; `settings["connector"]` is an unread fossil
key. Disconnect deletes the row — and with it the selection. Credential gone
means aperture gone; a fresh connect is a fresh selection.

## 2. Placement — the fixed grammar

```
inbound/{platform}/{selector}/{stamp}.{ext}
```

A law for this lane, not a default (ADR-594 D1). The rationale is a receipt
chain: ADR-423 re-keyed raw-ness to the ledger (a snapshot is raw because
`revision_kind='observation'`, wherever it sits — and the writer never
embeds, so raw is never ranked into recall); ADR-591 deleted the retention
GC (the last behavioral differential of a chosen destination); measured
2026-08-21, zero custom destinations had ever been set. What remained was
tree cosmetics — and at many connections, slop.

**The raw layer is addressed by mechanism; meaning lives at the consumer
layer** (the string's folder, the derived brief). Nothing sweeps this lane —
snapshots are kept, not swept (the retention dial's disposition is a named
pricing decision, ADR-594 §3).

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
| **Strings** (ADR-582 D6 + ADR-594 D2) | a `connector:` source in `_string.yaml` | the run reaches (aperture-intersected, freshness-floored), then Keeper folds the newest landed snapshot into the designated file, citing the landed path |
| **Agent reach aperture** (ADR-576 D2) | automatic | the github selection bounds which repos platform tools answer about |

The **digest** (ADR-580) is SUPERSEDED (ADR-594 D3): a prose leaf kept
current from connector raws is exactly an md string with connector sources —
member-designated, contract-governed, resident-run, desk-surfaced. Its 3
historical digest files remain ordinary attributed files. **Radar** was
deleted with its app (ADR-592).

The app-side rule: an app consumes **landed files** — never a platform API,
never a credential. The one sanctioned reach is *through the capture writer*
(ADR-594 D2), which is itself deterministic machinery under the aperture.
App opt-in selects within the aperture; a declared-but-unselected selector
gets the same honest empty as a dead feed.

## 5. The operator surface

The per-connection detail page (`web/components/settings/
ManageConnectionSubsurface.tsx`, the drill-in from Settings → Connectors)
has **two strata** (2026-08-19 recut): CONNECTION-level facts, then the
capture stratum.

| Stratum | Block | What it states | Where the truth lives |
|---|---|---|---|
| CONNECTION | **Access** | granted OAuth scopes + the validate probe | `metadata.scope`; the probe is the only liveness signal (ADR-401 D6) |
| CONNECTION | **What this connection does** | reads / writes / agents — capability FACTS | derived server-side: the capture binding's `reads` · the exporter registry · the ADR-577 refusal (`connector_does()`) |
| CONNECTION | **What this connection does** → the `chat` row | whether a chat turn may read through this connection, and — when it may — that what it reads goes to the member-chosen engine (ADR-585 D5, the engine disclosure) | derived from `TURN_REACH_ENABLED` in `connector_does()`; the disclosure rides the same flag as the capability |
| CAPTURE | **Capture** | the aperture: the selection (consent — never auto-filled; `Suggested` badge only). Where snapshots land is a stated FACT (the fixed lane), not a dial. No cadence: captures happen when a consumer asks | selection: `landscape.selected_sources`. There is no settings door (ADR-594 D1) |

Facts, not controls: there is no per-tool enforcement point on the outbound
side to bind permission dials to — the OAuth scope is the platform's control
and agent exclusion is species-level (ADR-577) — so the page states
capabilities and never renders a per-tool grid. (The per-verb grain exists
only on the INBOUND side, where ADR-563 scope tiers are enforced per call.)
Discovery failures RAISE and render scoped inside Scope; an empty landscape
is only ever the honest success case.

## 6. What this is not

**Turn reach** — an LLM calling a platform live inside a conversation turn
(the conventional-MCP shape) — is the sibling disposition
(intake-pipeline.md §5): [ADR-585](../adr/ADR-585-turn-reach-the-members-own-connections.md)
gives the member's OWN connections to their OWN open chat turn, transient,
excluded from every app path by construction. A string is the *standing*
disposition and lands receipts precisely because nobody is present. Any
proposal touching platform reach declares its disposition in its first
paragraph.

## 7. Gates

`test_adr582_connectors.py` (the writer's contract + the narrowing, driven) ·
`test_adr591_no_pull_job.py` (no clock; the seam has its caller) ·
`test_adr569_strings.py` §7 (reach with a receipt, driven) ·
`test_adr580_connector_derive.py` (the supersession + the shared turn) ·
`test_adr576_github_connector.py` (the aperture) ·
`test_intake_pipeline_contract.py` (the cross-lane grammar + observation law).
