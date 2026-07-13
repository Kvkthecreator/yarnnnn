# ADR-450: The Derive-Recipe Registry — "Learn From" as a Kernel Verb with Kernel Recipes

**Status**: Accepted (2026-07-13, operator-aligned across the 448/449 discourse — "select the
highest-leverage wins while ensuring we can actually pull it off"). The operator-facing face of the
ADR-448 derive step. Derivation: the [load-bearing-files note](../analysis/load-bearing-files-are-a-graph-fact-the-reference-edge-derive-step-and-design-system-2026-07-12.md) §4
+ the 2026-07-12→13 session discourse (verb-not-workflow; contracts + recipes, not sub-processes).
**Date**: 2026-07-13
**Dimension**: Mechanism (the recipe constrains judgment work) + Identity (the derive is the
member's-hands act, under the member's grant) + Channel (the Files entrance, the lane).

**Amends**: ADR-411/440 (the lane binding gains a second kind: a **derive binding**
`{derive_recipe, derive_source}` beside the Studio `artifact_path` — same `lane_meta` mechanism,
same per-turn posture-overlay pattern) · ADR-448 (its D7 "Learn from is posture, not subsystem"
gains the registry that makes the posture repeatable, and its named-deferred FE entrance lands —
the seed mechanism turned out to already exist as `LanePanel.composerSeed`, ADR-441).
**Preserves**: ADR-222 (the kernel ships vocabulary as code-seeded data — the STUDIO_LAYOUTS /
APPS-table precedent; the kernel names categories) · ADR-408/411 (the derive executes as an
ordinary lane turn — the member's hands, the member's grant, `member:{id} via {model}`
attribution; no new intelligence path, no kernel pipeline) · ADR-209/444 (no new write path — the
lane writes through its file verbs) · ADR-448/449 (outputs cite sources; the design-system recipe
produces the ADR-449 contract) · DP32 (retain + attribute + cite — the recipe's discipline
section enforces the cite leg) · ADR-335/336 (web *search* / source discovery stays perception
territory, out of this verb's scope entirely).

---

## 1. Context — the verb needs recipes; the recipes are data, not sub-processes

ADR-448 shipped the derive mechanics (edges, kinds, posture) and ruled "Learn from" a verb, not a
workflow. The operator's push, validated against the design-skills ecosystem: the verb's *results*
differ by target — a design system, a PRD, a context brief — and producing a good one needs
explicit constraints. The ecosystem's answer (Anthropic's own design-system maker included) is
uniformly **SKILL.md-grade instruction prose on a generic agent loop** — never an engine. So the
missing layer is a **recipe registry**: per-target instruction sets + output contracts the verb
resolves against.

Two boundary rulings from the discourse, recorded as decisions below: the registry is
**kernel-internal** (not workspace substrate, not user-editable — refined in this codebase), and
it must not be confused with workspace-authored skills/scaffolds (a separate, deferred, user-owned
concept — deliberately not even called "recipes").

## 2. The decision in one sentence

**A kernel-internal, code-seeded registry (`DERIVE_RECIPES`) defines the Learn-from targets — v1:
context brief · design system · PRD — each as label + accepted sources + output contract +
SKILL.md-grade instructions; a lane may carry a derive binding (`derive_recipe` + `derive_source`,
the ADR-440 binding pattern) whose turns compose the recipe as a posture overlay; and the Files
kebab gains "Learn from…" — a chooser that creates the bound lane and lands the member in it,
composer pre-seeded.**

## 3. Decisions

### D1 — The registry is kernel-internal, code-seeded data

`api/services/derive_recipes.py::DERIVE_RECIPES` — versioned in this codebase, refined by yarnnn,
**never** written to workspace substrate, never operator-editable, not exposed as files. The
precedent line: `STUDIO_LAYOUTS` / `STUDIO_ARRANGEMENTS` / the ADR-436 `APPS` table /
`LANE_MODELS`. The distinct, **named-deferred** concept: workspace-authored derive instructions
(operator- or agent-scaffolded skills) — user territory, a different mechanism, same status as
ADR-312's agent-composed applications; when it arrives it composes *beside* kernel recipes, never
edits them, and carries a different name.

### D2 — The row shape

Each recipe: `slug` · `label` · `description` (operator words, shown in the chooser) · `accepts`
(source kinds — v1: `file`) · `target` (the output contract in one line — what makes the result
valid) · `instructions` (the SKILL.md-grade constraint prose: steps, quality bar, anti-patterns,
citation discipline). Instructions are **LLM-facing content**: every edit follows the prompt
change protocol (`api/prompts/CHANGELOG.md`), and each recipe earns a Hat-B eval probe as it
matures (the `probe_*` pattern) so refinement is measured.

### D3 — Consumption is a lane binding (the ADR-440 pattern, second kind)

`POST /api/lanes` accepts optional `derive_recipe` + `derive_source`; validated against the
registry, stored in `lane_meta`, surfaced on the lane dict. Every turn of a derive-bound lane
composes the recipe section (instructions + the source path + the projection note + citation
discipline) into the lane conventions — exactly as a Studio binding composes the authoring
posture. The two bindings may coexist (a bound Studio lane learning from a source). The derive
itself is an ordinary lane turn: the member's grant, the member's attribution, file-verb writes,
`derived_from` cites — nothing new executes.

### D4 — The v1 recipes and the leverage matrix

Three recipes, chosen for highest leverage with quality we can stand behind:

- **`context-brief`** (the zeroth/default — the verb never dead-ends): a reusable understanding
  of the source — what it is, key facts/entities/decisions, open questions — landed in a
  meaning-folder, cited.
- **`design-system`** (the flagship): produces the **ADR-449 contract** — a meaning-folder with
  `_design.yaml` + token-first CSS — so the output is immediately consumable by Studio and
  immediately legible/protectable via the 448/449 edge machinery.
- **`prd`**: a conventional product-requirements document (Problem / Users / Goals / Non-goals /
  Requirements / Metrics / Open questions), grounded in the source, inferences marked.

Source legs, sequenced by variance: **uploads now** (ADR-395 intake is built; recipes read the
`.extracted.md` projection of binary raws) · **GitHub repo next** (the recipe's *read plan* makes
it tractable — fetch only the files the target needs via the existing ADR-147 client, retain those
as observations, cite them; never ingest a repo) · **webpage-for-prose** after (a one-shot fetch,
the TrackWebSources machinery) · **webpage → design-system last** (real fidelity needs a rendered
DOM; yarnnn owns no rendering engine — ADR-417 — the ecosystem solves this with headless-browser
loops we'd have to rent). Web *search* is out of scope (perception, ADR-335/336).

### D5 — The entrance: a contextual verb, surfaced where the operator is

The Files kebab gains **"Learn from…"** (files only): a small chooser (the recipes' labels +
descriptions, served on the existing `GET /api/lanes` capability envelope — no new endpoint)
creates the bound lane (named `Learn: <filename>`, default lane model) and navigates to the chat
surface with the lane active (`navigateToSurface('chat', {lane})`). The lane's composer arrives
**pre-seeded, not auto-sent** (the ADR-446 lesson: click selects, the member sends) via the
existing `LanePanel.composerSeed` mechanism, on first open of an empty derive-bound lane. Other
surfacings (post-upload nudge, Studio insert-menu "from a source…", a Setup step rendering the
same verb) are additive one-liners against the same binding — never separate features.

### D6 — Named-deferred

Repo + webpage intake legs (D4 order) · `brand-voice` and any skill-maker recipe (the latter
walks into the user-scaffolding boundary) · workspace-authored derive instructions (D1) · the
async-job protocol driver for derives that outgrow a turn (ADR-413's lane, not this one) ·
per-recipe eval probes beyond the design-system one.

## 4. Cascade / blast radius

- **New**: `api/services/derive_recipes.py` + `api/test_adr450_derive_recipes.py`.
- **Edited**: `api/routes/lanes.py` (create-request fields + validation + lane dict + turn
  threading + envelope `recipes`); `api/services/lane_runner.py` (runner params + conventions
  section); `api/prompts/CHANGELOG.md`; `web/lib/api/client.ts`;
  `web/components/workspace/FileContextMenu.tsx` (one item);
  `web/app/(authenticated)/files/page.tsx` (chooser + handler);
  `web/components/chat-surface/{ChatSurface,LanePanel}.tsx` (seed-on-empty for derive lanes).
- **Schema**: none (the binding lives in `chat_sessions.context_metadata.lane`, the ADR-440
  precedent). **Migrations**: none. **New endpoints**: none.

## 5. Why this shape

A dedicated ingestion workflow would reify a mechanism into a place (the ADR-324/331 anti-pattern)
and stand up a second intelligence path beside the lanes; per-source pipelines would freeze one
path through a combinatorial source × target × surface space. One kernel registry of constraint
prose, one binding mechanism that already exists, one contextual entrance — and every future
source leg or target recipe is a data row, not a build.
