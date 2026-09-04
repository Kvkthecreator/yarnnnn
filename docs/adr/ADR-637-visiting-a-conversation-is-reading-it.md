# ADR-637: Visiting a Conversation Is Reading It — one cursor discharges a mention

**Status**: Accepted (2026-09-04, operator-aligned in-discourse) — implemented same session.
**Dimension**: Channel (Axiom 6 — where attention routes, and how it stops)
**Amends**: ADR-492 §7 (the two-facts split moves from *badge vs membership* to *visit vs retain*), ADR-605 D2 (resolution keys on the read cursor; the reply floor is deleted)
**Preserves**: ADR-410 (one derivation, N mounts; no inbox table), ADR-492 D3 (no per-mention read flags), ADR-495 D2 (the visibility window is the read floor), ADR-407 (cursors are viewer presentation state, never authorization), DP29 (attention is derived, never stored)
**Gate**: `api/test_adr605_mentions_attention.py` (extended — the ADR-605 gate is the mention gate; a second file for one collapsed cursor would be the fragmentation this ADR exists to remove)
**Provenance note**: the code for this ADR landed in commit `72e734a`, whose message describes only ADR-636 §9. A concurrent session committed a working tree that already held these edits; the eight files are correct and gated, but that commit's message does not describe them. Recorded here rather than repaired by history rewrite — `72e734a` was already on `origin/main`. The files: `services/mentions.py`, `routes/mentions.py`, `routes/lanes.py`, `main.py`, `test_adr605_mentions_attention.py`, `web/lib/api/client.ts`, `MentionQueue.tsx`, `AttentionCenter.tsx`.

---

## 1. Context — the symptom, and the thing the symptom revealed

A mention sat at the top of the operator's bell for **one week**: *"Seul Kim
mentioned you · a direct chat · 1w ago."* The audit found the derivation
internally consistent and doing exactly what it was built to do:

| Test (`unresolved_from`, pre-637) | State on the live row | Cleared? |
|---|---|---|
| Before the visibility window? | `visible_from_sequence = 0` | no |
| Did the viewer SPEAK after it? | never posted in that conversation — reply floor −1 | no |
| Explicit Done cursor past it? | `{conv: 22}`, set 06:30 — the mention is seq **23**, at 06:35 | no |

So: the viewer cleared ping #1 with the Done button, ping #2 landed five
minutes later, and nothing since could discharge it. Not a bug in the
derivation — **a bug in the model the derivation faithfully implemented.**

The operator's ruling named the benchmark:

> *the reason for my mention is that user doesn't explicit click to confirm a
> notification but if visits that thread, or pane surface is considered "seen"
> by the user. and thus, my thesis is that that is the better approach.*

## 2. What the benchmark actually says

Slack is not one rule, it is a partition, and we had it backwards:

- **Unread state and the mention count both clear by VIEWING.** Open the
  channel; the bold clears, the red badge decrements. There is no per-mention
  confirm gesture anywhere in the product.
- **The explicit gesture is *Later* / saved items** — opt-in, additive. You
  act to make something **persist**. You never act to make it **go away**.

Gmail is the counterexample, and it is the one we had built: archive is an
explicit act, and the product is famous for making people feel behind. The
pre-637 design was Gmail's, documented as a virtue — *"a mention never
silently clears by scroll-by"* appears verbatim in the module docstring, the
route docstring, ADR-605 D2, and the gate's own assertion text.

⭐ **The stated fear (a mention scrolls past unnoticed and vanishes) is real
but rare; the cost we took instead was a permanent guilt row clearable only
through a button most members never find.** The bell's mention row — the
surface the operator was actually looking at — navigated to the conversation
and, by construction, discharged nothing.

## 3. The sharper argument: three cursors that could disagree

Convention is the weaker half of the case. The stronger half is that the
pre-637 design had **three** clearing mechanisms over one question, and they
**did** disagree on the live row:

1. `reply_floors` — a second `session_messages` scan keyed on
   `metadata->>author_principal_id`.
2. `resolutions` — `member_state['mention_resolutions']`, advanced only by Done.
3. `member_state['attention']` — the bell's badge cursor, advanced by opening
   the popover.

The stale mention survived **four MCP-authored turns into that very lane**
(sequences 24–27, `role='external'`, no `author_principal_id`), because only a
member-authored message counted as a reply. The viewer was demonstrably
working in the conversation while the row insisted they had not seen it.

⭐⭐⭐ **A second floor that can disagree with the first is not redundancy, it
is the defect.** Slack has one cursor per channel and derives everything from
it. So do we now.

## 4. D1 — Visiting a conversation advances the read cursor

