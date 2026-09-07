# How system-level documents are exposed — an audit

**2026-09-07.** Prompted by the operator: *"I see them surface on existing apps
like text, and files surface to be editable, moveable. I think this goes against
our canon and approach."*

The observation is right, the conclusion is right for one of the two surfaces,
and the reason is not the one it looks like. Files is sound *by design*. Text is
where the canon is actually broken, and one route family in `documents.py` is
broken worse than either.

---

## 0. What "system level" means — three notions that do not coincide

This is the root of the confusion, and it is worth stating before anything else.
`workspace_paths.py` carries **three orthogonal facts**, and a file can be
"system" under one and not the others:

| Notion | Source | Members |
|---|---|---|
| **display zone** — folds under the collapsed "System files" disclosure | `WORKSPACE_ROOTS[…].group == "system"` | `constitution` `governance` `contract` `persona` `agents` `system` `working` |
| **organize carve** — may not be moved/renamed/trashed | `operator_can_organize` | `system/**`, `inbound/**` except `inbound/uploads/**`, any `_*.{yaml,yml,json}` leaf anywhere |
| **write lock** — per caller class | `CALLER_WRITE_POLICY` | operator: `system/`. agent + mcp: `governance/ contract/ constitution/ persona/ system/` |

`workspace_paths.py:252` says so outright: *"group is the operator zone,
semantic_class is the permission class; two orthogonal facts."*

So **seven roots display as "system"**, **one root is carved from organize**, and
**five roots are write-locked to a non-owner**. A file the UI files under "System
files" is not thereby protected, and that is deliberate: `constitution/` and
`persona/` are *the operator's own intent*, which ADR-320 says the operator
writes. The operator seeing `MANDATE.md` as editable is not a bug **for the
owner**. It is a bug for everyone else, and the Text app cannot tell them apart.

---

## 1. Files — sound, and deliberately permissive-looking

The FE mirror exists and is faithful: `web/lib/workspace/ownership.ts:46`
(`operatorCanOrganize`) is a line-for-line mirror of
`workspace_paths.py:788`. Its header states the design:

> The backend is authoritative (it 403s what it forbids). This mirror exists so
> the FE can be OPTIMISTIC without being wrong: it does not defensively grey the
> verbs — it lets the operator try, and surfaces the backend's honest error if a
> rare carve is hit (the Windows-Explorer model).

Nine call sites consume it, including the shared organize hook. Rename / Move /
Trash **are** offered on `governance/_autonomy.yaml` — and clicking Rename shows,
with no request sent:

> **"_autonomy.yaml" can't be changed** — It's a settings file the system needs
> in this exact place. Moving, renaming, or deleting it isn't allowed.

Driven on prod 2026-09-07. Drag-and-drop *is* greyed
(`ContentViewer.tsx:143`), and the Move-destination picker excludes carved
folders (`MoveToFolderModal.tsx:75`). **The menu offering a verb it then explains
is the intended model, not a leak.** No change proposed.

---

## 2. Text — the canon is broken here

### 2a. The client claims a mirror it does not implement

`web/lib/file-types/index.ts:337` says the exclusions *"mirror the member write
door exactly (ADR-570 D4)"*. The door is
`is_prose_document(path) and operator_can_organize(path)`
(`routes/workspace.py:2954`). `operator_can_organize` has **three** carves. This
function implements **two** — arrivals and `_`-leaves. **`system/` is missing.**
Same omission in `isArtifactCandidate` (`index.ts:282`).

Consequence: `system/awareness.md`, `system/style.md`, `system/notes.md` and all
twelve mirrored `system/skills/{slug}/SKILL.md` route to Text. The `_`-leaf check
saves `_playbook.md`, `_schedule_index.md`, `_recent_execution.md`,
`_calibration.md` by luck of naming, not by rule.

### 2b. Text has no notion of a document it may not write

`TextEditor.tsx:1276` — *"ONE canvas: always editable, always styled (ADR-572
D8)."* `ProseCanvas` takes no `readOnly` prop. A grep for
`readOnly|canEdit|locked|disabled` across `web/components/text/` returns only
TypeScript `readonly` constructor modifiers. **Zero permission checks.**

So the failure is: type into the canvas → autosave at 2s idle → 403 → a raw error
string, work unsaveable. `studio.py:690` documents this exact shape as
already-fixed for Studio: *"a document created beside its source accepted typing
and 403'd every save."* Reproduced verbatim in Text.

This is strictly worse than the Files model, because the organize verbs are
one-shot acts with a pre-empt and a styled explanation, while the canvas is a
*continuous* affordance with no pre-empt and an asynchronous failure.

### 2c. Driven on prod, 2026-09-07

- `/text?text.file=constitution/MANDATE.md` — full authoring toolbar; canvas
  `contenteditable="true"`; no read-only banner; breadcrumb tooltip reads
  **"constitution/MANDATE.md — click to rename"**. The body still describes
  *"Freddie, the system agent"*, retired by ADR-632, and renders the kernel
  marker `<!-- yarnnn:steward-default -->` as body text.
