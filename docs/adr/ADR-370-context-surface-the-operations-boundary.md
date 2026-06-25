# ADR-370 — Context: the operation's boundary surface (In · Out · Flow)

> **Status:** **Accepted (2026-06-25).** Implementation in progress. FE + one backend file: a new kernel surface declared in `api/services/kernel_surfaces.py::KERNEL_SURFACES` (the surface registry that flows to the compositor via `GET /api/programs/surfaces`) → the API Render service is touched; no schema, no primitive, no scheduler/MCP/render-gateway change. The narrative lens re-mounts the existing `FeedSurface` (one body, two mounts — ADR-340 D8); the perception lenses re-mount the existing `SourcesCard` + `ConnectedIntegrationsSection`. No new substrate, no new data path.
> **Date:** 2026-06-25
> **Authors:** KVK (operator) + Claude (collaborator)
> **Discourse base:** the operator's feed-refactor question (2026-06-25) — *"I'm thinking of refactoring the feed surface to be more explicit and organized … having a split-type navigation inspired by our workspace settings … the information will be about feed IN, feed OUT, or feed TOTAL … essentially context in, context out … consolidating external triggers, MCP, connectors, sources, RSS, etc. with write-outs, both internal and external."* Pressure-tested across three forks: (1) IN/OUT/TOTAL is not a *Feed* restructure — the Feed is the narrative (ADR-289), a composition over one act (Read); the IN/OUT plumbing is the Perception field (ADR-335), already mirror-housed under Workspace Settings → Perception. (2) "Absorb the narrative into chat" — rejected: chat is not a surface (ADR-316, a dockable command rail), and pouring the full narrative into bubble grammar is the exact regression ADR-289 was written to prevent. (3) The convergent move: a new **composition** surface where the narrative becomes *one lens* (Flow) beside the perception mirrors (In) and the emission view (Out), with the `/feed` route folding into it.
> **Amends:** [ADR-297](ADR-297-surfaces-as-substrate-mirror.md) (adds one **composition** surface — slug `context` — to the kernel surface registry; `feed` drops from a search-only mirror to a lens of `context`, its route a redirect stub), [ADR-340](ADR-340-operator-experience-model.md) §9 / Derived Principle 29 (the deferred "Home re-derivation as front-page of compositions" + "launcher IA re-sort" arc gains a second composition: Context joins Home and Notifications as a third **composition** surface, each one operator act; the **Read** act now has a boundary-shaped composition in addition to its operating-work mount in Notifications → Activity), [ADR-335](ADR-335-perception-field.md) (the Perception field gains a first-class operator-facing **gathering** surface — the watches/transports that were Workspace-Settings panes are also mounted in Context → In; the substrate model is unchanged, this is a second mount).
> **Preserves:** [ADR-289](ADR-289-feed-and-conversation-surfaces.md) (the two render grammars survive intact — Flow uses the typed-row Feed grammar; chat keeps bubble grammar in the dockable rail; **the narrative is still not a conversation**, it is merely re-homed from a standalone route to a lens), [ADR-316](ADR-316-chat-as-dockable-rail.md) (chat stays the command rail over the foregrounded surface — including over Context; it is not folded in), [ADR-346](ADR-346-operation-composition-surface.md) + [ADR-349](ADR-349-launcher-ia-re-sort.md) (**Notifications stays the operating-work composition** — To do · Activity · Schedule — NOT demoted; Context is a *sibling* composition over the boundary, not a replacement), [ADR-350](ADR-350-standing-obligation-as-rendered-surface.md) (the standing band remains in its existing mounts — Context does not claim it), [ADR-367](ADR-367-home-as-operating-cockpit.md) D3 (the **macOS tiered-redundancy principle** is the load-bearing justification — the narrative appearing in both Context → Flow and Notifications → Activity is *intended consistency of access*, the same redundancy Home and Notifications already share, not a defect), [ADR-320](ADR-320-constitution-region-topological-cut.md) (the surface reads substrate, never writes it; the `context/` substrate ROOT is retired — the route slug `context` is unrelated to any filesystem namespace, see §6), [ADR-299](ADR-299-kernel-universal-operator-addressing-capability.md)/[ADR-304](ADR-304-operator-addressing-writes-generalization.md) (the Out lens *renders* the emission channels — it does not turn operator-addressing writes into workspace capabilities; they remain system infrastructure, surfaced for legibility).
> **Dimensional classification:** **Channel** (Axiom 6 — what the operator sees and where) over the **operation's boundary** (the In/Out edge of the six-dimensional cell where the workspace meets the outside world): context flowing in (Perception, Axiom 1 §8) and outputs flowing out (Channel), with the running narrative (Axiom 9) as the record of every crossing.

