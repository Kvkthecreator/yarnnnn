# Session handoff — 2026-08-18/20

Delete a PART in the commit that absorbs it — not the whole file. Parts A–F are prior sessions' owed items and are still open.

---

# Part G — the git-at-any-scale arc: ledger receipts, the export door, danger-zone cleanup (2026-08-20)

## What shipped

| Commit | What |
|---|---|
| `91fe2f6` | docs: authored-substrate — replay invariant measured, taxonomy re-synced, the no-compiler argument |
| `3751783` | blog: "Knowledge Work Has No Compiler" + **remark-gfm wired** (tables rendered as raw `\|---\|` on the live site; 4 posts) |
| `c6e9fcc` | feat: the export gets a door — Download Workspace card + purge confirm names the remedy |
| `7cc83a6` | fix: 168/1,613 export commits dated 1970 (py3.9 `fromisoformat`) |
| `d2c1281` | refactor: danger-zone condense — User Settings' dead L1/L2 plumbing deleted (net −81) |
| `5e76e3d` | fix: purge acts on the workspace it was asked about, and fails CLOSED |
| `99f5d51` | chore: api + web lanes validated |

## Measured facts (production, 2026-08-20)

- **Replay is clean**: 391/391 live files byte-identical to their head blob;
  0 dangling parents, 0 forked chains, 0 unattributed of 1,928 revisions.
  `workspace_files.content` is a genuine cache, not a second source of truth.
- **Concurrency is a real CAS** — migration 197's partial UNIQUE on
  `parent_version_id`. Not the read-then-insert it looks like.
- Attribution residue: 8 free-text `authored_by` rows, 2026-07-07→07-16, door
  since closed by `is_valid_author`. **They stay** — rewriting history to tidy
  the census trades the invariant for its appearance.
- Author census: operator 986 · system 769 · member 67 · yarnnn 56 · freddie 31.
  Machinery authors ~40% and touches more distinct paths (201) than the
  operator (141).
- 160 revision chains have no live file (the L1 orphan condition, below).

## OWED — needs a DECISION, not a patch

**1. Destructive paths bypass `delete_live_file` (unattributed destruction).**
The obvious fix is wrong: L2 deletes `workspace_file_versions` AND
`activity_log` in the same act, so any in-workspace record of the destruction is
destroyed by it. Needs a durable **out-of-workspace audit sink** first. For a
product whose invariant is "every change is signed by whoever made it", the one
unsigned path being the most destructive one is worth an ADR.

**2. L1 orphans revision chains.** `workspace_file_versions` has no FK to
`workspace_files` (keyed `(user_id, path)`), so L1's file deletes cascade
nothing — 160 chains already live. Arguably correct for a light L1, but
undocumented and the copy implies otherwise.

**3. `execution_events` (cost ledger) is destroyed by purge** — forced by a
`NO ACTION` FK, but in tension with ADR-291's "financial history preserved,
L4 only". Decision, not a patch.

## OWED — click-passes (mechanism verified, browser path not)

- **Download Workspace**: engine driven against the real 299-file workspace
  (1,613 commits, `git fsck --strict` clean, `git shortlog` names every
  principal). NOT clicked in a browser — the route streams a zip, and a
  `Content-Disposition`/CORS detail behaves differently there than in curl.
- Danger-zone condense (both doors after the cleanup).
- Everything in MEMORY.md still marked OWED from prior arcs.

## Gate notes

- `test_adr476_purge_scope` D3 pinned `?pane=danger` — a spelling the app has
  never used. RED since written. Re-anchored + falsified.
- `test_adr501_read_path_binding` pinned `resolve_purge_workspace(user_id)` in
  the `clear_integrations` window and read the fail-closed hardening as a
  regression. Re-anchored to accept either spelling.
- New: `api/test_purge_scope_and_failclosed.py` 8/8, each fix falsified against
  the real pre-fix code.

---

# Part F — ADR-586: the one-door rebuild (2026-08-19; BUILT + CLICK-PASSED)

**Built at `af92564`; DRIVEN at `d10c092`.** The whole door was click-passed on
a real deck and a real flow doc — run record:
`docs/evaluations/2026-08-19-adr586-one-door-click-pass-run1.md` (15 steps,
both halves per step, scope + non-coverage declared).

