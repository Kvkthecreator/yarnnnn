# ADR-300 — Pace as Atomic Kernel Surface

> **⚠ SUPERSEDED by [ADR-327](ADR-327-budget-and-the-self-improving-loop.md) (Proposed, 2026-06-08).** Pace retires as a concept — the `/pace` atomic surface this ADR created is repurposed to `/budget` (a dollar budget over a timeframe + window-to-date utilization). `_pace.yaml` collapses with `_token_budget.yaml` into one `_budget.yaml`. The `/pace` route survives only as a redirect stub to `/budget`. The atomic-kernel-surface *pattern* this ADR established (one substrate file → one atomic surface) is preserved and reused for `/budget`; only the pace *concept* dies. See ADR-327 D1/D7.

> **Same-day vocabulary note (2026-05-24 design polish):** the "Delegation" surface this ADR references throughout — `/delegation`, `DelegationCard`, `[ Delegation ]` launcher position — was renamed to "Autonomy" / `/autonomy` / `AutonomyCard` to align with the substrate file `_autonomy.yaml`. Schema field `default_delegation` is **kept** (precise data-layer term — the delegated level value). `/delegation` route survives as a redirect stub to `/autonomy` for bookmark safety. The architectural decision (atomic kernel surface for pace) is unchanged; only the neighbor surface's operator-facing label moved. See `docs/design/CHANGELOG.md` 2026-05-24 entry.

**Status:** Implemented (2026-05-22)
**Date:** 2026-05-22
**Supersedes:** [ADR-298](ADR-298-reviewer-wake-queue-and-pace.md) D5 §"New: cockpit Schedule tab section" (pace rendering site)
**Amends:** [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) D1 (kernel surface list extends from 15 to 16 with `pace`)
**Preserves:** ADR-298 D1–D11 (queue substrate, pace semantics, drain model, trifecta canon) · [FOUNDATIONS](../architecture/FOUNDATIONS.md) Axiom 1 (filesystem is substrate) · Axiom 4 (Trigger dimension) · ADR-297 atomic-substrate-mirror discipline
**Companion concept audit:** in-session 2026-05-22 (pace / cadence / schedule / queue / activity / feed disambiguation)

## 1. Context

[ADR-298](ADR-298-reviewer-wake-queue-and-pace.md) D11 canonized the **operator dial trifecta** — Pace (Trigger / Axiom 4), Autonomy (Mechanism / Axiom 5), Persona (Identity / Axiom 2) — as the three first-class operator levers. Each maps to its own substrate file and axiom dimension; none substitutes for the others.

Two of the three already have atomic kernel surfaces per [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) D1:

| Lever | Substrate | Atomic surface |
|---|---|---|
| Autonomy | `_autonomy.yaml` | `/delegation` |
| Persona | `IDENTITY.md` + `principles.md` | `/identity` + `/principles` |
| **Pace** | `_pace.yaml` | **— missing —** |

Pace currently surfaces as `PaceBadge` (kind + queue depth, read-only) mounted on the Cockpit and as a passing reference in ADR-298 D5 ("New: cockpit Schedule tab section"). There is **no edit affordance** anywhere in the operator-facing UI. Operators must use chat → `WriteFile` or hand-edit `_pace.yaml` in the Files browser.

This violates two principles:

1. **ADR-297 D1 atomic-substrate-mirror** — every kernel substrate concept gets its own atomic surface. `_pace.yaml` is kernel substrate (universal — every workspace has one) and is structurally peer to `_autonomy.yaml` (which has `/delegation`). The asymmetry is unjustified.
2. **ADR-298 D11 trifecta-as-canon** — pace was canonized as a first-class operator lever, but the operator has no first-class place to set it. The lever exists conceptually; the dial doesn't exist in the UI.

The in-session concept audit (2026-05-22) confirmed that **pace** (workspace rhythm cap), **cadence** (per-recurrence taxonomy), **schedule** (per-recurrence cron field), **queue** (transient compute), **activity** (execution ledger), and **feed** (narrative timeline) are six genuinely distinct concepts with healthy vocabulary discipline. The only gap is pace's missing edit surface — not concept overlap.

