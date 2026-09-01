# ADR-625 + ADR-626 click-pass — two agents in one room, driven in production

**Date**: 2026-09-01 · **Build**: `d0a876e` (ADR-626) live; `314b7c7` (the delete) deploying
**Principal**: `kvkthecreator@gmail.com` (owner) · workspace `d5b9029b…` · lane `fda32b61…`
**Lane**: surface (`browser`) — PASS/FAIL per step, both halves per step.

---

## Verdict

**PASS, and the strongest single receipt is Supervisor's own reply.** Every
ADR-626 decision is visible in one answer produced by the live system, from an
agent that had no way to fake it.

---

## The receipt

Asked, in a room holding **KVK + Editor + Supervisor**:

> *"@Supervisor who else is in this conversation right now? Name every
> participant you can see, and say which of the earlier messages here were
> written by you versus by someone else."*

Supervisor answered:

> "**Participants named in this conversation:** KVKtheCreator — the member (a
> person) · Editor — a colleague described to me as writing "with you — decks
> and documents" · Me — Supervisor…
>
> The reply that follows, which **opens with the line "Editor: I can't actually
> see the image…"** — that turn is **explicitly prefixed Editor**, so per the
> transcript it was written by Editor, **not by me. I did not generate that
> response.**"

Read against the three findings ADR-626 was written for:

| Finding | What the reply proves |
|---|---|
| **F1** — the transcript had no authorship | Supervisor quotes the literal prefix `Editor:` and uses it to disclaim the turn. **D1's tagging is working**, and the agent reasons *from* it rather than guessing. |
| **F2** — humans were anonymous (`- another person`) | It names **KVKtheCreator**, not "another person". **D2's enricher is reached on the turn path.** |
| **F1, multi-agent half** | Before this change, agent A read agent B's replies as its own `assistant` turns. Supervisor explicitly says **"I did not generate that response"** — the exact confusion the change removes. |

Two further properties fall out of the same answer, unprompted:

- **The responder tags itself.** Supervisor identifies its own message as its
  first in the room — only possible because the tagging is symmetric (D1's
  "a transcript naming only the others implies the untagged turns are its own").
- **It does not over-claim.** *"I have no visibility into anything beyond…"* —
  the cast section is a roster, not omniscience, and the agent reads it that way.

---

## Steps

| # | Step | DOM half | Substrate half |
|---|---|---|---|
| 1 | **ADR-625 D2** — the add door offers beings | ✅ Details → Add lists **AGENTS: Supervisor**. Pre-ADR-625 this read the empty `offered` roster and rendered **nothing**. | — |
| 2 | Adding a resident succeeds | ✅ panel flips to "3 IN THIS CONVERSATION" | ✅ `conversation_members` gains `agent/supervisor`, `window=0`, `2026-09-01T02:03:19` |
| 3 | Header reflects the room | ✅ **"Editor, Supervisor · 3 members"**; lane row in the list matches | — |
| 4 | **ADR-626 D1/D2** — the agent perceives the room | ✅ the reply above | ✅ 4 messages, authorship on every row |
| 5 | Responder selection is recorded | — | ✅ `seq2 editor reason=sole_agent` · `seq4 supervisor reason=addressed` — the rung *changed* when the room did, and the `@mention` outranked continuity exactly as ADR-495's precedence says |

Step 5 is worth its own line: `sole_agent` → `addressed` is the five-rung
ladder observed shifting under a real room change, not asserted in a unit test.

---

## What this does NOT prove

- **Agent-to-agent turns.** Still refused by construction, deliberately
  (ADR-626 D4). Supervisor *named* Editor and could have suggested addressing
  it; it cannot cause Editor's turn. Unchanged and intended.
- **The multi-HUMAN axis.** This room had one person, so `tag_humans` was False
  and only the agent axis fired. The human axis is covered by the driven gate
  (`test_adr626` §3b) but has not been seen in production. **The honest gap.**
- **D3's window clamp.** Both members joined at `window=0`, so `max()` had
  nothing to narrow. Gate-covered, not observed.

---

## Method notes

- **A synthetic `.value` set does not arm React's Send.** Setting `textarea.value`
  directly left Send disabled; the working form is the native setter
  (`Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set`)
  plus an `input` event.
- **A loose button match hit "Edit and resend".** Matching `/send/i` across the
  whole document selected the message-hover action and put the composer into
  edit mode — which, had it gone through, would have **replaced the transcript
  tail** and destroyed the very history under test. Scope the query to the
  composer's own `<form>`.
- The composer placeholder still reads **"Message Editor…"** in a two-agent
  room. Cosmetic, not a defect against any ADR-626 decision — the responder is
  the cast's to choose per turn, and it chose correctly here. Worth a look when
  the multi-agent room stops being a test case.
