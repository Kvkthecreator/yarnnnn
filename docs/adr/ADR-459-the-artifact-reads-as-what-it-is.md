# ADR-459 — The artifact reads as what it is: kind is lifted, name is the namespace, the format is not chrome

- **Status**: Accepted (2026-07-15)
- **Dimension**: Channel (primary — what the operator reads) + Substrate (the lift, no new storage)
- **Supersedes**: nothing
- **Amends**: ADR-388 (the mirror keeps its raw leaf — reaffirmed, not changed) · ADR-443 R2 (`data-template` promoted from Studio-internal to the served kind) · ADR-451 (`resolveSurfaceApplication` gains a sibling: the kind is *read*, still no table) · ADR-222/223 (layouts join the bundle union-load; the kernel stops naming the instances)
- **Preserves**: ADR-456 D1 (HTML sole source; no second source for any fact the artifact already carries) · ADR-443 R1/R2 (the DOM is the model; layout-switch is an attributed revision) · ADR-400 (legibility over concealment; not a Finder) · ADR-340 DP29 (mirror once, compose few) · ADR-209 (every mutation attributed) · ADR-436 (the one-file ratchet; `AppId` opaque)

---

## 1. The observation

The Studio landing shows five cards. Four of them read `document.html`, `page.html`, `deck.html`, `deck.html`. Three of those names are the same word the type label already says one line below it ("Deck · 7/13/2026"). The fifth reads `deck.html` too.

The operator named these. At `NewArtifactModal.tsx:55` they typed "IR deck v3" and the modal built `operation/ir-deck-v3/deck.html`. The name they chose went into the folder. The card shows the basename. **The card is displaying the one part of the path that carries no information the card isn't already displaying, and hiding the one part that does.**

Two facts follow, and they are the whole ADR:

1. **`.html` is the artifact's storage encoding, not its identity.** Claude's design surfaces do not tell you their backbone is HTML. Neither should ours — on the surfaces whose job is composition.
2. **The name is not lost. It is in the namespace**, which is exactly where DP33 says meaning belongs. Nothing needs to be stored to recover it.

## 2. What was proposed and why it was wrong

The first draft of this ADR proposed a `kind` column and a `title` column on `workspace_files`. Four adversarial probes killed it. The record is kept because the reasons are the design:

**`title` as a column violates ADR-456 D1.** The artifact carries its title in its `<h1>`. A column is a second source for the same fact. The operator edits the heading and either the column goes stale or a sync-back path appears — a parallel control plane (Axiom 1 §153). ADR-456 D1's own phrase applies at field grain: *a shadow model in a costume*. And it already exists under another name — `routes/studio.py:203` writes `summary=req.message`, `routes/studio.py:73` reads it back. A `title` beside it is two competing name fields with no rule for which wins.

**`kind` as a column violates DP7 and ADR-443 R2.** It already exists, in the content: `studio.py:896` writes `<html data-template="{layout}">`, `studio.py:1066` reads it back. ADR-443 R2 ruled on precisely this: *"`data-template` + the artifact's `<style>` skin ARE the layout… lands as an attributed revision. Never a view toggle — the rendering IS the file."* A column would be a denormalized cache of content — and, sitting on the HEAD row outside the revision chain, a mutation with no attribution, which ADR-209 rejects at the write-path boundary. ADR-451 refused it by name: *"deliberately not built… any DB/registry table."*

**A closed `kind` enum inverts ADR-222.** `test_adr443:67` asserts `set(STUDIO_LAYOUTS) == {document, deck, article, page}` — set equality. A bundle shipping a `tearsheet` turns CI red by construction. ADR-222:117: *"The kernel exposes the task primitive; programs ship the templates."* A kernel enum naming `deck` is the kernel shipping the templates.

**"Studio hides, Files shows" contradicts ADR-400.** The proposed split leaned on ADR-451's Finder analogy — but that analogy is scoped to *routing* (`ADR-451:8`: "which chrome a file opens in"), and ADR-400's subtitle is *"a GitHub-repo browser, **not a Finder**"*, with `ADR-400:103` naming the failure mode exactly: *"legibility over concealment… rather than faking a flat filesystem."* The draft borrowed the half of Finder canon that canon explicitly rejected.

**The design that survives deletes the storage half rather than building it.**

## 3. The line canon actually draws

Not Studio-vs-Files. **Composition-vs-mirror** — DP29, which already has a worked precedent for exactly this de-jargoning.

`ADR-312:63`, the plain-language pass, implemented at `routes/workspace.py:827-844`:

