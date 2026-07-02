# ADR-400: The Envelope Collapse Lands — One Thin Shape, Legacy Deleted

**Status**: Implemented (2026-07-02)
**Date**: 2026-07-02
**Deciders**: KVK + Claude
**Ratifies**: the envelope-collapse direction (`docs/analysis/the-envelope-collapse-2026-06-24.md`, Arm-B probe) on the strength of the Rung-3 measurements (`docs/evaluations/2026-07-02-freddie-envelope-rung3-armB-v2/`)
**Supersedes**: the Arm-A partitioned envelope (`_partition_envelope`), the `YARNNN_ENVELOPE_ARM` probe toggle, `_TRIGGER_FRAMING` (already re-carved by Rung 1 / ADR-397 — now deleted outright), the envelope fact sections (`principal_commons_fact`, `attribution_fact`, `peripheral_field_fact`, `reflection_gap_fact`, `specs_inventory`) and the per-wake `workspace_state` compact-index injection
**Correction (same day, pre-implementation-commit)**: the original deletion inventory listed the envelope fact sections for deletion; scoping the implementation surfaced that they carry the ratified ADR-364 (reflection loop) + ADR-389/390 (commons/attribution) arcs with standing gates — deleting their loaders exceeded the measured evidence. They are retained as empty-graceful compact sections (see inventory). The framing/partition/toggle/workspace_state deletions stand.

**Amends**: ADR-397 (the reactive liturgy prose is deleted with the framing; the close CONTRACT already moved to the frame — Rung-3 commit `6edaf6e`; the liturgy's residual value [standing-intent habit, reflection] is principles.md content per agent-composition.md §3.2.1, seedable there if evals demand it), ADR-390 (its curated fact sections retire — their catch is preserved, see Evidence), ADR-315 (ReviewerContext ABI sheds the deleted fields)
**Preserves**: ADR-276 (full governance at every wake — the governance block is intact and cache-marked), ADR-301 (operating-context block), ADR-284 (standing-intent in envelope), ADR-360 (close contract, now frame-carried), ADR-398 (locator rides the ask), the substrate-snapshot (heads-not-bodies, now with a pending-proposals line)

## The decision

**One envelope builder, the thin CC-shape, for every trigger:**

```
[block 0 — cached]   governance prefix: IDENTITY · principles · PRECEDENT ·
                     MANDATE · AUTONOMY · _budget · _expected_output ·
                     _preferences · OCCUPANT · domain constants (_operator_profile, _risk)
[block 1 — volatile] operating-context (clock) · wake-context · standing_intent ·
                     substrate snapshot (heads + pending proposals) · THE ASK
```

Everything else is read on demand from authored substrate. The governance prefix carries `cache_control` (the June finding: caching, not stripping, was the cost lever — the landed shape has both). Per-trigger **interface rules** (verdict-early on proposal wakes; one-WriteFile for long documents) fold into the ask branches where they apply — they are round-budget interface constraints, not coaching. No framing layer exists.

## Evidence (why this is safe to land, measured on the weak model)

- **Addressed** (6-ask byte-stable probe, Haiku): thin = 6/6 closed, parity on every structural metric with the fat envelope (24.9s/4.0 rounds/7.2 tools/448 chars vs 22.4/4.3/7.2/491).
- **Reactive** (bare-steward live wake, Haiku): ledger `success`; *more* thorough than the fat-envelope baseline — caught BOTH seeded stewardship conditions including the mis-attribution, i.e. **the ADR-389/390 attribution catch survives without the fact sections** — the steward discovered it by reading revisions itself. The bare-steward probe remains the standing regression instrument for this.
- **The one load-bearing sentence** the collapse surfaced (the ReturnVerdict close) was relocated to the minimal frame (DP22 interface) with its own gate — the fix that took the thin shape from 4/6 to 6/6.
- Scope note per the activation ladder (ADR-380/381): the launch-critical surface (Rung-1 steward: addressed + reactive) is what was measured. The alpha-trader dogfood lane's proposal wakes flip with everything else; the first live proposal wake post-deploy is the named watch item (off-critical-path per ADR-380).

## Deletion inventory (Singular Implementation)

| Deleted | Was |
|---|---|
| `_partition_envelope` + Arm-A block assembly | the fat envelope |
| `_build_user_message_stripped` | folded into the one builder |
| `YARNNN_ENVELOPE_ARM` toggle (both sites) | probe scaffolding |
| `_TRIGGER_FRAMING` | per-trigger coaching (Rung-1 re-carved, now deleted) |
| — (correction, same day) | the fact sections are **RETAINED, demoted**: the ADR-390 commons surface + the ADR-364 reflection gap-fact + the specs inventory are ratified, gate-covered arcs; they render as EMPTY-GRACEFUL compact sections in the volatile suffix (silent on a quiet workspace — the measured Arm-B bare-steward shape is unchanged) |
| — | program-DECLARED envelope keys (`signal_files`, watch signals — the ADR-281 D2 / ADR-336 bundle ABI) render via a generic block in the volatile suffix: the kernel is thin; a program's declared wake substrate is its ratified prerogative |
| `workspace_state` injection (+ `build_working_memory` call on the addressed route) | duplicated the snapshot's job |
| ReviewerContext fields for all of the above | ABI surface (ADR-315 doc updated) |

## Consequences

- Every wake sends the governance prefix (cached, ~10% rate) + a short volatile suffix; the fact-section queries stop running per wake.
- The envelope is model-portable by construction (small stable core + read-on-demand) — the shape Rung 4's routing experiment plugs into.
- Anything that later proves missing returns as **one snapshot head-line with a receipt**, never as a section revival (the ADR-390 removal-over-addition discipline, now structural).
