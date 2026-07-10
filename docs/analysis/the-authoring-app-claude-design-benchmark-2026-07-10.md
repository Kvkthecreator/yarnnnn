# The Authoring App — the Claude Design benchmark and the second app class

*The seven apps render; the eighth authors. Claude Design proves the modality (chat-driven mutation over one HTML artifact) — yarnnn inherits the modality for free and adds the one thing Claude Design structurally cannot: an artifact that REFERENCES a living, attributed filesystem instead of sealing its assets inside itself.*

> **Status**: Analysis (2026-07-10). Doc-first, receipts-backed. Follows the app-seam triptych (`the-app-layer-and-the-desktop-2026-07-09.md` → `the-commons-is-the-os-2026-07-09.md` → `the-app-seam-first-party-viewer-vs-third-party-principal-2026-07-10.md`) and ADR-436 (the app registry, shipped `d732bc4`).
> **Authors**: KVK, Claude
> **Hat**: A (system canon). Vocabulary: operator, member, principal, substrate, grant, powerbox, app, mount, lane, projection, minted capability.
> **Operator decision this doc records** (2026-07-10): build an **explicit first-party authoring app** — accepted with eyes open that it may be "the not-so-great Notion / not-so-great Claude Design" feature-wise, because the structural advantages (live filesystem references, image-swap-updates-everywhere, attributed provenance, workspace memory) are the bet. Benchmark: **Claude Design**, chosen for its shared HTML-native principles.
> **Canon position**: this is the app-seam §2 **reference-app exception** ("Preview.app so the platform isn't empty day one"), invoked deliberately — NOT a reversal of the house-don't-build thesis. The drift guard is §7.

---

## 0. Where the discourse stands

The app arc settled, in order: apps are frame-agnostic renderers behind a code-seeded registry (ADR-436, shipped); the powerbox is the commons's `access(2)` (ADR-434, shipped); a third-party App(principal) stays demand-gated behind three named primitives (app-seam §1). The open definitional question was: *what is an app users USE — an app that authors, not just renders — as a substrate object?*

The operator resolved the build-the-builder vs. see-if-the-build-works fence as a **sequence**: hand-author one real app first; its residue becomes the app-format canon; the S/W-engineer agent (an Altitude-3 hire, ADR-414 D5 / ADR-382) is the follow-on that builds *into* the ratified format. This document is the first step of that sequence: the benchmark that scopes the probe.

**The three-layer distinction the probe must respect** (operator's correction, load-bearing):

- **App RUNTIME** — what the app does when used. A spectrum: mechanical ↔ LLM-backed. Both are apps.
- **App CONSTRUCTION** — building the app. Never mechanical; always judgment + skills (software engineering), regardless of the app's shape.
- **The CONSTRUCTOR** — the agent doing the construction. For this first instance: us (Hat A). For every subsequent instance: the engineer hire.

---

## 1. The benchmark — Claude Design's anatomy, observed

From the product's own surface (operator screenshots, 2026-07-10 — the yarnnn IR deck being authored in it):

| Organ | What Claude Design does |
|---|---|
| **The artifact** | One self-contained **`.html` file** (`Edited IR Deck v2 - yarnnn.html`); multi-page *inside* the one file ("2 pages"). Slides, documents, prototypes, wireframes are **templates over the same HTML object**, not different object types. |
| **Mutation** | **Chat-driven.** The left pane is an agent narrating its edit ("Rebuilt slide 4's body from scratch… Done — slide 4 now tells the multi-platform gap story"). The user describes; the LLM rewrites the artifact; the canvas re-renders. |
| **The canvas** | Renders the artifact live; thumbnails rail for pages. Direct manipulation (Annotate / Tweaks / Edit) exists but is **secondary** — layered on top of chat mutation, not the primary modality. |
| **Context objects** | A **Design System** ("YARNNN Design System") attached per-prompt — a reusable style substrate. Templates (Prototype / Slides / Document / Wireframe / Animation). Projects list. |
| **Engine choice** | Model picker per generation (Opus 4.8 · Medium). |
| **Distribution** | Share / Present from the same object. |
| **Memory** | **None beyond the project.** The artifact is sealed inside its project: images are uploaded/baked in, context re-attached per session, no provenance below "version history." |

**The finding that matters most:** Claude Design is *already* a chat-mutation editor. The operator authored an entire IR deck without direct manipulation being the primary tool. This is empirical proof that **chat-driven mutation is a complete authoring modality** — which is yarnnn's own kernel law (ADR-236: mutation through chat; apps render, never edit; re-ratified by ADR-436 D3's mount contract, "NEVER edits"). The benchmark does not pressure yarnnn's discipline; it **validates** it.

**The irony that names the bet:** the deck being authored *in* Claude Design argues that each AI giant is a sealed island and "the gap between the islands is the product" — while Claude Design's own artifact is a sealed island. Swap the yarnnn wordmark image tomorrow and every deck that baked it is stale. The authoring app's entire structural thesis is the negation of that: **the artifact is a projection over living substrate references.**

