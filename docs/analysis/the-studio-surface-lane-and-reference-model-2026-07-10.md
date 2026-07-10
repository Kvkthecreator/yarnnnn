# The Studio — surface, lane, and the reference model

*How the authoring app is surfaced (a kernel surface on the launcher), how it thinks (a bound lane, not an agent), and what makes it categorically not-Claude-Design (objects are cited from the commons, never uploaded into a silo — and the citation rules flex per template).*

> **Status**: Analysis (2026-07-10). Doc-first, receipts-backed. Part 2 of the authoring-app probe — follows `the-authoring-app-claude-design-benchmark-2026-07-10.md` (part 1: the benchmark + the 80%-exists finding). Feeds the Studio ADR.
> **Authors**: KVK, Claude
> **Hat**: A. Vocabulary: surface, mount, lane, posture, binding, projection, pin, powerbox, altitude (A1/A2/A3 per ADR-408).
> **Operator directions this doc absorbs** (2026-07-10): (1) swap the `dashboard` template for a publishing shape — "blogs, articles" (final noun delegated: **Article**); (2) Studio reachable via the launcher, opening onto the dock like an OS app; (3) settle whether the left-side chat is "a dedicated LLM lane or agent" and how that is housed from the app program/runtime point of view; (4) expand the interaction/UX design, and the per-layout-mode reference rules that the filesystem-native substrate makes fundamentally different from Claude Design.

---

## 1. Surfacing — the Studio is a kernel surface; window = surface holds

**Decision proposed.** The Studio enters `kernel_surfaces.py` as a surface row — `slug: studio`, route `/studio`, its own icon, `launcher_tier: primary` — and thereby inherits the entire shell for free: launcher presence, dock keep/open/foreground, the one window manager (`useSurfacePreferences`), window-namespaced params. This is precisely how every OS-grade surface already works (receipts: the registry's `launcher_tier` rows at `kernel_surfaces.py:242,510`; ADR-340 P3 launcher tiers; ADR-412 D3).

Three disciplines this preserves, stated so nobody re-litigates them later:

1. **Window = surface** (ADR-436 invariant). The Studio *surface* is the window; there is still no per-file window. Which artifact is open is a **window-namespaced param** (`studio.file=operation/decks/ir-v2.html`), the ADR-358 D6 pattern. Two Studio windows on two artifacts = the same surface twice with different params — exactly how Files handles its detail selection.
2. **The mount contract** (ADR-436 D3). Inside the surface, the canvas is a *mount* of the Web Viewer renderer — the Studio adds a mount row to the catalog (frame: the canvas pane + pages rail) with zero app changes. The renderer stays frame-agnostic.
3. **DP29's composition class — used correctly this time.** After ADR-435 deleted Home, the registry is all mirrors. The Studio is the first new *composition* surface, and it must be justified the way ADR-340 demands: one surface ↔ one operator **act**. Home died because its act was fake (aggregation posing as action). The Studio's act is real and singular: **author an artifact**. That is the test any future Studio feature must also pass.

**Dock behavior**: standard. Kept in the dock like any surface; `foregrounded` when open; nothing new to build. The launcher's "New in Studio" affordance (template picker: Document / Deck / Article) and Open-With from Files ("Open in Studio" — the second app on `html`, lighting ADR-436 D2's ordered-list picker) are the two entry paths, matching the two launch shapes named in part 1 §6.

## 2. The interaction pair — lane left, canvas right, pointing in between

The layout Claude Design validated, run on yarnnn organs:

```
┌────────────────────────────── Studio (surface window) ─────────────────────────────┐
│ ┌── lane (left) ───────────┐  ┌── canvas (right) ─────────────────────┐ ┌─ pages ─┐ │
│ │ member ↔ model thread    │  │ Web Viewer mount over the artifact    │ │ rail    │ │
│ │ (full ADR-411 machinery: │  │ (sandboxed iframe, live re-render     │ │ (deck/  │ │
│ │  model-pinned, 5 file    │  │  on head revision)                    │ │ article │ │
│ │  verbs, attributed,      │  │                                       │ │ sections│ │
│ │  metered, BYOK)          │  │  events: navigate + POINT (§2.2)      │ │ )       │ │
│ └──────────────────────────┘  └───────────────────────────────────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Mutation stays single-path

The canvas **never edits**. Every mutation flows through the lane, which writes via `EditFile`/`WriteFile` under the member's grant — attributed, gated, revisioned, on the timeline, for free (`lane_runner.py:14-20`). The benchmark's core lesson (part 1 §1) is that this is a *complete* modality, not a compromise: Claude Design's own primary loop is describe → LLM rewrites → canvas re-renders.

One consequence worth naming because it is a structural *advantage*, not a limitation: the lane can **patch** (`EditFile` exact-replace) instead of rewriting the whole artifact each turn. Claude Design regenerates; yarnnn patches. That means finer-grained revisions (a slide-4 edit is a slide-4 diff in `trace`, not a whole-file churn), lower token cost per turn, and no whole-artifact context ceiling. The studio posture (§3) should *teach* patch-preference explicitly.

### 2.2 Canvas events — navigation and pointing, never mutation

"Actual event handling" on the right side, scoped to what preserves the discipline:

- **Navigate**: page/section selection (the rail), zoom, present-mode preview. Pure view state.
- **Point**: click a section/element in the canvas → the selection becomes *context for the lane's next turn* ("the member is pointing at `#slide-4 .headline`"). This is the cheap 80% of Claude Design's Annotate/Tweaks value at zero discipline cost — pointing is not editing; it is deixis. Mechanically: the canvas posts the selection anchor to the Studio's state; the next lane turn carries it in the turn envelope, the way lanes already carry conventions at turn time (derived, never stored).
- **Not in v1**: drag-resize, inline text editing, style scrubbing — each is a direct-manipulation mutation and belongs behind the drift test (part 1 §7). If demand proves out, they arrive as *lane-mediated* operations (the gesture composes an EditFile the lane executes), not as a second write path — but that is a future ADR's fight.

