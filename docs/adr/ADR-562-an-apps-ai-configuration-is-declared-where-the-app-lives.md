# ADR-562 — An app's AI configuration is declared where the app lives

> **Status**: **Accepted + Implemented** (2026-08-13, operator-ratified). Gate: `api/test_adr562_app_owned_config.py` (falsified ×6). D5 **click-pass PASSED** (2026-08-13): the bound lane introduced itself as *"I'm Designer — your maker in this workspace"*, which is the read-back this ADR built.
>
> **Amended by D6 (2026-08-13, same day, operator-ratified)** — **an app may NAME its resident.** `register_app("docs", resident="designer", name="Writer")`: in Docs the colleague is **Writer**, in Studio and IMAGES it stays **Designer**. §6's "does not add per-app agent names yet" is CLOSED — it was the one-line edit that section predicted, and the `name` field this ADR shipped declared-and-unread is now consumed. **A name, not a character**: writing is not a fourth addressed operation (PRODUCE covers making; the roster is closed at three — AGENT-TAXONOMY §5), so Docs pins the same maker under a name that fits the capture medium. The rename is stated in the prompt as an **override**, not an alias, because the character text opens *"You are Designer —"* and the colleague introduces itself by that name; two live names let the model pick the first it read. The app is **derived from the artifact's own `data-template`**, never stored on the lane, so a document changing hands cannot carry a stale label. Whether Docs earns its own capture **doctrine** is the open discourse on app-level standing instructions — doctrine is instructions, not identity.
> **Date**: 2026-08-13
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Mechanism** (Axiom 5 — where a declaration LIVES and who may assert it). No Identity change, no Purpose change: the same colleagues, the same engines, the same authority ceiling. What moves is the DECLARATION SITE.

**Amends**:
- [ADR-467](ADR-467-app-residency-and-the-cast.md) **D1** — residency stands exactly as ruled; its **LOCATION** moves. `web/lib/apps/authoring.ts` is DELETED; each app declares its resident in its own module via `register_app`. D2 (chat gets no default) and D3 (multi-residency) are untouched.
- [ADR-450](ADR-450-derive-recipes.md) — a recipe may declare a `resident` (D4). Same rule one rung down: the declaration owns its colleague.

**Preserves** (load-bearing, untouched): ADR-460 D3.a (the authority cliff — an app row cannot represent authority), ADR-464 (kernel corpus is code, member corpus is a folder), ADR-472 D2 / ADR-473 D2 (the app boundary is the module; the kernel never imports an app), ADR-495 (the cast decides who replies), ADR-558 (chat is the engine surface).

---

## 1. Context — a pin nobody could see

The operator's question was structural: *where should an app's dedicated AI/agent configuration be managed?* The audit's answer was that it already had a ratified home for everything **except** the AI facts.

`register_layouts` (ADR-472 D2) states the pattern in its own docstring:

> *"Rather than fork them per app (the dual-approach smell) or have Studio import IMAGES (a kernel depending on an app), each app REGISTERS its layouts here and the shared machinery resolves through one door."*

Every app-owned fact followed that rule — document types, arrangements, scaffolds, block vocabulary. One did not: **who the app's bound lane talks to**. That lived in TypeScript, on the client, in `web/lib/apps/authoring.ts`, while radar's lived hardcoded in `services/radar.py`. Two declarations, two languages, nothing holding them to one story, and no obvious home for app N.

**The receipt: the pin was real and invisible.** `StudioSurface` created its lane with `agent: residentFor(app.slug)` — correct, deliberate, ADR-467-compliant. Then it **discarded the served `agents` roster** in `refreshLanes` and rendered `modelLabel`. So a member working in Docs read:

> *"Claude Sonnet is working…"*

in a lane whose resident is **Designer**. The colleague was pinned at creation and never named again. This is the `models[0]` incoherence ADR-460 D4 removed — *"the last place in the OS that answered 'who am I talking to?' with an array index"* — surviving one layer up, in the surface, where nobody looked. The FE could not read the fact back because the FE was the one asserting it.

## 2. D1 — An app's AI configuration is an app-module fact

The app declares its resident where it declares everything else it owns:

```python
# services/apps/docs.py
register_layouts(DOCS_LAYOUTS)
register_app("docs", resident="designer")
```

One declaration per app, in the app's own module, through the same door as its layouts. `resident_for_app(slug)` resolves it; `all_apps()` serves the registry.

**Why not a workspace folder.** ADR-464's ruling holds verbatim — *"the member's copy is a folder; the kernel's is code."* A member's agent is `agents/{slug}/_agent.yaml`, theirs to author, discovered never registered. An **app is kernel**, so its resident is a code declaration. Were an app's resident member-editable substrate, a workspace could re-point Docs' colleague — the ADR-460 D3.a cliff arriving through a config file. **Same convention, different tree; that difference IS the cliff.**

