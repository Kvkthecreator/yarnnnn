# File lifecycle audit — what Trash actually does

> **Status**: Audit. **No code written, no decision taken.** Findings only.
> **Date**: 2026-07-20
> **Prompted by**: ADR-470 D5 made Trash the *only* cleanup path for abandoned
> untitled artifacts, which puts weight on a surface nobody had audited.
> **Method**: read the write path, the enum, every migration touching it, and
> swept all 123 `workspace_files` SELECTs for lifecycle filtering.

---

## 1. What is built, and it is better than expected

The delete verb is **trash-not-erase, and correctly so**:

- `DELETE /documents/{path}` writes a **new attributed revision** with
  `lifecycle='archived'` (`routes/documents.py:585-599`). The row survives, the
  revision chain survives, the storage binary survives. Axiom 1's second clause
  is honoured — deletion is a *write*, not an erasure.
- `GET /documents/trash` lists archived files within the operator's organize
  reach; `POST /documents/restore` writes a new `'active'` revision carrying the
  archived content verbatim. Symmetric and reversible.
- `TrashView.tsx` is mounted on the Files surface and offers Restore.
- **No hard-delete exists anywhere.** Deliberate (ADR-400 Q3).
- Both verbs are gated by `operator_can_organize` — the same singular carve the
  FE mirrors (`lib/workspace/ownership.ts`).

**The enum's history is resolved, not broken.** Migration 116 created
`('ephemeral','active','delivered','archived')`; migration 159 *removed*
`'archived'` on the reasoning that nothing wrote it; migration 184 **restored
it** when ADR-329 made delete write it again. A round-trip, correctly closed.

## 2. The finding: `archived` is enforced at the surfaces, not at the substrate

There is no central read filter. Each caller decides for itself, and **most
enumerating callers don't**.

Swept all 123 `workspace_files` SELECTs. Excluding exact-path reads (where
lifecycle is irrelevant — you asked for one file) and test/probe/script files,
**~38 enumerating readers carry no lifecycle filter.**

### Who gets it right

| Reader | Filter |
|---|---|
| `routes/workspace.py:587` — the Files **tree** | `or_("lifecycle.is.null,lifecycle.neq.archived")` |
| `services/workspace.py:250` — `UserMemory.list()` | `in_(["active","delivered"])`, ADR-119 |
| `services/primitives/workspace.py::_list_tree` — **ListFiles** | `in_(["active","delivered"])` |
| `working_memory.py:799`, `mcp_composition.py` (3 sites) | `in_(["active","delivered"])` |
| `agents_registry`, `design_systems`, `authored_substrate` | client-side `== "archived"` skip |

So a correct central helper **exists** (`UserMemory.list`) and the tree is right.

### Who does not

The consequential ones, hand-verified (not regex-inferred):

| Reader | Consequence |
|---|---|
| **`SearchFiles`** — `primitives/workspace.py:1438` + the `search_workspace` / `search_workspace_semantic` **RPCs themselves** (no `lifecycle` in `100_workspace_files.sql` or `145_semantic_search_workspace.sql`) | **a trashed file stays searchable by the agent, and its content flows into reasoning** |
| **Studio landing** — `routes/studio.py:91` | a trashed artifact still appears in Recents |
| `freddie_envelope.py:502` (specs sweep) | archived specs reach the wake envelope |
| `working_memory.py:660` (uploads) | archived uploads reach working memory |
| `routes/workspace.py:452 / 854 / 1902 / 2695` | assorted listings include archived |

**The Studio landing gap is newly load-bearing.** Pre-ADR-470 it was a minor
inconsistency. Now that untitled artifacts are `active` and Trash is their only
cleanup path, a member who trashes three abandoned "Untitled document"s **still
sees all three in Recents** — the cleanup appears not to work.

### Why this is the shape it is

Not carelessness — the filter has simply never had a home. `lifecycle` is a
column on `workspace_files`, and every caller composes its own PostgREST query.
There is no `visible_files()` helper, no view, no RLS predicate. `UserMemory`
is the closest thing to a chokepoint, and the direct-query callers bypass it.

