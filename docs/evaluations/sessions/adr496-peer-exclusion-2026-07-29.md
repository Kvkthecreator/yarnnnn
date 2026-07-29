# Hat-B — ADR-496 peer-exclusion: the multi-member negative, receipted

**Date**: 2026-07-29
**Hat**: B (evaluation of a shipped Hat-A change; no system code written here)
**Subject**: ADR-496 D1 — the account door's `scope="mine"` filter
**Trigger**: operator ruling. The ADR shipped with an honest gap recorded in §6: prod is N=1 for AI connections (both grants are the owner's), so the peer-exclusion was receipted at the data layer but **never observed**. The operator asked for the check rather than accepting the argument.

---

## 1. The claim under test

A member's account door shows **only the AI connections that member authorized**. A peer's connection must not appear. Stated in ADR-496 D1 as a *privacy boundary, not a display preference*.

Two independent layers have to hold, and the existing evidence only covered the first:

| Layer | Mechanism | Prior evidence |
|---|---|---|
| Server | `connected_by_is_you = (cb == auth.user_id)`, `routes/workspace.py:1319-1325` | code read only |
| Render | `scope='mine'` filter in `WorkspaceMembersCard` | gate asserts the *string* exists (`test_adr496` — a text check, not an execution) |

Neither had ever run against an actual two-member state, because one has never existed in prod.

## 2. Method

**Manufacture the state, observe, roll back.** The live workspace `d5b9029b` has two humans (owner `kvkthecreator`, member `nickyandnicholas`) but both AI grants belong to the owner. Inside a transaction, one grant was reassigned to the member — creating the N>1 condition — then the endpoint's own resolution expression was evaluated for *both* viewers over the same rows, and rolled back.

Note: seulkim, visible on an earlier screenshot, is a member of a **different** workspace; the actual second member of this one is `nickyandnicholas`. Checked rather than assumed.

## 3. Receipt — server layer

Pre-state (both grants → owner `2abf3f96`):

```
260825b4… | chatgpt   | foreign-llm | connected_by 2abf3f96 (owner)
f4a33a28… | claude.ai | foreign-llm | connected_by 2abf3f96 (owner)
```

Inside `BEGIN … ROLLBACK`, `chatgpt.connected_by → 6ae2318d` (the member), then the endpoint's `cb == auth.user_id` evaluated per viewer:

```
 principal_id | is_you_for_OWNER | is_you_for_MEMBER
--------------+------------------+-------------------
 chatgpt      | f                | t
 claude.ai    | t                | f
```

**Disjoint.** Each viewer resolves true on exactly their own grant. Post-rollback verification confirmed both rows restored to `connected_by = 2abf3f96`, `status = active` — byte-identical to pre-state.

## 4. Receipt — render layer

The SQL proves the server's *fields*; it cannot prove the component filters on them. The `scope='mine'` predicate was replicated verbatim against both viewers' payloads as the endpoint would build them:

```
✓ owner's account door shows ONLY their own      → ["claude.ai"]
✓ member's account door shows ONLY their own     → ["chatgpt"]
✓ the two views are DISJOINT (no leakage)
✓ owner does NOT see the member's chatgpt
✓ member does NOT see the owner's claude
✓ humans are excluded from the account door
✓ workspace door still shows BOTH (governance unbroken)
```

The last line matters as much as the exclusions: narrowing the account door must **not** narrow the commons. An owner governing the workspace still sees every principal.

## 5. Verdict

**The claim holds at both layers.** The ADR-496 §6 gap is closed for the peer-exclusion specifically.

## 6. What this does NOT establish

Stated plainly, so the receipt isn't over-read:

- **No browser was involved.** This validates the server expression and the filter predicate, not pixels. The rendered pane still needs a human click — as does the ADR-494 D4 dormant sub-label.
- **The manufactured state was transactional.** No member has *actually* connected an assistant; the OAuth path that would write a second member's `connected_by` (`_ensure_foreign_llm_grant`) was not exercised. ADR-431's own gate covers that write; this evaluation covers the read.
- **N=2, one workspace.** Not a scale claim.

## 7. Cost

Zero LLM invocations. Two `psql` statements and one predicate replay — mechanical throughout.
