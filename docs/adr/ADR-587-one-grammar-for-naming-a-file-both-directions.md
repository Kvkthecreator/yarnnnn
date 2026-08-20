# ADR-587 — One grammar for naming a file, in both directions

**Status**: **Accepted** (2026-08-20, operator-ratified). The operator commissioned the audit
with a thesis and a question, and explicitly asked for the question to be reasoned before the
thesis was built — *"above is thesis, and my initial proposal so reason with me further before
applying in full"* — then ruled on the framing: *"streamline this to a single conceptual framing
approach which i believe is the discipline your emphasizing we take."*
**Date**: 2026-08-20
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)
**Dimension**: Channel (Axiom 6 — the doors a file travels through, and whether a name that
leaves through one can come back through another)

**Amends**:
- **ADR-512 D5** — the handle grammar is unchanged as *grammar*. What changes is its **standing**:
  D5 said the emit half was "promoted from app-local prose to kernel grammar," but shipped it as
  an affordance of two apps and a parser on one side of the boundary. This ADR finishes the
  promotion D5's own text announced.

**Preserves**:
- **ADR-534 §3** (share links are not chased through mutations) — reaffirmed, and §4 below
  records *why* the streamlining request does not reopen it.
- **ADR-512 D6** (reach vs egress render as visibly different classes) — the reason a handle and
  a share link stay two objects, §4.
- **ADR-297 D19.2** (in-surface selection is component state, never a URL write) — the arrival
  door still drains its param; this ADR only normalizes what arrives.
- **ADR-448** (a reference edge is a historical fact, never a live foreign key).

---

## 1. Context — the app emits a name it cannot read

A file in this workspace has a canonical cross-boundary name, ratified in ADR-512 D5:

> `yarnnn://workspace/{workspace-relative-path}`

`parse_file_reference` accepts three honest spellings of it — the handle, the ledger's absolute
`/workspace/…` form, and the bare relative path — and refuses everything else. That function is
correct, tested, and lives in `api/services/mcp_composition.py`.

**It has no counterpart in the browser.** Measured, 2026-08-20: `yarnnn://` appears in
`web/app`, `web/components`, `web/lib` exactly **twice**, and both are EMITTERS
(`StudioShareExport`, `TextExport`). Zero parsers.

So the loop is broken on its return leg, and the break is invisible because each half works:

| Direction | Status before this ADR |
|---|---|
| yarnnn → AI: copy a name for the file | Built, in two apps |
| AI → yarnnn: resolve a name back to the file | **Absent** |

An operator who worked in ChatGPT through the connector, and now wants that file in front of
them, holds a perfectly good name that nothing in the app will accept. The Files
surface — the one place that shows *every* file, including the ones no app claims — could
neither produce a name nor consume one.

### 1.1 Three defects, one cause

The audit found the surface expression of that gap in three places, and they are the same defect
seen from three angles:

**(a) The path was on screen, in the wrong register.** The Files row subtitle read
`Workspace write: marketing/creative-brief.md`. That is not a path field — it is
`workspace_files.summary`, written by the substrate as `f"Workspace write: {path}"`
(`services/primitives/workspace.py`). The API **already judges this string a leak**:
`_artifact_title` in `routes/workspace.py` strips it with the docstring *"leaks paths to the
operator… so the Home reads like a Mac, not a workbench"* — but only on the Home slot. The tree
endpoint served it raw. The same string, judged a leak on one surface and shipped verbatim on
another; and inconsistently, since a folder row (`Workspace edit:`, or nothing at all) rendered
differently from a file row.

**(b) Properties showed a path field that was not the path.** `NodeDetailsPanel`'s Location row
ran `node.path.replace(/\/[^/]*$/, '')` — **stripping the filename** — and rendered the parent
directory, monospaced and muted, with no copy affordance. It read as "here is the path" and was
not one.

**(c) The arrival door accepted one spelling of four.** `?files.path=` is a real, working
mechanism — "THE ONE ARRIVAL DOOR" — but it handed its param to `openPath` verbatim, which
matches `workspace_files.path` exactly. Of the four spellings an operator plausibly holds, only
the absolute one resolved; a handle, a bare relative path, and the bare `?path=` spelling all
fell through to an empty selection. Silently: Files then renders its Recents, which looks like a
working page.