## 2. Decisions

### D1 — `/pace` is the sixteenth kernel atomic surface

Add `pace` to the `KernelSurfaceSlug` union and to `KERNEL_SURFACES` registry. Archetype: **Document** (single-substrate-file write, identical to `/delegation`). Default-pinned: **false** (operator may pin to dock if frequently tuned; most workspaces set pace once at activation and rarely revisit).

| Field | Value |
|---|---|
| slug | `pace` |
| title | `Pace` |
| archetype | `document` |
| substrate_paths | `["/workspace/context/_shared/_pace.yaml"]` |
| icon_key | `gauge` (lucide-react `Gauge` — the speedometer metaphor reads as "rhythm dial") |
| default_pinned | `false` |
| route | `/pace` |
| summary | `Workspace rhythm — how often the agent works. Edit via chat.` |

### D2 — Edit scope: kind-only

The surface renders + edits exactly what `_pace.yaml` currently models per ADR-298 §"Substrate":

```yaml
pace:
  kind: hourly | daily | weekly | continuous
  every: <ISO 8601 duration>    # optional numeric override (preserved on read, not editable in V1)
monthly_budget_usd: <number>     # optional (preserved on read, not editable in V1)
```

V1 ships radio/select for `kind`. The `every` numeric override and `monthly_budget_usd` fields are **read-and-preserve** — surface reads them, displays as supplemental info, writes them back unchanged on kind edits. Editing `every` and `monthly_budget_usd` defers to chat → `WriteFile`.

**Rationale:** Aligns with the rest of the atomic-Document surfaces (Delegation, Mandate, Principles, Identity, Brand) — primary lever editable in-surface, complex/secondary fields routed through chat. Honors the "Edit via chat" subtitle pattern already established on `/delegation`.

### D3 — Pure config, no telemetry

The surface renders:
- Current pace kind (editable)
- Current `every`, `monthly_budget_usd` (read-only display, preserved on write)
- Authorship trailer (operator | system:bundle-fork | …) per ADR-209 conventions
- "Edit via chat" affordance for full YAML edit

The surface does **NOT** render:
- Live `wake_queue` depths (stays on `/queue`)
- Recent drain telemetry (stays on `/activity`)
- Schedule-gate-error history (stays on `/activity` and Reviewer chat narrative)
- Per-pace-kind cost approximation (deferred — operator demand-driven)

**Rationale:** ADR-297 D1 one-substrate-one-surface. Cross-surface telemetry chips create coupling drift. The PaceBadge on Cockpit already serves the "see pace + queue depth at a glance" use case; `/pace` is the dial, not the dashboard.

ADR-298 D5 §"New: cockpit Schedule tab section" originally proposed pace + queue depth + per-pace cost approximation on a single cockpit tab. This ADR supersedes that decision: pace, queue, and activity each get their own atomic surface; cross-surface composition is the operator's responsibility via launcher pinning.

### D4 — Launcher slot: operator-dial trifecta cluster

Per ADR-298 D11, Pace + Autonomy + Persona is the canonized trifecta. The launcher should surface them adjacently:

```
[ Pace ]  [ Delegation ]  [ Identity ]  [ Principles ]
```

Concrete launcher ordering is set by `KERNEL_SURFACES` declaration order in `api/services/kernel_surfaces.py`. Place the new `pace` entry **between `cadence` and `delegation`** — this keeps Trigger-dimension surfaces (Cadence + Pace) adjacent, then transitions into Mechanism-dimension (Delegation) and Identity-dimension (Identity / Brand / Principles) surfaces in axiom order.

No SURFACES.yaml composition changes required — pace is kernel-universal, no program-bundle overrides expected at this layer.

### D5 — Singular Implementation: PaceBadge edit affordance dissolves

After `/pace` ships, the `PaceBadge` component on Cockpit becomes **read-only with a deep-link to `/pace`** — clicking the badge opens the atomic Pace surface. The badge does not gain its own edit affordance (would create a two-location edit model — violates ADR-297 atomic-surface discipline).

