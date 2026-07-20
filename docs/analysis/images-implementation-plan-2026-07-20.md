# IMAGES — the full implementation plan

> **Status**: Implementation scoping (2026-07-20), commit-grade. The conceptual frame, operator-stated: *reverse-engineer the Canva/Fabric-class canvas onto yarnnn's filesystem — instead of one flat image from a chatbot prompt, the OS provides the harness: a decomposed, layered, attributed artifact you can select, resize, and regenerate object-by-object.* The scoping map is `images-scoping-2026-07-20.md`; this doc is the executable plan — phases → commits → files → gates → click passes, in the worksheet discipline (receipts before advancing).
> **Code receipts**: from a full read of the ADR-466 object layer (2026-07-20). Key fact that shrinks Phase 1: the web chrome's positionable/measurable gates key on the DOM frame (`projection.ts:2111-2113` — `closest('.slide')`), **not** on the deck template — so a canvas artboard that reuses the `.slide` stage class inherits the bounding box, drag, resize, and the kernel position rule (`.slide [data-block][data-x][data-y]`, `studio.py:998-1000`) with near-zero chrome changes.

---

## Phase 1 — The canvas mode (WS-A; unblocked; ships quietly inside Studio)

**Decision set (ratify as ADR at commit 1 — the compact canvas-mode ADR):**
- **D-a: the artboard IS a `.slide`.** The canvas scaffold's page element carries `class="slide"` (+ `data-template="canvas"` on the root). One stage concept, shared frame class — the kernel position/size selectors, `positionable()`, `measurableFrame()`, and the empty-slot affordances all activate without new selectors. (The alternative — a new frame class + parallel selectors — is a Singular-Implementation violation for zero gain.)
- **D-b: canvas is `mode: "paged"`; pages are ARTBOARDS.** The navigator strip, New-‹noun› gallery, and nav-collapse all derive from the served `mode` (`StudioSurface.tsx:535-537`) — canvas gets multi-artboard for free, named "artboard" via the layout's noun.
- **D-c: aspect is a root token.** `data-aspect` on the artifact root (`1:1 · 16:9 · 4:5 · 9:16`), consumed by the canvas skin (`aspect-ratio: var(--stage-aspect, 1/1)`), default square. Per-artifact, member-set in the Design tab; deck stays hardcoded 16:9 (its identity).
- **D-d: z earns its token.** New measure `z` (`data-z` marker + `--yz` value, integer band), kernel rule beside the position rule, `STUDIO_KERNEL_CSS_VERSION` → 11 (retrofit lights it up in existing decks too). `StudioBlockMenu`'s "Move up/down = document order, NOT z" comment (`StudioBlockMenu.tsx:41-44`) is the pre-written justification — Bring forward/backward become honest verbs on positioned blocks.
- **D-e: everything-positioned is a CONVENTION, not an enforcement.** The canvas posture instructs the lane to position every block (and the New-artboard scaffold starts positioned); a flow block on a canvas degrades gracefully exactly as the kernel's `var(…, auto)` fallback intends. No new validation machinery.

**Commits (each with its gate; stage by name — concurrent Studio lanes are live in this tree):**