---

## 1. The question this answers

The Feed today is the **narrative** — the single chat-shaped, time-ordered log of every invocation (ADR-289, `invocation-and-narrative.md`). It answers one operator act: **Read** — *"what happened while I wasn't watching."* It is already demoted to `search-only` and fronted by Notifications → Activity (ADR-349); the `/feed` route is a deep-link transport, not a resting tile.

The operator's instinct was to reorganize the Feed into **IN / OUT / TOTAL** — to gather "what flows into this operation" (external triggers, MCP, connectors, sources, RSS) and "what flows out" (writes, both internal and external) alongside the running log. That instinct is correct about a real concept — **the operation has a boundary, and everything crossing it is one thing** — but wrong about *where* it lives. The Feed is a composition over the Read act; the IN/OUT plumbing is the **Perception field** (ADR-335), which is mirror-housed under Workspace Settings → Perception. Putting editable transport config and an immutable event log under one *Feed* would have merged two acts (Tune + Read) into one surface, violating "mirror once, compose few" (DP29).

The resolution: the operator's "IN/OUT/TOTAL" is a real and valuable **composition** — but it is a *new* surface (the operation's boundary), not a Feed restructure. The narrative becomes one lens of it.

## 2. The decision

### D1 — Context is the operation's boundary composition

A new **composition** surface (ADR-340 D1 surface-class: one surface ↔ one operator act, selective/opinionated/gathering — as opposed to a *mirror*, one surface ↔ one substrate concern). Slug `context`, route `/context`, label **Context**, `launcher_tier: primary`. Its act is *understand and manage the operation's boundary* — what context flows in, what flows out, and the running record of every crossing.

It owns no substrate and no state. Like Home (ADR-312) and Notifications (ADR-346), it is a composition over existing mirrors, mounted via the shared `SettingsPaneShell` (Singular Implementation — the same split-nav shell behind Workspace Settings, Notifications, and System Settings).

### D2 — Three lenses: In · Out · Flow

| Lens | Operator question | Mounts | Substrate behind it |
|------|-------------------|--------|---------------------|
| **In** | *What context feeds this operation?* | `SourcesCard` (watches/RSS) + `ConnectedIntegrationsSection` (connectors) + MCP-transport read | `_sources.yaml` + `platform_connections` + MCP bindings (ADR-335 Perception field) |
| **Out** | *What does this operation emit, and where?* | Emission view — operator-addressing **dispatch history** (what shipped, to whom, when) + the addressing channels + substrate write-targets | ADR-299/304 addressing dispatch ledger (read-only, via new `GET /api/emissions`); single-writer paths (ADR-286) |
| **Flow** | *What just crossed the boundary?* | `FeedSurface` (the complete narrative, typed-row grammar, **intact**) | `session_messages` (ADR-289 Feed grammar) |

**Flow is the complete narrative, not a filtered subset.** The operator's "TOTAL" is honored literally: everything `/feed` showed lives here unchanged — autonomous wakes, housekeeping, operator messages, Reviewer decisions. Nothing is orphaned; `/feed` *moves* here, it is not split. (An inbound/outbound *filter* over Flow is a cheap follow-on — the Feed's existing `FeedFilterBar` already faceting the narrative — but the default Flow view is the full log, preserving today's behavior exactly.)