- `/text?text.file=governance/_autonomy.yaml` — **the sharpest case.** The
  machine-parsed YAML the scheduler reads by exact path opens in a markdown
  editor titled "Autonomy.yaml". Comment lines render as H1 headings; `default:`
  and `substrate:` keys render as inline code; the Properties panel asserts
  *"Markdown, plain text. It stays a `.md` file — the same one your connectors
  read and write."* It is not a `.md` file.

  This one reaches Text by URL only — `resolveSurfaceApplication` correctly
  refuses to route a `.yaml` `_`-leaf — but nothing refuses it at the door.

---

## 3. The server hole the surfaces distracted from

`_is_path_locked_for_principal` — the ADR-501 S1 grant gate — is called in
exactly four live places: `routes/workspace.py:2991`, `routes/studio.py:686`,
`routes/documents.py:1188` (the launch-handler metadata write, not an organize
verb), and `permission.py:309/429`.

**It is absent from every destructive organize route.** `delete_document`
(`documents.py:714`), `restore_document` (`:922`), `permanent_delete_document`
(`:1038`), `empty_trash` (`:1062`), `duplicate_document` (`:1229`) and
`trash_folder_route` (`:1331`) gate on `operator_can_organize` **alone** — a
path-shape rule identical for every principal — and then act through
`get_service_client()`, so RLS is no backstop either. `move_document` (`:1115`)
is the exception: it delegates to the `MoveFile` primitive, which does consult
the gate.

Executed, not read:

```
MEMBER (agent class — locked from governance/ contract/ constitution/ persona/):
  /workspace/constitution/MANDATE.md    WRITE=403   TRASH=200 ALLOWED
  /workspace/persona/IDENTITY.md        WRITE=403   TRASH=200 ALLOWED
  /workspace/governance/AUTONOMY.md     WRITE=403   TRASH=200 ALLOWED
  /workspace/contract/notes.md          WRITE=403   TRASH=200 ALLOWED
```

**A principal who may not write a file may destroy it.**

### This is live, not latent

The code repeatedly assumes N=1 owner-only
(`primitives/workspace.py:2616`: *"At N=1 (every live workspace) the only grant
rows are the owner's with NULL scopes"*). **That assumption is stale.**
`principal_grants` on production, queried 2026-09-07:

| role | rows | class | locked from |
|---|---|---|---|
| owner | 11 | operator | `system/` |
| member | 5 | agent | governance · contract · constitution · persona · system |
| foreign-llm | 11 | mcp | governance · contract · constitution · persona · system |
| viewer | 1 | — | (read-scoped to one deck) |

Sixteen non-owner grants exist whose class is locked from writing four roots they
can currently trash. The ADR-501 S1 fix taught `edit_workspace_file` and
`write_artifact` to ask the grant. The organize verbs were never taught.

---

## 4. A latent hole in the edit door itself

`routes/workspace.py:2955`:

```python
editable_prefixes = [
    "/workspace/system/",     # awareness.md, notes.md, style.md
    ...
]
```

composed at `:2971` as `editable_prose OR editable_ds OR any(editable_prefixes)`.

The carve law rejects `system/`, and the very next clause admits it. Today the
write is still refused, but **only** because `CALLER_WRITE_POLICY` happens to
lock `system/` for every class — an accident this door does not rely on
deliberately. Any grant row with explicit `write_scopes` naming `system/` (or
`/`) flips `_is_path_locked_for_principal` to its allow-list branch
(`primitives/workspace.py:2871`) and the prefix becomes live.

`skills/__init__.py:128` states the intent this contradicts: *"`system/` is
locked for every caller class (CALLER_WRITE_POLICY) and hidden from the
operator's organize reach — the kernel's root, by ADR-320."*

---

## 5. What I recommend, in severity order

1. **Teach the destructive organize verbs the grant.** Add
   `_is_path_locked_for_principal` to `delete_document`, `restore_document`,
   `permanent_delete_document`, `empty_trash`, `duplicate_document`,
   `trash_folder_route`. This is the ADR-501 S1 fix, applied where it was
   missed. A ratchet belongs beside
   `test_adr570_member_prose_door.py:107`, which today asserts the gate only on
   the two write doors.

2. **Give Text a read-only face.** Either exclude `!operatorCanOrganize(path)`
   in `resolveSurfaceApplication` (making the comment's claim true), or have
   `TextEditor` render non-editable when the path is carved — preferably both,
   so the surface never accepts a keystroke it cannot save. The FE mirror
   already exists; nothing new needs deriving.

3. **Refuse a non-prose path at the Text door.** `governance/_autonomy.yaml`
   reaching a markdown canvas by URL is the case that most clearly *"goes
   against our canon"* in the operator's words: a machine-parsed file rendered
   as prose, with the inspector asserting it is markdown.

4. **Drop `/workspace/system/` from `editable_prefixes`**, or make the door's
   composition a conjunction with the carve law. Its three named files
   (`awareness.md`, `notes.md`, `style.md`) are kernel-tended; if a real writer
   needs them it should hold a named grant, not ride a prefix list.

5. **Refresh the stale N=1 comments** in `primitives/workspace.py:2616` and
   wherever else owner-only is assumed. Production has sixteen non-owner grants;
   reasoning that starts from N=1 will keep producing holes of this shape.

Not proposed: changing the Files context-menu model (§1), or narrowing the
owner's write reach over `constitution/` and `persona/` (ADR-320 says that is
theirs).
