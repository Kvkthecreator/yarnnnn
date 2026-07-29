# ADR-495: The Conversation — One Object, One Cast, One Visibility Question

**Status:** **IMPLEMENTED 2026-07-29** (drafted from the lifecycle discourse, **rewritten in full
the same day** after the operator's species-blind challenge — see §1.3 — then built, commit
`c643282`. The first draft carried a `scope: private|shared` column and a fork-on-human-invite
rule; both were species law in substrate costume and are deleted, not deprecated. What survives is
smaller and over-determined.)

> **Build receipts (2026-07-29).** Migration 226 applied to prod: 49 human + 32 agent participants
> backfilled at window 0; `conversations` + `conversation_messages` dropped (0 rows, verified empty
> immediately before the run); 0 conversations left without a human participant. `routes/rooms.py`
> (521 LOC) + `RoomPanel.tsx` (405 LOC) deleted into `lanes.py` + `CastBar.tsx`; net **−50 lines**
> while adding the cast, the window, and the invite. Gate `api/test_adr495_conversation.py` 12/12,
> including the ADR-405 §5 ratchet (an AST walk over If/IfExp test nodes proving no access function
> branches on participant class — substring greps would have passed `select("member_kind, …")` and
> failed honest code, so it inspects the tree). **Live prod probe** on a real 4-turn conversation:
> owner floor 0 · stranger floor None · defaults agent=0/human=5 · a from-now participant sees
> **0 of 4** turns · re-invite does not widen · removal revokes. Siblings green (ADR-411 14/14,
> registry 169/169); `test_adr407_phase4_chat_scope` 16/1 with the 1 **pre-existing at HEAD**
> (clean-worktree verified, unrelated). FE tsc + full `next build` clean.
>
> **Not built, per D6:** notifications/attention wiring (deferred to post-stabilization by operator
> ruling), human-`@mention` parsing, streaming for multi-participant conversations. A peer's
> message still reaches no attention surface — the standing honest gap.
**Dimensions:** Identity (primary — the cast is the model) + Substrate (one store) + Channel (one
surface grammar)
**Relates to:** ADR-405 (the witness dial — **§5's test is the instrument that killed this ADR's
first draft**; D4's "asymmetries are dial settings, not species rules" is the precedent D3 leans
on), ADR-373 (every actor is a principal with a grant; class defaults, not species law), ADR-492
(rooms — its two-store D2 is superseded here), ADR-460 §7 (the unified-object DEFER — **its stated
wait conditions have both arrived**), ADR-411 (the lane contract this generalizes), ADR-407 (DP35),
ADR-457 D2/D3 (settle; the transcript is never the system of record), ADR-408 D1 (the coworking
commons)
**Supersedes:** ADR-492 D2's two-store consequence and the `conversations` /
`conversation_messages` tables introduced by migration 225.
**Amends:** ADR-492 D6.b (scope-at-birth — **retired entirely**, see D2; the privacy *concern* is
preserved and relocated to the visibility window, which is a stronger and species-blind home);
ADR-492 D6.c (from a principle the code contradicted to one the code implements).
**Closes:** ADR-460 §7's DEFER on the unified Conversation object.

---

## 1. Context — three passes to the primitive

### 1.1 The lifecycle question

One day after rooms shipped (ADR-492, migration 225), the operator asked:

> *"What if a user selects a lane, but then wants to invite another agent or user? Think
> lifecycle. Shouldn't we have one single approach?"*

The audit found both invites walled, for one stated reason — ADR-492 D6.b, *scope is set at birth
and never flips* — that covered only one of them. Agent-invite was blocked by nothing but a scalar
(`lane_meta["agent"]`, `routes/lanes.py:287`), while ADR-492 D6.c explicitly permitted it. Canon
and code had disagreed since the day both were written.

### 1.2 The benchmark pass

The first repair kept `scope` as a column and made human-invite **fork** into a settle-seeded
child. The operator challenged it against conventional chat handling, and the challenge held:

