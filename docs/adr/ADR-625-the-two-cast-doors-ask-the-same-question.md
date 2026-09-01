# ADR-625: The two cast doors ask the same question

**Status**: Ratified 2026-09-01 (operator observation from the live product:
*"we do allow our agents in the chat. please confirm and remove this statement
if structurally true."*). Implemented same day.

**Supersedes** ADR-600 D3's `offered` check at the add-participant door.
**Builds on** ADR-614 D1 (the chat door leads with colleagues) · ADR-495 D1
(the cast is the single authority on who replies) · ADR-599 D1 (the offered
roster is empty) · ADR-601 D1 (capability lives at the app).

**`offered` is NOT deleted** — it keeps its meaning and its other readers. See
D3.

## Context

The operator read the being page's **"Add to a chat — No — you find them in
their app"** against a New chat modal that was, on the same screen, offering
both Editor and Supervisor as the primary way to start a conversation. Two
surfaces of one product, contradicting each other.

Audited at execution rather than by name, the contradiction is real and it is
in the API, not the copy:

| Door | Gate | Result for a resident |
|---|---|---|
| `POST /api/lanes` (New chat) — seeds the cast with the named colleague | `resolve_agent` only | **ALLOWED** |
| `POST /api/lanes/{id}/participants` (add to a chat you are in) | `resolve_agent` **+ `offered`** | **REFUSED 422** |

**These are the same act**, and ADR-614 D1 says so in its own words: picking a
colleague at the door *"seeds the CAST: the same act as adding them from
CastBar a second later, done at the door."* One act, two doors, opposite
answers.

**Measured in production 2026-09-01, before any change**: 74 agent cast rows in
the workspace, **every one of them an `offered: False` being** — editor 36 ·
designer 33 · supervisor 5 (of 79 total; the other 5 name slugs ADR-599 deleted). Members
chat with residents constantly. The refusal was not protecting an invariant; it
was contradicting the shipped product.

### Why nobody hit the 422

The add door's list is `agents` — the `offered` roster — which is **empty**
(ADR-599 D1). So it rendered no rows to refuse. The gate was unreachable from
the UI, which is why a contradiction this size survived: **one door was open,
the other was not merely closed but blank.** The member-visible symptom was
therefore not an error message but a page that stated the opposite of what the
product did.

### Which side was right

ADR-600 D3's reasoning was sound for the world it was written in: *"a desk's
resident was accepted into any chat lane's cast while the roster offered
nobody, so the API contradicted its own surface."* That is the ADR-373 D6
incorrect-success class, correctly identified.

**Then the premise moved.** ADR-614 D1 made naming a colleague the PRIMARY way
to start a chat — and did not add an `offered` check, because a colleague at
that door is the intent, not an invitation. From that commit onward the
contradiction D3 fixed existed again, in the opposite direction and with the
product's blessing.

The open side is right. `offered: False` means *its home is a desk — met where
it works* (the registry's own words). That is a statement about **where a
member FINDS a being**, and it was being enforced as a statement about **where
a being may WORK**. A resident answering in chat about the deck it is helping
you write is not a violation of anything; it is the product.

## Decision

### D1 — The add door gates on RESOLVABILITY, not on `offered`

`resolve_agent` is the gate: an unknown slug is still refused with its reason
(`No agent called '…'`). The `offered` check and its "works at a desk" refusal
copy are deleted. The two doors now ask one question, so the act cannot depend
on which one the member happened to use.

### D2 — The add door OFFERS what the New chat door offers

`ConversationDetail`'s invitable list reads `beings` (every being that exists),
not `agents` (the offered roster). It falls back to `agents` for an older
envelope — the same degradation the naming map beside it already uses.

A door whose server-side gate is open but whose list is empty is not a closed
door; it is a broken one. Both halves move together, deliberately: fixing only
the gate would leave the blank list, and fixing only the list would surface the
422.

### D3 — `offered` KEEPS its meaning, and its other readers

Not deleted, not deprecated. It still answers *"is this being on the roster a
member picks from"* — `list_agents()` (the hire roster) and `is_promoted`'s
no-desk clause both read it, unchanged.

`offered` is a **presentation** question, in the same family as `is_promoted`
(the registry says exactly this: *"`offered` is REACH, never authority"*). This
ADR's correction is that a cast door is **not a presentation** — it is an act,
and gating an act on a presentation field is the category error. The ADR-460
D3.a cliff is untouched: nothing here grants a being authority, and no field
names another being.

### D4 — The being page states what is true

`Add to a chat` now reads **"Yes — start a chat with them, or add them to one
you are in."** unconditionally, because after D1/D2 it is unconditionally true.
The `being.offered` branch is deleted rather than re-worded: a conditional whose
two arms can no longer differ is a branch waiting to state something false
again.

## Consequences

- One act, one answer, at both doors. A member who meets Supervisor at the
  Strings desk can bring it into a conversation, and the page that describes
  that no longer contradicts the modal beside it.
- The 74 live cast rows are retroactively *correct* rather than tolerated —
  they were always what the product did.
- If the offered roster is ever repopulated (ADR-599 D1's "until the
  scaffolding stabilizes"), `list_agents` lights up with no edit here: this ADR
  removed a gate, not the field it read.
- Gate: `test_agent_registry.py` §6 is **INVERTED** — it asserted the `offered`
  check and the desk-refusal copy were present; it now asserts both are gone,
  that resolvability still refuses an unknown slug, and (**new**) that
  `create_lane` does not grow an `offered` check either, so the pair cannot
  diverge again in the opposite direction. Falsified: re-injecting the check
  takes it 120/122.
- Named, not answered: the add door and the New chat door still render from two
  different components with two different list-building expressions. They agree
  now by construction of this ADR; a shared selector would make them agree by
  construction of the code. Not built — one duplication is not yet a pattern.
