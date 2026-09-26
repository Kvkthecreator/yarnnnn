# ADR-671 — Office files are first-class: the member's format is the document

> **Status**: **Accepted** (2026-09-26; operator, on the assessment: *"yes, aligned in full. would like to delegate
> implementation details as we're aligned. ensure singular streamlined discipline with code and docs, scoping in
> deletion and clean-up of code where warranted to avoid future ambiguity"*). Phase 1 implemented — §9.
> **Date**: 2026-09-26
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Substrate** (which bytes are canonical, and the one way they change) and
> **Channel** (which app a format opens in). No schema change in Phase 1.
> **Gate**: `api/test_adr671_office_files_are_first_class.py`.

**Amends** — ADR-395 am.2 §11.8 (round-trip in-place editing: deferred → the core mechanism) and §11.11 (an office
WriteFile over an existing office file: rebuild → refused) · ADR-574 D4 (narrowed: an app may apply *the file's own
styles*; a freeform formatting and layout editor stays refused) · ADR-621 D1 (MCP `open` on a readable office file
serves its words instead of `content: null`). **Preserves** — ADR-209 (every change is one attributed revision through
`write_revision`) · ADR-395 Piece B (the co-located `.extracted.md` projection, now addressed) · ADR-609 (the anchor
contract — an address confines an edit; omitting `old_string` replaces the addressed thing whole) · ADR-661 §6
(local hands are attended-only) · ADR-395 §8.7 (the agent code sandbox stays declined, trigger unchanged).

## 1. The problem

A beta member's first move is to bring what they already have: a `.docx` contract, a `.xlsx` budget, a `.pptx`
deck. ADR-395 am.1/am.2 made those files readable, viewable and exportable. It did not make them *workable*:

- **Every office writer built a new file.** `docx.Document()`, `Presentation()`, `openpyxl.Workbook()` — asked to
  change one figure in a formatted budget, an agent re-emitted the workbook's text and the sheet writer rebuilt it:
  formulas became numbers, number formats, merged cells, widths and colours were gone, and the write reported
  success. ReadFile's message *instructed* the agent to do this. A Word file lost its template, styles, headers,
  footers and images the same way; an uploaded deck could not be revised at all.
- **The member could not edit an office file anywhere.** The viewers are read-only by design.
- **An external LLM could not read one.** MCP `open` on a `.docx` answered `content: null` — "nothing to read as
  text" — although the words were extracted at upload. ADR-574 §2b's invisibility, for the formats members bring most.

The version history kept the original (r1), so "nothing is lost" held in the ledger and failed on the file the
member actually looks at: the latest one.

## 2. The reframe

**The office file is the document. Markdown is how an agent reads it, not what it becomes.**

ADR-574's case for `.md` is interoperability: any LLM can read it whole. That property does not require *storing*
work as Markdown — it requires every file to have a **readable, addressed text view**. Give every office file that
view and the AI-native property moves from the storage format to the projection layer; nothing has to be converted
into a yarnnn format to be workable. The commons is **format-plural**, and the member's own format is canonical.
`.md` and HTML remain the currencies of work that *starts* in yarnnn; they stop being the centre.

## 3. Decisions

**D1 — The bytes are canonical; an existing office file is patched, never rebuilt.** Building from a source (Markdown,
HTML, CSV, a Slides deck) is for *creating* a file: a new path, or the member's "Save as" sibling. A WriteFile to a
path that already holds an office file is refused, naming the edit path. `write_office_file` is renamed
`create_office_file`, because that is all it may do.

**D2 — The projection is addressed.** Each `.docx`/`.xlsx`/`.pptx` projection carries the addresses its edits use,
taken from the file's own structure:

| Format | Address | Example line |
|---|---|---|
| `.docx` | `pN` — the Nth paragraph of the body in document order, table cells and text boxes included | `[p12 · Heading 2] Pricing` · a table cell `[p31] 1,100` |
| `.xlsx` | `Sheet!A1` — the cell reference | `\| 20 \| Total \| =SUM(B2:B19) → 4210 \|` under a column-letter header |
| `.pptx` | `sN/id` — slide position / the shape's own id; `sN/id/rRcC` a table cell; `sN/notes` | `[s3/5] Revenue up 12%` |

A position address is guarded by content: an edit names the text it expects (`old_string`), or replaces the
addressed element whole — a stale address fails loudly, never lands on a neighbour. A workbook shows each formula
beside its last-calculated value. A document with pending tracked changes reads as if they were accepted, and says so.
The projection stays the co-located `.extracted.md` (ADR-395 Piece B): it is the search index's only route to an
office file's words and PDF shares it, so replacing the sibling is a search-substrate change, not an office one.

**D3 — One write language, one engine.** Office edits are addressed operations — replace text in a paragraph /
shape / cell, insert a paragraph after one, delete one, restyle one with a style the document already defines, set a
cell's value or formula — applied by ONE kernel engine (`api/services/office/`) at the level of the XML parts inside
the OOXML zip. Every part an edit does not touch is written back with identical content; the gate asserts it. The
engine never loads an existing workbook through openpyxl (which drops charts). Three doors reach it: **EditFile** with
`anchor={'at': …}` / `{'after': …}` or a batch of `edits` (one revision), **MCP `edit`** with `at`, and — Phase 2 —
the apps' office modes. Every edit is conditional on the head it read (ADR-406 D4).

**D4 — Attribution travels inside the file.** An edit to a `.docx` authored through a model — the member's lane, an
external LLM over MCP, an agent — lands as **Word tracked changes** (`w:ins` / `w:del` / `w:pPrChange`) authored under
the principal's display name (`display_author`: *"Kevin via Claude Sonnet 5"*, *"Kevin's Claude (via MCP)"*). Opened in
Word, the member sees who changed what and accepts or rejects it there. A member's direct edit (Phase 2) writes
clean. `.xlsx` has no tracked changes, so its attribution lives in the revision (and D5).

**D5 — History reads changes, not bytes** (Phase 2). A revision diff of an office file compares the two revisions'
addressed projections — *"B7 1,100 → 1,200 · Editor"*. Computed on demand through the one extractor; nothing stored.

**D6 — Fidelity comes from the member's own Office, not a server.** Pixel-faithful slides, exact recalculation and
legacy `.doc`/`.xls`/`.ppt` conversion need a real Office engine. The answer is the member's own, through the desktop
app (ADR-661 D3): scripting interfaces first (AppleScript/JXA on Mac, COM on Windows, possibly an Office add-in),
interface-driving computer use only for work no scripting path reaches. Renders are cached per revision and serve
every viewer. It is attended-only by construction, so it is a **fidelity layer, never the floor**: D1–D4 run
server-side for every principal, unattended included. **No fourth Render service** — a LibreOffice service is the
named fallback only if members without an attended Office machine ask for fidelity more than once.

**D7 — New work starts in Office** (Phase 3). Each app's "New" leads with its office format, built from the
workspace's house templates (a reference `.docx` / `.potx` / `.xltx`); exports from `.md`/HTML write through the same
templates. Markdown stays as "Plain text".

**D8 — Three apps, one per office family** (Phase 2). Text houses `.docx`, Slides houses `.pptx`, and a new **Data**
app houses `.xlsx` beside `.csv`. Each claims its format through `resolveSurfaceApplication` (ADR-451; the Open With
picker's forcing case fires), draws it faithfully, and edits at its grain — paragraphs, shapes, cells — with the
file's own styles, through D3. Anything past that grain is "Edit in Word / Excel / PowerPoint" (D9).

**D9 — The member's own Office is a first-class editor** (Phase 3). Desktop: open a local copy, watch for saves, land
each as an attributed revision; a save against a moved head lands as a sibling copy. Web: "Upload new version" on a
file. Later: an Office add-in — the member's own tool as the surface, as the Chrome extension is for the web (ADR-662).

**D10 — Edge cases.** Macros (`.xlsm`/`.docm`) are kept and never run; patching preserves `vbaProject.bin`.
Encrypted and rights-managed files take the D9 marker (ADR-395 am.1). A cell inside a merged range is written at the
range's anchor. Overwriting the master cell of a shared formula first materialises the group, so no dependent cell
loses its formula. A formula edit drops `calcChain.xml` and sets `fullCalcOnLoad`, so Excel recalculates on open.

**Still refused**: a freeform formatting or layout engine (ADR-574 D4's trap, narrowed not lifted) · a formula engine
of our own · executing macros · the agent code sandbox (ADR-395 §8.7).

## 4. What is deleted

- `extract_text_from_docx` / `_xlsx` / `_pptx` and `_docx_table_text` in `services/documents.py` — the addressed
  projections live beside the edit engine, so the addresses read and the addresses written cannot drift.
- `services/export/office.py` — moved to `services/office/create.py`; the office kernel has one home.
- The sheet writer's literal-`\t` rescue — it existed to make the lossy rebuild round-trip "work"; D1 removes the
  round trip.
- ReadFile's "WriteFile the WHOLE workbook back" instruction, and every "rewrite in place" branch of that message.
- The three copies of "land these bytes and re-derive the projection" (export, restore, now edit) → one
  `land_binary_revision` in `services/documents.py`.

## 5. Phases

| Phase | Builds | Status |
|---|---|---|
| 1 — kernel | D1 · D2 · D3 (EditFile + MCP) · D4 · D10 | **Implemented** (§9) |
| 2 — apps | D8 (Data app; office modes in Text and Slides) · D5 · recalculation for display (`xlcalculator`, MIT) | open |
| 3 — Office as editor | D7 house templates · D9 Upload new version + desktop Edit-in-Office | open |
| 4 — fidelity | D6: local Office scripting spike (Mac background render first, then Windows COM), per-revision render cache | open |
| 5 — in Office | D9 the Office add-in | open |

Each later phase writes its own amendment here and extends this gate.

## 6. Why not the alternatives

- **Convert office files into Text/Slides formats and edit those.** The first save would remove the member's template:
  the loss this ADR exists to stop, moved into the member's hands.
- **Embedded web Office editors** (Microsoft WOPI, OnlyOffice, Collabora). WOPI needs a Microsoft partnership; the
  others are a document server yarnnn would run — and all three are the word-processor trap.
- **A LibreOffice rendering service now.** Only accurate slide images need it in Phases 1–3; the member's own Office
  (D6) is more faithful, adds no service, and keeps the file on their machine.

## 7. Gate

`api/test_adr671_office_files_are_first_class.py` — drives the engine on real files written by python-docx /
python-pptx / openpyxl, and asserts on the XML, not on a mock:

- the addressed projection names every paragraph / cell / shape, and the address resolves to the element it names;
- each edit lands exactly the change asked, and every other part of the package has identical content;
- a `.docx` edit through a model is a tracked change authored by the principal's display name; a member's is clean;
- formulas survive a neighbouring edit; a shared-formula master overwrite keeps its dependents' formulas;
- WriteFile over an existing office file is refused; EditFile / MCP `edit` reach the engine; MCP `open` serves words;
- the client slide parser reads the addressed projection (executed across the language boundary).

## 8. Consequences

An agent's natural loop — read, then edit what it read — is correct on an office file for the first time: the read
names the addresses the edit takes (ADR-395 §11.12's lesson, *make the natural loop correct, don't warn*). Any
connected LLM can change a member's real Word file without breaking it. The Data app gets a model to build on instead
of a viewer to extend.

## 9. Implementation status

### 9.1 Phase 1 — the kernel (2026-09-26)

**One home**: `api/services/office/` — `package.py` (the OOXML zip: parts parsed with entities and network off,
changed parts serialised, every other part written back with identical content; `OfficeKind`), `docx.py` /
`xlsx.py` / `pptx.py` (each: the addressed `project` and the in-place `apply`, and one `KIND` the registry row
carries — so no format is named outside `services/file_formats.py`), `edit.py` (the one edit door), `create.py`
(moved from `services/export/office.py`; `create_office_file`, creation only).

**The doors**: EditFile's workspace branch routes an office path to `edit_office_file` (a text head under an
office name still edits as text); `anchor.at` / `anchor.after` / `edits` / `style`; `new_string` enforced in the
handler. WriteFile over an office head → `office_file_exists`. ReadFile names the in-place loop and never the
rebuild. MCP `open` serves a readable binary's words; MCP `edit` takes `at`. The restore route, creation and
edits land through ONE `land_binary_revision` (`services/documents.py`). The identity stamp is one helper,
`_identity_uuid` (was inline in WriteFile and EditFile). Client: `withoutAddresses` strips address labels from
every member-facing projection (the slide view, the terminal preview), and the slide parser reads an addressed
Markdown table as the TSV its renderer draws.

**Choices made in building**: position addresses for Word (`w14:paraId` is absent from python-docx, Google Docs
and LibreOffice output, and Word regenerates it) guarded by content; text written to a cell as an INLINE string so
`sharedStrings.xml` is never rewritten; a write widens `<dimension>` and the projection resets it (another tool's
stale hint must hide nothing); Excel's literal-text apostrophe (`'=…`) both shown and parsed, so a text cell that
says a formula never reads as one; a docx tracked replace SPLITS runs at the span's edges so only the replaced
characters are marked deleted; the paragraph-mark `w:ins`/`w:del` is the FIRST child of its `w:rPr`
(CT_ParaRPr order — Word treats an out-of-order child as damage). The in-app Word viewer (docx-preview,
`renderChanges: false`) draws insertions and hides deletions — "as if accepted", the projection's own reading.

**Gate** `api/test_adr671_office_files_are_first_class.py` **36/36**, proven RED by **16** in-place falsifications,
each turning exactly its arm red (paragraph mark appended · new words take the last run's look · shared dependents
untranslated · calcChain kept · DDE admitted · dimension not widened · stored dimension trusted · merge unchecked ·
model edits untracked · edit not conditional on the head · create rebuilds an existing file · ReadFile offers the
rebuild · MCP edit drops `at` · MCP open serves null · the client shows addresses · a stale Word address lands).
⭐ Two arms were blind on first cut and re-cut: the paragraph-mark arm's fixture had no mark formatting, so
append and insert produced the same XML; the stale-dimension arm had no stale fixture until one was built.
Re-pointed, not routed around: `test_adr395` (16 arms: the retired rebuild round trip → the in-place edit; the
TSV spelling → the addressed table; the literal-tab arm deleted with the rescue), `test_adr609`,
`test_adr545` #6 and `test_principal_display` #9 (the identity rule moved into its one helper — now driven),
`test_adr427` (the moved module's classification). `next build` exit 0 on HEAD + the two web files (the working
tree carries another session's unfinished `ChatSurface.tsx`).

**Driven on production** (2026-09-26, through the claude.ai connector against the live MCP server at `68f4ada`):
`save adr-671-drive/contract.docx` created a 36,918-byte Word file (revision `2c8e6523`); `open` served
`[p1 · Heading 1] Service Agreement … [p7] 1,100 …` with the edit grammar in its explanation; `edit(at='p2',
old='30 days', new='45 days')` landed revision `feff9c36`. Both revisions' bytes were downloaded and diffed: ONE
part changed (`word/document.xml`), none added or removed; the XML carries `w:del` "30 days" and `w:ins` by
*"KVKtheCreator's Claude (via MCP)"*; python-docx opens it. A text `save` over it was refused
(`binary_file_not_writable`). ⚠️ `0b5bb56` (a concurrent ADR-563 commit) had already shipped this ADR's
`server.py` half — `edit` passing `at=` to a `compose_edit` without it — for ~12 minutes; the MCP logs show no
`edit` call in that window.

**Found driving, fixed**: trashing the file left its `.extracted.md` projection LIVE — listed, searchable, citing a
file in Trash. Move had carried the sibling since ADR-554 D1; archive and restore never did, for every upload of a
format yarnnn reads. `archive_live_file` / `restore_live_file` (the one seam every delete and restore reaches) now
carry it via `_carry_projection`, for the binary text family only — a member's own `notes.extracted.md` beside
`notes.md` is never touched. Gate +3 arms (39/39), falsified both ways (18 falsifications in all).

**Owed**: the same drive with REAL Office-authored files, opened afterwards in Word / Excel / PowerPoint
(SESSION-HANDOFF).