- Slack / Teams: adding someone to a closed channel **prompts for history** (all / N days / none).
- WhatsApp / Signal: adding to a 1:1 makes a **new group** — and users read this as a limitation
  imposed by the crypto model, not as a feature.
- ChatGPT / Claude: an AI thread is **shared as a read-only snapshot**; the recipient does not join.

Nobody seeds a new conversation with a generated summary of the old one. The fork was not a chat
convention; it was invented. Worse, it charged a metered judgment call (a settle) for the act of
adding a participant.

### 1.3 The species-blind pass — the one that reached the primitive

The operator then removed the frame the whole design rested on:

> *"Take away the nuances of AI-think, or lanes or rooms. Treat AI (agents, or LLM counterparts)
> and humans alike. Shouldn't the invite and mechanisms also be levelled accordingly? And thus
> privacy should also be more primitive in nature."*

Applied honestly, this dissolves the design:

**There is no such thing as a private conversation.** What we called a private lane is a
conversation with two participants — the member and Freddie. It was never private in any primitive
sense: Freddie read every word. We called it private because we had decided in advance that one
participant *class does not count as a reader*. That is precisely the rule ADR-405 forbids.

The tell, stated plainly: the first draft agonized for an hour over whether adding a **human**
exposes history — and never once asked the same question about adding an **Agent** mid-conversation.
Same act, same disclosure, same transcript. Only the species differed, and only one triggered
concern. ADR-405 §5 is the instrument that catches this:

> *"Any future feature that wants to special-case 'AI edits' vs 'human edits' must instead answer:
> which grant, which act-class, which dial setting? If the feature can't be expressed in those
> three terms, it is reintroducing species law."*

`scope: private|shared` cannot be expressed in those terms. It is a proxy for *how many humans*,
which is a species distinction wearing a substrate costume. It is deleted here, not deprecated.

---

## 2. D1 — There is one Conversation object, and its model is the cast

A Conversation is **a set of participants and an ordered sequence of turns.** That is the whole
object.

- **Participants** are humans (by principal) and Agents (by slug). One list. No class field
  changes what a participant *is* — only the labeling and the grant defaults differ (D3).
- **A "lane" is a Conversation with one human and one Agent.** A "room" is a Conversation with
  more participants. These were never different objects; the distinction was an implementation
  artifact that leaked into the vocabulary and confused its own authors (the operator, one day
  after the build: *"is it lanes or rooms right now that we created?"*).
- **There is no `scope` field.** Nothing to set at birth, nothing to flip, nothing to fork. A
  conversation with one human is *narrow*; add a second and it is wider. Nothing changed class —
  the membership changed, which is what membership is for.

This is ADR-460 §7's unified object, arriving on the two conditions the DEFER named (`cast` needed
the Agent registry; the shared case needed rooms — both shipped). It is now **simpler** than that
sketch, because the third field the sketch carried (`scope`) turns out not to exist.

## 3. D2 — Privacy is not a property of the conversation; it is who can read it, from when

Privacy was never a conversation attribute. It is a **read grant**, and this codebase already has
that primitive (ADR-373: every actor is a principal with a grant).

- A Conversation is readable by **its participants**. Full stop. Not by workspace grant-holders at
  large, not by scope class — by cast membership.
- **Adding a participant grants read access.** That is what adding a participant *means*.
- The only real question is therefore **the visibility window: from when may this participant
  read?** — asked identically of a human and of an Agent.

This is where ADR-492 D6.b's concern *relocates*, and it lands in a stronger home. D6.b protected
something real — a member's unfinished thinking should not become readable by surprise. But it
protected it with a wall keyed on species, which (a) blocked Agent-invite for no reason, and (b)
left the actual disclosure question unasked in the case it did permit. The visibility window
protects the same interest, species-blind, at per-invite granularity.

**The window anchors on `session_messages.sequence_number`** — a monotonic per-conversation
ordinal that already exists and is already uniquely indexed (`unique_sequence_per_session`). A
participant row carries `visible_from_sequence`; the transcript read filters on it. Three
settings cover the space, and they are the settings the benchmark tools converged on
independently:

