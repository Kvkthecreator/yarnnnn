# The untitled document: scratch, Save-As, and the attributed floor

> **Status**: Discourse / audit. **No decision taken, no code written.**
> **Date**: 2026-07-20
> **Question**: should the Studio have a true "untitled scratch file that lives
> nowhere until you Save it" — the macOS unsaved-document lifecycle?
> **Touches**: Axiom 1 second clause (ADR-209 attributed substrate) · ADR-286
> single-writer-per-path · ADR-119 lifecycle (`ephemeral`) · ADR-400 Trash ·
> ADR-329 five file verbs · ADR-469 (the name is lifted)

---

## 1. Where this came from

Deferred from the 2026-07-20 OS-file-picker collapse. Having made New a Finder
gesture (name it → pick a destination → Create), the obvious next question is
whether it should be *more* like a Mac: `⌘N` gives you an untitled window that
exists nowhere until `⌘S`, and `⌘⇧S` puts it where you say.

The reason it was deferred rather than built: it looks like a modal change and
is actually a substrate question.

## 2. The apparent collision

Today every Studio artifact is a real `write_revision` from the moment of
creation. `authored-substrate.md` is unusually blunt about why that is not an
implementation detail:

> **Authored Substrate is the property, not the feature** … every byte in the
> substrate arrived attributed, purposeful, and retained, and the property
> applies uniformly to everything in `workspace_files` — **not to a curated
> subset.**

And it names *applying versioning to a curated subset* as one of the three
explicit reasons ADR-208 (the git-backend proposal) was **withdrawn**:

> **It applied versioning to a curated subset.** … Scoping versioning to a
> subset meant designing an inclusion test and maintaining it forever.

A naive untitled-until-saved document is exactly that: a class of bytes that
exist, that the member can type into and lose, and that are **outside the
ledger** until a Save promotes them. That is a second, unattributed substrate
with an inclusion test — the shape canon has already rejected once.

**So the naive form is closed.** But that is not the end of the question,
because the premise "it must live outside the ledger" turns out to be false.

## 3. The finding that changes the question

**A scratch lifecycle already exists, is ratified, and is live.**

`workspace_files.lifecycle` has carried `ephemeral` since migration 116
(ADR-119). It is not vestigial:

- `services/workspace.py::_infer_lifecycle` returns `ephemeral` for `/working/`
  and `/user_shared/` paths (`:135-142`).
- `AgentWorkspace.list()` **excludes ephemeral by default** (`:250`) — scratch
  is already invisible to ordinary reads without being invisible to the ledger.
- `routes/documents.py:893` writes `lifecycle="ephemeral"` today.
- Trash is already **archive-not-erase** (ADR-400/ADR-209): `DELETE /documents`
  archives; "Trash is a view, not an eraser."

So the substrate already models *"this exists, it is attributed, and it is not
part of your standing work."* An untitled document does not need to escape the
ledger to feel unsaved. **It needs to be `ephemeral` and unlisted.**

This reframes the whole question:

> Not *"how do we let bytes exist unattributed?"* — canon says never —
> but *"is `ephemeral` + Save-As-is-a-Move the macOS feel, at zero new
> substrate concepts?"*

### The corroborating detail, and the caution

The scheduler's own docstring records that the ephemeral **cleanup sweep was
removed**:

> *Workspace Cleanup and Agent Hygiene removed — neither had a creation trigger
> and no ephemeral files accumulate in prod (audited 2026-05-02).*

Read carefully, this cuts both ways and the honest reading matters:

- **For**: the mechanism is dormant precisely because *nothing creates
  ephemeral files*. Giving it a creation trigger is what it was built for.
- **Against**: the 2026-05-02 audit removed the reaper. If scratch documents
  start being created, **they accumulate forever** unless the sweep is restored.
  Reinstating a reaper is a real cost that must be counted in, not waved at —
  and a reaper that deletes member-typed content is a delicate thing to get
  right (see §6 Q3).

## 4. What "Save" would actually mean

If a scratch document is a real attributed file at a scratch path, then the
member-facing verbs map onto primitives that **already exist** (ADR-329's five
file verbs), with no new mechanism:

| macOS gesture | What it is here |
|---|---|
| `⌘N` → untitled window | `WriteFile` at a scratch path, `lifecycle='ephemeral'`, unlisted |
| typing | ordinary attributed revisions on that path |
| `⌘S` / Save | `lifecycle: ephemeral → active` (it joins your work) |
| `⌘⇧S` / Save As… | **`MoveFile`** to the picked meaning path + `→ active` |
| close without saving | leave it ephemeral; the reaper collects it |
| "unsaved changes?" | *there are none* — every keystroke was already retained |

The last row is the interesting one. In macOS the dialog exists because
unsaved bytes are **volatile**. Here they never are. So the honest port of the
gesture is not "do you want to save?" but something closer to **"keep this?"** —
and a system that never loses your work should probably say so rather than
imitate an anxiety it doesn't have.

