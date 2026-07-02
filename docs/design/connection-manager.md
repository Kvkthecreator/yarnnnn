# Design: The Connection Manager

> **Scoped by [ADR-401 — The Connection Lifecycle](../adr/ADR-401-the-connection-lifecycle.md) (2026-07-02).** This document survives as the **Phase-1 UI spec** of that ADR: the 4-section Manage drill-in (ADR-401 D7), the connector-grain decision (§2), and the no-fabrication discipline (§5) are ratified as-is. The macro concerns this document deliberately did not carry — ontology (peripheral, not principal), disconnect teardown, retention polarity, derive attention-routing — are ADR-401 D1/D3/D4/D5. The build order in §7 maps onto ADR-401 §8 phases 1/2/4.

**Status:** Draft for review (2026-07-02)
**Author:** KVK + Claude (Hat A — System Editor)
**Anchors:** [ADR-338 Management Plane](../adr/ADR-338-management-plane.md) (DP28, the consent line) · [ADR-392 The Connector Lane](../adr/ADR-392-the-connector-lane.md) · [ADR-393 Capture Pipeline](../adr/ADR-393-the-perception-capture-pipeline.md) · [ADR-394 Connector Capture — the Reader](../adr/ADR-394-connector-capture-the-reader.md) · [ADR-335 Perception Field](../adr/ADR-335-perception-field.md)

---

## 1. The question this answers

Today the per-connection **Manage** drill-in (`channels.pane=connectors&channels.connector=slack`) is a bare channel checklist. It shows *scope* and nothing else. The operator asks, reasonably: **what am I actually managing here, and can I see what these reads produce?**

This design answers that against **substrate reality** (not aspiration). Every claim below is receipt-backed; where the substrate can't back a surface, we say so and shape the UI to the truth rather than fabricate.

The governing frame is ADR-338: **the connection manager is a "driver" surface in the management plane** — the operator's half of the product, first-class, not setup friction. Its sections split on the **consent line** (D3): declaration/consent acts are legible and owned; mechanical enactment stays invisible.

---

## 2. First principles — what grain is a "capture"?

The load-bearing design decision. A capture is *deterministic perception* (ADR-393). The architecture already settled its grain:

- The operator's unit of **declaration** is the **connector** ("read Slack").
- The **channels** are the connector's **aperture** — its watch portfolio (ADR-335/342).
- Freddie reads the peripheral field as **one health line per capture** (`freddie_envelope.py::_peripheral_field_fact`, `_capture_signal.yaml` keyed by capture slug).

Therefore: **the connector is the unit; channels are its aperture.** The per-channel `inbound/slack/{channel}/…` files are storage layout, not a health grain. Any UI that tries to show *per-channel freshness* is reaching for a fidelity the architecture deliberately does not model — which is exactly why the old per-row "not reading yet" could never populate (the health signal has no per-selector `observed_at`; receipt: `capture/declarations.py:293-345`, keyed `captures[slug]`).

**Consequence (singular, future-proof):** connector-level freshness is not the *lesser* option — it is the *true* grain. Adding a per-channel health block would introduce a second, finer grain that **nothing else in the system consumes** (not Freddie, not the retention GC, not derive) — speculative surface against Singular Implementation. If per-channel health is ever genuinely needed, the `inbound/` write path already carries per-channel `last_error`/`paths_written` (receipt: `capture_connector.py:236-245`); it can be derived-on-read *then*, without committing substrate now.

---

## 3. Substrate reality (receipts) — what each section can honestly show