If the badge currently has any edit hooks, they are removed in the same commit that ships `/pace`. The "Edit via chat" subtitle on PaceBadge updates to "Tune on /pace" or equivalent deep-link copy.

> **Amendment (2026-05-24, ADR-297 D20)**: D5's "PaceBadge becomes a read-only deep-link" was the intermediate Singular-Implementation step. ADR-297 D20 advances this to: **the PaceBadge is deleted entirely** (its actual mount site at commit-time was the `/cadence` list surface, not the Cockpit — D5's "Cockpit" wording was loose; the badge had migrated to `/cadence` since). Pace state (kind + queue depth + next wake) surfaces instead as one chip in the agent-OS menu-bar status cluster mounted in the top-bar Right region. The cluster is universal (visible on every surface, not only `/cadence`), so the per-surface badge becomes redundant. The chip's popover footer links to `/pace` exactly as the badge did. Singular Implementation tightens: one pace indicator in the workspace, in kernel chrome, with `/pace` as the sole edit location.

## 3. Implementation scope

**Pivot at implementation time** (recorded for trace continuity): the original spec proposed a dedicated `PUT /api/cockpit/pace` endpoint with server-side merge. Implementation pivoted to FE-side serialize via `writeShape('pace', ...)` — same pattern as `DelegationCard`/`autonomy.ts`, honoring ADR-245 D5 WRITE_CONTRACT enforcement and Singular Implementation (one write path per configuration shape). The pivot also avoids creating a parallel HTTP surface for what is structurally identical to every other operator-edited configuration shape.

### Backend
- `api/services/kernel_surfaces.py` — `pace` entry added to `KERNEL_SURFACES`, ordered between `cadence` and `delegation`. Archetype: `document`. Icon: `gauge`. Substrate path: `/workspace/context/_shared/_pace.yaml`.
- `GET /api/cockpit/pace` already exists (ADR-298 Phase 5) — used by the `PaceBadge` for read-only display.
- `services.pace.read_pace`, `parse_pace_yaml`, `PACE_KINDS`, `InvalidPaceKindError` — preserved unchanged.
- **No new write endpoint, no new write helper** — writes route through the existing `api.workspace.editFile` primitive via `writeShape('pace', ...)` per ADR-245 D5. The Reviewer-write lock (`SHARED_PACE_PATH` already in `DEFAULT_REVIEWER_WRITE_LOCKS`) enforces operator-only authorship.

### Frontend
- `web/types/desk.ts` — `'pace'` added to `KernelSurfaceSlug` union, `KERNEL_SURFACE_SLUGS` array, and the surface-count comment (15 → 16).
- `web/app/(authenticated)/pace/page.tsx` — **new** — wraps `<PaceCard variant="full" />` in `<SurfacePage iconKey="gauge" title="Pace" summary="..." />` (verbatim follow of the `/delegation` page template).
- `web/components/workspace-concepts/PaceCard.tsx` — **new** — three variants (full / compact / chip). Full surface presents kind radio (`weekly | daily | hourly | continuous`), preserves `every` + `monthly_budget_usd` display when present, and routes mutations through `useCockpitPace().setKind()` → `writeShape('pace', ...)`. Modeled on `DelegationCard`.
- `web/lib/content-shapes/pace.ts` — **new** — content-shape registry entry per ADR-245 D3 (SHAPE_KEY=`pace`, PATH_GLOB=`**/_shared/_pace.yaml`, WRITE_CONTRACT=`configuration`, CANONICAL_L3=`PaceCard`). Exports `parse()`, `parseRoundTrip()`, `serialize()`, `useCockpitPace()` hook, `formatPaceSummary()` helper.
- `web/lib/content-shapes/index.ts` — `paceMeta` registered in `CONTENT_SHAPES`.
- `web/components/shell/SurfaceRegistry.tsx` — `PacePage` imported, `pace: PacePage` registered in `KERNEL_SURFACE_REGISTRY`.
- `web/components/work/PaceBadge.tsx` — simplified to `<Link href="/pace">` deep-link per D5. Read-only display preserved; no edit hooks. Tooltip gains "Click to tune pace" cue.
- `web/lib/api/client.ts` — **no changes** — `api.cockpit.pace()` reader unchanged; writes route through existing `api.workspace.editFile` via `writeShape()`.