### D3 — Deliberate tiered redundancy with Notifications (the macOS principle, again)

The narrative now appears in **two** compositions: Context → Flow and Notifications → Activity. Both mount the same `FeedSurface` (one body, two mounts — ADR-340 D8). **This redundancy is intended**, and it is the macOS resolution canonized in ADR-367 D3, not a defect:

> *the same data/action may appear on multiple surfaces as long as each surface owns one clear primary job and the overlap buys a different interaction cost. The failure mode is not redundancy — it is two surfaces with the same job and no clear primary.*

The primary jobs are distinct:
- **Notifications (operating workbench)** — *operate the recurring work*: To do (decide) · Activity (read) · Schedule (tune). The narrative appears here as the temporal read *of the work*. Reached from the bell.
- **Context (boundary surface)** — *understand the operation's edge*: what feeds it, what it emits, what crossed. The narrative appears here as the record *of the crossings*. The "data plumbing" view.

Same substrate (`session_messages`), two framings, two interaction costs — exactly as brightness is settable from both Control Center and System Settings. The operator chose consistency-of-access over single-mount minimalism (the same call made for Home vs Notifications in ADR-367 D3).

### D4 — `/feed` dissolves into Context; the route becomes a redirect stub

The `feed` slug ceases to be an operator-reachable surface. Its renderer (`FeedSurface`) survives as the Flow lens body. The `/feed` route becomes a pure server-transport redirect stub (ADR-308) → `/context?context.pane=flow` (the lens is a window-namespaced `pane` param, the shared `SettingsPaneShell` convention — ADR-358 D6), merging existing query params so `?prompt=` chat-summon deep-links keep working; the `/chat → /feed`, `/orchestrator → /feed`, `/workfloor → /feed` chain reaches `/context` transitively through the `/feed` stub. The `feed` registry entry's `default_pinned` flips False and its launcher slot is inherited by `context`; the `feed` FE-registry slug maps to `ContextPage` (Flow default) so legacy deck state foregrounding `feed` mounts the live surface, never the redirect stub.

### D5 — Context reclaims its name; the prior `/context → /files` stub is retired

The slug `context` was a redirect stub → `/files` (2026-06-01, "slug/route/label coherence"). That stub is **deleted** — the `context/` substrate ROOT was retired by ADR-320's topological cut (the kvk workspace migrated `context/` → `operation/`), so the word is free at the route layer. The Files surface keeps its own `/files` slug; only its legacy `/context` alias goes away.

The in-Feed **"Context" button** (the `WorkspaceContextOverlay` — Mandate/Rules/Pulse primer) is renamed → **"Substrate"** (it shows workspace substrate files; honest and collision-free) and travels into the Flow lens with the rest of the Feed. This prevents the surface name "Context" from colliding with a button labeled "Context" *inside* one of its own lenses.

### D6 — Chat is untouched

Chat remains the dockable command rail (ADR-316) floating over the foregrounded surface — including over Context. It is **not** a lens, **not** folded in. Bubble grammar stays in the rail; Flow keeps row grammar (ADR-289 preserved). "Absorb the narrative into chat" was considered and rejected (see §3).

## 3. What this does NOT do

- **Does not merge the Feed into chat.** Chat is a command rail, not a surface (ADR-316); the full narrative in bubble grammar is the exact ADR-289 regression. Flow keeps typed-row grammar.
- **Does not demote Notifications.** It stays the operating-work composition; the narrative redundancy is deliberate (D3).
- **Does not make the In/Out config a second writer.** The Perception mirrors (Sources/Connectors) keep their authoritative home and write path; Context → In is a second *mount* of the same self-contained components (ADR-335 substrate model unchanged). Context → Out *renders* emission dispatch read-only (ADR-299/304 — operator-addressing writes stay system infrastructure; the Out lens is a legibility view over what already happened, never a send affordance).
- **Does not change the narrative substrate, the Feed render grammar, schema, primitives, scheduler, MCP, or the render gateway.** Backend touch is two reads on the API service: the `KERNEL_SURFACES` registry entry (compositor surface declaration, flows to FE via `GET /api/programs/surfaces`) and a new read-only `GET /api/emissions` route projecting the operator-addressing dispatch ledger for the Out lens. No new table, no write path, no schema migration.
- **Does not resurrect the `context/` substrate root.** The route slug `context` is unrelated to any filesystem namespace (§6).

