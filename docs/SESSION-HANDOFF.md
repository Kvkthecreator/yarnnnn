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

## RESOLVED 2026-08-21 — the "unattributed destruction" item is WITHDRAWN

The three items previously listed here as "needs a DECISION" were re-examined
with the operator on 2026-08-21. **Item 1 was over-framed and is withdrawn;
items 2 and 3 dissolve with it.** Recorded so a future session does not
re-inherit the framing as an open gap.

**1. "Destructive paths are unattributed." WITHDRAWN.** The attribution axiom
("every change is signed by whoever made it") is about the COMMONS AND ITS
CONTENTS — so collaborators can trust what they read and can walk its history.
Purge is the operator ENDING the thing; the axiom does not extend to "the act
of ending the record is itself a record". A delete is supposed to leave
nothing — that is what makes it a real delete rather than a soft one.

The proposed fix was arguably worse than the gap: a durable out-of-workspace
destruction log is RETAINED DATA ABOUT A WORKSPACE AFTER THE OPERATOR ASKED
FOR IT TO BE GONE — in tension with our own privacy page ("Nothing expires on
a schedule…") and something a GDPR-style erasure request would make us
justify rather than celebrate.

The practical need it was really serving — "can support tell whether the
operator cleared it, or whether we lost it?" — is ALREADY MET server-side:
`workspace_delete.py:162,177` log actor + workspace on soft-delete/restore,
and `workspace_purge.py` logs the L2 scope. No table, no retention, no UI.

**2. L1 orphans revision chains** (160 live). Correct-as-designed for a light
L1 and not worth a schema change; if the copy overpromises, that is a copy
fix, not an architecture one.

**3. `execution_events` destroyed by purge.** Precisely: L2 (clear workspace)
PRESERVES it — only the ADR-578 FULL PURGE destroys it, forced by a `NO
ACTION` FK, and that path ENDS the workspace. A cost ledger for a workspace
that no longer exists has no consumer, so this is not in tension with ADR-291.
(An earlier note conflated the L2 and purge paths.)

**Current verified state:** purge/clear owner-gated (`workspaces.owner_id` or
an explicit `workspace:clear` scope; prod: 0 grants carry it) + typed
confirmation on the irreversible acts; delete reversible with restore; billing
history survives L2. A normal, complete SaaS deletion story. Nothing to build.

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

---

# Part H — ADR-592: an app declares how far along it is (2026-08-21)

## What shipped

`stage` — one field per kernel surface row (`internal | search-only | beta |
primary`, `services/app_stage.py`), from which `launcher_tier` +
`default_pinned` are DERIVED. Enforced at `kernel_surface_entries()`, the same
chokepoint ADR-375 §6 #4 uses for the steward.

- **Radar DELETED** — service, router, surface, registry row, app registration,
  API namespace, scheduler lane, its gate. Deleted rather than staged because
  its sweep was **metered spend on a clock**.
- **Docs `stage: internal`** — implementation intact (Studio parameterized),
  exposure gone. `/docs` → `/text`, `/radar` → `/files`, both stubs.

## The finding this came from

ADR-574 D2 declared Docs paused on 2026-08-17. Four days later it was still
fully reachable. Two mechanisms:
- `maybeReseedDock` only fires on **byte-equality** with the previous default,
  so any curated Dock keeps the icon permanently.
- `search-only` hides a tile at rest and nothing else — the route rendered,
  flat search matched `summary`, and a `document` double-click opened it.

Hence: `internal` removes the row from the **served roster** (nav is
backend-driven), which is the only spelling that reaches a curated Dock.

## ⚠️ The obligation `internal` carries

`middleware.ts` derives `SURFACE_PREFIXES` from the roster, so **a slug that
leaves the roster leaves the auth gate with it**. An internal app's route must
be a redirect stub AND hand-listed in the middleware. I nearly shipped this
wrong: a stash cycle silently reverted the middleware edit and the gate passed
green against an unprotected `/docs` until a falsifier caught it.

## Measured

- Gates: `test_adr592_app_stage.py` 35/35, falsified 3 ways (un-hide docs;
  unprotect the route; flatten the stage default — the last reproduces a real
  bug I hit, which promoted 27 surfaces to the Dock).
- 574 → 18/18, 518 → 36/36, 562/569/571/472/558 green, FE build green.
- **Pre-existing red, NOT introduced** (measured at `b0d03a6`):
  `test_adr297_phase1` 186/1 and `test_adr338_surface_registry_parity` 12/3 —
  every failure names `autonomy`.
- ADR-574 D3's recorded trap does NOT fire: `resolvedMode` comes from the
  LAYOUT vocabulary, not the app, and `document` still declares `mode: flow`.

## OWED

- **Operator (KVK)**: the Radar substrate. Workspace
  `d5b9029b-bd4e-4757-9fcb-e2b139fd4913` — 21 briefs under
  `operation/ai-frontier/briefs/` + `_radar.yaml`/`_watch_signal.yaml` there and
  under `operation/fundraising/deck-new-test/`. Workspace
  `bf5b25a9-477f-462e-b7f3-65812f489411` — `operation/desk-e2e/` declarations.
  Deleting the topic folder takes the briefs; delete only the `_*.yaml` to keep
  them. (The code change already stops the spend.)
- **Click-pass**: `/docs` + `/radar` redirect while logged in; logged-out both
  bounce to login (the auth pairing); no Docs/Radar icon on a CURATED Dock.
- **Staging envs** — discussed, not started. Separate ADR; needs a call on
  Supabase branching vs. a second project.
- `kind='radar'` rows in `tasks` are inert; harmless, could be swept later.

---

# Part H — a paged surface always names the page (2026-08-28)

Audit of a live turn: the Editor was asked to split "this slide", said **slide
6** for the slide the member was standing on (7), and then made the **right
edit anyway**. Both halves have one cause — it was never told where the member
was standing, so the number was narration and `data-block-id` was the operation.

## What shipped

Three layers had to line up for the silence; the fix holds each.

| Layer | Defect | Fix |
|---|---|---|
| Runtime | `reportScroll` bound to the `scroll` event + `stageShow` only — a deck the member never scrolled reported **nothing** | report on ARRIVAL (`setTimeout(reportScroll, 0)`) + after a restore |
| Declaration | with no selection and no viewport, StudioSurface fell to `document` scope — false on a paged artifact, not merely quiet | page grain is the FLOOR when `resolvedMode === 'paged'` |
| Renderer | `build_focus_line` renders `document` as `""` | **unchanged — correct**, and what makes the layer above load-bearing |

Judgment taken: **incident, not re-architecture.** ADR-522's declare-don't-scrape
contract is sound — Text and Strings hardcode `viewport: null` because they have
no page unit, and their `document` scope is truthful silence. Studio is the only
surface that can be silently wrong. The alternatives were all worse: enumerating
slides into the posture puts deck structure in the kernel (ADR-222); scraping the
viewport is the ADR-398 D2 locator ADR-522 replaced; storing slide ordinals is a
second source of truth against DOM order, walking back `3abfe20`.

`resolvedMode`, never `layoutMode` — the latter defaults to `'flow'` until the
vocabulary answers, so it would assert a page grain for an artifact not yet known
to have one (the ADR-480 reasoning at the same seam).

## The gate the old one couldn't be

`test_paged_focus_is_never_silent.py` — falsified **5 ways**, each red on its own
assertion: drop the arrival report · drop the restore report · revert the paged
floor (reproduces the original defect) · read `layoutMode` instead of
`resolvedMode` · drop `resolvedMode` from the dep array.

⭐⭐⭐ **`test_adr522_focus_declaration.py` certified the defect's own shape.** Its
assertion `"D5 document scope renders nothing (no finer grain to report)"` is
true for Text/Strings and **false for a deck** — and every focus dict it builds
already has `page_index` set, so it never exercised the state the incident was.
Rationale corrected in place; the renderer assertion stays (it pins the RENDERER,
and the declaration's obligation is now gated separately).

⭐ Two gate defects found in the writing: a 2000-char lookback window
false-flagged the restore call (proximity ≠ scope — now brace depth); and the
runtime region is **inside a template literal**, so backticks in my comment
terminated the string and broke the build. FE build green in an isolated
worktree (HEAD + my 2 files); the first "failure" was a missing `.env.local`,
not the change.

## OWED

- **Click-pass** (not driven in a browser): open a deck scrolled to a mid slide
  WITHOUT scrolling, ask "split this slide", confirm the Editor names the right
  one. The mechanism is gated; the browser path is not.
- **Two index spaces feed one `page_index`** — `currentSlideIndex()` counts
  `section.slide`; the pointer runtime's `pageIndexOf` counts
  `STRUCTURAL_PAGE_SEL` (`'section.slide, :is(body, main, article) > section'`).
  They agree on a pure deck and diverge on one bare `<section>` — so "slide 7"
  could mean different slides depending on whether the member clicked or
  scrolled. The rail uses the wide selector, the in-canvas `7 / 7` counter the
  narrow one. Deliberately NOT bundled here: collapsing them touches the rail,
  the stage counter and `arrangedPageAt`'s fallback ladder — a measured change.
- **Block scope drops the slide** — `build_focus_line`'s block branch names the
  block and never mentions `page_index`, though the FE populates it. A real gap,
  but a grain-composition question, not this viewport one.
- **Page scope sends no id** — `StudioSurface.tsx` hardcodes `id: null` for page
  grain, yet pages carry `data-block-id` since ADR-519. The one grain that gets a
  number gets no stable address — the same position-vs-identity failure
  `3abfe20` closed inside `artifactOps`.

---

# Part I — the Update door is deleted; the re-arrange comes home (2026-08-28)

**ADR-616.** Operator: *"completely delete the update button and its subfeatures.
any absorption required… streamlined and singular implementation discipline."*

## What the audit found before cutting

Update rendered **six act rows** over five rungs. Five were `onOpenPane(scope)` —
and the mount was `{ void sc; setRightTab('design'); }`. **A five-rung ladder
whose answer nothing read.** `StudioDesignTab` derives its own scope
(`scopeOf`, :1417), so those rows were one action wearing six labels.

⭐⭐⭐ **ADR-589's premise had expired.** Its §1 defect ("typography/palette/design
system have no entrance") became false independently: the pane renders them at
`document` scope whenever nothing is selected. It built a second door to a room
that already had one; ADR-613 then removed the judged verbs, leaving a
target-disambiguator for acts with nothing to disambiguate.

⭐⭐⭐ **The one row that could NOT go**: `handleApplyArrangement` had exactly one
caller and had already moved twice (out of the pane 2026-07-21, out of the
toolbar by ADR-589 D3). Add's gallery is a **different verb** — `onPick` →
`insertArrangement` (new page) vs re-lay this one, carrying content, dissolving
groups, running the ADR-479 placement judgment. Deleting blind would have taken
slide re-arrangement out of the product with nothing failing at build time.

## Shipped

- **D1** — `StudioUpdateMenu.tsx` + `updateLadder.ts` deleted; button, `onUpdateBlock`,
  `hasBlockSelection`, `hasPageAnchor`, `planning`, `updateMenu` state,
  `openUpdateDoor`, `retargetToRung` and the gesture's `!updateMenu` clause gone.
  `PaneScope`/`selection.ts` **survive** — the pane always derived its own.
- **D2** — the gallery is home in the pane's PAGE scope, above Layout.
  `arrangementCarryNote` **moved** with its one consumer (un-exported).
  `planning`/"Refining…" followed the act it describes.
- **D4** — the sparkle measures the **canvas column**, not `window.innerWidth`.
  This is the OUTER half of what `5abdce9` fixed on the inside. Both hosts
  supply it (Slides: `canvasWrapRef`; Text: `view.scrollDOM`).

## Gates

`test_adr616_update_door_deleted.py` — falsified **5 ways**: the act loses its
mount · the sparkle reverts to window arithmetic · the carry-note is left in two
homes · a row discards its scope again (`void sc`) · a second mount appears.
The one-mount check **globs the whole authoring tree** — a site-specific check
cannot see a second mount reappear elsewhere.

⭐⭐⭐ `test_adr589_update_matrix.py` **deleted with its subject**. Two dependent
gates read `StudioUpdateMenu.tsx` and would have passed **vacuously** (or
crashed) once the file was gone — `test_adr586_one_door.py` and
`test_adr612_judged_gesture.py` now assert the absence directly. ADR-612's gate
caught a real break: it pinned the suppression string `!slash && !citePicker &&
!updateMenu && !ctxMenu`; the roster shrank, so it now asserts the RULE plus
`"updateMenu" not in surface`.

FE build green (isolated worktree, HEAD + 7 files); tsc clean; ADR-589 marked
superseded with the reason.

## OWED

- **Click-pass** — not driven. Check: re-arrange from the pane (incl. a slotless
  arrangement's carry note and the "Refining…" state); the sparkle beside a deck
  selection with the pane OPEN, and again with it CLOSED; Text's sparkle at the
  right margin of the reading column.
- **Right-click menu clean-up** — operator-scoped as sequential, deliberately
  not bundled here.
- **ADR-589 D6's cited cell** (`edit source · swap citation · refresh pin`) was
  never built and is still unbuilt. It is owed against the PANE now, not the
  deleted door.
- **`document` rung's affordance** — the rail was the only *labelled* route to
  artifact scope from a live selection. The state stays reachable (empty-canvas
  click, `onPointClear`) and the pane names what to do there; if the operator
  wants it labelled, that is a pane-side crumb, not a door.

---

# Part J — the "+ Add" that did nothing, and the menu's families (2026-08-28)

Operator: *"when i created a new slide, the +Add like section was created, but
then the +Add doesn't work at all… most likely mismatch in implementation."*
Right on both counts.

## The dead "+ Add" — one attribute, three layers

ADR-544 D2 migrated the region grain `data-slot` → `data-area`. D7 states the
rule the migration left: **every consumer reads BOTH**. Every consumer did —
except `normalizeStructure`'s container predicate (`artifactOps.ts` Pass B),
which tested `data-slot` alone and **predated the migration** (written
2026-08-09; the rest of that file learned `data-area` on 08-19).

⭐⭐⭐ That straggler was **the pass that MINTS IDS**. So it did not mis-label —
it decided whether a region could be ADDRESSED:
- kernel emits only `data-area` → every **EMPTY** Area went unstamped;
- a **FILLED** region was caught by the other clause and worked — which is why
  it read as "new slides are broken" rather than as one attribute;
- the runtime draws "+ Add" **only inside an empty region** — exactly the
  unstamped set;
- `onAddHere` then returned **silently** for want of a `containerId`, never
  reaching `applyOp`'s honest shared error.

⭐⭐⭐ **An existing gate REQUIRED the defect**: `test_adr466_mode_native.py`
asserted the literal `"el.hasAttribute('data-slot')" in ops` under the label
*"an EMPTY declared region still gets identity"* — enforcing the bug and
blocking the fix, while reading GREEN. Re-anchored to the invariant.

**Shipped**: `REGION_SEL` in `structureLabels.ts` (one spelling); Pass B and
`countGroupsOnPage` (a 2nd straggler — Areas counted as authored groups, so the
carry note promised a false ungrouping) both read it; 4 hand-spelled pairs
converged; the runtime draws the BUTTON only where an id exists (bounds stay
wider — a button that does nothing is worse than no button); `onAddHere`
reports instead of returning bare.

## ADR-619 — the menu's families (operator, mid-turn)

Copy nests with Duplicate/Delete (it was stranded above Paste, whose subject is
the CLIPBOARD not the block). `Update ▸` deleted in full — three unrelated
families (Turn into · Move · Bring) under a verb naming none, each already
self-gated, now flat. Rewrite added as a **second entrance** to the floating
gesture's identical workflow; `seedRewrite` is the ONE producer, the menu reads
its own context target (never the rect — a rect-keyed row is inert on message
timing, the same silent class as above).

⭐⭐ Two gates had pinned SPELLINGS: 586's `<Flyout open={` **>= 3** (with a
comment citing the ADR-584 lesson against hand-kept counts — then failing on the
2nd correct deletion), and 612's `"Rewrite…" not in block_menu`. Both
re-anchored to invariants, not relaxed.

⭐ **ADR-618 was claimed by a peer lane mid-session** — renumbered to 619.

## Gates

`test_region_grain_is_one_selector.py` (falsified 5×) ·
`test_adr619_menu_families.py` (falsified 5×). ⭐Two of my own assertions were
too weak and were caught BY falsifying: a substring check that the guard's own
attribute-setter satisfied, and an ordering check against a mention that moved
with the guard (fixed by asserting the guard appears exactly once).

FE build green (isolated worktree, HEAD + 5 files); tsc clean; `test_adr466`
holds at its **10 pre-existing** failures.

## OWED

- **Click-pass**: create a slide → "+ Add" in an empty region inserts text;
  a MEDIA region still routes to the picker; right-click shows Copy/Duplicate/
  Delete together, flat Turn into/Move/Bring, and Rewrite seeding the composer
  identically to the sparkle.
- **The Add surface is NOT one mechanism** (mapped, not fixed): 5 doors, 6
  terminal ops, 4 target-resolution schemes, 2 taxonomies of one vocabulary
  (`categorizeBlockRows` for toolbar+right-click vs `groupBlockRows` for slash).
  ⭐**New-slide rail uses `anchor` (selection only) while the block rails beside
  it use `resolveInsertTarget()` (with viewport fallback)** — same popover, two
  answers to "where": on a deck paged to slide 2 with nothing selected, a block
  lands on slide 2 and a New slide lands at the END. ⭐**Paste ignores
  page/slide anchoring** and lands on the last slide. Both are real, both
  deliberately out of this scope.
- **~18 other silent no-op guards** on the insert paths (each an early `return`
  with no feedback); only `onAddHere` was fixed here.

---

# Part K — ADR-620: Compose is Rewrite at slide grain (2026-08-28)

Operator: *"the Add related details seem to only scaffold skeleton components…
similar to rewrite, we could have AI related compose"* → then *"can we have a
dedicated component… something that feels more first class and visual."*

## The finding

`+ Add` stamps registry fragments whose bytes are LITERAL (`42%`, `label`).
Correct for a CATALOG gesture — the member knows the noun — and unable to serve
an INTENT. Rewrite is judged/seeded/receipted and stops at the block.

⭐⭐⭐ **Not the re-arrange re-framed** (the operator's proposal, checked and
corrected): `applyArrangementPlan` MOVES existing nodes (`returnToFlow(b);
target.appendChild(b)`) — a PERMUTATION, which is exactly why it can promise
total coverage and fall back to a mechanical ladder. A compose has no such
floor, and its planner resolves **Designer** deliberately ("machinery that
happens to plan layout, not the desk's voice") while a member-facing slide act
is the **Editor**. Re-arrange is the narrowest member of the family, not the
frame for it.

## ⭐⭐⭐ Built, then DELETED before shipping

A first cut built `/studio/compose/plan` + a validator + `applyComposePlan` — a
faithful mirror of ADR-479. **A second write path** (ADR-462 D1). The lane
ALREADY has EditFile-with-anchor, the block grammar in the posture, and one
attributed write. Deleted whole; Compose is Rewrite's machinery unchanged.

## Shipped

- **D1** `compose` = 4th seed verb, slide grain. Page's own id + `page_index`.
- **D2** the colleague writes through the lane. No endpoint, no applier.
- **D3** `remove` is the member's PERMISSION, riding the seed, rendered in the
  frame in **BOTH** directions (an absent instruction is not a prohibition).
- **D4** the chip GROWS A BODY (slide's blocks by kind + the D3 toggle), never
  a modal — a modal covers the slide being described and has no transcript.
  ⭐The DOOR is the **pane's page scope**, not a floating sparkle: the runtime
  reports a rect for blocks and ranges, never a page.
- **D5** `+ Add` untouched — the catalog of things that EXIST.
- Extracted `_meter_plan` (one billing invariant, one home).

## ⭐⭐ Latent defect surfaced

`_seed_line` read the page grain as `page is not None and not bid` — "no block
id" standing in for the grain, true ONLY because pre-620 nothing at page grain
carried one. A composed slide carries the page's id (ADR-519), so it would have
said **"the slide block"**. Fixed in the frame AND the chip (they must read
identically before/after Send) and gated together.

## Gates

`test_adr620_compose_at_slide_grain.py`, falsified **5×** (additive case goes
silent · noun proxy restored · a second producer · plan endpoint returns · chip
noun diverges). ⭐**The gate caught my own D2 violation**: my first `composeSlide`
called `seedComposer` directly — a second producer — and it went red.

⭐⭐ `test_adr579_d7_structured_turns.py` was **PRE-EXISTING RED** (verified at
HEAD): it pinned the door ROSTER (`3× ask` + `rewrite` + `check`) and ADR-613
deleted Ask/Check from Slides. Failing since 613, unread. Re-anchored to D7's
actual claim (a door passes a TYPED target).

FE build green (isolated worktree); tsc clean; prompt ratchets pass.

## OWED

- **Click-pass** — the whole feature is undriven. Select a slide → Compose → the
  chip shows its blocks + the toggle → Send empty (judgment) and with an intent;
  check the slide changes in place and the transcript reads "slide N".
- **Receipt card** — D4 names one; the transcript currently renders the composed
  turn like any lane write (`artifactWrite="none"` in Studio, so the canvas IS
  the receipt). Decide whether a page-grain card earns its place.
- **Text has no Compose** — the verb is medium-agnostic but only Slides declares
  a door. A section-grain compose in Text is the obvious sibling.