### Doc cascade
- `docs/architecture/cadence-and-wakes.md` — add §"Pace surface" subsection pointing to `/pace`
- `docs/architecture/SERVICE-MODEL.md` Frame 5 — add `pace` row to kernel surfaces table
- `docs/architecture/GLOSSARY.md` — Pace entry already exists from ADR-298; append "Surface: `/pace` (atomic kernel surface, Document archetype). See ADR-300."
- `docs/adr/ADR-298-reviewer-wake-queue-and-pace.md` — append status-header note: "ADR-300 lands the atomic `/pace` surface (2026-05-22). D5 §'cockpit Schedule tab section' superseded by D3 of ADR-300 (pure-config, no cross-surface telemetry)."
- `docs/adr/ADR-297-surfaces-as-substrate-mirror.md` — append same-session amendment: "Kernel surface count extended from 15 to 16 with addition of `pace` per ADR-300."
- `CLAUDE.md` — extend `KernelSurfaceSlug` reference in the workspace canon section if/where the list is enumerated (current count → 16)

### Schema migrations
None. `_pace.yaml` substrate already exists (ADR-298 Phase 2). No DB schema changes.

### Render parity
None. Backend changes touch only the API service. Scheduler / MCP server / Output Gateway unaffected.

### Test gate
- `api/test_adr300_pace_surface.py` — asserts: (a) `pace` in `KERNEL_SURFACES`, (b) `GET /api/cockpit/pace` returns expected shape, (c) `PUT /api/cockpit/pace` writes only `pace.kind` and preserves siblings, (d) write uses `authored_by="operator"`, (e) write fails when caller is reviewer (lock honored), (f) lucide icon `gauge` resolvable.

## 4. Out of scope

The following are deliberately deferred — they are real concerns but each justifies its own discourse round:

- **Per-domain pace overrides** (e.g., `trading` domain hourly, `content` domain daily). Substrate doesn't model this; would need ADR-298 amendment.
- **Quiet hours** (e.g., "no wake 22:00–07:00 operator local"). Substrate doesn't model this; would need ADR-298 amendment + timezone substrate.
- **`monthly_budget_usd` edit affordance**. ADR-298 D9 already specifies the dual-cap pattern; surfacing editable budget is a billing/usage UX concern that pairs better with `/settings?tab=billing` than with `/pace`.
- **Auto-tune from drain telemetry** (e.g., "your declared cron rate exceeds pace cap; downgrade to weekly?"). Premature without operator-pace-change-frequency data. Re-evaluate after ≥10 operator pace changes observed in production.
- **PaceBadge re-styling** beyond the read-only-deep-link simplification. Stays as Cockpit chip.

## 5. Open questions

None at decision time. All clarifying questions resolved in-session 2026-05-22 (edit scope: kind-only; telemetry: pure config; launcher slot: trifecta cluster).

## 6. References

- [ADR-298](ADR-298-reviewer-wake-queue-and-pace.md) — Reviewer wake queue + pace substrate (D11 trifecta canon + D5 cockpit-tab decision superseded by this ADR's D3)
- [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) — atomic kernel surfaces axiom (D1 kernel surface list extended)
- [ADR-209](ADR-209-authored-substrate.md) — revision-chain attribution model (operator writes via `write_revision`)
- [ADR-293](ADR-293-governance-operational-substrate-taxonomy.md) — `_pace.yaml` in governance substrate set
- [FOUNDATIONS](../architecture/FOUNDATIONS.md) Axiom 4 (Trigger dimension)
- In-session concept audit (2026-05-22) — pace / cadence / schedule / queue / activity / feed disambiguation
