# Session handoff — 2026-08-16: close the Text↔Docs gap (ADR-571 phase 2)

`origin/main` at `3a9350a`. The Text app ships and is structurally correct; the
gap now is **the canvas and the feature depth**, not the housing.

> **The prior handoff (multi-agent conversations, ADR-495) is ABSORBED.** Its
> owed items live in memory (`project_adr495_addressing`) — chiefly the
> quiet-default click-pass and the FE @-autocomplete. Two items from it are
> carried in §"Owed from earlier arcs" below so nothing is stranded.

## Where things stand

ADR-570 gave prose a member write door (format class ∧ carve law ∧ principal
gate, CAS-guarded). ADR-571 gave it a dedicated app — slug `text`, colleague
**Editor** (the app's name for the `designer` resident, ADR-562's Docs/"Writer"
shape), unveiled in the launcher + Dock. Two operator corrections shaped it:

1. It was first built inline in Files → re-cut to a dedicated app (ADR-571).
2. It was first built on `DeskHousing` (the DASHBOARD housing — Radar/Strings)
   and read as *"lazily applied"* beside Docs → rebuilt on the Docs shape
   (`fa42a8d`).

**The operator's standing instruction — carry it into the new session — is
vis-à-vis parity with the Docs app**: *"try and have essentially all (most that
can be applied) features and look and feel. a direct comparison to
implementation seems fine."* Plus the standing disciplines: delegate the
details, commit+push to `main` with testing where warranted, **scope in
deletion of legacy/dual approaches**, and keep docs + codebase consistent.

## The gap, named by the operator's own screenshot

The Text canvas shows **raw monospace source** — `# Creative Brief — YARNNN`,
`**not**`, `---` — while Docs renders its document (serif headings, styled
tables, real typography, zoom). A 1,062-word brief reads as a source dump.
That is the headline gap; the feature depth behind it is the rest.

**Measured scale gap**: Docs is ~5,600 lines across 26 modules
(`web/components/authoring/`); Text is ~1,100 across 4
(`web/components/text/`).

## The one constraint that is NOT negotiable

**ADR-456 D1** (verbatim, `docs/adr/ADR-456-*.md`):

> **Named-deferred**: a `markdown.editor` app … (the ADR-436 Open-With moment —
> **textarea/CodeMirror-grade, never block-grade**; Studio's machinery must not
> leak into it).

And: *"`.md` is the substrate's prose currency; `.html` is the Studio's
authored-artifact currency… Studio is never bimodal."*

So: **do not port the block model.** No block ids, no `data-*` annotations, no
arrangements, no citation pins, no per-block Properties inspector. The file must
stay a plain `.md` that connectors read and write byte-for-byte — that
round-trip is the whole product thesis. **A rendered VIEW is not a block
model**; rendering markdown for reading is the honest way to close the visual
gap without becoming bimodal. If a proposed feature requires annotating the
source, it is out of scope — say so rather than smuggling it in.

## Suggested first move (assess, then propose — this operator asks-with)

Do a **feature-by-feature audit of Docs vs Text** and bring back a table before
building. Known candidates, roughly by value:

| Docs has | Text today | Notes |
|---|---|---|
| Rendered canvas (serif, tables, headings) | raw textarea | **The headline gap.** `MarkdownRenderer` (react-markdown + remark-gfm + mermaid) already exists and is mounted in ~10 places — reuse it, don't write one. Design call: preview/edit toggle, split view, or live render. |
| Zoom control | — | View-only, cheap. |
| `ArtifactThumb` (real scaled render) | text-preview card | Could render markdown at scale instead. |
| Insert menu / slash palette | — | Markdown-SYNTAX insertion (heading, list, table, link) is fine; BLOCK insertion is not. |
| Find/replace, outline nav | — | Genuinely useful at 1,000+ words. |
| `LearnFromFlowModal` (derive a doc from a source) | — | Works for prose; a lane derive. |
| Design systems / skins / tokens | — | **Out of scope** — that IS Studio machinery. |
| Properties inspector (per-block) | doc-level facts | Keep doc-level; per-block is the banned shape. |
| Export → print/PDF | download .md + copy AI ref | Print of a RENDERED view becomes possible once the canvas renders. |
| Revision history in-surface | points at Files → Get Info | Docs' trace affordance may be portable. |

Also check whether `MarkdownRenderer` needs a doc-grade reading skin: Docs'
typography comes from the artifact's own HTML + design system, and prose has
none, so the reading face is the app's to define.

## Files you will touch

- `web/components/text/` — `TextSurface.tsx` (landing), `TextEditor.tsx` (open
  state: crumb · Save · Share/Export · Properties|Chat rail), `TextExport.tsx`,
  `NameDocumentModal.tsx`.
- Reference implementation: `web/components/authoring/StudioSurface.tsx` (the
  landing is its start state ~`:4282`; open-state chrome ~`:3380-3800`).
- Backend: `api/services/apps/text.py` (registration + `build_text_posture`);
  `api/services/lane_runner.py` (the `app == "text"` branch).
- Gate: `api/test_adr571_text_app.py` — **script-style, run
  `python3 test_adr571_text_app.py`** (pytest reports a false pass). 37/37 now.
- ADR: `docs/adr/ADR-571-*.md` — amend it, or write ADR-572 if a real design
  decision emerges (e.g. how a rendered canvas coexists with source editing).

## Verification that must stay green

```
cd api && python3 test_adr571_text_app.py             # 37/37, script-style
node web/lib/file-types/__gate_adr514_d2.mjs          # 41/41, from REPO ROOT
cd api && python3 -m pytest test_lane_artifacts.py test_adr570_member_prose_door.py -q
cd api && python3 test_adr562_app_owned_config.py     # script-style
cd api && python3 test_adr297_navigation_enactment.py # 22/5 is the PRE-EXISTING baseline
cd web && node_modules/.bin/next build                # `pnpm` is NOT on PATH; 171/171 pages
```

## Traps this arc paid for — do not re-pay them

- ⭐**A green gate is not a finished app.** Every registration gate passed while
  the surface read as a placeholder. Gate the AFFORDANCE (§5 of the ADR-571
  gate does this), not just that a symbol exists.
- ⭐**Drive the deployed surface.** Both real defects this arc (a 422 that
  rendered as "No documents yet"; picker rows labelled by folder) were invisible
  to gates AND to `next build`, and were found only by clicking.
- ⭐**A rejected request wears an empty state's clothes.** Check the network
  panel, not just the DOM.
- ⭐**Strip comments before asserting in a gate** — an assertion can match its
  own explanatory prose (hit twice in this arc).
- ⭐**Vercel FE deploys lag the push by minutes**, and client markers live in
  hashed chunks, so `curl` of the HTML cannot detect them. Verify in the
  browser; confirm you are on the NEW bundle before concluding anything.
- The ADR-297 parity gate has **5 pre-existing failures** (`sources`,
  `system-agent`, `program`, `/openapi`) — verified against a stashed tree.
  Do not chase them.

## Owed from earlier arcs (unrelated to Text, still open)

- **ADR-570 D8 click-pass** — the connector round-trip end to end, including a
  real MCP-driven 409. All pieces are live; never driven as one pass.
- **ADR-495**: click-pass the quiet default (`b82d7b3`) — placeholder should
  read "Message Thinker…"; FE @-autocomplete for mentions is unbuilt.
- **ADR-514**: `DuplicateFile` is path-addressed but NOT gate-queueable, so its
  path branch is unreachable and the verb gates on nothing. ADR-514's to close.
