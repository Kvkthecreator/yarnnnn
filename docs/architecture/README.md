# Architecture Documentation Index

> **Last updated**: 2026-09-12 (the post-steward recut — ADR-596/603/632; every doc below describes the live system, and every retired-era version is archived under `previous_versions/`).

The canon is stacked: **THESIS** (the philosophical claim) → **FOUNDATIONS** (the axioms) → **GLOSSARY** + **LAYER-MAPPING** (the vocabulary and the taxonomy) → **SERVICE-MODEL** (how the pieces fit) → **agent-composition** + **lane-frame** (what an agent's turn is made of) → the substrate and surface canons. Start with SERVICE-MODEL.md for the operational picture. CLAUDE.md's canon table is the shortest way in.

## The spine

| Document | Covers |
|---|---|
| [THESIS.md](THESIS.md) | The philosophical claim — four architectural commitments, falsifiable predictions, terminal-vision optionality. Internal canon; not external messaging. |
| [FOUNDATIONS.md](FOUNDATIONS.md) | First-principles axioms every ADR derives from — the six dimensions, the filesystem as substrate, the agent (Axiom 2, v10), the two trigger shapes (Axiom 4, v10), ground truth, the derived principles. |
| [GLOSSARY.md](GLOSSARY.md) | Canonical vocabulary — one word, one concept. Terms move; this is authoritative. |
| [LAYER-MAPPING.md](LAYER-MAPPING.md) | The taxonomy of every acting entity: agents as a fact-vector, the clusters, machinery, the filesystem rule. |
| [SERVICE-MODEL.md](SERVICE-MODEL.md) | End-to-end — the acts, the entity model, the two execution paths, intake, outbound, interop, services, billing. |

## How an agent's turn is composed

| Document | Covers |
|---|---|
| [agent-composition.md](agent-composition.md) | The lane frame and the standing frame section by section; §3.3 the partition — where a sentence of prompt prose goes; what an agent reads and may write; versioning. |
| [lane-frame.md](lane-frame.md) | The pane frame in depth — the binding, the focus declaration, the cast, app-declared postures. |
| [primitives-matrix.md](primitives-matrix.md) | The kernel's verbs and who holds them — derived from the registry; the permission gate; the standing disciplines; the deleted-verbs ledger. |

## The substrate and the surfaces

| Document | Covers |
|---|---|
| [WORKSPACE.md](WORKSPACE.md) | The filesystem as the kernel tells it, the roots, genesis, what unattended work requires, the live failure modes. Paired with [design/WORKSPACE.md](../design/WORKSPACE.md) (the surface contracts). |
| [authored-substrate.md](authored-substrate.md) | The ledger — every write attributed, parent-pointered, revertible (ADR-209); attribution prefixes; the revision chain in depth. |
| [compositor.md](compositor.md) | The shell — the window manager, navigation, the kernel/app seam. |
| [intake-pipeline.md](intake-pipeline.md) · [connectors.md](connectors.md) · [grants-and-reach.md](grants-and-reach.md) · [connector-reach-and-the-commons.md](connector-reach-and-the-commons.md) | How the world reaches the commons, and how work leaves it: connections, capture, turn reach, outbound, grants. |
| [observability.md](observability.md) | Logging, telemetry, spend ceilings. |
| [YARNNN-DESIGN-PRINCIPLES.md](YARNNN-DESIGN-PRINCIPLES.md) | The two spectrums — what tightens, what loosens, and what holds the line while it does. |
| [propagation-discipline.md](propagation-discipline.md) | Substrate reapply — how a bundle's later changes reach a live workspace (ADR-292). |

## Reference and history

- [ADR-LEDGER.md](ADR-LEDGER.md) — per-ADR notes and supersession chains; search it before proposing an architectural change.
- [AGENT-TAXONOMY.md](AGENT-TAXONOMY.md) — the axes agents have been classified on, and the invariant that survived them.
- [DOMAIN-STRESS-MATRIX.md](DOMAIN-STRESS-MATRIX.md) — the verticalization stress test for ADRs.
- [os-framing-implementation-roadmap.md](os-framing-implementation-roadmap.md) · [bare-kernel-product-floor-2026-06-01.md](bare-kernel-product-floor-2026-06-01.md) — dated planning notes, kept for the ADRs that cite them; superseded where they name the steward or the bundle-fork as the constitution event (ADR-414 D4, ADR-632).
- [orchestration.md](orchestration.md) · [registry-matrix.md](registry-matrix.md) · [output-substrate.md](output-substrate.md) · [compose-substrate.md](compose-substrate.md) · [commerce-substrate.md](commerce-substrate.md) — earlier-era references; read their status headers before relying on them.

## Archived (`previous_versions/`)

The retired-era text, verbatim, so nothing is lost when the live document is recut. The 2026-09-12 recut snapshots: `FOUNDATIONS-v9.20-2026-09-12.md` · `GLOSSARY-2026-09-12-pre-recut.md` · `WORKSPACE-architecture-2026-09-12-pre-recut.md` · `WORKSPACE-design-v3.0-2026-09-12-pre-recut.md` · `agent-composition-v1-2026-09-12.md` · `primitives-matrix-v1-2026-09-12.md` · `SERVICE-MODEL-v2.1-2026-09-12.md` · `THESIS-2026-09-12-pre-recut.md` · `LAYER-MAPPING-v3-2026-09-12.md` · `ESSENCE-v20-2026-09-12.md`. The steward / review-seat canon archived by ADR-632 (`reviewer-*.md`, `cadence-and-wakes.md`, `invocation-and-narrative.md`, `execution-loop.md`, `agent-execution-model.md`, `persona-reflection.md`, the `adr296-*` audits) and the pre-2026 documents live beside them. Do not use any of them for a current decision.

## Database

- [SCHEMA-NOTES.md](../database/SCHEMA-NOTES.md) — current table names, deprecated columns, the ADR history behind each.
- [ACCESS.md](../database/ACCESS.md) — connection strings and psql commands.