## 4. Why a composition, not a mirror or a Feed restructure

The three forks the discourse rejected, recorded so the decision is legible:

1. **Feed gets IN/OUT/TOTAL tabs** → rejected. The Feed is a composition over the Read act; IN/OUT is editable Perception config (the Tune act). One surface, two acts → DP29 violation, and a schizophrenic build (forms in one tab, an immutable timeline in another).
2. **Narrative absorbed into chat** → rejected. Chat has no route (ADR-316); it is the command rail. Pouring the full narrative into bubble grammar re-creates the alpha-trader legibility bug ADR-289 was written to fix ("autonomous activity in bubbles reads as the system talking to me, which is a lie").
3. **Context as a sibling composition (this ADR)** → accepted. The narrative survives in its own grammar as a lens; the Perception mirrors are *gathered* (second mount, not duplicated); the boundary becomes one legible operator act; `/feed` folds in cleanly (route count drops, ADR-340 §9 direction).

## 5. The `context` slug ≠ `context/` substrate root ≠ "context domains"

A standing disambiguation, because the word is busy:
- **`/context` (this ADR)** — a route URL; a composition surface over the operation's boundary.
- **`context/` (retired)** — was a substrate root (ADR-151 context domains, ADR-320 topological cut); migrated to `operation/`. Does not exist as a live root.
- **"context domains" (ADR-151 fiction)** — `/workspace/context/{domain}/`; live workspaces don't use it (the `operation/memory/` inbox model of ADR-368 superseded the domain fiction in practice).
- **`pull_context` (MCP)** — superseded by the ADR-368 `recall` verb.

Future readers: the route slug came back; the substrate root did not.

## 6. Doc cascade (same commit)

- **New:** this ADR.
- **Amend banners:** ADR-297 (registry gains `context` composition; `feed` → lens), ADR-340 §9 (second composition lands; launcher IA gains Context), ADR-335 (Perception gains the Context → In mount), ADR-289 (narrative re-homed route→lens; grammar preserved), ADR-346/349 (Notifications-sibling note).
- **`docs/architecture/invocation-and-narrative.md`** — the narrative's surface home updates from `/feed` to "Context → Flow lens (and Notifications → Activity)"; the definition (narrative ⊇ chat; every invocation logs) is unchanged.
- **GLOSSARY** — "Context (surface)" entry + the §5 disambiguation; "Feed" entry notes route→lens fold.
- **CLAUDE.md** — surface-model addendum gains the Context composition; routes.ts redirect-stub table updated.
- **Gate:** `api/test_adr370_context_surface.py` — FE source-guards + `kernel_surface_slugs()` includes `context`, `/feed` is a redirect stub, the `/context → /files` stub is gone.

## 7. Open follow-ons (deferred)

- **Inbound/outbound filter over Flow** — facet the narrative by crossing-direction (the literal "IN/OUT" *within* Flow), reusing `FeedFilterBar`. Cheap; deferred to keep this ADR's Flow == today's Feed exactly.
- **Out lens depth** — the first cut renders emission channels + write-targets read-only. A richer "what shipped, to whom, when" projection over operator-addressing dispatch history is program-scoped follow-on.
- **MCP-transport UI in In** — currently the In lens shows Sources + Connectors; an explicit MCP-bindings panel (which foreign LLMs hold tokens, last `remember`/`recall`/`trace`) is a follow-on once the ADR-368 interop face has dispatch history worth rendering.