| Setting | `visible_from_sequence` | Meaning |
|---|---|---|
| **Full history** | `0` | the participant sees everything |
| **From now** | current max + 1 | the participant sees only what follows |
| **From a point** | chosen ordinal | the member picks where the participant joins |

That the Slack/Teams convention and the first-principles derivation converge on the same three
options is corroboration, not coincidence: it is the only question the situation actually poses.

**Consequences:**
- **No retroactive surprise is possible** — a window is chosen at invite time, explicitly, by the
  member doing the inviting.
- **No fork, no settle-on-invite, no metered charge for adding someone.** The costs and the
  invented semantics of the first draft go away entirely.
- **The window is append-only in effect**: widening a participant's window later is a new
  disclosure decision, and it is an attributed act like any other. Narrowing it does not un-read
  and is not offered as a privacy control (an honest limit, stated rather than implied).
- **`conversation_members` gains one column** and is otherwise unchanged from migration 225.

## 4. D3 — One invite mechanism; the defaults differ, and that is not species law

There is **one** invite: *add a participant, with a visibility window.*

Defaults differ by participant class, and the operator ruled in-discourse that grant defaults are
an upstream matter — a dial setting, not a species rule. ADR-405 D4 is the governing precedent
("the asymmetries that remain are dial settings, not species rules"), and the ADR-405 §5 test
passes cleanly: this is expressible as *which grant, which act-class, which dial setting.*

Indicative defaults, all overridable per invite, none enforced by a rule that reads the class:

- **Agent** → full history. An Agent that cannot see the conversation cannot be useful in it; this
  is also what already happens today and preserves current behavior byte-for-byte.
- **Human** → from now. A colleague usually does not need your false starts, and this is the
  conservative default when the disclosure is irreversible.

A member may set either to any window. No code path branches on species to *decide* the window —
it branches only to *pre-select* one, exactly as file-permission defaults differ without the
permission model caring.

**This closes ADR-492 D6.c**, which said Agent-invite crosses no boundary while the code made it
impossible. `lane_meta["agent"]` (a scalar) retires into the cast; a Conversation may hold N
Agents; addressing selects which one answers (ADR-492 D3, unchanged). Multi-engine-in-one-thread
is therefore not a picker feature and not "a room" — it is a Conversation with two Agents in the
cast.

## 5. D4 — The store is `chat_sessions`, grown; `conversations` is dropped

The unified object lands in **`chat_sessions` + `session_messages`**, not the ADR-492 tables.

Direction of travel is decided by mass and coupling, not recency:

- `chat_sessions` carries **87 references across 25 non-test files**, most of them *not* chat
  features: narrative (`services/narrative.py`), working memory, session continuity, wake queue,
  MCP, purge, workspace init. It is a workspace-wide substrate object that chat happens to use;
  folding it into a chat-owned table would drag all of that behind a chat noun.
- `conversations` has **3 non-test references** and, read against prod 2026-07-29, **zero rows**
  (0 conversations, 0 messages — shipped 2026-07-28, never used).

So this is not a two-way merge of populated stores. It is *delete the empty one and grow the real
one*: no data migration, no dual-read window, no backfill, no compatibility shim. The dual
approach to delete turns out to be the newer half — the cheapest possible moment to correct it.

**Retained:** `conversation_members` (well-shaped, empty) — re-pointed at `chat_sessions.id`, plus
`visible_from_sequence`. **Dropped:** `conversations`, `conversation_messages`.
`routes/rooms.py` folds into `routes/lanes.py` and is deleted; `api.rooms.*` folds into
`api.conversations.*`; `RoomPanel` folds into one panel.

**DP35 is satisfied without amendment.** The first draft proposed making `chat_sessions`
scope-bearing and amending DP35 to allow it. With `scope` deleted, there is nothing to amend:
`chat_sessions` rows remain what DP35 declared them, and read authorization derives from cast
membership — a grant question, which is where DP35 always wanted it.

## 6. D5 — One noun: conversation

Two nouns for one object caused the confusion this discourse opened with.

- **In code:** one noun — `conversation`. `lane` and `room` retire as object terms.
- **In the operator surface:** "conversation." Not "private conversation" or "shared conversation"
  — those states no longer exist. A conversation has participants; the member sees who.
