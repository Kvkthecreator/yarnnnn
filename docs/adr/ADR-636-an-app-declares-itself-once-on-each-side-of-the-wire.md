# ADR-636 — An app declares itself once on each side of the wire

> **Status**: **Accepted + Implemented** (2026-09-04, operator-ratified: *"aligned in full… ensure singular streamlined discipline with code and docs, scoping in deletion and clean-up of code where warranted to avoid future ambiguity"*). Gate: `api/test_adr636_app_declaration_parity.py`.
> **Date**: 2026-09-04
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Mechanism** (Axiom 5 — where a declaration LIVES and who may assert it). No Identity change, no Purpose change, no authority change: the same apps, the same agents, the same engines, the same ceiling. What moves is the DECLARATION SITE on the client, and what arrives is the parity that holds the two sides to one story.

**Extends**:
- [ADR-562](ADR-562-app-owned-ai-configuration.md) — *an app's AI configuration is declared where the app lives*. Same rule, one wire further: an app's **presentation** configuration is declared where the app lives on the client, and derived from the served roster wherever the roster can answer.
- [ADR-592](ADR-592-app-stage.md) — the stage is declared once and the six spellings are derived. This ADR closes the spellings ADR-592 could not reach, because they live on the other side of the wire.
- [ADR-633](ADR-633-the-artboard-is-a-stack-of-layers.md) **D2** — `objectModel` is DECLARED, never back-derived. That ruling is generalized: every app-shaped fact on the client is declared on one row, and the row is gated against the served roster.