**The cliff holds on this layer.** An app row carries `slug · resident · name` — identity only. There is no field for authority or reach, and the gate asserts the row shape, so the absence is structural rather than documentary (the D3.a pattern's fourth instance). **An app pins a colleague; it can never widen one.**

## 3. D2 — Registration is the door, and the package is the registration

`register_app` sits beside `register_layouts` in `services/authoring.py`. The kernel imports no app; apps reach the kernel. First registration wins, matching `register_layouts` — a second claim on a live slug is a programming error, caught by the gate rather than by a boot crash.

**The import-order hazard, closed deliberately.** Before this ADR the registrations ran only as a side-effect of importing `routes/studio.py` — adequate while the registry was read by that same router. It stops being adequate the moment `create_lane` resolves `app → resident`: a process importing `routes/lanes.py` without `routes/studio.py` would refuse a **valid** app with "Unknown app", and the failure would depend on router import ORDER rather than on anything real. So **the package itself is the registration point** (`services/apps/__init__.py` imports every app eagerly), and any caller resolving an app imports it. A new app adds one line there.

## 4. D3 — The app asks; the server answers who

`create_lane` takes `app`, never `agent`:

```
POST /api/lanes { app: "docs", artifact_path: "…" }
  → resident_for_app("docs") → "designer" → its engine
```

**The client can no longer assert identity, and a stale one is REFUSED.** `CreateLaneRequest` is `extra="forbid"`: during a deploy window a cached bundle sending `agent` would otherwise have it silently **dropped** by Pydantic, creating a bound lane with **no** resident — the panel falling back to the engine label, i.e. this ADR's own defect reintroduced by a rollout gap. A dropped field reads as supported and becomes a bug report (the ADR-460 strict-key precedent). It fails loudly instead.

**An unregistered app is a 422, never a default.** ADR-548's lesson: a fallback degrading to a *plausible* value is worse than one that fails.

### D4 — A recipe declares its own colleague

The two "Learn from" call sites passed `agent: 'scout'` as a literal — the same client-asserted identity, one rung down. A canvas-less derive lane has no app to speak for it, so **the recipe declares its resident** (`DERIVE_RECIPES[…]["resident"]`). `deck` and `prd` declare none on purpose: they produce a canvas, so the **app's** resident answers. App wins when both apply — the lane_runner's character-then-job order, resolved one layer up.

## 5. D5 — The name reaches the member

`StudioSurface` keeps the served roster, joins `slug → name`, and hands the panel a `speakerLabel`. `LanePanel` renders the **speaker** for "…is working", and keeps the **engine** where the fact is genuinely the engine's:

| Line | Reads | Why |
|---|---|---|
| "*X* is working…" | **speaker** | who is doing it |
| "*X* cannot see images" | **engine** | vision is the MODEL's limit, not the colleague's |
| "you via *X*" | **engine** | the ledger receipt (ADR-460 D2 — the face is an Agent, the fact is your hands) |

A name must never be shown where a receipt is meant. `speakerLabel` defaults to `modelLabel`, so a mount with no colleague renders byte-identically to pre-562 — which is why **chat is untouched**: a chat lane genuinely IS its engine until someone joins (ADR-558), and that default is honest, not a gap.

## 6. What this ADR does NOT do

- **It does not move Studio's tables.** `STUDIO_BLOCKS` is filtered for **every** app by `blocks_for_app()`, `MEDIA_BLOCK_KINDS` derives from it, kernel code reads `STUDIO_LAYOUTS` directly, and the tables are wrapped in ADR-447/544 grammar canon describing what the **shared** machinery implements. `services/authoring.py` is the authoring **kernel**, misnamed for the app that arrived first. Extracting them would fork that canon or invert the dependency. **Studio declares through the same door; the door, never the file path, is what makes app config uniform.**
- **It does not add per-app agent names yet.** `register_app` accepts `name` (so Docs could present "Writer" over the same resident) and nothing passes it. The demand-gated decision ADR-467 D3 deferred stays deferred — but it is now a **one-line edit in one file** instead of a new mechanism.
- **It does not build app-level `AGENTS.md` / `skills/` — and that is now a STANDING REFUSAL, not a deferral** (2026-08-13, operator-ratified; recorded at [AUTHORING.md §Standing refusals](../design/AUTHORING.md)). The discourse that followed this ADR measured the ground and found the premise false: the instructions **already exist**, generated, always-on (a bound lane's job overlay is ~13K and already teaches the source-first citation route verbatim), there is **no retrieval seam** (`ReadFile` cannot reach kernel files, so a tier needs a new primitive — new reach on the surface ADR-467 D4 made uniform), and the entire candidate body was **one paragraph**. A second home for shipping instructions is the drift this ADR just deleted. The reopening condition, the generated-vs-authored split, and the correct shape *if* it is ever warranted (one domain skill with `references/`, never one per block kind) are all recorded at that section.
- **It does not fix the /agents "Start a chat" door.** Found by this ADR's build, **broken since ADR-558** (`af5339f`): it created an unbound lane naming a colleague, which ADR-558 D3 refuses with a 422. Every click has failed since. Not repaired here (operator's call) because the fix must choose between resolving the engine server-side from the colleague and having the client name one — and the client is deliberately not served `model` (ADR-460 D4) while ADR-467 D2 forbids inventing a default. **That is an ADR-558/467 decision, not a drive-by repair.** The door now states the working route (open Chat, pick an engine, add the colleague to the cast) instead of throwing a 422 at a member who did nothing wrong.
- **No schema, no migration, no new env var.**

## 7. The gate

`api/test_adr562_app_owned_config.py` — one declaration per app · the row shape (the cliff) · first-registration-wins · the kernel imports no app · eager registration (no router dependency) · every declared resident resolves · create derives and refuses a stale assertion · the name reaches the member · no dual approach.

Falsified ×4: dropping the roster join, collapsing speaker→engine, removing an app's eager import, and adding a `tools` key to a row each turn it **red**.

Repaired alongside (gates that pinned a retired spelling, all pre-existing): `test_agent_registry` 166/170 → **173/173**, `test_adr518_docs_app` → 33/33, `test_adr558_chat_is_engines` 25 → 26/26. One of them had been **green over a dead call** — the /agents door — which is the standing lesson: *a gate pinning a call's spelling cannot see that the call fails.*

---

**An app's AI configuration belongs where the app lives — declared in its own module through the door its layouts already use, resolved server-side so the client can neither assert an identity nor drift from it, with the colleague's name reaching the member who was reading an engine's; the cliff holds because an app row has no field for authority, and Studio's tables stay put because that file is the kernel, misnamed.**