**This is the strongest argument for the whole direction**: the destination
picker built on 2026-07-20 is already a Save-As dialog. It picks a folder and
composes a path. Save-As would reuse it verbatim.

## 5. The three real objections

Not fatal, but each needs an answer before code.

### (a) The scratch path is still a path — and the key problem is fresh

A scratch file needs *some* path. `operation/untitled/document.html` collides
for the second scratch document, which is precisely the injectivity failure
[ADR-469](../adr/ADR-469-the-name-is-lifted-the-path-is-a-key.md) just fixed.
`services/naming.py::disambiguate` already solves it (`untitled`, `untitled-2`)
— but the scratch region and its key policy must be **declared**, not
improvised, or this reintroduces the bug one week after closing it.

### (b) `MoveFile` currently eats metadata — and Save-As *is* a MoveFile

ADR-459 §5 records a live bug: `primitives/workspace.py:1176` selects only
`path, content`, so a move lands `content_type`, `content_url`, `lifecycle`, and
`metadata` at DB default and **overwrites `summary`** with `"Moved from …"`.

ADR-459 was immune (the kind rides in content). **Save-As is not**: it is a
move whose entire purpose includes carrying `lifecycle` across. Under today's
`MoveFile`, Save-As would silently reset the very column the design depends on.

**This is a hard prerequisite, not a footnote.** Fixing `MoveFile` (widen the
SELECT, thread every metadata column, stop clobbering `summary`) is a standalone
bug fix that must land first. It is independently worth doing — it also sits
under ADR-427's binary work, where a moved PNG loses its content-type today.

### (c) Does this earn its complexity?

The current New flow is: name it → Enter. That is **one field and one
keystroke**, and the 2026-07-20 collapse made the destination a picked default.
The macOS gesture exists because naming-before-writing is friction; it is not
obvious that friction is present here.

A defensible smaller read: **the gap is not "no scratch," it is "New demands a
name."** If the real complaint is being asked to name a thing before knowing
what it is, the minimal fix is to let the name be *optional* at create — the
artifact opens as "Untitled", and naming it later is the crumb rename that
already exists. That is a fraction of the work and touches no lifecycle.

## 6. What must be resolved before any code

1. **Is scratch a region or a lifecycle?** `/working/` already infers ephemeral
   by path. Placing scratch there is free but puts member-facing documents in a
   machine-scratch namespace. The alternative is `lifecycle` set explicitly at
   create, with meaning-placement from birth. (DP33's instinct — *category into
   data, namespace for meaning* — favours the latter.)
2. **Does an ephemeral artifact appear on the Studio landing?** If yes it isn't
   scratch; if no, a member can lose track of a document they were typing into.
   A "Drafts" affordance may be the honest answer — but that is a surface, and
   ADR-340 DP29 says compose few.
3. **What reaps it, and is deleting member-typed content ever acceptable?**
   A 24h sweep on a file someone typed into is a different act from sweeping
   agent scratch. Trash-instead-of-delete (ADR-400) is the obvious softening,
   but then scratch never actually goes away and (2) worsens.
4. **Is `MoveFile`'s metadata bug fixed first?** Non-negotiable per (b).
5. **Is the simpler read in §5(c) sufficient?** Optional-name-at-create should
   be explicitly rejected before the lifecycle work is justified.

## 7. Where the weight falls

**The naive temp-file is closed** — bytes outside the ledger contradict Axiom 1's
second clause and repeat ADR-208's withdrawn "curated subset."

**The ledger-native version is open and cheaper than it looked**, because
`ephemeral` + unlisted-by-default + Trash-not-erase + the five file verbs
already exist. Save-As is a `MoveFile` and a lifecycle flip; the picker is
built. No new primitive, no new table, no new column.

**But it is not obviously worth doing.** The honest sequence is:

1. Fix `MoveFile`'s metadata loss — needed regardless, unblocks ADR-427 too.
2. Try **optional-name-at-create** (§5(c)) — a fraction of the work; if the felt
   friction is naming-before-knowing, this dissolves the question.
3. Only if that proves insufficient, write the ADR for ephemeral-scratch +
   Save-As, and count the restored reaper as part of its cost.

## 8. Explicitly not claimed

- Not claimed that scratch documents are needed. The felt problem was never
  stated beyond "it would be more macOS-like."
- Not claimed the `ephemeral` machinery is ready. Its reaper was deliberately
  removed and would have to come back, carefully.
- Not claimed §5(c) is sufficient — only that it is untested and much cheaper,
  and that skipping past it would be building the expensive thing first.

## 9. The one-line statement

**Nothing here needs to escape the ledger — an unsaved document is not
unattributed bytes, it is an attributed file that hasn't been given a place
yet; so "Save As" is a Move, and the only question left is whether the member
ever actually wanted one.**