1. **`docs(adr)`: the canvas-mode ADR** (D-a…D-e above + the §5b unveil rule from the scoping doc as an amendment note on ADR-468 §8).
2. **`feat(studio server)`: the canvas layout.** `api/services/studio.py`: `STUDIO_LAYOUTS["canvas"]` (`:184` family — `mode:"paged"`, skin with the aspect-token stage, scaffold = one `.slide` artboard + a positioned heading block, `flow` prose = the canvas grammar); x/y measures `applies` += `"block-canvas"` grain (`:871-888`, `MEASURE_GRAINS :894`) — note the kernel CSS needs **no** selector change (D-a); `STUDIO_ARRANGEMENTS["canvas"]` = `{free}` (one arrangement, no slots — the stage is the arrangement). Auto-derived, untouched: `build_skeleton`, `STUDIO_TEMPLATES`, `_SCAFFOLD_TITLES`, the `routes/studio.py` comprehensions. Gate: extend `test_adr466_mode_native.py` — the deck-only x/y falsifier (`:108-115`) revises to deck+canvas; add canvas-layout presence/mode/scaffold checks.
3. **`feat(studio server)`: the z measure** (D-d). `STUDIO_MEASURES["z"]`, kernel rule + version 11 + retrofit, served spec flows via the existing comprehension (`routes/studio.py:156-168`). Gate: measure-shape + kernel-rule checks in `test_adr461_geometry.py` family.
4. **`feat(studio web)`: the canvas surface fit.** `StudioCanvas.tsx:219` `isDeck` string-test generalizes to staged templates (`deck|canvas`) so the auto-fit stage applies; `projection.ts` `DECK_STAGE_CSS` (`:289-297`) parameterized by the aspect token; `artifactOps.ts` `setGeometry` axis list (`:502`) `['x','y','w']` → `+z`; `StudioBlockMenu` Bring forward/backward wired to the z token on positioned blocks; Design tab gains the aspect picker (D-c). FE verify: `tsc` + `next build` (worktree if the shared tree is dirty). Gate: source-guards in the ADR-466 gate file for the generalized stage test + z axis.
5. **`feat(studio posture)`: the canvas job posture.** The layout's `flow` prose (commit 2) carries the base; this commit tunes the composed posture the way the Designer pass proved effective: everything-positioned discipline, z usage, figure-leaf citation (`data-ref`/`data-ref-rev` — the shipped convention, `studio.py:115`), and the *composition* stance (a canvas is one visual statement, not a document). `api/prompts/CHANGELOG.md` entry. Gate: `build_studio_posture` intent assertions (the ADR-466 gate pattern `:196-201`).
6. **Click pass (Hat B; the worksheet's 6 steps, third application).** Adapt `docs/evaluations/2026-07-20-designer-click-pass/harness_bound_turn.py` to the canvas skeleton: one live bound turn — "compose a launch visual: headline + product figure + accent shapes" with a fixture image in the workspace. Observe: does Designer position every block, cite the figure by `data-ref`, stamp measures, use z when overlapping? Apply only what the turn proves; capture to `docs/evaluations/`; extend gates. **Phase 1 exit: the canvas mode exists in Studio, grammar validated by an observed turn.**

## Phase 2 — The binary substrate (WS-B; the dedicated arc; ADR-427 Ph2–3 + GC)

Runs exactly ADR-427 §10's own sequencing — this plan adds no design, only the arc structure:

1. **Ph2 — binary as Category-1** (its own session(s); the risk center). `write_revision` accepts a binary stream; parent-pointers/attribution/ADR-406 linearity for binary; `blob_sha` authoritative; `content_url` minted; `content_type` derived (D5). **The 52-site `.content`-reader classification pass + ratchet** (ADR-427 §8/correction E — `working_memory`, `compose/*`, `embed`, `freddie_envelope`, `recurrence`, `wake`, `lane_runner`, …: each reader classified binary-safe or text-only, gated so a new naked reader fails CI). Gate: a binary revision round-trips through `trace` + revert AND every reader is classified.
2. **Ph3 — media intake + serving.** Conformance-DAG check replaces the `documents.py` `ALLOWED_TYPES` + 25MB gate (`:115-131`); range-read/resumable-write driver implementation; per-request LFS-batch URLs. Gate: a real image uploads, versions, streams, serves.
3. **GC — pins as roots.** Root set = HEAD revisions + `data-ref`/`data-ref-rev` citations + `derived_from` edges; sweep reclaims unreferenced blobs (the 34,698 orphans measured 2026-07-14). Its own commit + a dry-run receipt BEFORE the destructive sweep (operator sees the count/pathology first — deletion discipline).
4. **Doc cascade** per ADR-427 §10.4.

**Discipline notes**: this arc gets dedicated sessions (not ridden alongside surface work); every gate that crosses Supabase/storage proves the code path only — the upload/serve smoke needs a human click, and the plan says so rather than claiming prod-proven.

## Phase 3 — The generation workflow (WS-C; gated on Phase 2)

1. **`docs(adr)`: the GenerateImage ADR.** The primitive's shape + **the uniformity ruling** (scoping doc §5 Q3 — operator decides here: uniform producer verb per ADR-467 D4 discipline [my lean] vs bound-canvas-only); metering (a rented call = a metered event on the one ledger); the cut-out contract; the `data-gen-prompt`/`data-gen-model` provenance convention (the `data-ref` pattern's generation sibling).
2. **`feat(primitives)`: GenerateImage.** Rented provider call (default `gemini-2.5-flash-image` via the `google-genai` SDK — `GEMINI_API_KEY` already on env; NO plumbing exists today, this is greenfield); result settles via the Phase-2 binary `write_revision` as an attributed asset (`assets/` beside the artifact, `member:{id} via {model}`), returns the path + dimensions for citation. Registered in `HANDLERS` (`registry.py:534`), tool schema, lane-surface entry per the ADR ruling (through `lane_tools_openai`'s loud-guard door — the schema lands in the same edit, the ADR-467 gate enforces it). Consequential-class (a write) → flows the ADR-307 gate under the member's grant like WriteFile.
3. **`feat(generation)`: the cut-out step.** Prompt contract (isolated subject, transparency/chroma request) + a rented matting fallback; provider chain chosen against ADR-468 §9 falsifier 2 (reliability/cost measured, not assumed) — a small Hat-B probe run first, receipts in `docs/evaluations/`.
4. **`feat(posture)`: the decompose discipline.** The canvas posture gains the D3 workflow: one prompt → named layer plan → route by kind (text→text blocks, shapes→SVG/CSS, subjects→cut-out leaves) → generate per object → compose positioned. CHANGELOG entry.
5. **Click passes (the soul's evaluation).** The decompose eval: one live turn, one composite ask ("a launch ad: headline, product hero, warm background") → observe the layer plan, the per-object calls, the landed object tree. Then the re-roll eval: "make the background warmer" → exactly one leaf regenerates, provenance updated, siblings untouched. Both captured to `docs/evaluations/`; both are ADR-468 §9 falsifier-1 instruments. Apply-only-what-observed governs posture tuning.

## Phase 4 — The /images surface (WS-D; the unveil)

1. **`feat(web)`: the surface shell.** Route `/images`; the canvas-mode editor full-frame; entry points (New canvas · from-prompt [the decompose flow as the front door] · from-upload); `AUTHORING_APPS.images = { id: 'images', resident: 'designer' }` (the ADR-467 declaration's second row — the registry comment already reserves it); LaunchServices routing (ADR-451 pattern) for canvas artifacts opening into IMAGES.
2. **Export**: flat PNG/JPEG as a projection of the tree (ADR-468 D2's export rule) — rides the ADR-466 P6 Export machinery precedent.
3. **The unveil gate (the D1 rule, per the scoping recommendation)**: this phase ships **only after Phase 3's click passes are green** — the app named IMAGES is AI-native from its first pixel.

## The delegation & execution discipline (how the phases run)

- **One phase = one arc; one commit = one gated step.** Each commit names its ADR, runs its gate (`python3 api/test_*.py` directly — never bare pytest for check-gates), and updates its doc in the same commit. Stage by name always; `git show --stat` after every commit; FF main by name from the branch.
- **Parallelizable**: Phase 1 commits 2–3 (server) and 4 (web) can run as separate lanes in worktrees (the design-systems precedent); Phase 2 must not run beside other api/services work (the reader-classification pass touches 30+ files — it owns the tree).
- **Hat separation**: click passes and provider probes are Hat B — harnesses + captures preserved under `docs/evaluations/` (the Designer-pass precedent; a lost harness is a lost receipt). Fixes they motivate land as Hat-A commits citing the capture.
- **Honesty rails**: any gate crossing Supabase/storage/env = "needs a human click," never "prod-proven." Every "the model does X" claim = an observed turn or it's a hypothesis.
- **Worksheet continuity**: the canvas click pass (P1.6) and the decompose evals (P3.5) are entries in the per-agent worksheet's Designer section — same 6-step shape, same receipts-in-one-place rule.

## Sequencing at a glance

```
P1 canvas mode (small, now)      →  P2 ADR-427 Ph2-3 + GC (the arc)  →  P3 generation  →  P4 /images unveil
   6 commits incl. ADR + click        4 steps per ADR-427 §10             5 commits incl. ADR + 2 evals   3 steps
   Studio-quiet (no AI-native         dedicated sessions; owns the        gated on P2                     gated on P3 green
   promise made)                      tree during the reader pass
```

**The one-line statement**: the plan reverse-engineers the Canva-class canvas onto the attributed filesystem in four gated phases — a `.slide`-reusing canvas mode that inherits the shipped object layer almost for free, the binary substrate arc that everything real waits on, a decomposed-generation workflow whose every layer is a cited attributed asset, and a surface that only opens once the name it carries is true.
