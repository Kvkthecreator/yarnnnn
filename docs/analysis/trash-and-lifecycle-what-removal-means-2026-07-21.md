# Trash and lifecycle — what "removal" means now that the layers beneath it are honest

> **Status**: Discourse. **No code written, no decision taken.**
> **Date**: 2026-07-21
> **Sequenced after**: [ADR-474](../adr/ADR-474-content-inherits-the-files-scope.md)
> (content got an owner) + [ADR-476](../adr/ADR-476-purge-is-workspace-scoped.md)
> (purge got the right scope). Both were prerequisites: "empty my trash" could
> not mean anything complete while the layer beneath it leaked.
> **Supersedes the open questions of**: [the file lifecycle audit](file-lifecycle-audit-what-trash-actually-does-2026-07-20.md)
> — whose two *defects* have since been fixed; what remains are the *decisions*.
> **Method**: measured the live database and re-read the code first. Every
> number is a query.

---

## 1. What changed since the audit — two defects are gone

The audit (2026-07-20) named four gaps. Two were defects and both are now fixed
by other lanes:

| Audit gap | Status |
|---|---|
| Search returns trashed content to the agent | **FIXED** — migration `218_search_excludes_archived.sql` adds `lifecycle IS NULL OR lifecycle <> 'archived'` to both search RPCs |
| Studio Recents shows trashed artifacts | **FIXED** — `routes/studio.py:134` (commit `ee65c43`) |
| No central visibility rule (~38 readers decide independently) | **OPEN** — the design question |
| No bulk gesture, no retention policy | **OPEN** — the product questions |

So this discourse is not a bug report. The delete verb works, the surfaces that
matter honour it, and Trash genuinely restores. What is left is three questions
nobody has *decided*, which is a different kind of thing.

## 2. Measure first — the population is tiny, and that matters

```
active     201 files
archived     3 files   14.1 KB   oldest: 1 day
ephemeral    0 files
```

**Three files. Fourteen kilobytes. One day old.**

This number should discipline the whole discourse. Every framing that treats
Trash as an accumulation problem is answering a question the data does not ask.
Whatever we decide, we are not decidingit because storage is at risk — the
retention question here is about **meaning**, not volume.

Contrast with the content layer two ADRs ago: 34,393 orphan blobs, 98% of all
substrate bytes. That was a leak. This is not.

## 3. The three open questions, stated honestly

### Q1 — Should visibility be enforced at the substrate, or per caller?

Today `archived` is a **convention each reader opts into**. Five hand-copied
filters exist (`documents.py` ×2, `studio.py`, `workspace.py` ×2), the search
RPCs now carry it in SQL, and `UserMemory.list` / `ListFiles` carry their own
variant (`in_(["active","delivered"])`). There is no `visible_files()` helper,
no view, no RLS predicate.

DP7's singular-implementation instinct says this should be one rule. The honest
counter-argument is that the two correct behaviours are **genuinely different**:

- *enumerating* readers (a tree, a recents feed, a search) should exclude archived;
- *exact-path* readers (open this file, read this revision) must NOT — Trash
  itself lists archived rows, and restore reads their content.

So a single global predicate would be wrong. The real question is narrower:
**should the enumerate-case have one home?** My reading is yes, and that it is
cheap — the filter is already identical in five places; a
`visible_files(query)` helper plus a lint that catches a new unfiltered
enumerator is a small change with a durable payoff. But it is a *tidiness*
argument, not a correctness one, and it should be argued as such.

### Q2 — Does Trash need a retention policy?

Today archived files accumulate forever. That is not a decision anyone made; it
is what the absence of a reaper does. Three defensible positions:

- **(a) Keep forever.** Consistent with ADR-209 (retention is the point) and
  with the fact that an archived row is a *revision*, not a tombstone. The
  ledger already says "this was archived at T by X"; deleting the row would not
  remove that fact, only the ability to restore.
- **(b) Age out after N days.** Familiar (macOS 30 days), bounds the surface,
  and Trash is explicitly a *temporary* state in every product that has one.
- **(c) Let the member empty it.** A gesture, not a policy. The operator
  decides; the system never deletes on its own.

