# ADR-488 — IMAGES Goes Internal: the Unveil Bar Is Polish Parity

> **Status**: **Implemented** (2026-07-28, operator-ratified). The `images` surface is re-tiered `primary` → `search-only` and leaves the default Dock. Development continues internally; nothing is deleted.
> **Date**: 2026-07-28
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Channel** (Axiom 6 — what the operator is shown at rest). No Substrate, Identity, or Mechanism change of any kind.
> **Relates to**: [ADR-468](ADR-468-images-decomposed-generation-on-a-layered-object-substrate.md) (whose D1 unveil rule this restates), [ADR-472](ADR-472-images-as-a-first-class-app.md) (the app housing — untouched), [ADR-475](ADR-475-decomposed-generation.md) (generation — untouched, stays live), [ADR-486](ADR-486-ai-radar-the-standing-app.md) (D7 — the registration-is-not-unveil pattern this reuses; Radar unveiled the same day this hid), [ADR-473](ADR-473-document-types-the-launchservices-shape.md) (type→app routing — the reason hidden ≠ unplugged).

---

## 1. Context — the operator's call, and what it is not

IMAGES is **functionally complete through its core loop**: the carve into its own app (ADR-472), the shared object kernel (`block-staged`), dimensions-first creation, decomposed per-object generation live on Gemini and metered per leaf (ADR-475, prod-smoked with a real shippable ad), client-side PNG export. This ADR is **not** a verdict on the app or its thesis — the composition-as-source / raster-as-derivation model worked end to end on the first real ad.

It is a **focus decision** (operator, 2026-07-28): the pre-v1-beta work goes to polishing the core services, Studio, and the newly-landed Radar app. What remains on IMAGES is precisely the long-tail interaction-polish class of work — true alpha matting, per-object regeneration UX, export fidelity (gradients / `object-fit` / webfonts), the owed human click-passes — and that class of work is exactly what should *not* be funded ahead of a beta whose thesis is the record, not the canvas.

### The unveil rule, restated honestly

ADR-468 D1 set the unveil gate at "generation works" — and generation working is what unveiled `/images` into the Dock (2026-07-22, the five-app Dock). That gate fired too early. For a **Canva-class app**, the honest unveil bar is **polish parity**: the app competes on interaction feel against very deep incumbents, and a beta operator meeting a rough canvas reads it as the product's quality, not the app's youth. ADR-486 D7 already ratified the correct pattern for exactly this situation — **registration is not unveil**; the dock icon is *earned*, not shipped. This ADR applies Radar's own rule back to the app whose lesson taught it.

## 2. Decision

**D1 — Hidden, not unplugged.** The `images` registry row re-tiers `launcher_tier: "primary"` → `"search-only"` and `default_pinned: True` → `False`. Everything else stands: the route, the register, the backend package (`api/services/images/`), the layout registrations, the generation engine, the metering, the gates. A composition in Files still opens into `/images` via `openPath` (ADR-473 type→app routing). The app is findable by flat search — which is the internal-development access path, exactly as Radar's pre-unveil state was.

**D2 — The Dock converges without clobbering authorship.** `DEFAULT_KEPT_SURFACES` drops `images` (new operators get the four-app Dock + Radar). For existing operators, the dock-reseed **generation ladder** (surface-preferences.ts) carries the change: the 2026-07-28 generation rewrites a stored Dock to the current default **only when it is byte-equal to the prior seeded default** — an operator who curated even one icon is never overwritten, so a *deliberate* Images pin survives the hide. One generation carries both of the day's moves (Radar in per ADR-486, Images out per this ADR).

**D3 — Public docs de-list the app.** The GitBook removes the Images app page and its mentions from nav, quickstart, and feature lists. Internal canon (ADRs 468/471/472/473/475, the analysis docs, the gates) is untouched — it is the record of a live internal arc, not a public promise.

**D4 — Development continues internally, gated as before.** The ADR-472 (27 checks, incl. the new §6 hidden-state block) and ADR-475 (47 checks) gates stay in force so the hidden app cannot silently drift while Studio's shared kernel evolves under it. Work on matting, regen UX, and export fidelity proceeds on engineering time, unadvertised.

## 3. What re-unveiling takes (§5 of the future session that does it)

Re-unveiling is a **deliberate decision recorded against this ADR**, not a flag flip:

1. The polish-parity bar is judged met (the named debts: alpha matting or an honest scope statement without it; per-object regeneration UX; export fidelity click-pass green on a real ad).
2. Registry: `search-only` → `primary`, `default_pinned` → `True`.
3. `DEFAULT_KEPT_SURFACES` re-adds `images` (Studio-adjacent, per the maker-band order) **plus a new reseed generation** whose `previous` is the then-current default — the D2 ladder pattern.
4. `test_adr472_images.py` §6 is updated in the same commit (it pins the *hidden* state and will correctly fail on a half-unveil).
5. GitBook re-lists the app.

## 4. What this ADR explicitly does NOT do

- Does **not** delete or deprecate any code, gate, or canon. Singular-implementation discipline cuts the other way here: the app is one implementation, merely unpromoted.
- Does **not** revisit ADR-472's housing (the app carve stands; the shared kernel keeps both consumers).
- Does **not** stop the metering or the engine — an internal compose still ledgers its per-leaf cost (ADR-475).
- Does **not** create a "hidden apps" mechanism. `search-only` already is that mechanism (ADR-340 D5; exercised by Radar pre-unveil, the dormant `setup`/`program` rows, and now Images).

## 5. Receipts

- Registry flip: `api/services/kernel_surfaces.py` (`images` row, ADR-488 comment).
- Dock default + generation ladder: `web/lib/shell/surface-preferences.ts`.
- Gate: `api/test_adr472_images.py` §6 (5 new checks — search-only, unpinned, still routable, absent from default Dock, de-seed path exists) — 27/27.
- Sibling gates green post-change: ADR-486 radar (co-asserts the shared dock state), ADR-297 (pinned == primary set-coherence), ADR-412, ADR-440, ADR-475.
- ADR-415's stale `['chat']` dock assert (broken since the 2026-07-22 five-app Dock, pre-existing red) repaired to the anchor invariant it actually owns ("chat leads").