### 2.3 Live re-render

The canvas subscribes to the artifact's head revision and re-renders on write (the lane's `EditFile` lands → the iframe refreshes). Today's `useFileLoad` loads once; the Studio needs a reactive variant (poll-on-turn-completion is sufficient for v1 — the only writer in the loop is the lane whose turn the surface itself just streamed, so the surface *knows* when to refetch; true realtime subscription is an optimization, not a requirement).

## 3. The dedicated LLM — a **bound lane**, not an agent

The operator's question ("do we need a dedicated LLM lane or agent built out for this?") has a precise answer from the altitude taxonomy (ADR-408):

| Altitude | Candidate | Verdict |
|---|---|---|
| A1 — Freddie | the steward, one per workspace, rail-only (ADR-412) | ❌ wrong seat — stewardship, not authoring labor |
| **A2 — lane helper** | **the member's hands, `member:{id} via {model}`** | ✅ **exactly this** — acts only when addressed, under the member's grant, meter, and witness |
| A3 — persona agent | standing intent, mandate, wake, Rung-2 clock | ❌ the Studio LLM has no standing intent; it never wakes; it holds no seat |

**The Studio's LLM is an ADR-411 lane with two additions — a *binding* and a *posture*:**

1. **Binding**: the lane is bound to one artifact path. Stored where lane identity already lives (`chat_sessions.context_metadata.lane`, alongside `name` + `model` — `lanes.py:52-57`). The binding is what makes it a *studio* lane rather than a general helper: its file-verb activity centers on the bound artifact, and the surface opens lane + artifact as one unit.
2. **Posture**: a studio overlay composed into the conventions projection *at turn time* (the ADR-411 D6 mechanism — derived, never stored). It carries: the bound artifact's path and current outline, the active template's grammar (what a Deck section is, what an Article's front-matter needs), the **reference syntax** (§4), patch-preference (§2.1), and the design system pointer (`BRAND.md`/`brand_css`). This is the same pattern as the existing prompt-profile registry (ADR-186/233) — a new posture key, not a new machine.

Everything else the question worried about **already exists and is inherited unchanged**: model-pinning from `LANE_MODELS` (the member picks Sonnet/GPT-5/Gemini per lane — the Claude Design model picker, already built, `lane_runner.py:52-66`), the five file verbs as a *sufficient* tool surface (edit the artifact + search the commons for assets — no new primitives), attribution, the one meter (`execution_events`, slug `lane`), BYOK (ADR-439), the powerbox on every path it touches. One parameter needs attention: `_LANE_MAX_TOKENS = 2048` is sized for chat turns, not authoring turns — the studio posture either raises the cap for bound lanes or (better) leans on patch-editing so turns stay small.

**How this is housed from the app "program/runtime" point of view** — the residue for the app format:

> An LLM-backed app's runtime declaration = **(renderer, mount)** for its face + **(lane binding-kind, posture, tool scope, token profile)** for its mind. Both halves are code-seeded for the probe (the `APPS` table pattern); both become manifest fields the engineer-agent fills when the format ratifies. A *mechanical* app declares only the first half. Runtime-spectrum-as-composition, confirmed: no `is_llm_backed` flag, just the presence or absence of a lane declaration.

No new principal class, no new runtime, no new meter — which keeps the app-principal questions (an app acting as *itself*, with its own grant and bill) exactly where the app-seam parked them: with third-party App(principal), demand-gated.

## 4. The reference model — the categorical difference from Claude Design

This is the operator's core bet, made mechanical. Claude Design *imports*: an image is uploaded into the project and baked into the artifact. yarnnn *cites*: the artifact holds a *workspace reference*, resolved to bytes at render time (projection, ADR-333). Three consequences, then the rules.

**The import flow inverts.** "Upload an image" in the Studio means: the asset settles into the commons first (an attributed file — Downloads/attachments zone, `revision_kind` per ADR-423), *then* the artifact cites it. Import = settle-then-cite, never copy-into-silo. This is DP32's ledger discipline (`retain + attribute + cite`) applied to authoring — one more place the same axiom lands, not a new rule.

**Objects, not just images.** Because references resolve through the same file layer, the citable set is anything the commons holds: an image, a CSV → rendered as a live table (compose already has `data-table`/`metric-cards` section kinds — `engine.py:38-40`), a metric from ground-truth, an excerpt from a memo. The Studio's insert affordance is a **picker over the commons** (SearchFiles/recall), not an upload dialog with an upload fallback.

**The OpenDoc guard.** A cited object **renders read-only inside the artifact** — projection, never an embedded editor. Editing the *source* happens in its own surface or lane; the artifact re-renders because the reference resolves fresh. Reference-render, never embedded-edit: this single rule is what keeps the Studio out of the compound-document graveyard the app-seam frame refuses (OpenDoc/OLE), while delivering the thing those systems promised — documents made of living parts.

**The binding axis, per template.** The operator is right that the rules change per layout mode. The axis is *when a reference resolves*:

| Template | Compose mode | Reference binding | Why |
|---|---|---|---|
| **Document** | `document` | **head-tracking** — always resolves to the source's current head | an internal working doc should never be stale |
| **Deck** | `presentation` | **head-tracking** | same; swap the wordmark once, every deck is current (the bet's canonical example) |
| **Article** | `article` *(new mode; `dashboard` stays in the engine for reports but is not a Studio template)* | **head-tracking while drafting → PIN at publish** — publishing snapshots every reference to its revision id | a published artifact must be stable to its readers; the author re-publishes to advance the pins |

Both sides of the axis are auditable for free: head-tracking artifacts show *why they changed* (the cited source's revision), pinned artifacts show *what they cited* (the pin) — `trace` under every slide and every paragraph. Claude Design can retrofit neither, because there is no attributed substrate beneath it to cite into; this table is the honest core of "fundamentally different."

**In-shell vs served resolution** (unchanged from part 1 §4): inside the shell, references resolve through the existing signed-blob path; served-to-strangers resolution gates on the minted capability (ADR-427 Ph2/3) — which is *also* what pin-at-publish naturally waits for. Publish remains deferrable and severable.

## 5. Feature scope — v1, sharpened

**v1 (the probe):**
1. `studio` kernel surface row — launcher, dock, one WM, `studio.file` param (§1).
2. The pair: bound lane (left) + Web Viewer canvas mount (right) + pages rail; refetch-on-turn re-render (§2).
3. Lane binding + studio posture in the conventions projection; patch-preference; `LANE_MODELS` picker inherited (§3).
4. Templates: **Document · Deck · Article** — the compose engine's `document`/`presentation` modes + a new `article` mode (bump `COMPOSE_ENGINE_VERSION`).
5. The reference model, head-tracking half: settle-then-cite for images; the commons picker; read-only object projection for at least images + tables (§4).
6. Registry row: Studio as the second app on `html` → the Open-With picker lights (ADR-436 D2, zero kernel change).

**Explicitly deferred, each already named:** publish + pin-at-publish (waits on minted capability); pointing (§2.2 — v1.1, the first UX iteration after real use); direct-manipulation anything (drift test); desktop-tile mount (ADR-438 D2, waits on a desktop file-trigger); the app manifest as substrate (the engineer-agent's format, ratifies from this probe's residue).

## 6. Open to the operator

1. **"Studio" as the name** — soft-adopted in discourse; confirm or rename before the ADR.
2. **Launcher tier at ship**: `primary` from day one (the operator's stated instinct — launcher + dock like an OS app) vs `search-only` until the surface stabilizes, then promote. Recommendation: **primary** — the probe needs real traffic to produce residue, and the launcher is where the act lives.
3. **Article as the publishing noun** (delegated pick) — covers blog post / essay / announcement; "Post" was rejected as platform-flavored, "Page" as site-builder-flavored. Veto welcome.
4. **First template to polish**: Deck (the live IR-deck use case pulls it) or Article (closest to the publishing bet). v1 ships all three skeletons either way; this only orders the polish.

## 7. The one-line statement

**The Studio surfaces as one kernel surface on the launcher and dock (window = surface, the first honest DP29 composition since Home's deletion — its act is authoring); its mind is not an agent but a bound A2 lane — an ADR-411 lane plus an artifact binding and a turn-time posture, inheriting model-pinning, five sufficient file verbs, attribution, the one meter, BYOK, and the powerbox unchanged, which is also the app-format residue (an LLM-backed app = renderer + mount + lane declaration); and its categorical difference from Claude Design is the reference model — settle-then-cite over the commons, objects rendered read-only by projection (never embedded editors), head-tracking for documents and decks, pin-at-publish for articles — living references with trace beneath them, which a sealed-island tool structurally cannot copy.**