**PASS**: the category rail with medium ordering (deck leads Slide, flow leads
Text and has no Slide at all) · schematic galleries · a Stat insert landing in
the slide the header named, drawn by the kernel with the delta themed by the
palette marks · right-click tiers expanding INLINE at the bottom edge with the
box re-measuring upward (125→352px, top 647→421, never off-screen) · contextual
Update pre-expanded with the meter badge as the only mechanical/metered seam ·
the bottom sheet as one component + class fork · the FULL ADR-583 loop: lane
composes a contract-clean `*.component.html` → it appears "shared" in the
Components gallery → insert cites it directly (pin = head revision, attributed
`member:… via …`) → editing the SOURCE moves the citing artifact (GROWTH/$79)
while the pin stays the fallback, exactly as D4's "reference, never copy" says.

**ONE defect found by driving and fixed in-run (`d10c092`)**: the named target
did not COMPOSE — "ADD — INTO AFTER THE SELECTED BLOCK" on every block-selected
open, both housings, both media. The header hard-coded "into" while the block
branch of `resolveInsertTarget` already returned a prepositional phrase. Each
branch now owns its preposition; the header states the label verbatim.
`test_adr586_one_door.py` 27→31 (both new checks falsified against real breaks);
`test_adr509_insert_route.py` re-anchored off the pinned spelling that read the
correction as a violation.

## Verification (the standing set)

```
cd api && python3 test_adr586_one_door.py            # 31/31
cd api && python3 test_adr583_component_library.py   # 28/28
cd api && python3 test_adr581_medium_regroup.py      # 13/13
cd api && python3 test_adr579_verb_grammar.py        # 16/16
cd api && python3 test_adr509_insert_route.py        # 37/37
cd api && python3 test_studio_slash_anywhere.py      # 51/51
cd api && python3 test_adr462_context_menu.py        # 49/54 — the 5 fails are PRE-EXISTING (another arc's)
cd web && node_modules/.bin/next build               # 172/172 (was 171 — a concurrent lane added a page)
```

⚠️ `test_eval_suite_gate.py` (PYTEST, not script-run) has **2 pre-existing
failures** in the `adr518-*` manifests — mutating steps with no `restore:`,
last touched at `95922dd`. Owned by the ADR-518 arc, not the insert lane.

## Owed

- **Logo-row height preset** — NOT RUN: the rig has 0 images, so the multi-pick
  has nothing to pick (its empty state was driven and teaches correctly). Needs
  an image in the workspace.
- **The in-frame right-click gesture itself** — the parent half (positioning,
  tiers, re-measure) is probed; the in-frame hit-test is inferred (opaque-origin
  ceiling, playbook §2). Operator-packet lane if it needs probing.
- ADR-581 D5 the app split · 579 D7 pane turns · **D8 "from sources…"** (583's
  named front door) · flow medium at narrow width.

---

# Part E — ADR-579/581/583: the verb-grammar arc (2026-08-19; D4 + 583 ABSORBED)

**Owner: the insert/verb-grammar lane.** The D4 build spec this part carried is
**EXECUTED** in the commit that rewrote this section — ADR-581 D4 shipped: five
registry rows (stat · comparison · timeline · person composed; logo-row cited →
ADD), kernel CSS v19 written against the v18 child-inset geometry, icons, the
logo-row multi-pick (gallery machinery, kind kept at the terminal), and the
D4.a decisions recorded in the ADR (turn-into refused for composed; UPDATE =
existing tier + tone token; delta via palette marks; columns by auto-fit).
Arc commits before it: `9b901e4` (579 ratified) · `a73bdef` (provenance
grouping) · `ea5aa52` (toolbar verbs) · `e6d2319` (verb doors) · `25e7d3f` +
`8bceaec` (581 D2/D3, renumbered from the 580 collision).

**ADR-583 landed same day (operator-ruled after the D4 discourse): a component
is a workspace FILE** (`*.component.html`, cited like a CSV/image — the
library). The colour law recut (never a raw colour/face/radius; geometry free,
homed in component files); the `component` kind re-cut to `cites="fragment"`
(fourth citation value → lands in ADD by construction); projection inlines
through the shared executable strip (live + pinned); picker lists the library;
the compose/reverse-engineer act is a posture-taught JOB on the designer (no
new app). **The catalog is CAPPED** — a new registry row needs a click-door
gap, never a component need. ⚠️ ADR-582 was TAKEN by the connector lane
mid-session — 583 verified at commit time; 584+ can collide the same way.

## Verification (the standing set)

```
cd api && python3 test_adr583_component_library.py  # 28/28
cd api && python3 test_adr581_medium_regroup.py     # 13/13
cd api && python3 test_adr579_verb_grammar.py       # 16/16
cd api && python3 test_adr509_insert_route.py       # 37
cd api && python3 test_adr538_block_classification.py  # 64/64
cd api && python3 test_adr539_vocabulary_declares.py   # 41/41
cd api && python3 test_adr462_context_menu.py       # 49/54 — the 5 fails are PRE-EXISTING at HEAD (verified in a clean worktree)
cd web && node_modules/.bin/next build              # 171/171; `pnpm` NOT on PATH
```

