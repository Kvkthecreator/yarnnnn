# ADR-497 — The Rendered Role Vocabulary Matches What Can Exist

**Status**: Accepted (2026-07-29, operator-ratified — "shouldn't we not show workspace level component there if it isn't built yet? help us streamline production" → "yes do the sweep"). Implemented same day.
**Date**: 2026-07-29
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A
**Dimension**: Channel (Axiom 6 — the surface describes the world the substrate actually has)
**Relates to**: ADR-373 (`principal_grants`, the role vocabulary), ADR-431 (the connecting member owns the MCP grant), ADR-496 (the account-door mirror that put this roster under fresh scrutiny), ADR-414 D5 (program-as-hire — why `own-agent` stays), ADR-382 (persona agents — the reserved `a2a` seat), ADR-401 D1 (platform-as-principal, explicitly deferred)
**Amends**: nothing. Deletes presentation only; no schema, no API, no grant lifecycle.

---

## 1. Context — the operator's question, and the honest answer

Reviewing the members roster after ADR-496: *"shouldn't we not show workspace level component there if it isn't built yet? help us streamline production."*

**The literal premise did not hold, and saying so mattered more than acting fast.** The roster is data-driven — it renders whatever `principal_grants` returns. Live population (2026-07-29, all workspaces):

```
 role        | count
-------------+-------
 foreign-llm |     2      ← the operator's ChatGPT + Claude
 member      |     1
 owner       |    11
```

No `a2a`, `platform`, or `own-agent` row exists, so none could render. **Nothing unbuilt was on screen.**

**But the instinct was pointing at something real.** The roster carried full *presentation* — labels, icons, one-line kind hints — for principal classes the system cannot create. Invisible to operators, yet it told the next reader of `AI_ROLES` that four AI kinds exist when two do. That is vocabulary drift: the surface describing a world the substrate doesn't have.

**A correction to an earlier claim in this session.** ADR-496 §5 stated that `own-agent` and `a2a` have "no code path." That was half wrong: `own-agent` *is* minted, by `programs.py::mint_hire_grant` on program activation (ADR-414 D5 program-as-hire). Reachable, zero live rows. Only `a2a` and `platform` are genuinely uncreatable — their sole trace was presentation metadata.

The vocabulary therefore splits three ways, not two:

| Role | Creation path | Live rows | Rendered? |
|---|---|---|---|
| `foreign-llm` | `oauth_provider.py::_ensure_foreign_llm_grant` | 2 | **yes** |
| `own-agent` | `programs.py::mint_hire_grant` (ADR-414 D5) | 0 (reachable) | **yes** |
| `a2a` · `platform` | **none, anywhere** | 0 | **no** (this ADR) |

## 2. D1 — Display narrows to the creatable; defensive sweeps stay broad

`AI_ROLES` becomes `['foreign-llm', 'own-agent']`. The `a2a`/`platform` `ROLE_META` entries, their `kindHint` branches, and their slot in `isExternalAI` are deleted, along with the now-orphaned `Plug` icon import. ~10 lines.

`own-agent` is **kept** deliberately: it has a live code path, and deleting its presentation would mean a program activation renders an unlabeled row. A reachable-but-unused path is not the same as an unreachable one.

**The asymmetry is the load-bearing part of this decision.** The eviction sweep — `principal_grants.py::cascade_member_ai_connections`, matching `["foreign-llm", "a2a", "platform"]` — **must stay broad.** If such a row ever comes to exist, it must still be cleaned up when its authorizing member is evicted. Narrowing *that* list to match the display would convert a cosmetic tidy into a real bug.

So:

> **A reserved seat is a SUBSTRATE fact, not a RENDERED one.** It belongs in the DB CHECK constraint and in defensive cleanup. It does not belong in presentation until something can mint it.

The gate asserts both directions — the FE list shrank, the sweep did not.

## 3. What this is not

Not a fix for a production defect. Nothing was wrong on the operator's screen; no row rendered, no promise was made. Framing this as a bug fix would misrepresent it. It is a **vocabulary sweep**: the code now says what is true, so the next reader isn't misled about how many principal kinds exist.

The distinction matters for the ADR record. ADR-494 D6 (the blurb promising a read that couldn't happen) *was* operator-visible dishonesty. This is not — it is legibility debt paid before it becomes one.

## 4. Validation

- `api/test_adr497_role_vocabulary.py` — **9/9**: the rendered set is exactly `{foreign-llm, own-agent}`; `a2a`/`platform` carry no presentation; both rendered roles have a verified creation path (checked in `oauth_provider.py` / `programs.py`); **the eviction sweep still matches all three**; the CHECK constraint still carries the reserved seats; the orphaned import is gone.
- Partition replay against the live population: all four row kinds still land in a section (`AI: [chatgpt, claude.ai]`, `People: [kvk, nicky]`) — the sweep orphans nothing real.
- Siblings green: ADR-496 15/15 · ADR-431 7/7 · ADR-373 + ADR-386 38 passed / 4 skipped (the known `.venv-mcp` 3.11 gating).
- `tsc --noEmit` clean; `next build` green (170/170).

**Not verified** (needs a human click): the rendered roster. The partition replay covers the logic, not pixels — though since the only live AI rows are `foreign-llm`, which is unchanged by this sweep, the visible roster should be byte-identical to before.
