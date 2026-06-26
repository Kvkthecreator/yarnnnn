# ADR-377 — Context as the Perception Home: connections + their flow, in one place

> **Status**: **Accepted + Implemented** (2026-06-26) — D1 = **Option A** (Settings-like section nav). Final shape: **Perception**[Connections · Sources] + **Feed**[Context In · Context Out · Flow]. Operator decision over the §3 recommendation (which leaned B); the operator's "treat Context closer to Workspace Settings" framing is the ratified shape. The Feed group renamed from "Boundary" and split into three **direction-filtered views over the one complete narrative** ("track everything, filter at the surface"): In = inbound crossings (direction inferred FE-side from the `writtenTo` envelope signal — MCP `remember`, connector sync, upload), Out = the emissions ledger, Flow = the complete unfiltered narrative. The narrative envelope was widened to carry `writtenTo`/`tool` (backend-only `extra_metadata` before) so direction is derivable FE-side; `lib/feed-direction.ts::isInbound` is the helper; In/Flow are one `FeedSurface` filtered/unfiltered (Singular Implementation). No new endpoint/schema. Gate `api/test_adr377_context_perception_home.py` (14/14). See §2 for the honest data ceiling (direction is *inferred*, not stored; reads vs writes distinguished, but a per-event inbound ledger at platform-message granularity remains out of scope — ADR-153).
> **Date**: 2026-06-26
> **Authors**: KVK (operator) + Claude (collaborator)
> **Discourse base**: live screenshot-walk of `/context` (2026-06-26) — In showed connector *setup* (Connect buttons, API-key fields), the title bar read "Feed" not "Context", Flow dumped raw `subject:…returned:0` system rows. The operator's read: "the boundaries are all over the place; In shouldn't show connector setups." Escalated from a render-tweak to a scope question: *what if Context is treated closer to Workspace Settings — the all-in-one home for connections AND the feed-per-platform?*
> **Amends**: [ADR-370](ADR-370-context-surface-the-operations-boundary.md) — reverses its core "Context owns no substrate and no state — a composition over existing mirrors" stance for the **In** lens specifically: Context becomes the **canonical home** for platform connections (perception), not a second mount of the Settings→Perception panes. Out (emissions) + Flow (narrative) stay compositions.
> **Amends**: the connector home — connections move from Workspace-Settings → Perception being their *home* to being a thin **pointer** ("manage connections in Context →"); Context owns the rich UI. Singular Implementation: one real home.
> **Preserves**: [ADR-335](ADR-335-perception-field.md) (the Perception field — watches declared, transports peripherals; this re-homes the *surface*, not the model), [ADR-299](ADR-299-operator-addressing-writes.md)/[ADR-304] (sends stay system infra; Out is read-only legibility), [ADR-289](ADR-289-feed-and-conversation-surfaces.md) (Flow row grammar), [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) (compositor owns the registry; this changes Context's *body*, not its slug/tier).
> **Companion**: [ADR-374](ADR-374-presentation-ia-substrate-face-and-the-steward-posture.md) — Context is the membrane FACE; this ADR makes that face self-contained (it carries the connections + their flow, the GitHub-repo-page equivalent). The two are consistent: 374 says "the membrane is the landing"; this says "and the landing is rich enough to be a home, not a thin lens."
> **Dimensional classification** (Axiom 0): **Channel** (Axiom 6 — the perception surface's structure) + **Substrate** (Axiom 1 — Context gains ownership of the connection-read).

---

## 1. The problem (grounded in the walk)

ADR-370 made Context a thin **composition over mirrors**: In = a *second mount* of the Workspace-Settings → Perception panes (`ConnectedIntegrationsSection` + `SourcesCard`), Out = `EmissionsView`, Flow = `FeedSurface`. The walk exposed why that's incoherent:

1. **In is a borrowed config console.** It mounts the full connector *management* component — Connect buttons, OAuth redirects, API-key paste fields ([`ConnectedIntegrationsSection.tsx`](../../web/components/settings/ConnectedIntegrationsSection.tsx)). The boundary question "what is feeding me" is answered with a setup drawer. The asymmetry is stark: Out is a clean read; In is a management surface.
2. **The dual-home violation.** `ConnectedIntegrationsSection` is mounted in BOTH [`context/page.tsx:86`](../../web/app/(authenticated)/context/page.tsx#L86) AND [`workspace-settings/page.tsx:131`](../../web/app/(authenticated)/workspace-settings/page.tsx#L131). Two homes for one concept — the exact thing Singular Implementation forbids.
3. **The title bug ("Feed" not "Context").** A separate, confirmed navigational gap (the `feed`→`context` cleanup was half-done — `DEFAULT_KEPT_SURFACES = ['feed']` still pins the dissolved slug). Tracked here for context; fixed regardless of which structure D1 picks. See §5.

The operator's reframe: don't *hide* the connections to make In a pure read — **promote** Context to own them. If Context is the perception home, showing connections isn't a borrowed drawer; it's Context's job. The incoherence dissolves by promotion, and Context becomes the **GitHub-repo-page equivalent** — connections + their activity in one place — which is *more* faithful to the membrane metaphor (ADR-374) than the thin version.

## 2. The honest data finding (constrains what "feed-per-platform" can be)

The aspiration is a legacy-Feed-style **per-event inbound ledger** ("Slack #general → 3 messages → written to operation/context/X at 09:42"). **That granularity does not exist in the data:**

- `platform_content` (the per-item inbound store) was **sunset by ADR-153**. `_count_activity(provider)` returns a hardcoded `0` ([`integrations.py:417`](../../api/routes/integrations.py#L417)) with the comment "activity tracked via tasks now."
- What *does* exist per-platform: connection status, the resource list (channels/pages/repos), and **`sync_registry` freshness** — `last_synced_at`, `item_count`, `source_latest_at`, `last_error` per resource ([`integrations.py:1994` sync-status](../../api/routes/integrations.py#L1994)).
- Inbound content, post-ADR-153, lands in substrate via task/recurrence execution and is recorded as **narrative entries** with `provenance` paths — not a queryable per-platform ingestion log.

**So "feed per platform" can faithfully mean: per-connector COVERAGE + FRESHNESS (which resources, how many items, last synced, errors) + a deep-link into the narrative filtered to that platform's provenance.** It cannot (without rebuilding the ADR-153-sunset store) mean a per-message inbound event row. This ADR must not promise the latter. (If a richer per-event inbound ledger is later wanted, it is its own ADR — reversing part of ADR-153 — not assumed here.)

## 3. The decision to make: D1 — Context's structure

Two structures. Both make Context the perception home; they differ in whether the boundary keeps the In/Out/Flow lens model or reorganizes into a Settings-like section nav.

### Option A — Settings-like section nav (the "treat it closer to Workspace Settings" reading)

Context becomes a `SettingsPaneShell` split-nav owning sections:

```
PERCEPTION
  Connections   — each platform: status · resources · freshness · manage-inline · "→ that platform's flow"
  Sources       — standing web/RSS watches (SourcesCard)
BOUNDARY
  Emissions     — Out (EmissionsView, read-only)
  Flow          — the complete narrative (FeedSurface)
```

- **Per-platform:** each connection is a row/pane showing coverage+freshness (§2's real data) with a deep-link to Flow filtered by that platform.
- **Pro:** maximally legible; mirrors the Settings mental model the operator named; Context genuinely *owns* perception.
- **Con:** biggest refactor; Context stops being a "composition" entirely and becomes a container (furthest from ADR-370). Connections management UI moves here wholesale.

### Option B — Keep In/Out/Flow, enrich In (evolutionary)

Context keeps the three lenses; only **In** changes — from borrowed setup panes to an **owned perception read**:

```
In    — connected platforms (status · resources · freshness, the §2 real data) +
        standing sources; each with a "view this platform's flow →" deep-link.
        Setup relocates to a "manage connections →" link (Settings keeps the thin pointer).
Out   — Emissions (unchanged).
Flow  — the narrative (unchanged; or filtered, see D3).
```

- **Pro:** preserves ADR-370's lens model + In↔Out symmetry (both reads); smaller blast radius; In becomes coherent by ownership without restructuring the surface.
- **Con:** "feed per platform" is a deep-link from In into Flow, not a co-located per-platform view — less of the "all in one place" the operator described.

**Recommendation: Option B.** It fixes the named incoherence (In is a borrowed console) by giving Context real ownership of the In read, preserves the In/Out/Flow symmetry that's actually good, and is the smaller, more reversible move. Option A's "Context = Settings-for-perception" is cleaner conceptually but is a large container-ization that re-opens more of ADR-370 than the problem requires. *Operator decides.*

> **RATIFIED: Option A** (2026-06-26). The operator chose the Settings-like section nav — the "all-in-one perception home" framing wins over the smaller evolutionary move. Context becomes a `SettingsPaneShell` with two groups: **Perception** (Connections · Sources) + **Boundary** (Emissions · Flow). The In/Out/Flow lens triple is retired in favor of the four named panes; `context.pane` values become `connections | sources | emissions | flow` (default `connections` — the perception home lands on what's feeding it). `/feed` redirect-stub re-points to `?context.pane=flow`. Connections is the owned rich UI (status · resources · freshness · manage-inline + per-platform flow deep-link); Settings keeps the thin pointer (D2).

## 4. D2 — Connector home: move vs. defer (settled in discourse)

**Decided:** Context owns the rich connections UI; **Workspace-Settings → Perception keeps a thin pointer** ("manage connections in Context →"), not the full component. One real home (Context); Settings stays the place for account/governance.

Cascade (the real blast radius — all reference the connectors home today):
- [`workspace-settings/page.tsx:131`](../../web/app/(authenticated)/workspace-settings/page.tsx#L131) — mounts `ConnectedIntegrationsSection`; becomes the thin pointer.
- [`connectors/page.tsx`](../../web/app/(authenticated)/connectors/page.tsx) — already a redirect stub → Settings; **re-point to Context**.
- `SetupSequence.tsx` (ADR-331), `ConnectionsStatusItem.tsx` (top-bar status), `DestinationSelector.tsx`, `HarvestPicker.tsx`, `redirectTo` deep-links in `ConnectedIntegrationsSection` — audit each; repoint connect-flow returns to `/context`.
- The `redirectTo="/context?context.pane=in"` already in `context/page.tsx` confirms the OAuth round-trip can land back on Context.

## 5. D3 — folded-in fixes (independent of D1, do regardless)

- **The "Feed" title bug** — flip `DEFAULT_KEPT_SURFACES` from `['feed']` → `['context']` ([`surface-preferences.ts:36`](../../web/lib/shell/surface-preferences.ts#L36)) + the keyed checks in [`Desktop.tsx:61`](../../web/components/shell/Desktop.tsx#L61) + the stale `/feed` reference in `AuthenticatedLayout.tsx`. Completes the ADR-370 `feed`→`context` cleanup.
- **Flow noise** — the `subject:…returned:0` MCP-probe rows read as debug. Either filter them or accept (Flow = complete narrative per ADR-370). Deferred sub-decision; not blocking.

## 6. What this does NOT do

- **Does not rebuild the ADR-153 inbound store.** Per-platform "feed" = coverage+freshness + a filtered-narrative deep-link, not a per-message event log (§2).
- **Does not move Sources or Emissions out of their current models** — only connections get the home-move.
- **Does not touch the gate, the write path, or attribution** — pure presentation + one read.
- **Does not change Context's slug/tier/registry entry** (ADR-297) — `context` stays `primary`; only its body changes.

## 7. Rejected / deferred

- **Two homes for connectors (Context + Settings both rich).** Rejected (D2) — Singular Implementation; Settings keeps a pointer only.
- **Per-event inbound ledger now.** Deferred (§2) — would reverse ADR-153; its own ADR if demand surfaces.
- **Abandoning In/Out/Flow entirely (Option A) without operator sign-off.** Open (D1) — recommendation is B, operator decides.

## 8. Sequencing (doc-first)

1. This ADR (decide D1).
2. D3 fixes (title/dock) — independent, smallest, highest-value; can land first.
3. The In refactor per the chosen D1 structure + the connector home-move (D2) + the Settings thin-pointer.
4. Source-guard gate (`api/test_adr377_context_perception_home.py`) + `tsc --noEmit`.