---

## 2. The anatomy mapped — what already exists in yarnnn

Pressed against live code (post-`d732bc4` + ADR-437/438/439 lanes):

| Claude Design organ | yarnnn organ | Status |
|---|---|---|
| The `.html` artifact | A `workspace_files` `.html` file — attributed, revisioned (ADR-209), lazily projected (ADR-333) | ✅ exists |
| Chat-driven mutation | **Chat lanes** (ADR-411): five file verbs under the member's grant, writes attributed `member:{id} via {model}` (ADR-408 A2 — "the member's hands") | ✅ exists, and it is kernel law, not a feature |
| The canvas | **Web Viewer** app — `html` kind, sandboxed iframe (ADR-436 D1) | ✅ exists (live re-render on revision: gap, §4) |
| Templates (slides/doc/dashboard) | **Compose engine layout modes** — `document \| presentation \| dashboard`, `surface_type: report \| deck \| digest \| workbook` (`api/services/compose/engine.py:5,48`) | ✅ exists, in-API, pure-Python (ADR-417) |
| Design System | `brand_css` injection in compose (`engine.py:50`) + `BRAND.md` as substrate (kernel-seeded, `workspace_paths.SHARED_CONTEXT_FILES`) | ✅ exists in primitive form — and it is *shared with every output the OS makes*, not tool-local |
| Model picker | Engine catalog + LiteLLM router (ADR-413, flag-gated) | 🟡 seam exists |
| Share | The shared-artifact wedge (migration 214: link → member grant, artifact as landing page) | 🟡 in flight (concurrent lane, uncommitted) — *share-inward*, not publish-outward |
| Present / publish to strangers | The **minted serving capability** (ADR-427 D4 / app-seam §3) | 🔴 named, not built |
| Project memory | The workspace itself — memory, context domains, `recall` | ✅ exists, **and is categorically deeper** |
| Provenance | `write_revision` + `trace` (primitive #5, the moat) | ✅ exists; Claude Design has no equivalent |

**Read the table honestly: roughly eighty percent of Claude Design's architecture is already standing in yarnnn, as kernel organs rather than app features.** The authoring app is predominantly *composition* of existing organs, not construction of new ones. If the build starts demanding new organs, the scope is wrong (§7).

---

## 3. The structural delta — why second-class features still win

The operator's acceptance ("even if it ends up being the not-so-great Notion") buys four structural properties no feature-parity race could:

1. **References, not copies.** Claude Design bakes assets into the artifact/project. The yarnnn artifact *references* substrate files — swap `brand/wordmark.png` once and every deck, page, and report that references it is current at next render. This is DP32's cite-don't-rewrite discipline applied to visual assets, and it is mechanically impossible for a sealed-island tool to retrofit.
2. **The design system is the workspace's, not the tool's.** `BRAND.md`/`brand_css` styles *everything the OS emits* — this app, report delivery, composed emails. One authored style substrate, N consumers. Claude Design's design system styles Claude Design.
3. **Provenance under the artifact.** Every mutation is an attributed revision; `trace` works on a deck the same as on a memo. "Who changed slide 4, when, from what" is a query, not a guess. No competitor in the benchmark class has this — it is the moat (ESSENCE v15) made visible in an authoring surface.
4. **The author has memory.** The lane drafting the artifact reasons from the workspace — the operation's mandate, accumulated context, prior outputs — not from a per-session context attach. The CS-agent that "knows the company" is the same mechanism as the deck that already knows the product's positioning.

The corresponding honest concessions (accepted): no direct-manipulation editing at first (no Tweaks/Annotate equivalent), no per-element operations, generation quality bounded by the same models everyone rents. **TextEdit, not Word** — deliberately modest, existing to prove the document ABI.

---

## 4. The honest gap list — what must actually be built

In dependency order:

1. **The Studio mount** *(working name; operator to name)* — one surface pairing a **chat lane** (the mutation engine, exists) with a **live canvas** (the Web Viewer, exists) over **one HTML artifact** (exists). This is a *mount-catalog addition* under ADR-436 D3 — the mount contract already permits new mounts with zero app changes. The mount still never edits: **the lane edits, the canvas renders.** Claude Design's own layout (chat left, canvas right, pages rail) is the validated reference layout.
2. **Live re-render** — the canvas subscribes to the artifact's revisions and re-renders on write. Today's viewers load once (`useFileLoad`); the studio needs the file's head to be reactive. Small, FE-bounded.
3. **The asset-reference model** — the one genuinely new definitional piece. How does an HTML artifact embed a substrate image? Compose today takes `assets: [{ref, url}]` (`engine.py:49`) with URLs from the legacy `content_url` sidecar. The probe must define **workspace-relative references resolved at render time** (projection, per ADR-333): in-shell, resolvable via the existing signed-blob path (`useSignedBlobUrl`, the single FE consumer per ADR-436 §10); served-to-strangers, gated on the minted capability (ADR-427 Ph2/3). *This is the "swap out images" advantage — it is also the piece whose residue matters most for the app format.*
4. **Templates as layout modes** — wire the compose engine's `document | presentation | dashboard` modes as the studio's new-artifact templates. Slides are NOT a new engine; the deck/page/document distinction is a template choice over one object. (This dissolves the earlier scope debate: the operator's slides/publishing/documents short-list is one app with three templates.)
5. **The registry row** — the studio registers as the **second app claiming the `html` kind** (and plausibly `markdown`). ADR-436 D2 built exactly this seam: "the Open-With picker renders only when `resolveApps(file).length > 1` — the first two-app type lights the picker with **no kernel change**." The probe app is thus also the **first live exercise of the ordered-list resolver** — the registry proves itself on our own second app before any stranger's.
6. **Publish** *(deferrable)* — serving the artifact to a non-principal. The neighboring cell of the shares wedge: the wedge serves an artifact to a stranger *by minting them a member grant*; publish serves it *without minting anything*. Gated on the minted capability; explicitly severable from v1.

**What v1 does NOT require, and why that is remarkable:** no new attribution class (lane writes are `member:{id} via {model}`, ADR-411 D4); no new metering (lane LLM calls are already the one meter, ADR-396); no new permission machinery (the powerbox already scopes who reads/writes the artifact's path, ADR-434); no new window manager (the studio is a mount; window = surface, ADR-436 invariant). The app-principal questions (an app *being* a principal, its own grant row, its own meter) stay exactly where the app-seam left them: deferred with App(principal).

---

## 5. Disciplines preserved — the probe breaks no law

- **Mutation through chat (ADR-236)** — not merely preserved but *embodied*: the studio's editor engine IS a chat lane. The benchmark's chief lesson is that this is sufficient.
- **Window = surface** — the studio is a mount with a frame, not a per-file window; no second WM.
- **The powerbox (ADR-434)** — the artifact is a path; who may author, who may view, who may (later) publish are grant questions already answerable.
- **House-don't-build** — invoked exception acknowledged (app-seam §2's reference app). The registry's shape still admits a stranger's row; the studio occupies a row like any other app would.
- **Arrange-not-edit for spatial surfaces** — untouched; the studio is not the desktop.

## 6. The residue — what this instance settles for the app format

The probe, built as scoped above, answers with receipts what was previously undefined:

| App-format question | How the probe answers it |
|---|---|
| Where does an app live? | A registry row (code-seeded, ADR-436) + a mount. The *substrate-installed* app (manifest in `agents/{slug}/` or `apps/`) remains the engineer-hire's question — the probe deliberately does not pre-decide it. |
| How is it launched? | Opened *on* an artifact (Open-With, second app on `html`) or launched *to create* one (template picker → new file). Two launch shapes, both mount-native. |
| Runtime spectrum declaration | The studio is LLM-backed via the lane; a mechanical app would be a renderer + external calls. Runtime is a property of composition, not a manifest flag — confirmed empirically. |
| Whose grant, whose meter? | The using member's, via the lane. App-as-principal deferred, now with evidence it isn't needed for first-party. |
| The asset-reference model | Defined by build (§4.3) — the piece with no prior art in-repo. |
| The publish boundary | Named precisely (§4.6): grant-minting share vs. no-grant serve. |

The engineer-agent hire (ADR-382-shaped, deferred) inherits this table as its build target format.

## 7. The drift guard

The standing test for every feature request against the studio, canonized from the discourse:

> **Does this force a definitional question about the app format, or is it just a better editor?**
> The first kind is the probe's job. The second kind belongs to a third party's app — building it ourselves is the feature-race the whole arc refuses (the scar: "the lane felt like a worse Claude.ai because it competed on chat").

Concretely out of scope until the format ratifies: direct-manipulation editing, per-element tweaks, annotation layers, real-time multiplayer cursors, animation timelines, a slides-specific engine, any asset *generation* (ADR-417: generation is rented, not owned).

## 8. Open to the operator

1. **Name the app** (working: "Studio" — deliberately generic; the templates carry the deck/page/document nouns).
2. **First template**: deck (matches the live IR-deck use case, presentation mode exists) or page (the md → HTML homepage cut, closest to publish)? The engine supports both; the pick orders §4, nothing else.
3. **Publish in v1 or deferred?** Recommendation: deferred — in-shell authoring + the existing share wedge cover the near demand; publish lands with ADR-427 Ph2/3.

## 9. The one-line statement

**Claude Design proves chat-driven mutation over one HTML artifact is a complete authoring modality — which is already yarnnn kernel law — so the first authoring app is composition, not construction: a studio mount pairing an existing chat lane with an existing web renderer over an existing attributed HTML file, templated by an existing compose engine, scoped by the shipped powerbox, attributed and metered by machinery that needs no extension; what it must newly define is exactly one thing, the asset-reference model (artifact → living substrate files), and that one thing is the structural bet no sealed-island competitor can copy — the artifact as a projection over the commons, with trace beneath every slide.**