- **Grandfathered:** `session_type='lane'` and the `chat_sessions` table name stay (relabel-keep-slug,
  ADR-251/ADR-381 precedent). Renaming a live table with 87 call sites to serve vocabulary is the
  churn Singular Implementation exists to prevent, not cause.

## 7. D6 — What this ADR does not do

- **No notifications.** Operator-ruled: attention wiring waits for core-infra stabilization.
  Standing honest gap, unchanged: a peer's message and an `@mention` reach no attention surface.
- **No human-`@mention` parsing** — it belongs with notifications; a mention routing nowhere is
  theatre.
- **No streaming for multi-participant conversations, no presence, no typing indicators, no read
  receipts.** ADR-492 §6 non-goals carry forward.
- **No per-turn engine picker.** Responder selection is addressing (ADR-492 D3); engines stay
  behind Agent names (ADR-460).
- **No merge/CRDT.** Append-only; ADR-406's appender rule holds.
- **No change to never-ambient.** A model turn fires only on a human act, at every cast size.
- **No fork, no scope, no settle-on-invite** — deleted with the first draft, recorded here so a
  future session does not re-derive them.
- **No narrowing of an existing participant's window as a privacy control** — it does not un-read.
  Stated as a limit rather than implied.

## 8. The build shape

Indicative; each step its own commit with its own gate.

1. **Schema** — `conversation_members` re-pointed at `chat_sessions.id` + `visible_from_sequence`;
   drop `conversations` + `conversation_messages`. Existing conversations backfill one human
   participant (the owner, window `0`) and their Agent if `lane_meta["agent"]` is set (window `0`)
   — byte-identical behavior.
2. **Fold** — `routes/rooms.py` → `routes/lanes.py`; one runner path (the `ledger_slug`
   distinction is retained for metering legibility, keyed on cast shape, not on a scope field);
   `api.rooms` → `api.conversations`; one panel.
3. **Cast** — `lane_meta["agent"]` scalar → participant rows; add/remove participants in any
   conversation; addressing generalizes.
4. **Visibility window** — the invite carries a window; transcript reads filter on it; the
   composer's participant list shows who can see what.
5. **Falsifier repair** — `services/falsifiers.py:97` filters `.eq("slug","lane")` and joins
   `chat_sessions`; the fold changes what it sees. Updated in the same wave so the ADR-492 §7
   per-phase comparison stays honest against the recorded baseline
   (`docs/analysis/w0-falsifier-baseline-pre-rooms-2026-07-28.md`).

Gates: ADR-492's rooms gate is rewritten as the conversation gate (never-ambient, attribution
verbatim, grant-gated membership, no notification writes — all survive the fold and must keep
passing); ADR-411's lane gate stays green throughout (one-human-one-Agent conversations
byte-identical); a **new gate asserts no code path branches on participant species to determine
read access** — the ADR-405 §5 test, mechanized, so the rule this ADR was rewritten to obey is
enforced rather than remembered.

## 9. Ratification points

1. **D1** — one Conversation object; participants + turns; no `scope` field; lane/room were
   implementation artifacts.
2. **D2** — privacy is a read grant scoped to the cast; the one question is the visibility window,
   anchored on `sequence_number`; ADR-492 D6.b's concern relocates here and its wall is retired.
3. **D3** — one invite mechanism, species-blind; class-differing **defaults** are dial settings per
   ADR-405 D4, not species law. Closes ADR-492 D6.c.
4. **D4** — the store is `chat_sessions` grown; `conversations`/`conversation_messages` dropped;
   `conversation_members` retained, re-pointed, one column added. DP35 needs no amendment.
5. **D5** — one noun; `session_type='lane'` and the table name grandfathered.
6. **D6** — the non-goals, in particular notifications deferred to post-stabilization.
7. The **supersession** of ADR-492 D2 and the **amendment** of D6.b/D6.c as declared in the header.
8. The **species-blindness gate** (§8) as a permanent CI ratchet, not a one-time review.