> **Plain-language pass (the macOS lesson).** A Mac shows "Storage: 234 GB available," not inode counts. The Home was showing inodes. … recent artifacts **strip machine/path summaries** … server-side via `_artifact_title()`.

Its docstring says the quiet part: *"which leaks paths to the operator. Strip those shapes and fall back to the titleized slug so the Home reads like a Mac, not a workbench."* It already strips `.md` and `.html` and titleizes the slug. **The mechanism this ADR needs exists, is server-side, and is three ADRs old.** What it lacks is a home in the Studio and a name for the rule.

DP29 (`ADR-340:34-35`) supplies the rule:

> **Mirror surface** — one surface ↔ one substrate concern. **Complete, neutral, faithful.** … Mirrors are correct … and are never deleted: **they are the escape hatch, the `/proc` of the OS.**
> **Composition surface** — one surface ↔ one operator-**act**. **Selective, opinionated**, program-weighted, synthesized over many substrates.

`/proc` does not rename inodes. **Files keeps its raw leaf, extension included. That is not a concession — it is the surface doing its job.**

The Studio, however, is not one thing. **The Studio landing is a composition** (one operator act: *reopen my work*; it synthesizes over many artifacts; it is already selective — 20 rows, newest-first). **The Studio editor is an app over one file** (ADR-440/443), and an app tells the truth about the file it has open.

That seam is not new. It is the seam the codebase already drew — `StudioSurface.tsx` holds both, and they already have different jobs.

## 4. Decisions

### D1 — The kind is LIFTED from `data-template`, never stored

`GET /studio/artifacts` reads each row's kind from the artifact's own content via the existing `extract_template()` (`studio.py:1065`). Content stays authoritative. No column, no migration, no backfill, no second source.

This is the ADR-448 D3 "lift" pattern, one door: the kind is computed where it is served, from the fact the artifact already carries. A layout switch (ADR-443 R2) changes `data-template` in an attributed revision, and the kind follows for free — because it *is* the revision.

**The FE's `studioShapeFromPath` (stem-matching) is deleted.** It was honest about being wrong (`studioShapes.ts:45`: *"a renamed artifact falls to UNKNOWN — the label reads 'File' honestly rather than guessing"*), but it is now unnecessary: the server knows. Rename `deck.html` → `ir-deck-v3.html` and the kind survives, because the kind was never in the name.

### D2 — The name is the namespace, titleized. No new field.

The operator typed "IR deck v3". It became `operation/ir-deck-v3/deck.html`. The card renders **"IR deck v3"** — the titleized folder slug, via the ADR-312 `_artifact_title()` mechanism.

DP33: *"move the category to data, keep the namespace for meaning."* The meaning is already in the namespace. There is nothing to move. The extension is not shown because a composition does not show inodes.

`summary` is left exactly as it is — a description, written from the commit message. It is not promoted to a name. Promoting it would re-open ADR-456 D1 (a name outside the DOM is a second source) for a fact the folder already carries.

**Sentence case, not Title Case — a deliberate deviation from ADR-312's spelling.** `_artifact_title()` uses `.title()`, which capitalizes every word. Driving this against live substrate showed why that's wrong here: the operator's own "IR deck yarnnn march 2026 v5" came back **"Ir Deck Yarnnn March 2026 V5"** — wrong in *every* word. The modal lowercases the typed name into the slug (`slugify`), so casing is genuinely unrecoverable; every reconstruction is a guess, and the only question is which guess loses smallest.

Sentence case is wrong in **one predictable way** (an acronym reads "Ir" not "IR") rather than wrong everywhere. An acronym heuristic was implemented and then **rejected**: "has no vowels" makes IR/KPI/PRD look like ordinary words while flagging "my", and no rule can distinguish a typed "IR" from a typed "ir" once the case is gone. A cleverer guess is wrong less often but wrong less *predictably* — worse, because the member can't learn it. The dumbness is load-bearing.

The ceiling is honest and recorded: true fidelity needs the typed name stored, and storing it is the second source D2 refuses. **If acronym fidelity ever outweighs the storage cost, that is its own ADR — not a smarter regex.**

### D3 — The kind is an OPAQUE STRING, and layouts join the bundle union-load

`AppId = string` (`apps.tsx:49`) is the shape ADR-436's ratchet already blessed, for exactly this reason (`ADR-436:74`: *"the table's shape admits a stranger's row"*). The served kind follows it: an opaque slug + a label, resolved through a registry, never a closed union the FE re-narrows.

