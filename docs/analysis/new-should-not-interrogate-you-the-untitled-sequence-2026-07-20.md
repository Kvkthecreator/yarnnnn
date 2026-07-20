# New should not interrogate you — the untitled sequence

> **Status**: Discourse / design direction. **No code written.** Supersedes the
> framing (not the findings) of
> [the-untitled-document-scratch-save-as-and-the-attributed-floor](the-untitled-document-scratch-save-as-and-the-attributed-floor-2026-07-20.md),
> which treated this as a storage question. It is a **sequence** question.
> **Date**: 2026-07-20
> **Touches**: ADR-452 (the landing) · ADR-469 (the name is lifted) · ADR-329
> (five file verbs) · Axiom 1 second clause · ADR-119 `ephemeral`

---

## 1. The felt problem, stated correctly

Not *"we lack scratch storage."* The operator's words:

> the user experience associating this with sequence of New and file entry that
> feels un-like existing OS, other doc processors which have the blank or empty
> state handling in line with the "untitled" or "unsaved" consideration

**New interrogates you before it gives you anything.** Pages, Word, Docs, Keynote
all open a blank thing immediately; the name falls out of the work, usually at
the first save or never. Ours demands a name *and* a destination as the price of
admission — the artifact does not exist until you have answered two questions
about a thing you have not made yet.

That is a sequence defect, and it is felt at the exact moment of highest
intent — the moment someone decided to make something.

The prior note's §5(c) called this "the cheaper read" and filed it as a
fallback. That was the wrong weighting. **It is the thesis.** Scratch lifecycle
is one possible mechanism underneath it, not the goal.

## 2. What is already built

The system already has a complete, coherent concept of an untitled artifact.
Nothing needs inventing — the modal simply refuses to let anyone reach it.

| Piece | Where | State |
|---|---|---|
| Untitled placeholder in every layout | `studio.py:200/242/275/314` — `<h1>Untitled document</h1>`, `Untitled deck`, … | **live** |
| Skeleton builds without a name | `build_skeleton(layout, title=None)` — *"Absent, the placeholder stands"* (`:1231`) | **live** |
| `<title>` gets the placeholder too | `build_skeleton` writes `<title>{placeholder}</title>` | **live** |
| The placeholder is *recognised* as untouched | `_SCAFFOLD_TITLES` is DERIVED from the scaffolds (`:1166`); `_is_placeholder_title` gates every retitle | **live** |
| Naming later is a first-class gesture | the crumb rename — `commitRename`, Enter/blur | **live** |
| The crumb can arm on mount | `StudioSurface.tsx:1699` — *"the crumb arms as the workbench mounts"* | **live** |
| The name reads back from content | ADR-469's lift — `artifact_name(path, content)` | **live (yesterday)** |

Verified end-to-end: `build_skeleton('document')` with no title yields
`<title>Untitled document</title>`, and `artifact_name(path, html)` returns
**"Untitled document"** — through yesterday's lift, with no fallback to the path
slug. **The untitled artifact already renders correctly everywhere.**

The single missing link is that `NewArtifactModal` will not submit without a
name (`canCreate = !!name.trim()`), and `create_artifact` composes the path
from that name.

## 3. Why ADR-469 is what makes this possible

This would not have been clean a week ago. Under ADR-459 D2 the name was
*derived from the folder slug*, so an unnamed artifact had nowhere to get a name
from — `operation/untitled/document.html` would read back "Untitled", which
happens to look right but only by coincidence of the slug fallback. Naming it
later meant **moving the folder**, so the name and the location were the same
act.

ADR-469 severed them. The name lives in `<title>`; the path is only a key. That
means:

- an artifact can be born **named "Untitled document" and placed** at a
  disambiguated key, with both facts honest;
- naming it later is a **retitle** (one attributed revision, content-only) —
  it does not have to move anything;
- the key never has to be beautiful, because nobody reads it.

**The sequence fix is a dividend of the naming fix.** That is a good sign about
the ordering: the first-principles correction came first, and the UX it unlocks
follows without strain.

## 4. The design: three doors, one artifact

The OS models this as *three ways in, converging on one object.* Ours can too,
without a new substrate concept:

1. **New → immediate.** Click a type, get a workbench. Named "Untitled ‹kind›",
   placed at a disambiguated key under the default region. The crumb arms (the
   mechanism at `:1699` already exists) so the name is *offered*, never demanded
   — type over it or ignore it and start working.