## 3. The other two enum values

- **`delivered`** — written once (`workspace.py:678`, `save_output`). Treated as
  visible everywhere (`in_(["active","delivered"])`). Effectively an annotation
  on active files, not a distinct state.
- **`ephemeral`** — the ADR-119 `/working/` + `/user_shared/` scratch lane.
  `_infer_lifecycle` still assigns it by path; `UserMemory.list` excludes it by
  default. **Its reaper was deliberately removed** (`unified_scheduler`
  docstring, audited 2026-05-02: *"no ephemeral files accumulate in prod"*). So
  today it is a state that is created (rarely) and never collected.

ADR-470 D5 deferred `ephemeral` for untitled artifacts partly on the cost of
restoring that reaper. This audit confirms the reaper is genuinely gone, not
merely dormant — that deferral was correctly priced.

## 4. The gaps, in priority order

1. **Search returns trashed content to the agent.** The substrate-level one.
   Fixing it means the RPC (SQL), not just the caller — every search path goes
   through `search_workspace` / `search_workspace_semantic`.
2. **Studio Recents shows trashed artifacts.** One `.neq("lifecycle","archived")`
   on `routes/studio.py:91`. Now load-bearing because of ADR-470 D5.
3. **No central visibility rule.** ~38 enumerating readers each decide
   independently; the correct behaviour is copy-pasted in ~8 places and absent
   in the rest. This is the *cause* of (1) and (2), and the durable fix.
4. **No bulk gesture.** Trash restores one file at a time. No "empty trash"
   (deliberate — no hard-delete), and no multi-select.
5. **Trash has no retention policy at all.** Archived files accumulate forever.
   That is a defensible reading of ADR-209 (retain everything) but it has never
   been stated as a decision — it is simply what the absence of a reaper does.

## 5. What is NOT a gap

- **No hard-delete.** Deliberate (ADR-400 Q3), consistent with Axiom 1.
- **The archive round-trip in migrations 159 → 184.** Closed correctly.
- **`ListFiles` and the Files tree.** Both filter properly. (My first sweep
  reported `ListFiles` as unfiltered; that was a false positive from too narrow
  a search window — `_list_tree` filters correctly. Recorded because it is the
  kind of error a source-grep audit produces, and the reason each consequential
  finding above was re-verified by hand.)

## 6. The question this raises for the next discourse

The gaps in §4 are three different kinds of thing, and only one is a bug:

- (1) and (2) are **defects** — the surface promises removal and doesn't deliver.
- (3) is a **design question**: should visibility be enforced at the substrate
  (a view / RLS / a mandatory read helper) rather than per-caller? DP7's
  singular-implementation instinct says yes; the cost is touching ~38 call sites
  or introducing a chokepoint every reader must adopt.
- (4) and (5) are **product decisions** nobody has made: does Trash need bulk
  operations, and does it need a retention policy — or is "keeps everything
  forever, restorable" the honest and intended answer under ADR-209?

My reading: (2) is a one-line fix that ADR-470 made urgent; (1) is a real
substrate defect worth its own small change; (3) is the durable answer and
deserves the ADR; (4) and (5) should be answered *by the operator*, not
inferred, because "retain everything forever" is a legitimate position and the
absence of a reaper may already be the intended design rather than an omission.

## 7. Explicitly not claimed

- Not claimed that ~38 unfiltered readers are all defects. Many enumerate
  machine-config or system paths where an archived row is impossible or
  harmless. Only the five in §2's second table were hand-verified as
  consequential.
- Not claimed the search RPC *should* filter. A case exists for archived content
  remaining searchable (it is retained, attributed substrate). But today's
  behaviour is unstated and unowned — that is the finding, not the verdict.
- Not claimed Trash is broken. It does what it says for the surfaces that
  honour it, and it is genuinely reversible.

## 8. The one-line statement

**Delete is honestly a write, and Trash genuinely restores — but "archived"
is a convention each reader opts into rather than a property the substrate
enforces, so a trashed file is gone from the tree, still in the search index,
and still on the Studio's landing.**
