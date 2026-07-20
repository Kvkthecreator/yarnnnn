# Trash is not history — scoping the lifecycle fix

> **Status**: Scoping / discourse. **No code written.** Follows the
> [file lifecycle audit](file-lifecycle-audit-what-trash-actually-does-2026-07-20.md).
> **Date**: 2026-07-20
> **Challenges**: ADR-400 Q3 (`NO empty-trash — ADR-209 retain-everything`)
> **Touches**: ADR-209 / Axiom 1 second clause · ADR-329 · ADR-373 · DP7 · DP29

---

## 1. The conflation at the root

ADR-400 Q3 reads, verbatim:

> **Q3 = NO empty-trash** (ADR-209 retain-everything — Trash is a view,
> archived is permanent-but-hidden)

It borrows ADR-209's authority for a claim ADR-209 does not make.

**ADR-209 retain-everything is about revisions of a path.** Its words:
*"Overwrites never destroy; they append a new revision"*; *"nothing is lost.
Every prior state of every file is still there."* The property protects
**history from being rewritten**.

**It says nothing about whether a path must remain in the active namespace
forever.** Those are different claims, and the schema proves they are separable:

```sql
CREATE TABLE workspace_file_versions (
    user_id UUID NOT NULL REFERENCES auth.users(id) …,
    path    TEXT NOT NULL,
    blob_sha TEXT NOT NULL REFERENCES workspace_blobs(sha256),
    parent_version_id UUID REFERENCES workspace_file_versions(id),
    …
);
```

There is **no foreign key to `workspace_files`.** The revision chain keys on
`(user_id, path)` alone. Removing the active-namespace row would leave the
entire attributed history intact, walkable, and diffable — `ListRevisions`,
`ReadRevision`, `DiffRevisions`, and `trace` all key on path, not on the row.

So "empty the trash" and "retain everything" are **not in tension**. Q3
concluded otherwise because it treated the `workspace_files` row as if it *were*
the history. It isn't; it is the **current-state pointer** into the history.

### What Trash is actually for

Two different jobs got merged:

| Job | Substrate | Rule |
|---|---|---|
| **The record** — what happened, who did it, what it said | `workspace_file_versions` + `workspace_blobs` | **immutable, retained forever** (ADR-209) |
| **The namespace** — what is present in my workspace now | `workspace_files` | **the member's to curate** |

Trash belongs to the second. A member emptying their trash is saying *"this is
not part of my workspace"* — not *"pretend this never happened."* The ledger
still answers *"you made an untitled deck on July 20 and removed it on the
22nd,"* which is the honest thing to preserve.

**This is the same operation DP33 keeps performing**: the category (is this
present?) is data on the row; the record (what happened?) is the ledger. They
were conflated because one column carried both.

## 2. Why this matters more after ADR-470

Untitled artifacts are `active` and Trash is their only cleanup path. Under Q3
that means **exploration is permanently costly**: three abandoned "Untitled
document"s are three rows that can never leave. The member is asked to be
careful about clicking New — which is precisely the friction ADR-470 removed
from the front of the flow, reappearing at the back.

A workspace whose namespace only grows is not a filesystem; it is a log with a
folder tree drawn on it.

## 3. The three defects, and the one framing that fixes all of them

The audit found search + Studio-landing as defects and "no central visibility
rule" as a design question. **They are one problem.** Both defects exist
*because* visibility is per-caller. Fixing them individually would add the ninth
and tenth copy of a rule that should have one home.

### The constraint that shapes the answer

`substrate_scope_filter(user_id)` is already the universal chokepoint — **103
call sites** — and exists for exactly this purpose: a cross-cutting substrate
rule with one home. Visibility is the same kind of rule as scope.

But it returns a `(column, value)` tuple consumed as `.eq(*…)`. It
**structurally cannot add a second predicate.** So the natural chokepoint is the
wrong shape, and that is the real design constraint.

### The options

**Option A — a `visible_files()` query helper.** Returns a pre-filtered
PostgREST builder (`.eq(*scope).neq("lifecycle","archived")`).

- *For*: one home, no SQL, incremental adoption, works with the existing
  client.
- *Against*: adoption is by convention — a new caller can still bypass it. Needs
  a CI ratchet to hold (the codebase already uses this pattern; `test_adr414`
  greps for `.eq(*substrate_scope_filter(...))`).
- *Does not fix search*: the RPC is SQL and must be changed separately.

**Option B — filter in the SQL layer (view or RPC predicate).**

