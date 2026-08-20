# ADR-588 — Folders are first-class, and the told-name is an accepted address

**Status**: Accepted + Implemented
**Date**: 2026-08-20
**Supersedes**: nothing. Amends **ADR-424 D2**'s implementation (the create-folder
route seeded a README; that seed is deleted) and closes a live instance of the
**ADR-373 D6** incorrect-success class on the interop write door.
**Related**: ADR-424 (the pure-OS filesystem model + peer folders) · ADR-209
(`write_revision` is the single write path) · ADR-373 D6 / ADR-573 / ADR-584 (the
incorrect-success class: 200 + attributed + went somewhere the principal did not
mean) · ADR-563 (guard at the chokepoint, never at call sites) · ADR-388 D1 (the
derived roots tree) · ADR-395 (`is_upload_projection`, the hide-at-presentation
precedent) · ADR-427 D5 (content type) · ADR-571 (`.md` routes to the Text app).

---

## 1. The root cause: folders do not exist in the substrate

`workspace_files` stores leaf paths. **A folder exists iff a file exists under its
path prefix**, and the tree is *derived* from those paths (`_build_tree`,
`routes/workspace.py`). There is no directory row, no parent pointer, no
`workspace_folders` table. That is a legitimate design — it is how a path-addressed
store works, and it is why `list` could honestly tell a participant "in a
path-addressed store a folder exists only through its files."

But it means **an empty folder is inexpressible**, and two defects fell out of that
one fact. They look unrelated in a bug tracker. They are the same fact twice.

## 2. Defect A — the README seed signs the operator's name to a document

`create_folder` could not make a folder, so it made a *file* and let the folder
appear as a side effect:

```python
result = await execute_primitive(auth, "WriteFile", {
    "path": f"{rel_folder}/README.md",
    "content": f"# {leaf}\n\n_This folder was created to hold work about {leaf}._\n",
    "authored_by": "operator",
})
return {"success": True, "path": abs_folder, "seeded": abs_readme}
```

Three things are wrong, in increasing order of seriousness.

**It ejects the operator out of Files.** The route returned `seeded`, and the
surface did `if (r?.seeded) openPath(r.seeded)`. Since **ADR-571** routed `.md` to
the Text app, *creating a folder opened an editor*. No operating system opens a
text editor on `mkdir`. The comment beside that call still described the
pre-ADR-571 behaviour ("falls through to inline") — it had been stale since the
Text app shipped, and stale prose is how a wrong behaviour keeps looking
intentional.

**The prose is a guess.** "_This folder was created to hold work about {leaf}._" is
the system inventing a claim about the operator's intent from a slugified folder
name.

**It is a false signature in the attribution ledger.** `authored_by: "operator"`
on a document the operator never wrote, with a real revision, a real blob, and a
real parent pointer — indistinguishable at every read from something they typed.
This is the one invariant the product is built on: *every mutation is attributed,
and the attribution is true* (FOUNDATIONS; ADR-209). A workaround that lies in that
ledger is more expensive than the inconvenience it works around, however small the
lie. It was also **1,928 rows of otherwise-clean attribution** away from being the
only false one.

## 3. Defect B — the told-name is not an accepted address

This is the important one.

`PARTICIPANT_FILESYSTEM_MODEL` (`services/workspace_paths.py`, ADR-424 D1) is the
**singular** prose that teaches every LLM participant the filesystem. It says,
verbatim:

> Two homes are provided: **Documents** (where authored work lives when it has no
> more specific home) and **Downloads** (what arrived from outside…)

Those are *display* names. The kernel paths are `operation/` and `inbound/`. **And
nothing translated between them at any door.** A participant that used the exact
vocabulary this codebase handed it wrote to a path that did not mean what it was
told it meant.

This is not hypothetical. From the production ledger:

```
yarnnn:mcp:claude.ai | save via interop: Documents/adr572-clickpass-brief.md | 2026-08-16
yarnnn:mcp:claude.ai | save via interop: Documents/adr373-d6-roundtrip.md    | 2026-08-17
```

Claude.ai wrote to `Documents/` believing it was the home it had been told about.
The write **succeeded**. It was **attributed**. It created a *real* top-level root
`/workspace/Documents/` holding three live files — which `root_metadata()`
title-cases back into the display name **"Documents"**, rendering an exact visual
twin of `operation/` beside it in the operator's tree.

That is the **ADR-373 D6 incorrect-success class** precisely: 200, attributed,
landed somewhere real, went somewhere the principal did not mean, and *no signal
anywhere*. `Downloads` → `inbound/` had the identical hole; it simply had not been
hit yet.