**(d), found while fixing (c):** the bare `?path=` param was still EMITTED in three places —
`memory/page.tsx`'s redirect, `tp/SystemCard.tsx`'s output link, and `lib/routes.ts`'s
documentation of the stub. Surface params are slug-namespaced (`scopeParamKey`), and the
reconciler leaves a non-matching param untouched, so all three had been dead links.

### 1.2 The drift that proves the duplication was already costing

The AI-reference sentence shipped hand-written in two apps. They had **already diverged**: Studio
told every external AI that `` `trace` shows who changed it``; Text said `` `history` ``. The
roster (`_INTEROP_VERBS`) has ten verbs and `trace` is not one of them — it was a pre-ADR-543
name. Studio's clipboard had been instructing hosts to call a verb that does not exist.

Neither copy was wrong when written. One was updated and the other was not, which is what a
duplicated sentence does.

---

## 2. The single framing

> **A file's name is one grammar, and every door speaks it — in both directions.**

Everything below is that sentence applied. The grammar was already ratified (ADR-512 D5); what
was missing was that it be *the* grammar rather than one app's string, and that it be **read** as
well as written.

Three consequences, which are the decisions:

1. If it is one grammar, it has one implementation per runtime — not one per surface. (D1)
2. If a door speaks it, the door shows it and lets the operator take it. (D2)
3. If it is spoken in both directions, a name that arrives is parsed by the same grammar that
   emitted it. (D3, D4)

---

## 3. Decisions

### D1 — One grammar module per runtime, and the sentence is built once

`web/lib/interop/fileHandle.ts` is the browser half of the ADR-512 D5 grammar: `parseFileReference`
(the three spellings and the refusals), `toWorkspacePath`, `relPath`, `formatFileReference`, and
`formatAiReference` — the handle wrapped in host guidance.

**A twin, not a fetch.** Resolving a name is pure string grammar with no workspace state in it,
and the surfaces that need it (the arrival door, quick-open) need it *before* a request is in
flight. Round-tripping to the server to learn whether a path is well-formed would make every
deep-link wait on the network to discover it was spelled correctly.

The parity obligation this creates is discharged by a gate that **drives both implementations
over one table**, refusals included (§5), rather than trusting that two functions which look
alike behave alike. They did not: the falsification run had the TS half accepting
`../../etc/passwd` while Python refused it.

Studio and Text now call `formatAiReference`. The two hand-written sentences are deleted, and
with them the `trace`/`history` divergence.

### D2 — The path is an affordance, and it REPLACES the machine string

On the Files surface the path becomes a first-class, copyable field:

- **The row subtitle** carries the workspace-relative path — **substituting** for
  `Workspace write: {path}`, not sitting beside it. No new row, no new column, one fewer machine
  leak. (The WHERE column stays empty in folder listings, which is correct and deliberate: every
  row lives in the same folder, and the grid geometry must not change per caller.)
- **Properties** gains a **Path** row — the file's actual path, not its parent — rendered in
  `CopyField`, and the misleading Location row is gone.
- **`CopyField`** is lifted out of `ShareDialog`'s private `linkField`, preserving the part that
  matters: **on a clipboard rejection it selects the text instead of reporting success.** A Copy
  button that swallows a denied-permission rejection tells the operator it copied while the
  clipboard still holds something else — the incorrect-success class this codebase keeps paying
  for.

Server-side, `_plain_summary` drops the machine summary at the tree endpoint, and
`_MACHINE_SUMMARY_PREFIXES` is now shared with `_artifact_title` — one place to add a prefix, two
readers. (`_artifact_title` had been missing `"Workspace edit:"` entirely.)

**Dropped, not re-titled.** The Home slot substitutes a titleized slug because an artifact card
needs *some* title. A tree node already has its name and now its path, so the honest move is to
serve nothing rather than invent prose. An operator- or agent-authored summary passes through
untouched.