**These are not mutually exclusive, and (c) is the one that actually needs a
decision** — because (a) is the status quo and (b) is only worth building if
the population grows, which at 3 files it has not.

The sharp sub-question inside (c): **does "empty trash" hard-delete?** Today
*no hard-delete exists anywhere* (deliberate, ADR-400 Q3). Emptying trash would
be the first — and it collides with Axiom 1's second clause, which says every
mutation is retained.

I think that collision is resolvable and the prior note got it right: **the
ledger holds the record, so removing a namespace row is not erasing history.**
The revision chain still shows the file existed, who wrote it, who archived it.
What is lost is *restorability*, not *the record*. That is a coherent thing to
offer a member, and it is now genuinely complete — because ADR-474 means the
content goes too, and ADR-476 means the scope is right.

### Q3 — Whose trash is it?

This one is **new since the audit**, and it is the question the last two ADRs
force. In a multi-member workspace:

- A trashed file is *workspace content* (ADR-407), not the trasher's property.
- If a member trashes a file another member authored, whose restore right is it?
- If "empty trash" hard-deletes, that is a **shared-content destruction** — which
  ADR-476 D2 just established is owner-grade, not member-grade.

The live workspace has 3 humans, so this is not hypothetical. **Any empty-trash
gesture must gate the way L1/L2 now do** (`workspaces.owner_id` or a
`workspace:clear` grant), or it reintroduces exactly the asymmetry ADR-476
closed one layer up.

Trash *listing* and *restore*, by contrast, are ordinary organize-scope acts —
they are already gated on `operator_can_organize`, and that seems right.

## 4. What I would recommend, and why it is small

**A gesture, gated, with no reaper.** Concretely:

1. **`visible_files()` helper for the enumerate-case** — folds the five copies
   into one, leaves exact-path reads alone. Correctness-neutral, drift-proof.
2. **"Empty trash" as an owner-gated gesture** — hard-deletes the namespace rows
   *and* their content (now possible and complete), leaving the revision ledger
   intact. Reuses `has_workspace_clear_authority` — no new permission concept.
3. **No time-based reaper.** 3 files. Build it when the population argues for
   it, not before.

The reason this is the right size: the *capability* that was missing (delete
that actually deletes) landed in the last two ADRs. What is left is a surface
decision plus one tidy-up — and the honest thing is to say so rather than
inflate it into an architecture.

## 5. The one thing I would push back on

If the instinct is "Trash needs a retention policy because things accumulate" —
the data says no. 3 files, 14 KB, one day. Building an aging reaper now would be
answering the ADR-474 question (a real leak, 34,393 rows) at the wrong layer.

The question Trash actually raises is **semantic**: what does a member mean when
they say "remove this," and is the system's answer complete? For the first time,
it can be — which is why this is worth deciding now rather than earlier.

## 6. Questions for the operator

1. **Does "empty trash" exist at all** — or is "keeps everything forever,
   restorable" the intended answer? (Both are defensible; only one is decided.)
2. **If it exists, does it hard-delete** the namespace row + content, leaving the
   ledger? Or only the content?
3. **Owner-gated, per ADR-476 D2?** My reading is yes — it destroys shared
   content — but that means a member cannot empty trash in a shared workspace,
   which is a real ergonomic cost worth naming.
4. **Is the `visible_files()` tidy-up worth doing now**, or left until a new
   unfiltered enumerator actually causes a bug?

## 7. What I am not claiming

- Not claiming Trash is broken. It archives, lists, and restores correctly, and
  the two surfaces that leaked have been fixed.
- Not claiming the ~38 unfiltered readers are defects. Most enumerate machine
  config or system paths where an archived row is impossible or harmless. Only
  five consequential ones were ever hand-verified.
- Not claiming a retention policy is wrong — only that today's data does not
  argue for one, and a policy built without demand becomes a thing to maintain.
- Not claiming Q3 is urgent. No member has trashed another's file yet. It is
  *structurally* live because the workspace has 3 humans, which is why it should
  be decided before the gesture ships rather than after.

## 8. The one-line statement

**Trash's defects are fixed and its population is three files — so this is not a
retention problem but a semantic one: for the first time "remove this" can mean
something complete, and the only real decisions left are whether to offer that
completeness as a gesture, and whether one member may exercise it over another's
work.**
