# ADR-440 — The Studio: the first authoring app (the second app class)

> **Status**: **Accepted** (2026-07-10, operator-delegated full scope). The first instance of the **authoring-app class** — an app users *use* to make artifacts, distinct from ADR-436's viewer class (renderers). Ships as: a `studio` kernel surface (launcher + dock), a **bound lane** as its mind (ADR-411 machinery + an artifact binding + a turn-time posture), three templates (**Document · Deck · Article**) as kernel-constant HTML skeletons, and the **reference model** (cite-by-path + last-resolved pin) for substrate objects. Derivation lives in the three probe analyses: `the-authoring-app-claude-design-benchmark-2026-07-10.md` (part 1 — the benchmark; ~80% of the anatomy already exists as kernel organs), `the-studio-surface-lane-and-reference-model-2026-07-10.md` (part 2 — surface + lane + per-template reference rules), `the-studio-content-and-the-reference-mechanics-2026-07-10.md` (part 3 — program-not-substrate, no app namespace, pin mechanics).
>
> **Canon position**: this is the app-seam §2 **reference-app exception** ("Preview.app so the platform isn't empty day one"), invoked deliberately with the operator's eyes open ("even if it ends up the not-so-great Notion / Claude Design") — the bet is STRUCTURAL: living filesystem references, provenance under every slide, workspace memory. NOT a reversal of house-don't-build; the registry's shape still admits a stranger's row. The probe's residue is the app format the future S/W-engineer hire (ADR-382-shaped, deferred) builds into — **probe first, builder second**.