**Preserves** (load-bearing, untouched): ADR-460 D3.a (the authority cliff — no client row may represent authority), ADR-464 (kernel corpus is code, member corpus is a folder), ADR-472 D2 / ADR-473 D2 (the kernel never imports an app), ADR-562 D1–D3/D5/D6, ADR-600 D2 (`offered`/`kernel` are fields), ADR-601 D1 (capability lives at the app), ADR-297 (one resolver for a surface's mark).

---

## 1. Context — the boundary the kernel holds, and the one it does not

The operator's question was structural: *are the agent/app displays mismatching because the architecture is weak?*

The audit's answer is precise, and it is not the one the symptom suggested.

**The backend derivation is sound.** Driven live at `7ed27fb`:

```
blogger    apps=['blogger']            promoted=True   offered=False
designer   apps=['images']             promoted=True   offered=False
editor     apps=['slides','text']      promoted=True   offered=False
supervisor apps=['strings']            promoted=True   offered=False
```

Three registries, three questions, no copies: identity/character/engine on `AGENTS`, the agent→app relation derived by `apps_for_agent()` from the app's own `register_app`, exposure derived by `launcher_tier_for`/`is_default_pinned`/`is_promoted` from one `stage` field. Promoting an app promotes its agent in one edit (the ADR-602 D3 dividend). Nothing about that needs repair.

**The mismatches come from the other side of the wire.** `services/apps/__init__.py` states the kernel's rule in its own docstring:

> *"The kernel never imports an app. Registration is the only direction: an app reaches the shared machinery, never the reverse."*

The frontend has no such door. An app is re-declared there by hand, in six places, none of which the app owns:

| # | Site | Re-declares |
|---|---|---|
| 1 | `lib/shell/surface-preferences.ts` `DEFAULT_KEPT_SURFACES` | the Dock default (a copy of `is_default_pinned`) |
| 2 | `components/shell/SurfaceRegistry.tsx` | slug → window component |
| 3 | `types/surface.ts` `KernelSurfaceSlug` + `KERNEL_SURFACE_SLUGS` | the navigable slug set |
| 4 | `lib/file-types/index.ts` `APP_SURFACES` | app → surface/param/label |
| 5 | `components/authoring/StudioSurface.tsx` `AuthoringApp` | label · tagline · icon · `objectModel` · the `slug` union |
| 6 | `components/authoring/OpenArtifactModal.tsx` `SERVED_INDEX_APPS` | which apps serve an index |

Plus `components/agents/AgentIcon.tsx` `BEING_ICONS`, a hand map against `AGENTS[*].icon`.

## 2. The finding that decides the design — the lists AGREE, and that is the problem

The sweep diffed every one of these against the derived truth. **They agree today.** There is no live user-visible mismatch to repair.

That is the whole point. The operator's instinct was not about today's data; it was about the cost of the next change, and the instinct is correct: **agreement is holding by memory, not by construction.**

What is actually guarded, driven at `7ed27fb`:

- `BEING_ICONS` — **properly derived-gated**, bidirectionally, off `AGENTS` (`test_agent_registry.py`). This is the model. Its own comment records the failure that earned it: *"Supervisor rendered the fallback Bot for a day because the registry said `clipboard-list` and the map had three keys."*
- `DEFAULT_KEPT_SURFACES` — **gated** against `is_default_pinned` (`test_adr592_app_stage.py`). The hand-copy is justified and stays: the Dock seeds client-side before any roster arrives.
- The slug set — **gated** three ways by `test_adr338_surface_registry_parity.py` (backend navigable == FE allowlist == window registry minus panes).

What is not:

**No gate anywhere derives an FE app list from `all_apps()`.** Zero. Falsified by search across all `api/test_*.py`: four gates import `all_apps`, none of them reads sites 4, 5 or 6.

The checks that exist over those sites are **negative** — `"APP_SURFACES no longer claims docs"`, `"SurfaceRegistry carries no docs row"`. A negative check catches a **deletion** that was forgotten. It cannot, by construction, catch an **addition** that was forgotten. Every app added since has been correct by the author remembering six files.

⭐⭐⭐ **A negative assertion is not parity.** It pins the last thing that went wrong; parity pins the relation. The six sites are one relation with six spellings, and ADR-592 already wrote the sentence this ADR reuses: *an app is hidden because of what it is, not because six people remembered.*

## 3. The failure mode, already in the record

Every recent display defect is the same shape — *a property of an app, spelled somewhere the app does not own*:

- **ADR-592**: "hide an app" spelled by hand in six places; Docs declared PAUSED 2026-08-17 and still reachable at `/docs`, in the Dock, and by double-clicking any document.
- **ADR-633 §1.1**: images was never NAMED by the `layout === 'deck'` ternary, fell through onto the document branch, and one object read "Slide" in the crumb and "Sections" in the rail.
- **AgentIcon**: the registry gained `clipboard-list`; the map had three keys; Supervisor wore the fallback for a day.

ADR-633 D2's answer — *"A derivation has a default; a declaration does not"* — is right and is hereby generalized. The remaining gap is that a declaration nothing checks is just a better-organized copy.

## 4. D1 — An app's client-side presentation is ONE row, in one registry

`web/lib/apps/registry.ts` holds one `AppDescriptor` per app: the client mirror of `register_app`.

```ts
export interface AppDescriptor {
  slug: string;              // the app identity; keys the served roster join
  label: string;             // operator-readable name
  objectModel: 'flow' | 'pages' | 'layers';  // ADR-633 D2 — REQUIRED, never derived
  artifactParam: string;     // the surface param namespace
  servesIndex: boolean;      // does OpenArtifactModal list this app's artifacts
  dimensionsFirst?: boolean; // ADR-472 D3 — a raster artifact is born at a size
}
```

Sites 4, 5 and 6 become derivations over `APP_DESCRIPTORS`. `AuthoringApp.slug` stops being a closed union (`'slides' | 'images' | 'blogger'`) — a union is a fourth hand-kept list wearing a type's clothes, and adding an app should not require editing a type.

**What is NOT in the row, deliberately:** the resident, the engine, the stage, the tier, the pin. Those are the server's and arrive on the roster. A client row that named a resident would be ADR-562's deleted `web/lib/apps/authoring.ts` returning, and a client row that named a stage would be ADR-592's derivation forked. The row carries **only what the client alone knows**: what to render and how the member's object is shaped.

**Icons stay on the surface row** and resolve through `resolveSurfaceIcon` (ADR-297) — an app has one mark everywhere, and a re-icon moves every rendering at once. `AuthoringApp.icon` is dropped as a second home; ADR-602 D4 already repaired one drift where Slides wore Palette on its landing and Presentation in the launcher.

## 5. D2 — The parity gate is derived, bidirectional, and fails on an ADDITION

`api/test_adr636_app_declaration_parity.py` asserts, from `all_apps()` and `AGENTS` as the source:

1. every registered app has an `AppDescriptor` row — **the addition case, which nothing previously caught**;
2. every `AppDescriptor` names a registered app (no phantom);
3. every authoring app declares `objectModel` (ADR-633 D2, no `?`, no `??` at any read site);
4. every registered app that owns artifact types appears in the type→app association;
5. `BEING_ICONS` ⟷ `AGENTS[*].icon`, both directions (re-anchored, not duplicated — the existing check in `test_agent_registry.py` is the home; this gate does not fork it).

The gate reads the FE source as text — the same technique the eight existing parity gates use, and the only one available across a Python/TypeScript wire.

⭐ **The gate must be falsified in both directions before it ships**: add a fake registered app → red; add a phantom descriptor → red. A parity gate that has only ever been run green is indistinguishable from one that parses nothing (the ADR-630 index-ceiling lesson: *a ceiling that is gated but never enforced*).

## 6. D3 — Deletion and cleanup, so the ambiguity cannot regrow

Per the operator's ruling (*scoping in deletion and clean-up of code where warranted to avoid future ambiguity*):

- **`AuthoringApp.slug`'s closed union is DELETED** — replaced by `string` validated against the descriptor registry.
- **`SERVED_INDEX_APPS` is DELETED** — derived from `servesIndex`.
- **`APP_SURFACES` is DELETED as a hand map** — derived from the descriptors.
- **`AuthoringApp.icon` is DELETED** — the surface row's `icon_key` is the one home (ADR-297).
- **`test_adr338_surface_registry_parity.py`'s stale pane expectation is repaired**: it hand-spells `autonomy`, which left the union 2026-08-26 with the allowlist. That gate has been RED at HEAD since; a hand-spelled expectation set inside a parity gate is the same defect the gate exists to catch, one level up. It becomes derived.

**Not deleted, deliberately:** `DEFAULT_KEPT_SURFACES` (seeds before the roster arrives; already gated), `SurfaceRegistry` (a slug→component map cannot be derived — components are imports), `KernelSurfaceSlug` (the type union is real type safety and is already three-way gated).

## 7. What this ADR does NOT do

- It does **not** move any fact from the server to the client. Every server-derived truth stays server-derived; the client gets a gate, not a copy.
- It does **not** touch the agent registry, `register_app`, `stage`, or any authority surface. The ADR-460 D3.a cliff is untouched — no client row can represent authority, and the descriptor's key whitelist is the mechanism, as it is on the agent row.
- It does **not** add a runtime code path. Every change is a declaration site plus a gate; behaviour at every rendering is byte-identical on the day it ships (the ADR-375 D4 rule — a seam that changes nothing on arrival).

## 8. Open

- The client roster could eventually be **served** rather than mirrored (`AppDescriptor` arriving on the surfaces payload), which would delete the gate along with the copy. Deferred: the descriptor holds component references and lucide icons, which do not cross a wire, so serving it would split the row and re-create the second home. Revisit when the row's remaining fields are all data.
- `standing_executor` is declared by ZERO apps since ADR-610 dissolved `keeper` — a live seam with no filling. Left standing per ADR-604 D2's own reasoning (*a mechanism is not wrong because its first filling was*), and noted here so a future session does not rediscover it as a defect.
- `offered` is `False` for all four agents, so `/agents`' "TO WORK WITH" section has been structurally empty since ADR-599 D1. That is the ruled state, not a bug; the empty state is the one the operator ruled on.
