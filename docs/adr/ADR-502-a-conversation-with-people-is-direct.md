# ADR-502 — A Conversation With People Is Direct: the Reply Set Derives From the Cast

**Status**: Accepted (2026-07-29, operator-observed — "adding seulkim88 to a chatroom from creation automatically inserts claude sonnet"). Implemented same day.
**Date**: 2026-07-29
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A
**Dimension**: Identity (Axiom 2 — who acts) + Channel (Axiom 6)
**Relates to**: ADR-495 (the Conversation = participants + turns; the cast IS the object), ADR-408 A2 (the engine is the member's hands, never a principal), ADR-500 (the person-picker create path), ADR-411 (member attribution)
**Amends**: nothing — this rule was latent in ADR-495's object model; the turn runner just never read the cast.

---

## 1. The defect

Starting a conversation with a person (the ADR-495 people picker) created a lane whose pinned engine answered every message: "hey", addressed to a colleague, got "Claude Sonnet is working…". The header and list labeled the conversation by the engine, so a chat WITH seulkim read as a chat WITH Claude Sonnet. Live receipt: lane `1ee9f2eb`, cast = two humans, zero agents — and the engine replied anyway.

The cast was already right (the create path deliberately picks no agent — ADR-500's fix noted "choosing a person is choosing a person"). The turn runner ignored it: every lane turn invoked the lane's model unconditionally.

## 2. D1 — The reply set derives from the cast, at turn time

Rule (in `_turn_stream_response`, so it covers send AND regenerate):

> **Two or more humans with NO agent in the cast → the turn persists and broadcasts; nobody auto-replies.** One human (a solo lane) → the engine IS the conversation, today's behavior. Add an Agent to the cast and replies begin; remove it and they stop.

Stateless and retroactive: derived from `conversation_members` per turn, so existing person-conversations became DMs with no migration, and the dormant engine remains the capacity an added Agent will use. The DM path runs before the draw gate — a broadcast turn costs nothing and is not metered.

## 3. D2 — Authorship in a multi-human transcript

A DM's user rows stamp `authored_by = member:{user_id}` + `author_principal_id` metadata. The FE aligns own-vs-other (foreign rows left, with the author's label) — previously every `user` row right-aligned as "you", which made a two-human transcript unreadable. Edit-and-resend now verifies the row's author (`author_principal_id`) server-side — role=user alone would have let one participant truncate the other's words. The FE hides the edit affordance on foreign rows to match.

## 4. D3 — Labels follow the humans

An agent-less conversation with other humans is labeled BY those humans (list, header, sub-label "Direct chat"); the engine label renders only where the engine genuinely is the counterpart (solo/pre-registry/Studio lanes — "its engine is what it is").

## 5. D4 — Delivery to the other participant

The `done` frame carries `direct: true` so the sender's UI drops the reply placeholder (no "[no reply]" lie). The recipient's transcript refreshes on a slow poll while a direct conversation is open — Realtime is blocked by the creator-scoped `session_messages` RLS (the ADR-501 §6 deferred item); when that RLS learns the cast, the poll retires.

## 6. What is deliberately NOT here

- **The "you were added" signal.** Visibility is correct (the list is cast-scoped ∩ acting workspace — the added member sees the conversation when bound to that workspace via the switcher), but nothing NOTIFIES them. That is the ADR-495 owed notifications/@mentions item, operator-deferred to post-stabilization; this ADR does not preempt it.
- **@-mentioning an agent from inside a DM** — arrives with the same deferred work.

## 7. Validation

`api/test_adr502_503_gate.py` (source-anchored) + `py_compile` + `tsc` + `next build`. Behavioral verification needs two browsers (owner + member) — expected: the member bound to the shared workspace sees the conversation; a message broadcasts without an engine reply; each side sees the other's rows left-aligned with their email.