**The default Copy is the bare relative path**, with the handle-plus-guidance as the labeled
second act (`Copy AI reference`, unchanged in Studio and Text). Rationale: the relative path is
the form useful in the most destinations — quick-open, a chat message, a connector's `open`,
which accepts it — while the handle-plus-sentence is specifically shaped for pasting into
another AI's chat box. Since D3 makes the app parse all three spellings, the choice of *emitted*
default costs nothing in reachability.

### D3 — A name that arrives is parsed by the grammar that emitted it

The Files arrival door normalizes through `toWorkspacePath` before opening. All three spellings
resolve; a refusal (another scheme, `..`) opens nothing rather than guessing.

The three dead `?path=` emitters are corrected to `files.path`. This is a plain bug fix that
predates the interop question and is fixed here because the audit found it.

### D4 — Quick-open: the operator can knock on the door

The arrival door was fully built and reachable only by hand-writing a query string. The Launcher
— already the Spotlight surface for surfaces — accepts a pasted path and opens the file.

**Detection is the grammar itself, not a heuristic**: the input must parse as a file reference
*and* look like a path rather than a word (a separator or an extension). A bare word stays a
surface search, so ordinary launching is untouched. When a path is present it wins on Enter: an
operator who pasted a file name meant that file, not whichever surface fuzzy-matched it.

### D6 — The share sheet names the file, not its leaf (amended 2026-08-21)

Operator-confirmed after the Files surface click-passed: *"maybe similar, same
mechanism for front end should be repeated for the share modal for both studio,
txt apps."*

The sheet's subtitle rendered `target.name` — in the operator's screenshot,
`deck.html`. A leaf is the one string that does NOT identify a file; a workspace
holds many `deck.html`. And the dialog **already held the path**: `path` drives
`createShare` and the active-link filter. It was simply never shown.

`ShareDialog` is ONE component mounted by Files, Studio and Text, so the fix is
made once and all three surfaces gain it — which is why the request "repeat it
for studio and txt" resolves to a single edit rather than three. The gate
asserts all three still mount the shared dialog, because a surface that grew its
own sheet would silently stop inheriting this.