| Axis | Substrate today | Renderable now? |
|---|---|---|
| **Granted scopes** | Stored as `metadata.scope` (comma-joined) for Slack + GitHub (`oauth.py:345, 435`). Requested scopes hardcoded per provider (`oauth.py:69-78`). Notion stores none (`oauth.py:87`). | **Yes** — needs a small backend map (`metadata.scope` → response), not new capture work. |
| **Token health** | `status` column is **always `'active'`** in practice — `expired`/`revoked`/`error` are defined in the enum (`types.py:24-29`) but **never written** by any code path. Real liveness only via `GET /integrations/{provider}/health?validate=true`, which for Slack actually calls `list_channels` (`validation.py:210-235`). No expiry column, no refresh routine, no reconnect endpoint (reconnect = re-run authorize→callback). | **Partial** — honest health = the validate probe on demand. The status column alone is theatre and must not be presented as "healthy." |
| **Scope (channels)** | Fully built. Save → `_watch.yaml` (`connector_watch.write_selection`) + seeds `capture-slack @every 15min` (`connector_watch.seed_connector_capture`, `:181`). | **Yes** — done. |
| **Cadence** | `@every 15min` lives in `_captures.yaml`, hardcoded at seed-time. Runs via `drain_due_captures` (`unified_scheduler.py:355`), **gated on `AGENT_ENABLED`** (default on) + ≥1 channel selected (deselect-to-empty → `paused`). | **Yes** to display; **editable** = small follow-on. |
| **Yield (freshness)** | `_capture_signal.yaml` keyed by capture slug → **one block per connector**: `{status, observed_at, items, target, last_error}` (`declarations.py:333-345`). `items` = count of channels captured, not messages (`lane.py:298-306`). | **Yes** at connector grain. Per-channel = not in substrate (see §2). |
| **Yield (content)** | Raw lands per-channel at `inbound/slack/{channel}/{ts}.md` (`capture_connector.py:236`). **Not auto-derived** (ADR-394 D3 — "sitting un-derived is the legible state") and **not embed-eligible** (`embed.py:50-53` excludes `inbound/{slack,…}`), so `recall` returns nothing for it until Freddie derives it into `operation/`. | **Yes** as raw files (deep-link to Files surface). "Understanding" only appears post-derive — and the UI should say so. |

---

## 4. The design — four sections, consent-line ordered

The Manage drill-in becomes a 4-section pane. Section order follows the operator's ownership arc (grant → scope → cadence → yield), which is also the consent-line order (grant/scope/cadence above the line; yield is the read-back).

```
← Connections

[icon] Slack                                          ⟳ Refresh
       Connected · workspace "yarnnn" · since Apr 2026

┌─ ACCESS ────────────────────────────────────────────┐  ← above the line
│  Granted permissions                                 │    (consent fact)
│    channels:read · channels:history · chat:write …   │
│  [ Test connection ]   ✓ read OK · 2s ago            │    (validate probe)
│  Reconnect ↗  (re-runs authorization)                │
└──────────────────────────────────────────────────────┘

┌─ SCOPE ─────────────────────────────────────────────┐  ← above the line
│  Selected channels become the operation's perception.│    (the aperture)
│  Selecting is a declaration, not a sync.             │
│    ☑ #general  ☑ #api  ☑ #social  ☐ #random …        │
│  [ Save selection ]   40 in scope                    │
└──────────────────────────────────────────────────────┘

┌─ CADENCE ───────────────────────────────────────────┐  ← above the line
│  Reads every 15 minutes.        [ change ▾ ]  (later)│
└──────────────────────────────────────────────────────┘

┌─ YIELD ─────────────────────────────────────────────┐  ← the read-back
│  ⏱ Last read 3m ago · 40 channels read · ok          │    (connector grain)
│  Captured messages are retained in the operation's   │
│  inbound lane. Your agent distills them into memory  │
│  when it next engages.   [ View captured files ↗ ]   │
└──────────────────────────────────────────────────────┘
```

### 4.1 ACCESS (above the consent line)
- **Granted permissions** — render `metadata.scope`, split on comma. For Notion (no scope stored) show the platform's fixed capability description instead. *Requires:* map `metadata.scope` into a response (either extend `IntegrationResponse` or a thin new field on the capture-signal/GET path).
- **Test connection** — a button that calls `GET /integrations/{provider}/health?validate=true` and renders the real probe result (`read OK` / `degraded` / `unhealthy`). This is the *only* honest health signal; do not show a green "healthy" from the status column.
- **Reconnect** — links to `GET /integrations/{provider}/authorize`. No new endpoint; the authorize→callback upsert overwrites credentials. Frame it as "Reconnect" for the operator even though mechanically it re-authorizes.
- **Explicitly NOT shown:** expiry countdown, auto-refresh status, revoked-detection — none exist in substrate. Do not fabricate.