- *For*: a caller cannot bypass it; fixes search at its source.
- *Against*: no view over `workspace_files` exists today (migration 058 shows
  the `SECURITY INVOKER` trap the last view hit), and a view would need the FTS
  and embedding indexes to still be usable. Higher blast radius.
- *Correct for*: `search_workspace` + `search_workspace_semantic` specifically —
  those are already SQL, and adding one predicate is small and contained.

**Option C — RLS.** Rejected: RLS is authorization, not presentation. Archived
files must remain readable (Trash lists them, Restore reads them). Encoding a
*view* concern in an *authorization* mechanism is exactly the dimensional
conflation Axiom 0 exists to catch.

### The shape that seems right

**B for search, A for everything else.** Not a compromise — the two are
different mechanisms because the two readers are different: the RPCs are SQL and
should carry their own predicate; the PostgREST callers share a Python
chokepoint and should share a Python helper. One rule, expressed once per
language boundary, with a CI ratchet holding the Python side.

## 4. What the retention question actually asks

Given §1, the honest question is no longer *"may we delete?"* but:

> **What does a member's namespace curation mean, and who may perform it?**

Sub-questions, each a real fork:

1. **Manual empty-trash, or automatic expiry, or both?** Manual is a member act
   (clear intent, no surprise). Automatic (e.g. 30 days) matches macOS/Drive and
   handles the abandoned-exploration case without asking. Automatic on
   *member-typed content* is the thing to be careful about — but note it is only
   removing the *namespace row*, not the record, which is a much weaker act than
   the usual "auto-delete" and changes the risk calculus.
2. **Does "empty" delete the `workspace_files` row, or set a further state?**
   Deleting the row is the honest reading of §1 (the ledger holds the history).
   A third state would re-merge the two jobs the section separates.
3. **Do the blobs stay?** Yes — content-addressed and shared; ADR-427's GC is a
   separate concern with its own (unshipped) design. Removing a namespace row
   must not touch `workspace_blobs`.
4. **What does `trace` show for an emptied path? — VERIFIED, and it mostly
   already works.** This was the claim most likely to falsify §1, so it was
   checked rather than assumed:
   - `list_revisions` queries `workspace_file_versions` by `(user_id, path)`
     with no reference to `workspace_files` (`authored_substrate.py:883`).
   - `resolve_trace_path` (`mcp_composition.py:535`) tries the **ledger first**
     — an exact-path hit against `workspace_file_versions` — and only falls
     back to `workspace_files` for name search.

   So an emptied path stays fully traceable **by exact path**. The one real
   loss is **fuzzy name lookup**: the name-match branch filters
   `in_("lifecycle", ["active","delivered"])` (`:600`), so `trace("ir deck v3")`
   would stop resolving once the row is gone, while
   `trace("/workspace/operation/ir-deck-v3/deck.html")` still works.

   That is a contained, nameable gap with an obvious remedy (let the name-match
   branch fall back to distinct paths in the ledger), not a refutation. It
   should be **fixed in the same change as any empty-trash**, and stated as a
   falsifier: *a trashed-and-emptied artifact is still traceable by name.*

## 5. Sequencing, if this proceeds

The defects are cheap and independent of the retention decision:

1. **Studio landing filter** — one predicate. I created this exposure with
   ADR-470 D5; it should not wait on a discourse.
2. **Search RPC predicate** — small SQL, contained, fixes the substrate-level
   leak of trashed content into agent reasoning.
3. **The `visible_files()` helper + ratchet** — the durable answer to (3) in the
   audit. Converts the ~8 copied filters into one, and the ~30 absent ones into
   a decision each caller makes explicitly.
4. **The retention ADR** — only after 1–3, because it needs the separation in §1
   ratified and the visibility rule to have a home to be stated in.

**1–3 are strictly additive and reversible.** 4 is the one that needs the
operator's decision on §4's four forks.

## 6. What I am not claiming

- Not claiming ADR-400 Q3 was careless. It was decided in a Files-surface
  context where "archived" had just been made visible; borrowing ADR-209's
  language was reasonable then. ADR-470 changed what it costs.
- Not claiming automatic expiry is right. §4.1 is a genuine fork and the
  "removing a row ≠ deleting the record" framing makes *both* answers more
  defensible than before, not just one.
- Not claiming the ~30 unfiltered readers are all wrong. Many enumerate
  machine-config paths where archived rows can't occur. The helper makes each
  one an explicit choice rather than an accident — that is the value, not a
  bulk find-and-replace.

## 7. The one-line statement

**Retention protects the record, not the namespace — the revision chain has no
foreign key to the file row, so a member may curate what is present in their
workspace without anything being forgotten.**