**The handle is deliberately NOT offered here.** This sheet is where a GRANT is
minted; the handle is an ADDRESS carrying no authorization. Putting both
spellings in the one surface whose job is capability is exactly the
reach-vs-egress blur §4 refuses. The handle stays on Export ("Copy AI
reference"). The gate enforces the refusal **against comment-stripped source** —
its first cut went red against correct code by matching the comment that
explains the refusal.

### D7 — The identifying line is the path, on every face, for both kinds (amended 2026-08-21)

Operator-directed, and the framing is the decision: *"treat my request as to infer
the consistent and streamline implementation instead of just a one-off approach."*

D2 fixed the Files **list** row and **file** Properties. Audited as a matrix, the
surface was answering the same question three different ways:

| Face | File | Folder |
|---|---|---|
| List row subtitle | path (D2) | path (D2) |
| **Grid tile subtext** | **attribution** | **attribution → renders EMPTY** |
| **Properties** | Path row (D2) | **nothing** |

Two defects fall out of that table, and neither is cosmetic:

**The grid tile spent its one line on attribution.** The list view already has a
dedicated AUTHOR column, so the grid was duplicating it at a different altitude
— and for a FOLDER it rendered nothing at all: folders are derived from path
segments and carry no `authored_by`, so `formatAuthorLabel` returned null and the
tile showed a bare accent dot with no text (operator-observed: three folder
tiles, three empty dots). The path is the one line that is true for both kinds.

**Folder Properties never named the folder.** It opened straight into "Recent
changes in this folder", so the one surface that exists to answer *what is this*
was silent about identity for half the objects it describes. A folder is as
addressable as a file — it is what `list` takes, what a move targets, what an
operator pastes to a colleague.

**The rule, stated so a fourth face inherits it**: *wherever the Files surface
shows an object, the identifying line under its name is its path — every face,
both kinds, through the one `CopyField` and the one grammar.* Attribution keeps
its own dedicated slot (the AUTHOR column) rather than borrowing the identity
line. The gate checks this as a MATRIX, not as three spot-checks, so a new face
that skips it fails rather than quietly disagreeing.

---

## 4. The rejected alternative, recorded — merging the handle into the share flow

The operator's opening question was whether to *"streamline the URL link creation flow with the
file path."* **Refused, and the refusal is the load-bearing part of this ADR**, because it is the
turn a future session will re-derive as an obvious convenience.

A handle and a share link look similar and are different objects:

| | `yarnnn://workspace/marketing/gtm.md` | `https://yarnnn.com/s/7HWee…` |
|---|---|---|
| What it is | an **address** | a **grant** |
| Carries authorization | **no** — reach is always the caller's own grant (ADR-512 D5 §6) | **yes** — accepting mints a membership |
| Who can resolve it | a principal already holding reach | anyone holding the token |
| Cost of pasting it in the wrong place | zero | **access to the commons widened** |
| Lifecycle | none — it is a name | minted · revocable · expiring · listed |

Merging their creation flows would put a grant-minting act one click from a naming act. That is
exactly the reach-vs-egress flattening **ADR-512 D6** warns "launders the moat." The two stay two
surfaces: Share mints capability; Copy hands over a name.

**And the stale-link state is not a defect to streamline away.** The screenshot that opened this
audit showed *"This file has been moved, renamed, or deleted"* — which is **ADR-534 D4 working**.
§3 of that ADR records that its own first draft proposed chasing paths through moves and the
operator overruled it, on three converging arguments (the web's `404`/`410` precedent; ADR-448
already ruling the same way for the derive edge; DP34's anti-silent-drop clause). Binding to file
identity is additionally *unavailable*: `MoveFile` is write-new-delete-old, so
`workspace_files.id` does not survive a move.

Nothing in this ADR touches that. A name that no longer names anything says so.

**Noted, not taken** (a real observation, deliberately out of scope): `MoveFile` *does* record
its destination — as free text in the tombstone's revision message
(`f"MoveFile: to {abs_dst}"`). A forwarding pointer exists but is not machine-addressable without
parsing prose. Whether that should become structured is a substrate question, not a naming one,
and it is not needed by anything here.

**Also named, not taken**: a real file search. The exact-path capability exists
(`SearchFiles match='exact'`) but has no HTTP route and no client method, and the MCP `search`
verb's `_naturalize_query` strips `/` before matching, so a pasted path there is worse than
useless. Quick-open (D4) resolves a name the operator *holds*; finding a file they cannot name is
a different question and wants its own ADR.

---

## 5. The gate

`api/test_adr587_handle_grammar_parity.py` — 17 checks.

The load-bearing one is **parity, driven**: the TS module is executed under node over the same
table the Python is executed over, refusals included, and the two result vectors must be equal.
A source comparison could not have caught what falsification caught — removing the traversal
guard from the TS half left both functions looking correct and disagreeing on
`../../etc/passwd`.

The remaining checks defend the arrival normalization (D3), the absence of any `/files?path=`
emitter (D3 — and it skips comment lines, so describing the deleted behavior stays legal), the
machine-summary drop (D4-summary, driven not grepped), and the single-sentence rule — including
that **every verb the sentence names is on the parsed `_INTEROP_VERBS` roster**, which is the
check that would have caught `trace`.

The roster is parsed, never pinned as a count: a hand-kept number reads growth as a violation
(the ADR-584 lesson).

**Every check was falsified** — broken deliberately, observed to fail, restored from a backup
copy.

---

## 6. What is owed

- **The click-pass.** The Files surface **list-view** copy affordance is operator-confirmed
  working (2026-08-21). Still undriven: the grid tile and folder Properties (D7), the share
  sheet's path field on Studio and Text (D6), and pasting a handle into the Launcher.
- **Not mine, observed in passing**: `files_arrival_door.mjs` A7 reports 8/9 ("found 3" arrival
  handlers) at baseline — introduced by concurrent work on `files/page.tsx`, red before this
  arc's D6/D7 changes and unaffected by them.
- **The round-trip through a real host.** Copy an AI reference from Studio, paste it into
  ChatGPT/Claude.ai, confirm `open` resolves it, then bring the path back through quick-open.
  That is the loop this ADR exists to close, and it has been proven in parts, not end to end.
- The two pre-existing `test_adr297_d196` failures on the **agents** surface (24 passed / 2
  failed at baseline, unrelated to this arc) remain open.