The connector arc has now produced this class three times (D6 itself, ADR-573's
silent degrade, ADR-584's unobservable fallback). Each time the lesson is the same:
**a door that accepts a name it does not honour is worse than one that refuses**,
because the failure is invisible on both sides.

---

## Decisions

### D1 — A folder is a row. The README seed is deleted.

An empty folder becomes expressible as a real `workspace_files` row at **the
folder's own path**, carrying the filesystem's own directory MIME type:

```
path         = "/workspace/deals/acme/"     ← trailing slash, always
content_type = "inode/directory"
content      = ""
```

Written through **`write_revision`** — the ADR-209 single write path — not through
the `WriteFile` primitive, whose empty-content guard correctly refuses a 0-byte
write (a directory has no body, so the marker is exactly the write that guard
exists to block *for documents*). It is attributed to the operator because the
operator really did perform this act: **naming a folder**. That is precisely the
difference from the deleted seed, which attributed a *document* they never wrote.

**The trailing slash is load-bearing, not cosmetic.** It makes a marker
unambiguously not-a-file at every path-shaped consumer, including ones that never
learn the `content_type`:

- `git_export._repo_rel` already returns `None` for `rel.endswith("/")` — the
  export excludes markers *for free*, and can never write a zero-byte blob named
  `acme` that collides with the real git tree entry `acme/`. That collision would
  be tree corruption, not a cosmetic bug.
- `UserMemory.list` (non-recursive) already emits `"acme/"` for such a row — it
  reads as a directory, which is what it is.
- A file and its folder can never collide on the unique `(workspace_id, path)`
  index: `…/acme` and `…/acme/` are distinct keys.

`is_folder_marker(path, content_type)` is the **singular predicate** every consumer
filters on — the `is_upload_projection` precedent (ADR-395): hide at
**presentation**, never at authorization. Swept and filtered: the tree
(`_build_tree` registers a marker as a **folder node**, never a file), roots
(a marker makes a root *exist* without inflating the operator-facing `file_count`),
MCP `list` and `open`, `ListFiles`, `QueryKnowledge`, `is_searchable_root`,
`is_embed_eligible`, `UserMemory.list`, `AgentWorkspace.list`, Recents, Trash, the
working-memory domain index, the scaffold entity scan, and the radar brief shelf.

A marker is a **convenience, not a requirement**: a folder holding files still
exists through those files with no marker row, exactly as before, and the two
spellings converge on one tree node. Deleting the last file in a marked folder
leaves the folder standing — which is Finder/Explorer grammar, and the point.

### D2 — The told-name resolves. It does not refuse.

`HOME_ALIASES` maps what the participant is **told** to what the kernel **has**:
`Documents/…` → `operation/…`, `Downloads/…` → `inbound/…`, case-insensitively,
**first path segment only**.

Applied at **`parse_file_reference`** — the one chokepoint every interop verb
resolves a path through, read and write alike. This is the ADR-563
`resolve_request_client` discipline: *guard at the chokepoint, never at the call
sites*. Applying it there rather than at the save door is what makes the round-trip
hold — a participant that wrote `Documents/x.md` can `open`, `edit`, `move` and
`history` it back **by the same name it used**.

**Resolve, not refuse.** Refusing would break live connectors mid-flight, and it
would be the wrong answer besides: the participant used the exact vocabulary this
codebase handed it, so honouring that name is correct. The resolution is **not
silent** — the write lands at the real path, and the real path is what the
response, the ledger, and the operator's tree all show.

Only the first segment aliases. A nested `operation/Documents/notes.md` is an
ordinary folder someone named, exactly as `~/Projects/Documents` is on any real
machine; aliasing it would be the same category of silent misroute this closes.

The alias keys must stay in sync with what the model actually says — the gate
asserts each key appears verbatim in `PARTICIPANT_FILESYSTEM_MODEL`, so renaming a
home in that prose without updating the map **fails the gate** rather than quietly
re-opening the hole.

### D3 — A top-level folder may not wear a home's display name.

`create_folder` refuses a **top-level** folder named `Documents` / `Downloads` (or
any `WORKSPACE_ROOTS` display name *or* kernel root name) with an honest,
operator-facing reason:

> Documents already exists — What you and your agents author and keep — your work,
> context, reports. Pick another name, or put this folder inside Documents.

Never a bare "invalid name", which would leave the operator guessing why a
perfectly ordinary word was refused. Derived from `WORKSPACE_ROOTS`, never
hand-listed: a home added there is reserved automatically. The kernel root name is
reserved too — hand-creating `operation/` would merge a new folder into the real
home invisibly.

**Only depth 1 collides.** A nested `Projects/Documents/` is allowed.

---

## What this does NOT do

- **No migration of live data.** The three files already at `/workspace/Documents/`
  and the root itself are untouched by this ADR; relocating them is a separate,
  operator-run act.
- **No `workspace_folders` table.** Folders remain derived; the marker is a row in
  the existing substrate, through the existing write path.
- **No new primitive, no new verb, no flag.** The seed is deleted outright — no
  shim, no dual path (CLAUDE.md §2, Singular Implementation).
- **No folder-delete verb.** Trashing a folder is not currently a shipped
  affordance; the marker filters defensively in Trash, but the verb is future work.

## Gates

- `api/test_adr588_folder_markers_and_home_aliases.py` — 42/42. Drives
  `_build_tree` over real marker rows rather than grepping it; executes the alias
  resolver over every accepted reference spelling; asserts each alias key appears
  in the prose that promises it.
- `api/test_adr424_pure_os_filesystem.py` — **re-anchored, not routed around**. Its
  `create-folder seeds via WriteFile … README.md` assertion had encoded the
  workaround as canon; it now pins the marker and the *absence* of the seed.

⭐ **A gate assertion can match its own comment.** The first cut of both gates went
red against *correct* code because the docstring explaining the deletion contains
the word "README", and the comment describing the reserved-name check contains its
function name. Both now strip comments and docstrings before any text test, and pin
**mechanism** (`reserved_top_level_folder_reason(`, `write_revision`) rather than a
spelling. This is the recorded never-pin-a-spelling lesson, hit twice in one arc.

Every assertion was falsified against pre-fix code: the alias removed from the
chokepoint, `_build_tree`'s marker branch disabled, the reserved-name refusal
deleted, `is_folder_marker` stubbed to `False`, the `compose_list` filter dropped,
and the full README seed restored verbatim — each went red, each restored green.