2. **New → deliberate.** The member who arrives knowing ("IR deck v3, in
   clients/") still gets today's modal. This is not a fallback; the deliberate
   path is real and the picker built on 2026-07-20 serves it well.
3. **Name it later.** The crumb rename, already live, already one revision.

The macOS reading: (1) is `⌘N`, (2) is New-from-template-with-a-name, (3) is
renaming in the title bar. None of them is "unsaved."

### What "Save" honestly means here

There are never unsaved changes — every keystroke is already an attributed
revision. So the macOS Save gesture has **no honest port**, and imitating it
would be theatre: a dialog implying volatility the substrate does not have.

The truthful analogues are:

- **Save As…** → `MoveFile` to a picked path (the destination picker is
  already a Save-As dialog).
- **Keep / Discard** → only meaningful if untitled artifacts are `ephemeral`.

Which raises the one genuinely open question.

## 5. The open question: is an untitled artifact `ephemeral`?

Two coherent designs. This is the decision, and it is the operator's.

### Design A — Untitled is just *active* work with a default name

Born `active` at a disambiguated key. Appears on the landing immediately as
"Untitled document". Naming is optional forever. Cleanup is the Trash verb the
member already has.

- **For**: zero new machinery — literally an optional-name change at create
  plus arming the crumb. No reaper. No second visibility rule. Every existing
  surface already handles it (proven in §2).
- **Against**: abandoned starts accumulate as ordinary files. A member who
  clicks New three times exploring gets three "Untitled document" rows they
  must trash by hand.
- **Honest note**: this is *exactly* how Notion behaves, and Notion is the
  closest comparable. Untitled pages persist and you delete the ones you meant
  not to make.

### Design B — Untitled is `ephemeral` until it earns a place

Born `ephemeral` (the ADR-119 lifecycle, already live and already excluded from
default listings). Naming it — or an explicit Keep — flips it to `active`.

- **For**: abandoned starts self-clean; matches "unsaved" most closely.
- **Against**: needs a **reaper restored** (deliberately removed —
  `unified_scheduler` docstring, audited 2026-05-02: *"no ephemeral files
  accumulate in prod"*), and a reaper that deletes member-typed content is a
  delicate thing. Also needs a second visibility rule (a Drafts affordance),
  which ADR-340 DP29 counsels against — *compose few*. And it can lose work:
  the member who typed for an hour without naming is exactly the person the
  attributed floor exists to protect.

**Where the weight falls: A, with B available later.** A is a strictly smaller
change that delivers the whole felt problem — New stops interrogating you.
B only adds *automatic disposal*, which is a different complaint (clutter), and
one nobody has actually reported. If clutter shows up, B is still reachable
because `ephemeral` is a column value, not an architecture: the artifact is born
`active` today and could be born `ephemeral` later with no change to how it is
named, placed, read, or attributed.

That is what makes A future-proof rather than a shortcut — it does not foreclose
B, and it introduces nothing that would have to be undone.

## 6. What is still a hard prerequisite

Unchanged from the prior note, and it binds **Design B only** (and any
Save-As-as-Move work):

**`MoveFile` eats metadata.** Verified live: `primitives/workspace.py:1193`
selects only `path, content`; `:1221` clobbers `summary` with `"Moved from …"`;
`_upsert_workspace_file` writes only non-`None` keys, so an insert lands
`lifecycle`, `content_type`, `content_url`, `metadata` at DB default. A Save-As
that must carry `lifecycle` across would silently reset the very column the
design depends on.

**Design A does not touch `MoveFile`** — that is a further point in its favour.
The bug remains worth fixing regardless (a moved PNG loses its content-type
today, under ADR-427's binary work).

## 7. What must be decided before code

1. **A or B?** (§5) — the only architectural fork.
2. **Does an untitled artifact land in the default region, or a `drafts/`
   one?** DP33's instinct — *category into data, namespace for meaning* —
   favours the default region with the state carried as data, not as a folder.
3. **Does the crumb arm focused-and-selected, or merely focused?** Selected
   means typing replaces "Untitled document" wholesale (Finder's new-folder
   behaviour). This is the difference between "offered" and "demanded" being
   felt correctly.
4. **Does the deliberate modal stay reachable, and from where?** It should —
   but if New is now immediate, the named path needs its own affordance.

## 8. Explicitly not claimed

- Not claimed that Design B is wrong — only that it solves a complaint (clutter)
  that has not been reported, at meaningfully higher cost, and that A does not
  foreclose it.
- Not claimed this is only a frontend change. It is small on both sides
  (optional name at create; arm the crumb), but it *is* both.
- Not claimed the deliberate modal should go away. Two doors is the OS pattern,
  not a transition state.

## 9. The one-line statement

**A blank document is not an unsaved one — it is a named-by-default one; so New
should hand over the workbench and let the name arrive from the work, which is
possible now only because the name stopped living in the path.**
