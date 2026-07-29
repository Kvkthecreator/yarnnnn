# ADR-500 — The Roster Follows the Binding, and a Failed Act Leaves No Orphan

**Status**: Accepted (2026-07-29, operator-reported — "this is now from invited seulkim chat", API Error: 422 on the conversation picker). Implemented same day.
**Date**: 2026-07-29
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A
**Dimension**: Substrate (Axiom 1 — a cache must not outlive the fact it mirrors) + Channel (Axiom 6 — a surface must not offer a choice the gate will refuse)
**Relates to**: ADR-499 (the mid-session rebind that broke the cache's assumption), ADR-407 D9 (the hard-reload-on-switch assumption the cache was written against), ADR-495 D3 (species-blind participant invite), ADR-408 D1 (the commons boundary — a grant is the prerequisite), ADR-373 (grants), ADR-498/499 (the invite arc this continues)
**Amends**: nothing. Both server 422s were **correct**.

---

## 1. Context — a picker offering an impossible choice

The invited member, now able to load their account (ADR-499), opened the chat picker and hit `API Error: 422` on the PEOPLE row.

**The server was right.** `_workspace_humans` derives the invitable set from active grants — the commons boundary (ADR-408 D1). Live state:

```
workspace 4ca9c664 (seulkim's own) → 1 human grant: seulkim (owner)
kvkthecreator in 4ca9c664?         → 0
```

Seulkim's workspace contains exactly one human: themself. The picker nonetheless offered `kvkthecreator@gmail.com`. The 422 — *"that person isn't in this workspace"* — was the gate doing its job on a choice the frontend should never have presented.

## 2. Defect 1 — a cache that outlived its binding

`useWorkspaceMembers` memoizes the roster in a module-level promise, on an assumption stated in its own comment: *"one fetch per page life is enough (the workspace switcher hard-reloads on bind change, ADR-407 D9)."*

That proviso was true when written. **ADR-499's self-heal broke it the same day** — it clears a stale pin and retries *mid-session, with no reload*. The roster fetched under the old binding (`d5b9029b`, where you and seulkim were both members) outlived the rebind to `4ca9c664`, so the picker kept offering a person from the previous workspace.

This is the third instance of one shape in this session — ADR-491's stale pane, ADR-499's stale pin, and now a stale roster. Worth naming:

> **A cache keyed on nothing is keyed on the assumption that nothing changes.** When the fact it mirrors can change mid-session, key it to that fact.

**Fix**: the cache records the binding it was fetched under; a mismatch drops both promises. Invalidation is *by construction* — no call to remember at the (now several) sites that can rebind, which is exactly how this bug arrived.

## 3. Defect 2 — a two-call act with no rollback

Starting a conversation *with someone* is two calls: `create`, then `addParticipant`. When the second 422'd, the first had already landed — so the member got an error **and** an empty conversation they never asked for.

Receipt: lane `d59090d6…`, created 02:02:09, orphaned by the failed add. Not corrupt (the creator was cast, so it was usable) but unwanted — a failed action leaving a trace.

**Fix**: on failure the created lane is archived. The cleanup is best-effort and swallowed — the member must see *why the act failed*, never a cleanup error stacked on top of the real one.

The orphan was archived in prod as part of this change.

> **A multi-call act must not leave partial state behind on failure.**

## 4. What is NOT changed

The server contract. Both 422s stay: a non-member cannot be cast into a conversation, and the commons boundary stays grant-derived. The gate asserts both. The frontend's job was never to bypass the gate — only to stop offering choices the gate will refuse.

## 5. Validation

- `api/test_adr500_roster_binding.py` — **11/11**: the cache keys on the binding, both promises drop together, both hooks sync before reading, the superseded ADR-407 D9 assumption is documented; the lane is tracked, archived on failure, cleanup never masks the original error; and both server rejections survive.
- **Behavioural replay** (gates grep text, not execution) — **9/9**: first read fetches, repeat is cached, a rebind invalidates and refetches, the new roster excludes the stale person, clearing the pin also invalidates; the failure path surfaces the original error and archives the orphan, and the success path archives nothing.
- Live receipts in §1 and §3, reproducible.
- `tsc --noEmit` clean; `next build` green (170/170).

**Not verified** (needs a human): the picker in a live browser. Expected: seulkim now sees the four kernel agents and **no** PEOPLE section (their workspace has one human — themself), which is the honest state.

**Adjacent, deliberately unfixed**: the picker renders a PEOPLE header whose list can legitimately be empty. That is now correct-but-plain; whether a solo workspace should say something warmer ("invite a teammate to chat with them here") is a copy decision, not a defect.