`GET /api/lanes/{lane_id}/messages` calls `_mark_visited`, which advances the
caller's per-conversation cursor to the top sequence **returned by that read**.

- **Bound to the READ, not to an FE "I opened it" ping.** Every door that
  renders the transcript passes here; a ping is a fourth thing to remember to
  call, and the failure this ADR closes is precisely a discharge path that
  existed only where nobody went.
- **Monotonic max-merge, server-side** (`mark_read_up_to`), so the
  fire-and-forget visit write races the explicit dismiss safely — an older act
  can only agree with a newer one. Driven: `mark_read_up_to(…, 5)` against a
  cursor at 27 left it at 27.
- **Under-advances honestly.** The read caps at 200 rows from the visibility
  floor; in a longer lane the member has demonstrably not seen the tail, so a
  mention past the cap keeps wanting them. Under-advancing is the correct
  answer, not a rounding error.
- **Best-effort and silent.** A cursor that fails to advance leaves the
  mention listed — the honest degrade — and never fails the read.

## 5. D2 — One cursor decides membership; the reply floor is DELETED

`unresolved_from(rows, *, floors, read_cursors)` — the `reply_floors`
parameter is **deleted, not defaulted**. A reply is a visit, so the read
cursor subsumes it, and the deleted scan could never see a visit that produced
no message.

The gate asserts this as a **fact about the signature**, not a spelling:

```python
params = set(inspect.signature(unresolved_from).parameters) - {"rows"}
_assert(params == {"floors", "read_cursors"}, …)
```

A revived reply floor — or any third rival cursor — goes red. Falsified: adding
`reply_floors: dict = None` back turns it red.

Renames, so the vocabulary matches the act: `load_resolutions` →
`load_read_cursors`, `resolve_mentions_up_to` → `mark_read_up_to`,
`POST /api/mentions/resolve` → `POST /api/mentions/read`,
`api.mentions.resolve` → `api.mentions.markRead`. The `member_state` KEY stays
`mention_resolutions` — renaming it would strand every live cursor to buy a
nicer word.

## 6. D3 — The explicit gesture survives as DISMISS, never as the only way out

The queue's **Done** becomes **Dismiss** ("Clear without opening") — the same
cursor, for the mention you know you needn't read. This is Slack's *mark as
read*, not Gmail's archive: an alternative to visiting, never the sole exit.

The bell's mention row drops locally on click, because the click IS the visit —
leaving the row until the next 60s derive would re-teach the old model.

**Refused, recorded**: a *Later* / saved-mentions flag. Slack has one and it
earns its place, but nothing in the discourse asked for retention, and a flag
nobody requested is a store to keep honest forever. If a member later wants a
mention to persist past a visit, that is its own decision with its own surface.

## 7. Verification — driven against production, not simulated

The live derivation reproduced the operator's screenshot exactly
(`cursor {conv: 22}` → `mentions [(a direct chat, 23, Seul Kim)]`), then the
visit seam was driven against the real row:

| Step | Result |
|---|---|
| cursor before | `{1ee9f2eb…: 22}` |
| mentions before | `[('a direct chat', 23, 'Seul Kim')]` — the week-old row |
| `mark_read_up_to(…, 27)` (the visit) | `{1ee9f2eb…: 27}` |
| mentions after | `[]` |
| `mark_read_up_to(…, 5)` (older act) | `{1ee9f2eb…: 27}` — no rewind |
| other viewer, own workspace | 3 mentions still listed — derivation intact |

Gates: `test_adr605` 55/55 (was 53; +2 new, each falsified individually) ·
`test_adr495_addressing` · `test_adr593_notifications_management` 40/40 ·
`test_adr411_lanes` — all green. `tsc --noEmit` exit 0.

⭐⭐ **A new assertion passed vacuously and was caught by falsifying it.** The
check that the lane read *selects* `sequence_number` — the column the seam
reads off the rows — was first written as a substring search over a source
slice. Removing the column from the `select()` left it **green**, because the
nearby `.gte("sequence_number", floor)` satisfied the substring. It now reads
the `select()` call's argument via AST and goes red on exactly that defect.
The defect was real, not hypothetical: the first cut of this change wired the
helper without adding the column, and every advance would have been a silent
no-op.

## 8. Consequences

- The list and the badge can no longer disagree: one cursor decides
  membership, and the badge's recency filter is presentation over the same
  rows, never a rival definition.
- One fewer `session_messages` scan per `GET /api/mentions`.
- The prose that taught the old model is gone from the module, the route,
  `main.py`, the client, both mounts, and the gate — *"never clears by
  scroll-by"* was true and is now false, so it does not survive anywhere as a
  comment that reads as live.