## Traps this arc paid for

- ⭐⭐⭐ **Verify the ADR number at COMMIT time** (`ls docs/adr | sort -V | tail`):
  two lanes shipped two different ADR-580s to main within hours; the medium regroup
  is now ADR-581. With parallel lanes live, 582+ can collide the same way.
- ⭐⭐ **Concurrent lanes commit mid-session**: stage by explicit pathspec, verify
  with `git log -S"<your string>"`. This arc's build once broke on ANOTHER lane's
  in-flight `projection.ts` backticks-in-OBJECT_SCRIPT — verify your own build in an
  isolated worktree (HEAD + your files) before diagnosing your code.
- ⭐ **Gate craft**: two of my own checks matched my own comments (the retired header
  quoted in a comment; a label in the file docstring) — anchor on WIRED handlers
  (`run(onCheck)`), and never quote retired strings in comments.

## Owed (the arc's remaining ledger)

**The click-pass this section owed is RUN** (2026-08-19, run record
`docs/evaluations/2026-08-19-adr586-one-door-click-pass-run1.md`): the D4 kinds
were driven (a Stat inserted, drawn by the kernel, delta themed by the palette
marks) and the 583 compose→cite→edit-source loop closed end to end. The
toolbar topology it describes below is ADR-586's now, not the 579 triad's.

Remaining:

- **ADR-581 D5** the Deck/Articles app split (phased; the mechanism — `apps`
  column + `register_app` — already exists).