Concretely:
- `test_adr443:67` and `test_adr440:38` change `==` to `⊇` — assert the kernel **seeds** four layouts, not that only four **exist**.
- `bundle_reader.py` gains `list_bundle_layouts()`, alongside the five existing `_normalize_bundle_*` union-loads (`bundle_reader.py:489` is the pattern).
- The FE stops holding a `Record<string, StudioShapeMeta>` keyed by a hardcoded set. It resolves label + icon from the served registry, with an honest fallback for a slug it has no icon for.

Then alpha-trader ships `tearsheet` as a MANIFEST row with a `scaffold`/`skin` and **zero kernel touches** — which `ADR-222:85` promised and `ADR-223:472` ("extend via additive fields") already licenses.

This is the `watches[].shape` precedent (ADR-335): **the kernel names the slot, the bundle fills the value.**

### D4 — The extension leaves the composition, and stays everywhere else

| Site | Class | Renders |
|---|---|---|
| Studio landing cards | composition | **"IR deck v3" · Deck · 7/15** — no extension, no path |
| Studio editor crumb | app-over-one-file | raw leaf, unchanged |
| Studio Rename modal | shared verb (`useFileOrganizeVerbs`) | raw leaf, unchanged |
| Files rows / tiles / tree | **mirror** | raw leaf, unchanged |
| `FileMeta` / `ArtifactCard` | mirror-adjacent | unchanged |

The Rename modal is the coherence test, and it passes: STUDIO.md:100 ratifies that Studio's Rename is *the same shared `useFileOrganizeVerbs` flow Files uses*, and `RenameModal.tsx:30` pre-fills the full extension while selecting only the stem — the Finder-correct gesture that hides nothing. Because the change is scoped to the **landing composition** and not the editor, the shared modal is untouched and the fork is avoided.

### D5 — `prd` stays a downcast, and that is now recorded rather than hidden

`StudioSurface.tsx:1294-1298` downcasts the `prd` derive-recipe to `template: 'document'`. A PRD is structurally a document and semantically a PRD; the layout can hold one. **This ADR does not fix that** — a derive-recipe and a layout are orthogonal taxonomies, and collapsing them would be the mistake this ADR just refused in the other direction.

What changes: the downcast is no longer *silent*, because the kind is served from content rather than guessed from a stem, so the seam is visible in one place instead of being smeared across a filename convention. Naming the recipe on the artifact is a future ADR if demand appears. Recorded as a known, bounded loss.

## 5. The prerequisite bug (MoveFile eats metadata)

Surfaced by the probes; **not caused by this ADR, and not blocking it** — but it is real, it is live, and it belongs on the record here because the next person to reach for a metadata column will hit it.

`primitives/workspace.py:1176` selects only `path, content`, then `write_revision`s to a brand-new destination row. Because `_upsert_workspace_file` only writes non-`None` keys and the destination is an insert, **`content_type`, `content_url`, `lifecycle`, and `metadata` all land at DB default** — and `summary` is overwritten with the literal `"Moved from …"` (`:1204`).

Move a PNG today and its content-type and blob URL are gone. That sits directly under ADR-427's binary work.

This ADR's design is **immune** to it — the kind is in the content, and the content is what `MoveFile` carries. That immunity is not luck; it is the argument for the lift restated. Fixing MoveFile (widen the SELECT, thread every metadata column, stop clobbering `summary`) is a standalone bug fix, tracked separately.

## 6. What is deliberately not built

- **No `kind` column, no `title` column, no migration.** The storage half is deleted, not built.
- **`summary` is not promoted to a name.** It stays a description.
- **The Files surface is not changed.** It is the mirror; it shows what is there.
- **The Studio editor crumb is not changed.** An app over one file names the file.
- **No per-artifact recipe field.** The `prd` downcast stands (D5).
- **The derive-recipe and layout taxonomies are not merged.** They are orthogonal.

## 7. Falsifiers

1. A Studio artifact renamed away from its template stem still reads its correct kind on the landing. (Today: "File".)
2. A bundle can add a fifth layout with zero edits to `studio.py`, `studioShapes.ts`, or any test's expected set.
3. Grep: no `.html` string reaches an operator-facing render on the Studio landing.
4. `grep -rn "workspace_files.*kind\|ADD COLUMN.*title" supabase/migrations/` returns nothing new — the ADR shipped no storage.
5. The Files surface renders byte-identically before and after.

## 8. The one-line statement

**The format is not the artifact's identity; the folder already holds its name; and the kind is a fact the file carries, not a fact the filename spells.** Compositions read like a Mac. Mirrors read like `/proc`. Neither lies.