### 4.2 SCOPE (above the consent line)
- Keep the current checklist. This section is done. Copy stays: "Selecting is a declaration, not a sync."

### 4.3 CADENCE (above the consent line)
- **Now:** display the read interval from the connector's `_captures.yaml` entry ("Reads every 15 minutes"). If the entry is `paused` (0 selected), say "Not reading — select at least one channel."
- **Follow-on:** make it editable (a small enum: 15m / 1h / 6h / daily) writing the capture entry's `schedule`. Gated by pace (ADR-298) if a cap applies.
- **Honesty note:** if `AGENT_ENABLED` is off for the workspace, captures never run regardless of cadence (`unified_scheduler.py:314-322`). At Rung-0 (interop wedge) this section should reflect that state rather than imply reads are happening.

### 4.4 YIELD (the read-back)
- **Freshness line** — connector-level, from `observed["capture-{provider}"]`: `Last read {relative} · {items} {resourceNoun} read · {status}`. Before the first run: "not reading yet." **(This is the correctness fix already landed — see §6.)**
- **The derive truth, made legible** — a one-line explainer: captured content is *retained* now; it becomes *understanding* (searchable, reasoned-over) when the agent derives it. This is not an apology for a gap — it *is* the product model (substrate floor vs judgment layer). Making it legible is what converts "I don't trust this" into "I see what it does."
- **View captured files** — deep-link into the Files surface at `inbound/{provider}/` so "see the readings" is real (the raw files) rather than fabricated (per-channel timestamps that don't exist). *Requires:* a Files-surface deep-link to a folder path (verify the Files surface accepts a path param).

---

## 5. What we deliberately do NOT build (and why)

- **Per-channel freshness** — not the substrate grain (§2). Would add a consumer-less second grain. Deferred; derivable-on-read from `inbound/` if ever needed.
- **Token expiry / auto-refresh / revoked-detection** — no substrate, no detection logic. Building the *display* without the *detection* would be a lie. If token health becomes a real problem (Slack bot tokens don't expire; this mostly bites GitHub/Reddit), that's a separate backend workstream (a health sweep that writes real `status` transitions), and the ACCESS section absorbs it then.
- **Auto-derive of connector raw** — ADR-394 D3 ratifies that raw sitting un-derived is the legible state; derive is the seat's on-engagement act, not a cadence. Not this design's to change.
- **Embedding connector raw** — `inbound/{slack}` is intentionally not embed-eligible (raw reached by deterministic key, not ranked). Recall-findability comes via derive, correctly.

---

## 6. Landed with this design (correctness fix)

The old per-channel `observed[selectorId]` lookup was **dead code** — the signal is slug-keyed, so it matched nothing and rendered "not reading yet" on every channel permanently (a standing falsehood, not an empty-because-new state). Fixed in `web/components/settings/ManageConnectionSubsurface.tsx`:
- Removed the per-selector `observed` map + `freshnessFor` helper.
- Read the connector block directly (`observed["capture-{provider}"]`).
- Render **one** honest connector-level freshness line above the channel list.
- `tsc --noEmit` clean.

This is the YIELD freshness line (§4.4) shipped ahead of the rest, because removing a falsehood isn't a feature to schedule.

---

## 7. Build order (after sign-off)

1. **ACCESS** — backend: surface `metadata.scope`; FE: permissions list + Test-connection (validate probe) + Reconnect link. *(Small, high-trust.)*
2. **CADENCE display** — FE reads the capture entry's schedule; honest paused/AGENT_ENABLED states. *(Small.)*
3. **YIELD "View captured files"** — Files-surface deep-link + derive-truth explainer. *(Small; verify Files path-param.)*
4. **CADENCE edit** — write the capture schedule; pace-gated. *(Follow-on.)*
5. **Token-health sweep** — only if token expiry becomes a real failure mode. *(Deferred backend workstream.)*

Each is an independent, above-the-line increment. None requires touching the capture lane or the derive/embed model.
```