- **ADR-579 D7** pane structured turns (seed → receipt; coarse grain only)
  · **D8** file-altitude ADD/NEW with "from sources…" (the multi-source derive,
  and ADR-583 D5's named front door).
- **Logo-row height preset** — still unexercised: the rig has 0 images.

# Part D — ADR-575: the document hears other principals before it collides

**The operator drove the deployed surface and found a logic collision.** One
screenshot carried three claims that cannot all be true:

| The surface said | Actually true |
|---|---|
| *"Someone else revised this document"* | there had been a 409 |
| **`Editing…`** (copy means *nothing is at risk*) | autosave was **suspended** |
| **`No revisions yet.`** | **four** revisions existed in production |

Their diagnosis was right and better than mine: *"most likely the way the
autosave to features and thus artifact mutation is handled."*

## ⭐⭐⭐ The turn that made this worth doing

I proposed two repairs (refresh the revision, fix the copy). **The operator
refused the symptom fix and asked for the benchmark** — *"how does Notion handle
their multi-user workspace to artifacts?"* That overturned the framing:

- **Notion never shows a "choose whose version wins" dialog for prose.** Text
  merges; only non-text properties are LWW.
- **"Last edited by" is PUSHED** — MessageStore sends a *version number*, the
  client refetches what went stale. The push is an invalidation signal, never
  content.
- **ADR-572 D7's premise was false.** It said a 409 "cannot be re-applied
  without inventing a merge". **Merging prose is the most solved problem, not
  the least** — OT and sequence CRDTs operate on flat character sequences, which
  is exactly what a `.md` is. Blocks add the *harder* problem (tree moves).
  **Fourth instance this arc of a constraint read as a ceiling.**

What blocks genuinely buy, and we cannot have: **conflict-domain partitioning**
(Figma — a conflict needs *same property, same object*; a markdown string is one
object with one property) and **stable anchors**. So we cannot have edits that
never meet. We can have edits we *hear about* before they meet.

**The conflict banner was the cost of not listening**, handed to the member as a
decision.

## What shipped

- **Migration 240** publishes `workspace_file_versions` to `supabase_realtime`.
  ⭐ Verified against production FIRST: the publication carried only
  `chat_sessions` + `session_messages`, so a subscription would have delivered
  **nothing while reporting `SUBSCRIBED`**.
- **`useFileRevisionsRealtime`** — second tenant of the primitive
  `use-session-messages-realtime.ts` already declared reusable. Server-side
  filter on `path=eq.…`.
- ⭐ **The own-write echo rule.** Every autosave INSERTs a row that comes back
  down the channel; without the filter the surface announces the member's own
  typing as a peer edit ~2s after every pause.
- **Revision-only refresh on save** — `reloadKey` would re-fire `setText` and
  destroy a keystroke landing during the refetch (the D12 shape, already shipped
  once here).
- **A peer write branches on unsaved text**: none → reload silently; unsaved →
  notify, never touch the document.
- **`Paused — resolve above`** so the header says one thing at a time.

Whole-document CAS is **unchanged** — the 409 still asks, but becomes rare.

## ⭐⭐ RLS was falsified, not assumed

In a `ROLLBACK` txn as the real principal: 6 workspaces / 1758 revisions exist;
member `2be30ac5…` sees **2 / 1517** (owner ∪ one grant); a principal with no
grants sees **0**. Publishing widens *when* a member finds out, never *what*
they may see. The migration also **refuses to publish if RLS is off**.

## ⭐⭐⭐ Gate craft — 9 falsifiers, two findings

- **19g catches a temporal-dead-zone throw that `tsc` passes CLEAN.**
  `ownRevisions` is written by `commit` and must be declared above it; the
  broken form throws on first save with a green typecheck **and** a green
  `next build`. I verified `tsc` exits 0 on it.
- **19j passed its own falsification** (NINTH this arc). It required
  `pg_publication_tables` + `RAISE EXCEPTION` anywhere in the migration —
  deleting the whole verify block left both tokens in the **sibling RLS block**.
  Now extracts the branch.

## Part D verification

```
cd api && python3 test_adr571_text_app.py            # 232/232, SCRIPT-STYLE
cd api && python3 -m pytest test_lane_artifacts.py test_adr570_member_prose_door.py -q   # 19
cd api && python3 test_adr562_app_owned_config.py    # GREEN
node web/lib/file-types/__gate_adr514_d2.mjs         # 41/41, from REPO ROOT
cd web && node_modules/.bin/next build               # 171/171, tsc clean
```

## Part D owed — a TWO-PRINCIPAL click-pass

This is the one thing gates cannot do. Two browsers, two principals:

1. B saves → A's `LAST EDITED` updates **without A reloading**; A's document
   reloads silently (A had not typed).
2. A types, then B saves → A sees the notice, **A's text is still there**,
   `Keep writing` dismisses it.
3. A saves normally → **no** peer notice (the echo rule).
4. Force a 409 → header reads `Paused — resolve above`; both exits work.
5. Network tab during typing: one WebSocket, **no** `getFile` per save.

⚠️ A peer lane committed into this tree mid-session (`9fe241c`, `1d81883` —
the latter touched `TextEditor.tsx` in the Properties FILE row, disjoint from
this work). Stage by explicit pathspec; verify with `git log -S`.

---

# Part C — ADR-572 D18: the CSV question, answered by measuring first

**The operator asked whether a CSV-sourced table is structurally impossible in
markdown. It is not — and D17's `❌` was too strong.** The refusal had collapsed
three different things into one verdict.

| | What is in the file | Verdict |
|---|---|---|
| **Snapshot** — rows as GFM + an italic source note | the ROWS | ✅ **shipped** |
| **Automatically live** | a POINTER (= Docs' `data-ref`) | ❌ unchanged |
| **`csv-table` fence** — rows + `source=`, refresh on demand | the ROWS | ⚖️ offered, **declined** |

The surviving refusal is the middle row, and it is D17's own reason: a
self-updating table must hold a pointer instead of rows, which is exactly the
empty-container shape ADR-574 names as a reason Docs paused.

## ⭐⭐⭐ The finding worth carrying

**Nothing had to be built to answer the question.** `/studio/citable` already
served the workspace's CSVs (`tables`, beside `images`), `StudioCitablePicker`
already carried the title *"Insert a table from a CSV"* for Docs, and
`GET /api/workspace/file` already returned content by path. The machinery was
shipped; only *what goes in the file* was ever open.

**Checking that BEFORE writing the refusal is what turned a feasibility claim
into a design choice.** This is D13/D15's rule applied one step earlier —
*execute the thing you are calling impossible* — and it is the third time this
arc that a recorded "limitation" was a constraint under-read.

⭐ The fence option's cost was **larger than I first stated**: our own
`MarkdownRenderer` matches `/language-(\w+)/`, which `csv-table source=…` does
not satisfy — so it needs a handler in the shared renderer *and* a canvas
widget, not one. Corrected to the operator before they chose.

## What shipped

`Table from CSV` in both doors (toolbar + `/csv`), reusing the image picker
with `cites='source'`. It writes a real GFM table under
`_From `data/q3.csv` · snapshot 2026-08-17_`.

- **A snapshot's defect is SILENCE, not staleness** — rows that look live and
  are not. The provenance line is ordinary italic prose in the document (no
  `data-*`), so a connector reads it, a member can edit it, and the freeze is a
  stated fact. Re-running the insert is the refresh.
- **One quote-aware parser, not two.** Strings had its own copy; a naive
  `split(',')` makes `"Kim, Kevin"` two cells and shifts every later column
  *silently*, and an unescaped `|` ends the cell. Folded into the pure module
  where the gate **calls** it.
- **The only insert that awaits I/O**, so it reads the document from the canvas
  at apply time — the captured string would delete typing done during the fetch
  (the D12 shape, already shipped once here). A failed read inserts **nothing**
  rather than asserting "that file is empty".

## ⭐⭐⭐ Gate craft — two more, from ten falsifiers

- **An EIGHTH check passed its own falsification.** 18k required `setCsvError`
  + the error copy; gutting the catch body left the setter in its own
  `useState`/timeout and the copy in the JSX. → now reads the **catch body**
  and asserts no insert happens there. Same class as 17f, 11h, 11L.
- **⭐⭐ 18c FAILED against CORRECT output** — it split on a bare `|`, counting
  an escaped `\|` as a cell boundary, i.e. asserting the very corruption the
  escape prevents. **The gate was wrong, not the code.** It now counts
  boundaries the way GFM does, with a control proving it measures alignment and
  not "did it split at all".

## Part C verification

```
cd api && python3 test_adr571_text_app.py            # 221/221, SCRIPT-STYLE
cd api && python3 -m pytest test_lane_artifacts.py test_adr570_member_prose_door.py -q   # 19
cd api && python3 test_adr562_app_owned_config.py    # GREEN
node web/lib/file-types/__gate_adr514_d2.mjs         # 41/41, from REPO ROOT
cd web && node_modules/.bin/next build               # 171/171, tsc clean
```

⚠️ **A transient `tsc` failure in `viewers/projection.ts` was NOT a defect** —
the peer lane was mid-write in that file and the reported error line moved
between two runs seconds apart. It landed as `9fe241c` and builds clean.
**Before diagnosing a parse error in a file you did not touch, check whether
another lane is writing it.**

## Part C owed

- **Click-pass D18**: `/csv` → pick a CSV → the rows land as a grid under the
  source note; then a CSV with a quoted comma and an embedded `|`, to see the
  escape hold on the real surface.
- Everything owed by Parts A and B below is unchanged.

---

# (earlier parts)

**Two lanes ran concurrently today and both landed.** They touch disjoint files
except `ADR-LEDGER.md`, where both entries coexist (verified). Read whichever
part matches your next task; the shared residuals are consolidated at the end
of Part A.

- **Part A — ADR-572 D10**: the Text app's second operator click-pass (`f852c82`).
- **Part B — the MCP connector audit**: ADR-563/573 (`ec58956`, `116792d`).

---

# Part A — ADR-572 D10: the operator's second click-pass

`f852c82`. **Five operator findings diagnosed, fixed, gated and pushed.** Two
were structural (a face split, and a false premise inside a ratified decision);
three were surface defects. None were visible to `next build`, to `tsc`, or to
the 128 gate checks that were green over them.

## What shipped

| # | Operator's words | What it actually was |
|---|---|---|
| 1 | *"the table render doesn't show the rendered style on the editor"* | **Two hand-maintained faces**, drifted. The table was only where it showed. |
| 2 | *"the tool bar inserts don't work for an empty line"* | One predicate bug, three call sites. |
| 3 | *"do we need a distinct save button?"* | **D5's premise about Docs was factually false.** |
| 4 | *"the ... file handling is not available. colour and highlight, also not available"* | A real gap **and** a correct-but-invisible refusal. |
| 5 | *"the design system application also please double check"* | The canvas was reading a token namespace its medium cannot have. |

New module: `web/components/text/readingFace.ts` — the ONE reading-face
declaration both renderers derive from.

## ⭐⭐⭐ The two findings worth carrying forward

**1. A refusal documented only in canon is invisible.** ADR-572 §3.1 refused
colour/highlight for good reasons and said, in writing, that it wanted the
absence *"named rather than leaving the absence to look like an oversight"* —
then named it only in the ADR. The operator opened the pane and read it as a
gap, exactly as predicted. Docs prints its refusals **in the pane**; Text now
does too. **If an absence is deliberate, the surface has to say so where the
absence is felt.**

**2. A ratified decision can rest on a false premise about a neighbouring
module.** D5 justified Text's Save button by asserting Docs "autosaves with no
CAS". Docs' `writeAndAdvance` is a queued CAS commit per operation with a 409
refetch-and-retry. Docs had everything the button was justified by and still
had no button. **Text was not more careful than Docs — it was less capable, and
it handed the member the difference as a chore** (the ADR-550→551 shape: a live,
correct mechanism in the wrong housing). Sibling of Part B's *"a ratified ADR is
evidence of a decision, never of an implementation"*: **verify the claim an ADR
makes about its neighbour, not only the decision it draws from it.**

## The parent-tag trap (D10.a), named so it is not re-set

`tags.heading1` is `t(heading)` — a **child** of `tags.heading`. Tag inheritance
flows parent→child, so a rule on the child **never** matches a node tagged with
the bare parent. `@lezer/markdown` tags a **table header** with exactly that
bare `heading`. Measured, not read:

```
heading (table header) -> NO CLASS (unstyled)
heading1               -> ͼo
content (table cell)   -> NO CLASS (unstyled)
atom (task marker)     -> NO CLASS (unstyled)
```

Same shape as D1's `prose-sm`/`prose-base` collision: **a rule that looks like
it covers the case and doesn't.**

## The type-token finding (D10.b) is subtler than "a missing token"

`--font-serif` **is** a real token — an **artifact-skin** token (`skinVars.ts`),
declared by an applied design system and parsed at runtime by `skinVarMap()`. It
exists only inside a skinned Docs artifact. **A `.md` has no skin**, so in Text
that var could never resolve; the inline fallback always won while Tailwind's
`font-serif` took its stock stack. Two faces on one document, by construction.
The fix declares an **app** type vocabulary distinct from the **artifact** one.

## ⭐⭐⭐ Gate craft — two checks passed their own falsification

Both caught only because every new check was falsified. Same error, one screen
apart:

- **11h** asserted `"var(--font-serif)" in tailwind.config.ts`. Repointing
  `serif` at `["Georgia","serif"]` left the string present **in the check's own
  explanatory comment** and in the `mono:` line beside it. → now extracts the
  per-key value.
- **11L** required `openMenuFromButton` **and** `"File actions"`. Deleting the
  `aria-label` left `title="File actions"` behind. → now matches the wired
  `onClick` and the mounted menu node.

**Fourth and fifth occurrences this arc** of an assertion matching a
*decoration* of the behaviour rather than the behaviour. (Part B hit the same
shape independently — see its gate-craft note.)

Also worth keeping: **11a's falsification is what proves it tests the table.**
Removing the plugin fails 11a while `canvas_styled` stays `True` — without that
control, 11a could have been passing on "did anything render at all".

## Part A verification

```
cd api && python3 test_adr571_text_app.py            # 160/160, SCRIPT-STYLE (pytest = false pass)
cd api && python3 -m pytest test_lane_artifacts.py test_adr570_member_prose_door.py -q   # 19
cd api && python3 test_adr562_app_owned_config.py    # script-style
node web/lib/file-types/__gate_adr514_d2.mjs         # 41/41, from REPO ROOT
cd web && node_modules/.bin/next build               # `pnpm` NOT on PATH; 171/171 pages
```

⚠️ **`__gate_adr514_d2.mjs` prints a stray `Node.js v25.1.0` line after its
summary.** It exits 0 and reports `ALL PASS — 41/41`. A `tail -3` on it looks
like a crash and is not one — **read the summary line or the exit code**, not
the tail. (Nearly reported as a false negative this session.)

## Part A owed — the D10 click-pass

Everything was gated by mounting the real components and executing the real
functions, but **not driven on production**. Drive it **cold**:

1. Open a document with a table → it reads as a **grid**, not raw pipes.
2. Caret on an **empty line** → bulleted list / task list / quote → each inserts
   its marker with the caret ready to type.
3. Type, then **stop** → the header goes `Editing…` → `Saving…` → `Saved` within
   ~2s. **There is no Save button** — confirm nothing reads as lost.
4. Properties → the **`⋯`** beside the filename → Copy link / Duplicate /
   Rename / Move / Move to Trash.
5. Properties → **Appearance** → the refusal reads as a decision, not a gap.

## Traps Part A paid for

- ⭐⭐⭐ **A green gate is not a rendered surface** (fifth time). Five defects,
  128 green checks, clean `tsc` and clean `next build` across all of them. §11
  now mounts the real canvas in jsdom, because a source grep cannot see which
  CSS class a tag resolved to.
- ⭐⭐ **Check the detector before trusting a negative** — a passing gate's
  trailing output read as a crash.
- ⭐⭐ **A concurrent lane can land work in your tree.** The MCP files present at
  this session's start were committed by the Part B lane mid-flight; `git add -A`
  would have swept them. Staged by explicit pathspec, verified with
  `git log -S"<my string>"`.

---

# Part B — the MCP connector audit, and what it produced

The audit asked: **does the connector show user
information and let you select a workspace — in the OAuth flow, and in the app?**
Four items shipped; one was **deliberately dropped after measurement**, and that
is the most reusable finding here. (Lane commits: `52b6538`, `3803c5b`,
`ec58956`, `116792d`.)

> The prior handoff (ADR-572 D8, `dbccbd1`) is **ABSORBED**. Two of its owed
> items are now CLOSED by this session — the stranded-row backfill (audited, not
> needed) and "a connector cannot NAME a workspace" (ADR-573). Its remaining
> item, the Print/PDF click-pass, is carried forward below.

## ⭐⭐⭐ The correction that opened this session — carry it

The audit's first finding was **WRONG**. I reported that MCP requests fall
through to a per-principal default with `workspace_id` unset — a real defect,
**fixed at `e0fa233` five hours before this session started**. I read the
*fixed* file and did not notice the D6 block inside it.

**A file read mid-session is evidence of that moment only.** A peer lane was
committing into the same working tree throughout. Before auditing anything, run
`git log --oneline -10` for work that landed after your context was built.

The paired lesson, from the parallel lane: **a ratified ADR is evidence of a
decision, never of an implementation.** D6 was ratified, cross-referenced,
written in the tense of intent — and never built.

## What shipped

### 1. ADR-373 D6's stranded-row backfill — AUDITED, not needed (`4b550bc`)

The prior handoff warned pre-fix connector rows were stranded and needed a
backfill. **Counted against production: they aren't.** 53 MCP-authored versions
across 4 workspaces; exactly **2 sit in a workspace their author doesn't own**,
and both are `Documents/d6-probe-2.md` — the D6 probe itself, caught by the bug
it was probing. **Zero NULL-`workspace_id` rows** on either substrate table.

⭐ **The published remediation query could never have run**: it selected
`authored_by FROM workspace_files`, and that column lives on
`workspace_file_versions`. **A query that errors on contact is worse than no
query — it reads as a discharged obligation.** Replaced with a runnable form
that also answers what the original couldn't: *does each row's workspace belong
to its author?*

No bulk UPDATE run, none warranted. Deleting the two probe rows would rewrite an
attributed revision chain (ADR-209) to tidy test files.

### 2. ADR-563 consent screen — who, where, what (`52b6538`)

The screen named the client and redirect host, then printed a **fixed sentence
wrong twice over**: *"read and write your memory"* — `memory` is pre-ADR-512
vocabulary (the unit of interop is the FILE), and a legacy `read` token can also
**DELETE** files and mint share links granting **MEMBER** access. Neither was
mentioned. ADR-563 made the tiers *enforced*; the consent surface never showed
them.

It also never said **which account** the bind would use (identity comes from the
JWT — on a shared browser, that is approving as someone else), nor **which
workspace**.

⭐ Tier definitions moved to **`api/services/mcp_scopes.py`**: the API serves the
consent screen and **cannot import `mcp_server.auth`** (py3.9 venv + py3.11-only
`mcp` SDK — the same constraint that put `delete_tokens_for_client` in
`services/principal_grants.py`). `auth.py` re-exports them. A route-side copy
would have rebuilt the pre-563 defect at the surface: a label free to disagree
with the check.

### 3. Members pane — the connection's verb tier (`3803c5b`)

The pane showed only the **path** axis (ADR-532 read/write regions). Production
carries **both** `read` (legacy full) and `files:read` tokens today, and they
rendered identically. Now its own line — merging it into the zone chips would
imply one narrows the other, and it doesn't: a connector scoped to `Documents`
can still hold a token that deletes and shares within it.

### 4. ADR-573 — the connector is bound to a workspace at consent (`ec58956`)

⭐⭐⭐ **The demand was measured, not assumed.** Exactly one production principal
reaches two workspaces: owns `My Workspace`, holds an active member grant into
the shared `yarnnn workspace`. **All three of their connector writes landed in
the owner workspace** — the commons their membership exists FOR was
*unaddressable* from the connector.

The operator now picks at consent; stamped on the code, carried to **both**
tokens, read per request.

- **A stamp NARROWS, never grants** — routed through the same
  `resolve_workspace_for_principal` the JWT door uses, and
  `principal_reaches_workspace` is uncached, so a member revoked *after* their
  token was minted loses reach on their next call.
- **NULL is not a missing value; it is "the principal's default."** All **421**
  live pre-573 tokens carry it. **No backfill** — stamping them would *freeze* a
  default that may legitimately move. Nothing repointed on deploy day.
- The binding **rides the refresh token**, or silent rotation un-binds every live
  connector with nobody acting (the ADR-386 D1.a shape).

## ⭐⭐⭐ The item I DROPPED — and why it matters more than the ones I built

I had recommended threading `workspace_id` into `AgentWorkspace`: it re-derives
on every call, while `AuthenticatedClient`'s own docstring says to derive once
and thread. It **reads** like an un-swept second path. Measured before "fixing":

- the owner branch is `lru_cache`d — a repeat call is a dict lookup, not a query;
- the uncached branch needs a principal with an active grant and **no owned
  workspace** — **production count: 0**.

~90 construction sites, zero behaviour change, zero queries saved. **Dropped**,
with the rationale and the reversing condition recorded *in
`api/services/workspace.py`* so it is not re-proposed from the shape alone.

**Measure the exposure before paying for the cleanup.** A pattern that looks
wrong is not the same as a pattern that costs anything.

## Gate craft this session paid for

- ⭐⭐⭐ **A falsifier FAILED and exposed a worthless check.** My FE grants check
  grepped `"grants"` and `".map("` independently; replacing `info.grants.map(…)`
  with `[].map(…)` left both tokens present, so **a screen rendering nothing read
  green**. Now matches the iteration over the payload. *A co-occurrence check
  cannot defend a specific site.*
- ⭐⭐ **Moving a definition can blind a gate.** ADR-563's AST loader keeps only
  `Assign` nodes, so an `import` re-export is invisible to it. It errored
  honestly — the dangerous version passes on a stale copy. It now follows the
  definitions to their new home, and calls the **shipped** `satisfied_by` rather
  than re-deriving containment (a gate that re-implements a rule can only prove
  the rule agrees with itself).
- ⭐⭐ **`bound_workspace_id` initialized inside the `try`** would raise
  `UnboundLocalError` on the stdio/static-bearer path, which takes the *except*
  branch. Caught while writing; now gated by AST.
- ⭐ **A comment can satisfy a check about behaviour.** My own explanatory comment
  quoting the banned copy failed the "copy is deleted" check. The gate was right.

## Verification that must stay green

```
cd api && /tmp/mcpenv/bin/python3.11 test_adr573_connector_workspace_binding.py  # 18/18
cd api && python3 test_adr563_consent_discloses.py                              # 23/23
cd api && /tmp/mcpenv/bin/python3.11 test_adr563_mcp_scope_enforcement.py       # 16/16
cd api && /tmp/mcpenv/bin/python3.11 test_adr373_rekey.py                       # 20/20
cd api && python3 test_adr373_sweep_spine.py                                    # 26/26
cd api && python3 test_security_2026_08_01_fixes.py                             # ALL PASS
cd web && node_modules/.bin/next build                                          # 171/171
```

⭐ Anything importing `mcp_server/*` needs **py3.11** (`/tmp/mcpenv`); the API
venv is 3.9 and dies at import on a `str | None` default annotation.
⭐ `test_adr404_member_invites.py` has **1 PRE-EXISTING failure** — verified by
stashing this work and re-running, not assumed.
⭐ Migrations run through `scripts/db/run-migration.sh` (`--dry-run` first); the
runner's exit code is **not** verification — read the live object back.

## Still OWED

1. **ADR-573 operator click-pass** — re-authorize a connector, pick the *second*
   workspace, prove the write lands there. The one principal who can drive it is
   `2be30ac5…` (owns `My Workspace`, member of `yarnnn workspace`).
2. **ADR-563 consent click-pass** — read the new screen on a real re-authorize:
   account, workspace, real tier, legacy-full warning.
3. **Print/PDF click-pass** (carried from ADR-572) — a native modal the harness
   cannot dismiss. Two minutes of operator time: Text → Export → Print/PDF →
   confirm the A4 page reads as a document.
4. **The connector is still not TOLD which workspace it is in.** ADR-533 D6
   refuses to export workspace *intent* into a third-party context window;
   whether the workspace **name** — as distinct from its mandate — should cross
   that line is **unaddressed**. Note the instructions string is composed at
   **import time**, so per-connection identity would have to be a **resource**,
   never the instructions.

## Deferred, deliberately — named so it is not re-discovered as novel

- **A per-verb `workspace` argument** was considered and rejected in ADR-573 §2:
  nine signatures change, the **model** becomes the chooser (a wrong guess writes
  to the wrong commons with full attribution), and ADR-512 D5's
  `yarnnn://workspace/…` grammar has no workspace slot.
- **`context-brief`** (carried from ADR-572) — in
  `api/services/derive_recipes.py`, targets markdown, resident `scout`, **zero FE
  consumers**. Text is its natural home; it needs its own decision about where a
  derived brief lands.
