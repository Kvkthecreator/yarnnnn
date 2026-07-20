# ADR-470 — New hands over the workbench

> **Status**: Implemented (2026-07-20)
> **Depends on**: [ADR-469](ADR-469-the-name-is-lifted-the-path-is-a-key.md) — this is only possible because the name stopped living in the path
> **Amends**: ADR-452 (the landing's creation flow)
> **Preserves**: Axiom 1 second clause · ADR-286 · ADR-329 · ADR-340 DP29 · DP33
> **Derivation**: [`docs/analysis/new-should-not-interrogate-you-the-untitled-sequence-2026-07-20.md`](../analysis/new-should-not-interrogate-you-the-untitled-sequence-2026-07-20.md)

---

## 1. The defect

New **interrogated you before it gave you anything.** Clicking a shape opened a
modal demanding a name *and* a destination; the artifact did not exist until you
had answered two questions about a thing you had not made yet.

Every doc processor — Pages, Word, Docs, Keynote, Notion — opens a blank thing
immediately and lets the name fall out of the work. The operator's report:

> the sequence of New and file entry … feels un-like existing OS, other doc
> processors which have the blank or empty state handling in line with the
> "untitled" or "unsaved" consideration

This is a **sequence** defect, not a storage one, and it was felt at the moment
of highest intent — the moment someone decided to make something.

## 2. What was already built

The system already had a complete concept of an untitled artifact. The modal was
the only thing preventing anyone from reaching it:

- every layout ships `<h1>Untitled document|deck|article|page</h1>`;
- `build_skeleton(layout, title=None)` already falls back to it — *"Absent, the
  placeholder stands"*;
- `<title>` gets the placeholder too;
- `_SCAFFOLD_TITLES` is **derived** from those scaffolds, so `set_artifact_title`
  already distinguishes an untouched placeholder from authored words;
- the crumb rename is live and **already arms on mount**
  (`StudioSurface.tsx` — *"the crumb arms as the workbench mounts"*).

The single missing link was `canCreate = !!name.trim()`.

## 3. Why ADR-469 is the enabler

Under ADR-459 D2 the name was derived from the folder slug, so naming later
meant **moving the folder** — name and location were one act, and an unnamed
artifact had nowhere to get a name from.

ADR-469 severed them: the name lives in `<title>`, the path is only a key. So an
artifact can be born **named "Untitled document" and placed**, both facts
honest, and naming it later is a content-only retitle that moves nothing.

**The sequence fix is a dividend of the naming fix.**

## 4. Decisions

### D1 — Two doors, one artifact

| Door | Gesture | What happens |
|---|---|---|
| **Immediate** | pick a shape in `+ New` | created at once, workbench opens, crumb armed |
| **Deliberate** | `+ New` → "Name it first…" | the modal — shape + name + destination |
| **Learn-from** | `+ New` → "Learn from…" | unchanged; its source *is* its name |

The deliberate door is a **peer row, not a toll on every creation.** Arriving
knowing is the rarer intent; it keeps a first-class path, and the destination
picker built the same day serves it well.

### D2 — No name means the skeleton's placeholder stands. Nothing is invented.

`create_artifact` with no `name` leaves `template["skeleton"]` untouched.

**This is load-bearing, not stylistic.** Writing an invented name (e.g. one
derived from the path, the previous fallback) makes the `<h1>` look *authored*,
and `set_artifact_title`'s placeholder guard then **refuses to replace it** — the
member's later rename would silently no-op on the h1, permanently. Verified:

```
placeholder "Untitled document" → rename → "My real name"        ✅ replaced
invented    "Untitled document 2" → rename → "Untitled document 2" ❌ frozen
```

Leaving the placeholder is what keeps the later rename an **offer**.

### D3 — The server places it, reusing ADR-469's one key rule

`_untitled_path()` builds the key with the same `path_slug` + `disambiguate` the
named door uses, against the region's existing meaning folders:
`untitled-document`, `untitled-document-2`, … Per shape, so a deck and a
document never contend.

One placement authority — the FE never invents a scratch path, so there is no
second rule to drift.

### D4 — It lands in the ordinary region, not `drafts/`

An untitled artifact is real work that hasn't been named yet, not a separate
class of thing. DP33: the state is **data** (the placeholder title it carries),
the namespace stays **meaning**. Naming it later is a retitle; moving it is the
member's Move verb. Neither is forced by where it was born.

### D5 — Untitled is `active`, not `ephemeral`

An untitled artifact is an ordinary file: visible on the landing, cleaned up
with the Trash verb the member already has.

`ephemeral` (ADR-119) was considered and **deferred, not rejected**. It only adds
*automatic disposal* — a different complaint (clutter) that nobody has reported —
and it costs a restored reaper (deliberately removed, audited 2026-05-02), a
second visibility rule against DP29's *compose few*, and the risk of deleting
work someone typed for an hour without naming.

It stays reachable: `ephemeral` is a column value, not an architecture. Nothing
here would have to be undone to adopt it.

## 5. What "Save" means here — and why there is no Save

There are never unsaved changes: every keystroke is already an attributed
revision (Axiom 1 second clause). A Save dialog would be **theatre**, implying a
volatility the substrate does not have.

The honest analogues already exist: **Save As…** is `MoveFile` (the destination
picker is already that dialog), and **Discard** is Trash. Neither needed
building here.

## 6. What is deliberately not built

- **No `drafts/` namespace, no scratch region** (D4).
- **No `ephemeral` lifecycle for artifacts** (D5) — deferred, not foreclosed.
- **No Save / "unsaved changes?" dialog** (§5).
- **No reaper.** Nothing here creates files that need sweeping.
- **`MoveFile` untouched.** Its verified metadata-eating bug (ADR-459 §5) binds
  Design B and Save-As-as-Move; Design A never moves anything, so this ADR does
  not depend on that fix. It remains worth fixing on its own.

## 7. Falsifiers

1. `+ New → Document` opens a workbench with no dialog in between.
2. It reads "Untitled document" on the landing and in the crumb.
3. Typing in the armed crumb renames it — the h1 follows, not frozen.
4. Three consecutive News produce three distinct paths, no collision.
5. `+ New → Name it first…` still offers shape + name + destination.
6. A produced untitled path contains no `//`.
7. Learn-from artifacts carry their source's name, not a slug round-trip.

## 8. The one-line statement

**A blank document is not an unsaved one — it is a named-by-default one; so New
hands over the workbench and lets the name arrive from the work, which is
possible only because the name stopped living in the path.**
