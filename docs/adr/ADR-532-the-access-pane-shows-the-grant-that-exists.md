# ADR-532 — The Access Pane Shows the Grant That Exists

**Status**: **Accepted** (2026-08-07, operator-commissioned surfacing audit — *"the +Agents and operation seem out of date; is per-folder wrong?"*). Implemented same day.
**Date**: 2026-08-07
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A
**Dimension**: Identity (Axiom 2 — the grant, never the species) + Channel (Axiom 6 — what a principal is shown about its own reach)
**Relates to**: ADR-434 (the powerbox — the two-axis model this ADR surfaces faithfully), ADR-405 (no rule keys on species), ADR-504 (the external LLM is a first-class principal), ADR-460 (the desk agent is the member's hands), ADR-501 D1 (the display/gate divergence, here recurring on the read axis), ADR-517 (grants govern)
**Amends**: nothing in the kernel. **The powerbox is correct.** This ADR fixes the surface that misreports it, and amends `docs/architecture/grants-and-reach.md` with the NULL-axis display contract.

---

## 1. Context — the model was right and the pane disagreed with it

The operator asked whether the Workspace Members access pane was out of date,
and specifically whether **per-folder scoping was the wrong grain**.

It is not. ADR-434 D2 ratified path prefixes at **arbitrary depth** — root,
folder, or single file — under an explicit mental model: *"the macOS
security-scoped-bookmark granularity: the OS hands an app **this file**, not
**the disk**. Teams share folders and files, not kernel roots."* Per-folder is
the intended grain, and per-file is intended too.

Nor is the human/AI framing out of date. ADR-405 makes permission a **grant**,
never a species rule; ADR-504 makes a connected external LLM a **first-class
principal** with its own grant row and its own attribution. The one real
distinction is ADR-460's, and it is about **where the write enters** — an agent
addressed at the desk acts under the member's grant (the member's hands); an
LLM over the interop face acts under its own. The pane already renders humans
and AI connections in one list with one affordance shape. That is correct and
stays.

What is out of date is **what the pane says about a grant that has not been
narrowed** — which, live, is every grant in the workspace.

---

## 2. The receipts

Live state, workspace `d5b9029b`, at time of writing: **all four active grants
(owner, member, `chatgpt`, `claude.ai`) are NULL on both axes.** NULL is the
mint default for every invite, share, and OAuth connect. So the unconfigured
case is not an edge — it is the only case in production.

Three defects follow, all in the surface:

| # | Defect | Site |
|---|---|---|
| 1 | The dialog **fabricates a grant**: both axes NULL seeds a synthetic `operation/ Read+Write` row | `WorkspaceMembersCard.tsx:866` |
| 2 | The **two axes are fused** into one ladder (No Access / Read / Read+Write) | the same dialog |
| 3 | The pane **misreports read reach**: a NULL read axis is displayed as the *write* class default | `routes/workspace.py:1326` |

Defect 3, executed rather than argued:

```
NULL read axis  → _axis_state = 'all'
pane reports      read_regions = ['operation/']
gate returns      _is_path_readable_for_principal(…) = True   # read-all
```

The pane tells the operator a member reads `Documents`. The kernel lets that
member read **the entire commons**. This is precisely the ADR-501 D1 shape —
the display and the gate consulting different tables — recurring on the read
axis, which ADR-501 did not sweep.

Defect 1 is the dangerous one. The fabricated row is not inert: it is seeded
into dialog state, so an operator who opens the dialog to inspect a member and
presses Apply **writes `operation/` into a grant that had none** — narrowing a
principal they never intended to narrow, and silently converting "class
default, follows policy as policy evolves" into "pinned to this literal path".

---

## 3. D1 — NULL renders as what it is, and is never seeded as a row

A NULL axis means *"class default — not narrowed"*. It is a **distinct state**,
not a path list, and the pane must render it as prose, never as an editable row
carrying a fabricated path.

The dialog opens with **no rows** for an unconfigured principal, above a line
naming the real state and the real reach. Adding the first row is the act that
narrows; until then, Apply has nothing to write and is inert.

**Why not seed the class default as a row?** Because it is a lie of type, not
just of value. `NULL` and `['operation/']` are different grants: the first
tracks the class policy, the second pins a literal prefix. ADR-434 D3 made the
three-state polarity load-bearing precisely so these stay distinguishable
(*"`scopes: []` failed OPEN … 'this principal touches nothing' was
unrepresentable"*). A UI that collapses NULL into a path re-introduces the
collapse D3 removed.

## 4. D2 — The two axes are shown and set independently

ADR-434 D1 built `read_scopes` and `write_scopes` as **independent** axes, with
`read ⊇ write` as *"the BACKFILL DEFAULT, not a constraint"*. The fused ladder
made the shapes that motivated the ADR unreachable: the read-only auditor
(`read: operation/`, `write: []`), and the ADR-434-named *"external AI that sees
much but changes little"* — which, post-ADR-504, is the shape the product's
central claim runs on.

Each row carries **two** controls, one per axis. The ladder's implicit
`read ⊇ write` is kept as a *default when a row is created*, and as a nudge, not
a lock: setting write above read raises read to match (the grant the operator
means), rather than refusing the edit.

## 5. D3 — The read display reads the read gate

`read_regions` for a NULL read axis reports **read-all**, matching
`_is_path_readable_for_principal`. The write display is unchanged (it was
already correct). One rule, stated once: **every reach the pane displays is
computed from the function that enforces it.**

## 6. What is NOT in scope (named, not silently dropped)

- **Dropping the legacy `scopes` column.** ADR-434 deferred it pending "no
  reader remains". Readers remain — `principal_grants.py` (261/275/312/370/418),
  `principals.py` (98/129), `routes/workspace.py:1311`,
  `primitives/workspace.py:2436`. Bundling a column drop into a display fix
  would be exactly the dual-implementation ambiguity the cleanup is meant to
  prevent. It needs its own migration and its own pass.
- **`+ Agents`** stays. It is a quick-pick for the `agents/` root, not stale
  vocabulary. It sits oddly beside ADR-434's *"teams share folders and files,
  not kernel roots"*, but a quick-pick is a shortcut, not a claim about grain.
- **Prefix-RLS.** `grants-and-reach.md` §3 defers it deliberately; this ADR does
  not disturb that contract.

## 7. Consequences

- An operator opening the access dialog sees the grant that exists, and cannot
  narrow a principal by merely looking at it.
- The auditor / sees-much-changes-little shapes become reachable from the UI.
- The pane's read claim and the read gate agree, closing the ADR-501 D1 shape on
  the second axis.
- `docs/architecture/grants-and-reach.md` gains the NULL-axis display contract,
  so the next surface that renders reach does not re-derive it.