**Date**: 2026-07-10
**Dimension**: Channel (Axiom 6 — a new authoring surface) + Identity (Axiom 2 — the bound lane acts as the member's hands) + Substrate (Axiom 1 — artifacts + references are files and revisions)

**Extends / builds on**: ADR-436 (app registry + mount contract), ADR-411/408 (lanes; the A1/A2/A3 altitude taxonomy), ADR-414 D2 (constitution-as-kernel-constants precedent), ADR-434 (powerbox), ADR-209 (authored substrate — the pin's floor), ADR-333 (lazy projection), ADR-427 (binary Cat-1 + the minted serving cap — the named dependency of pins-on-binary and publish), ADR-340 DP29 (mirror once, compose few), ADR-396 (one meter), ADR-439 (BYOK, inherited via lanes).

**Preserves**: mutation-through-chat (ADR-236 — the canvas NEVER edits; the lane is the single write path); window = surface (no per-file window); no second window manager; the powerbox on every path; no hidden substrate (DP29 + ADR-328); the ADR-435 world (no Home resurrection — see D2).

---

## D1 — The second app class: authoring apps

ADR-436's seven apps are **renderers** (read-only, opened *on* files, frame-agnostic). The Studio is the first **authoring app**: it *makes and mutates* an artifact. The class distinction is not tokens or complexity (operator's three-layer correction, part 1 §0): **runtime** is a spectrum (mechanical ↔ LLM-backed) expressed as *composition*, not a flag —

> An app = **(renderer, mount)** for its face **+ optionally (lane binding-kind, posture, tool scope, token profile)** for its mind. A viewer app declares only the first half; an LLM-backed authoring app declares both. There is no `is_llm_backed` flag.

This composition rule is the app-format residue the engineer-agent inherits. **App construction** (building the Studio itself) is Hat-A engineering now, the hire's job later.

## D2 — Surfacing: one kernel surface, launcher-primary; the first honest DP29 composition since ADR-435

`studio` enters the surface registries (BE `kernel_surfaces.py` + FE `SurfaceRegistry`) as a first-class surface: route `/studio`, `launcher_tier: primary`, dockable, windowed by the one WM. The open artifact is the **window-namespaced param** `studio.file` (ADR-358 D6 pattern) — two Studio windows on two artifacts = same surface, different params.

DP29 justification, stated so it never re-litigates: after ADR-435 the registry is all mirrors; the Studio is a **composition** surface and passes the test Home failed — one surface ↔ one real operator **act**: *author an artifact*. Every future Studio feature must pass the same test (the drift guard, D7).

Layout: **lane pane (left) + canvas (right) + pages rail**. The canvas is a **mount** (ADR-436 D3) of the Web Viewer renderer — zero app changes, one new mount row. Canvas events are **navigate only** in v1 (pointing is v1.1 — deixis, not editing); re-render is refetch-on-turn-completion (the surface just streamed the lane's turn; it knows when to refetch).

## D3 — The mind: a **bound lane**, not an agent

Altitude test (ADR-408): not Freddie (A1 stewardship), not a persona agent (A3 — no standing intent, never wakes, holds no seat). The Studio's LLM is an **A2 lane** — the member's hands — plus exactly two additions:

1. **Binding**: an `artifact_path` in the lane's metadata (`chat_sessions.context_metadata.lane`, beside `name`/`model`). Optional on `POST /api/lanes`; a lane with a binding is a *studio lane*.
2. **Posture**: a studio overlay composed into the conventions projection **at turn time** (ADR-411 D6 mechanism — derived, never stored; ADR-414 D2 housing — kernel constants, program not substrate). Carries: the bound artifact's path + how to read it, the active template's grammar, the **reference syntax** (D5), **patch-preference** (`EditFile` over whole-artifact rewrites — finer `trace` granularity than Claude Design's regenerate, and it defuses the token ceiling), and the `BRAND.md` pointer.

Inherited unchanged, zero new machinery: model-pinning (`LANE_MODELS` — the model picker), the five file verbs as a *sufficient* tool surface, attribution `member:{id} via {model}`, the one meter (`execution_events` slug `lane`), BYOK (ADR-439), the powerbox. Bound lanes get an authoring **token profile** (a higher `max_tokens` than the chat-sized 2048) — a constant, not a schema change.

## D4 — Templates: Document · Deck · Article, as kernel-constant skeletons

Three templates, each a **kernel-constant HTML skeleton** written as the artifact's first revision at create time, self-described by `data-template` on the root element. **Article** is the publishing shape (operator-delegated noun — replaces the earlier `dashboard` slot, which stays a compose-engine mode for reports but is not a Studio template). Templates are *starting grammar*, not engines: the lane authors the HTML directly from the skeleton; the compose engine is not on the Studio's write path.

## D5 — The reference model: cite-by-path + last-resolved pin

The categorical difference from the benchmark (Claude Design imports into a silo; yarnnn cites the commons):

- **Settle-then-cite** (DP32 applied to authoring): an "upload" lands in the commons as an attributed file first — into `assets/` beside the artifact — then the artifact cites it. Citing an *existing* workspace object never copies it.
- **Citation shape**: `data-ref` (the living path) + `data-ref-rev` (the last-resolved pin), on the element that holds the object. Resolution is a **projection pass** at render: path resolves → serve head; path dangles → serve the pinned revision + flag broken-but-rendering. **Pins refresh on authoring turns, never on render** — reads never write (read-purity; read-only grants render too), so the posture instructs the lane to stamp/refresh `data-ref-rev` whenever it writes a citation; moved → **tombstone-heal** (MoveFile's tombstone records the destination — `workspace.py:1188-1205`); deleted → the lane surfaces the choice. Duplication is rejected: blobs are content-addressed (`authored_substrate.py:236`), so a copy stores zero bytes and forfeits the living-reference thesis.
- **Relative vs absolute**: the project's own `assets/` are cited artifact-relative (`./assets/…`) so a project folder moves intact; commons objects are workspace-absolute and head-track.
- **The OpenDoc guard**: a cited object **renders read-only by projection — never an embedded editor**. Editing the source happens in its own surface/lane.
- **Per-template binding axis**: Document/Deck **head-track**; Article head-tracks while drafting and **pins every reference at publish** (stable public artifact; re-publish advances pins). Publish itself is deferred with the minted capability (ADR-427 Ph2/3); **pins are GC roots** is a rider that lands with it.
- **Binary honesty**: images are Cat-1 (ADR-427 Ph1) — living path-refs + signed-URL serving now; the pin hardens for binary when Phase 2 puts it in the revision chain. v1's pin is fully real for text-native objects (md/svg/csv).

## D6 — App content: program, not substrate; no app namespace

- The Studio's envelope (posture, template grammars, reference syntax) is **code** — kernel constants projected at turn time. **No hidden files, ever** (DP29 mirror + ADR-328 portability); the fallback for persistent machine state is a *visible* write-locked `_studio.yaml` (ADR-254), not used in v1.
- **The app owns no namespace**: projects are meaning-placed folders (`operation/fundraise/ir-deck/`, never `studio/…`) — one artifact file + a local `assets/` sibling. The Studio's new-artifact flow takes a landing path; it never invents an app-named root.
- An app ships **no substrate** — or we recreate what ADR-414 D4 killed, one app at a time.

## D7 — Scope: v1 ships / deferred, and the drift guard

**v1 (this ADR's implementation):** the `studio` surface (D2) · bound lanes + posture + token profile (D3) · three template skeletons (D4) · the reference model's head-tracking half with pin-recording + in-shell resolution for images (signed URL) and text objects (D5) · Open-in-Studio affordances (launcher template picker + open-existing `.html`).

**v1.1 SHIPPED** (2026-07-10, same-day): **pointing** — the projection pass strips every artifact-authored executable (scripts, iframes, inline handlers, `javascript:` URLs — D5's no-script rule enforced mechanically) and injects the kernel's pointer runtime; the canvas moves to `sandbox="allow-scripts"` (opaque origin, no same-origin/credentials/top-nav; blank-on-projection-failure, never raw); a click selects the nearest pointable element and seeds the lane's composer (`Pointing at the h2 "…" — `) via `postMessage` → `composerSeed` (an additive LanePanel prop, slated to become a mount-contract slot). Deixis only — mutation stays single-path. Plus the **insert menu** — prompt-composer buttons (Image / Table / Chart) over `GET /studio/citable`: they prefill the ask, never write.

**Deferred, each already named**: publish + pin-at-publish + pins-as-GC-roots (ADR-427 Ph2/3) · tweak gestures (v1.2 — the gesture-composer; see the direct-manipulation clarification below) · any further direct manipulation (drift test) · desktop-tile mount (ADR-438 D2) · the app manifest as substrate + the engineer-agent hire (the format ratifies from this probe's residue) · Open-With picker listing (the Studio is a *surface*, not an `APPS` renderer row — it does not enter the ADR-436 table; "Edit in Studio" affordances are navigation, preserving the registry's renderer purity).

**Two scope clarifications** (2026-07-10, first-session discourse):
- **Asset creation splits on the text/binary line, not the "generation" word.** HTML-native visual assets — SVG charts, diagrams, icons — are *plain-text authoring* and therefore IN scope today: the lane writes `./assets/chart.svg` and cites it (the posture teaches this). RASTER image generation is a rented engine (ADR-417: generation is rented, not owned) — demand-gated, and when wired it lands as settle-then-cite (external call → attributed file in `assets/` → citation), never as a hosted engine.
- **Direct manipulation, when it comes, is a gesture-composer — never a second write path.** The benchmark itself proves the shape: Claude Design's Edit mode banner reads "this file does not support automatic edits… we will describe changes to Claude to apply on exit" — even there, gestures mutate a preview and are *described back to the model* to apply. The Studio's future tweak-mode composes `EditFile` patches from gestures (deterministic property changes may not even need the model), applied as attributed revisions. Keystroke-level realtime co-editing is a permanent non-goal: the revision is the atom, and there is no merge/CRDT layer, ever (ADR-406/286).

**The drift guard** (part 1 §7, standing): *does this feature force a definitional question about the app format, or is it just a better editor?* The second kind is refused — TextEdit, not Word.

## Consequences

- **Positive**: the second app class exists with a live instance; the app-format residue (D1's composition rule, D5's reference mechanics, D6's no-substrate/no-namespace rules) is earned from running code; the structural moat (living references + trace under artifacts) becomes demonstrable; lanes/powerbox/meter prove they generalize to app runtimes with zero new machinery.
- **Cost**: one new surface + one posture + skeleton constants + an FE projection pass; a `MODEL_ROUTER_ENABLED`-off environment shows the Studio with a disabled lane pane (lanes are the mind — the flag gates them).
- **Risk**: low-moderate — no schema change, no new principal, no new meter; the canvas renders sandboxed HTML through the existing Web Viewer path.

## The one-line statement

**The Studio is the first authoring app: one kernel surface on the launcher whose act is authoring (the first honest composition since Home's deletion), whose mind is a bound A2 lane — an artifact binding plus a turn-time posture over unchanged lane machinery — whose templates are three kernel-constant skeletons (Document, Deck, Article), and whose artifacts cite the commons by living path with a self-healing pin (settle-then-cite, render-only projection, tombstone-heal, pin-at-publish deferred with the minted capability); it ships no substrate, owns no namespace, and its residue — renderer+mount for the face, lane+posture for the mind — is the app format the engineer hire will one day build into.**
