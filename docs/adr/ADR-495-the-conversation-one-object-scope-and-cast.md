# ADR-495: The Conversation — One Object, Scope and Cast; the Invite That Forks

**Status:** Proposed (drafted 2026-07-29 from the lifecycle discourse — the operator's question:
*"what if a user selects a lane, but then wants to invite another agent or user? Think lifecycle.
Shouldn't we have one single approach?"*). Aligned in-discourse on the shape below (one
Conversation object; scope + cast; human-invite FORKS rather than flips; singular codebase with
the dual approach deleted, not shimmed; the noun collapses to **conversation**). Implementation
is a separate go.
**Dimensions:** Substrate (primary — one store) + Identity (cast) + Channel (one surface grammar)
**Relates to:** ADR-492 (rooms — its two-store D2 is superseded here; its D6.b concern is
preserved and its overreach removed), ADR-460 §7 (the unified-object DEFER — **its stated wait
conditions have now both arrived**), ADR-411 (the lane contract this generalizes), ADR-407 (DP35
one-scope-per-store — satisfied differently, see D3), ADR-457 D2/D3 (diverge privately, settle
publicly; the transcript is never the system of record), ADR-408 D1 (the coworking commons),
ADR-405 (the witness dial — permission is grant, never species)
**Supersedes:** ADR-492 D2's two-store consequence (shared conversations as a *separate object*)
and the `conversations` / `conversation_messages` tables introduced by migration 225.
**Amends:** ADR-492 D6.b (scope-at-birth → **disclosure-safe fork**; the privacy rule survives,
the structural wall does not); ADR-492 D6.c (from a principle the code contradicted to one the
code implements).
**Closes:** ADR-460 §7's DEFER on the unified Conversation object.

---

## 1. Context — the question this settles

ADR-492 shipped rooms as a second object beside lanes (migration 225). One day later the
operator asked the lifecycle question, and it exposed an incoherence the two-object model could
not answer:

> A member is in a lane with an Agent. They want to bring in another Agent — or a colleague.
> What happens?

Today: **nothing can happen, in either direction.** Both are walled, and ADR-492 D6.b states one
reason for both walls — *scope is set at birth and never flips.*

The audit found that reason only covers one of the two cases:

| Act | Blocked today | Justified by D6.b's reasoning? |
|---|---|---|
| Add an **Agent** to a lane | Yes — `lane_meta["agent"]` is a scalar (`routes/lanes.py:287`) | **No.** ADR-492 D6.c explicitly says an Agent invite "crosses no scope boundary — the Agent is the member's hands, so the lane stays private." Canon permits it; the code never did. |
| Add a **person** to a private lane | Yes | **Yes** — but only for the privacy half of the argument (below). |

So one wall enforces a real rule and the other enforces nothing. The member experiences both as
the same refusal, which is why the surface reads as arbitrary.

### 1.1 The two halves of D6.b, separated

D6.b's rationale was twofold. They are not equally load-bearing:

- **The privacy ratchet (STRONG, preserved in full).** A private conversation holds half-formed
  thinking — dismissed ideas, unfinished takes, possibly remarks about a colleague. If inviting
  a human flipped the scope, *every prior turn would become readable retroactively.* That is a
  disclosure event, not a scope change, and it is irreversible: you cannot un-read. This survives
  as an absolute.
- **The store crossing (WEAK, retired).** D6.b also credited itself with dissolving "the DP35
  store-crossing migration: no conversation row ever changes store class mid-life." This is an
  implementation consequence presented as a principle. We *chose* the two-store layout; that
  choice cannot also be the reason the layout can't change. ADR-495 removes the premise instead
  of obeying it.

### 1.2 Why now, and not later

ADR-460 §7 deferred the unified object with an explicit condition:

> "`cast` can't be specified before the registry exists; `scope: shared` can't before rooms.
> The object is the right *end-state description* — declaring it now buys a migration you can't
> fill in. Amend ADR-411 in place a third time, from evidence."

**Both conditions have arrived.** The Agent registry shipped (`services/agents_registry.py`,
ADR-460/467); rooms shipped (ADR-492, migration 225). The DEFER's own stated expiry is met, and
the evidence it asked to wait for is exactly the lifecycle gap this ADR answers. This is not a
schedule jump; it is the deferred item arriving on the condition it named.

### 1.3 The decisive receipt — the collapse is cheap

Read against prod 2026-07-29, workspace `d5b9029b-bd4e-4757-9fcb-e2b139fd4913`:

```
chat_sessions:          49 lane + 13 thinking_partner
session_messages:       164
conversations:          0        ← shipped 2026-07-28, never used
conversation_messages:  0
```

**The new store is empty.** This is therefore not a two-way merge of populated stores; it is
*delete the empty one and grow the real one*. No data migration, no dual-read window, no
backfill, no compatibility shim. The "legacy dual approach" to delete turns out to be the
*newer* half — which is the cheapest possible moment to correct it, and the reason this ADR is
worth writing one day after ADR-492 rather than one quarter after.

---

## 2. D1 — There is one Conversation object

The Conversation is a single substrate object with two orthogonal facts:

- **`scope`** — `private` (one human's working context) or `shared` (a workspace-content object,
  readable by grant-holders).
- **`cast`** — the members: humans by principal, Agents by slug.

A **lane** is not a different object. It is the degenerate Conversation: `scope: private`, cast
of one human plus N Agents. A **room** is `scope: shared` with two or more humans. Nothing else
distinguishes them.

This is ADR-460 §7's end-state description, now buildable because the two facts it named are
both specifiable.

**What this forbids** (the singular-implementation edge, extending ADR-492 D1): no second
conversation store, no parallel runner, no parallel settle path, no parallel notification story.
One grammar, one owner (Chat), one table set.

## 3. D2 — The store is `chat_sessions`, grown; `conversations` is dropped

The unified object lands in **`chat_sessions` + `session_messages`**, not in the ADR-492 tables.

Rationale — direction of travel is decided by mass and by coupling, not by recency:

- `chat_sessions` carries **87 references across 25 non-test files**, and most are *not* chat
  features: narrative (`services/narrative.py`), working memory, session continuity, wake queue,
  MCP, purge, workspace init. `chat_sessions` is a workspace-wide substrate object that chat
  happens to use. Folding it into a chat-owned table would drag all of that behind a chat noun.
- `conversations` has **3 non-test references** and zero rows.

Moving 3 references into 87's home is the small direction; the reverse is not.

**Retained from migration 225:** `conversation_members` — the cast table is well-shaped
(humans by `principal_id`, Agents by `agent_slug`, `invited_by` as the attributed act, partial
unique indexes per kind) and empty. It is re-pointed at `chat_sessions.id`.

**Dropped:** `conversations`, `conversation_messages`. `routes/rooms.py` folds into
`routes/lanes.py` and is deleted. `api.rooms.*` folds into `api.conversations.*` on the FE.

### 3.1 DP35 — satisfied, not violated

ADR-407's DP35 says one scope per store, and ADR-492 D2 read that as *therefore shared
conversations need a second table*. That reading is re-examined here.

DP35's purpose is that a store's rows must not silently mix member-private state with workspace
content, because the two have different read-authorization and different lifecycle. ADR-495
satisfies that purpose by making scope an **explicit, indexed, gate-consulted column** rather
than an implicit property of which table a row sits in. The authorization boundary becomes a
predicate the gate reads, not a fact only the schema knows.

`chat_sessions` is re-declared in `services/scope_manifest.yaml` as **scope-bearing**: its rows
are member-experience when `scope='private'` and workspace content when `scope='shared'`. This
is a manifest change and a DP35 amendment, and it is named as such rather than smuggled.

The guard that makes this safe is D4: a row's scope is **append-only** — `private` may fork to a
new `shared` row, but no row's own scope is ever mutated. So no row changes class mid-life, which
was DP35's operative concern.

## 4. D3 — Two invites, finally distinct

The single "invite" gesture resolves by *who* is invited and *what scope* the conversation is:

| Invite | Into `private` | Into `shared` |
|---|---|---|
| **Agent** | Additive. Cast grows. Scope unchanged. No one new can read. | Additive. Cast grows. |
| **Human** | **FORKS** (D4) — never flips. | Plain membership add, attributed. |

**Agent-invite is now implemented, not merely permitted.** `lane_meta["agent"]` (a scalar, fixed
at creation) retires into the cast. A private conversation may hold N Agents; addressing selects
which one answers, exactly as in a room. This is ADR-492 D6.c's stated rule, which the code
contradicted from the day it was written.

This also lands ADR-492 D3's claim that "multi-engine-in-one-thread is not a picker feature; it
is a room with two Agents invited" — with the correction that it need not be a *room*. It is a
conversation with two Agents invited, private or shared.

## 5. D4 — The human invite forks; retroactive disclosure never happens

Inviting a human into a `private` conversation **creates a new `shared` Conversation** and leaves
the private one untouched and private, permanently.

The child is seeded with a **settle distillate** — the ADR-457 D3 verb, already built
(`services/settle.py`), which distils a conversation into an authored artifact. Never the raw
transcript. The private turns are never copied, never exposed, never reachable by the invitee.

This is ADR-492 D6.b's bridge ("start a room from here… seeds the distillate, never the raw
transcript") promoted from a *manual affordance the member must think of* to **the semantics of
the invite gesture itself**. The member reaches for the intuitive act ("bring Sara in") and gets
the disclosure-safe outcome by construction, rather than being refused and told to go find a
different verb.

Properties:
- **No retroactive disclosure, ever.** Not "with a warning" — structurally impossible. The
  invitee's conversation begins at the fork.
- **The fork is attributed** — a real act on the timeline, with a `forked_from` pointer in the
  child's metadata for provenance.
- **Scope is append-only.** No `UPDATE chat_sessions SET scope='shared'` exists in the codebase;
  a gate test asserts its absence. This is the invariant that keeps D3.1's DP35 amendment honest.
- **Cost is disclosed.** A settle is a metered judgment call (draw-gated per ADR-491 §9). The
  fork inherits that gate and the member sees the act, not a silent spend.

**Open sub-question (deliberately not closed here):** whether the member may fork from a *chosen
point forward* (share from here on) in addition to the distillate. It is disclosure-safe by the
same construction and may be the more intuitive default for a conversation the member never
intended to keep private. Deferred to the implementation discourse rather than guessed at now.

## 6. D5 — The noun collapses to "conversation"

Two nouns for one object is the dual approach at the vocabulary layer, and it is a direct cause
of the confusion this discourse opened with (the operator, one day after the build: *"is it lanes
or rooms right now that we created?"*).

- **In code:** one noun — `conversation`. `lane`/`room` retire as object terms. `lane_meta`
  amends in place (ADR-460 §7's "amend ADR-411 a third time, from evidence" — this is that
  amendment).
- **In the operator surface:** "conversation" is the object; **"shared"** and **"private"** are
  its states. "Room" may persist as informal UI shorthand for a shared conversation where it
  reads more naturally than "shared conversation" — but it names a *state*, never a second thing.
- **Grandfathered:** the `session_type='lane'` enum value and the `chat_sessions` table name stay
  (GLOSSARY Exceptions pattern, ADR-251/ADR-381 precedent: relabel-keep-slug). Renaming a live
  table with 87 call sites to serve vocabulary is the kind of churn Singular Implementation is
  meant to prevent, not cause.

## 7. D6 — What this ADR does not do

- **No notifications.** Operator-ruled in-discourse: attention wiring waits for core infra
  stabilization. Building the attention derivation against a two-object model and then adapting
  it is exactly the double-build this sequencing avoids. (Standing gap, unchanged and honest:
  a peer's message and an `@mention` reach no attention surface today.)
- **No human-`@mention` parsing.** It belongs with notifications; parsing a mention that routes
  nowhere is theatre.
- **No streaming for shared conversations, no presence, no typing indicators, no read receipts.**
  ADR-492 §6 non-goals carry forward unchanged.
- **No per-turn engine picker.** ADR-492 §6 + ADR-460: responder selection is addressing; engines
  stay behind Agent names. Multi-engine arrives as multi-Agent cast (D3).
- **No merge/CRDT.** Conversations are append-only; ADR-406's appender rule holds — no CAS
  precondition on messages.
- **No change to the never-ambient invariant.** A model turn fires only on a human act, in a
  private conversation with one Agent exactly as in a shared one with four.

## 8. The build shape

Indicative; each step is its own commit with its own gate.

1. **Schema** — `chat_sessions.scope` (`private` default, indexed); `conversation_members`
   re-pointed at `chat_sessions.id`; drop `conversations` + `conversation_messages`. Every
   existing row is byte-identical (`scope='private'`).
2. **Fold** — `routes/rooms.py` deleted into `routes/lanes.py`; one runner path
   (`ledger_slug` distinction retained for metering legibility — a shared conversation's spend
   stays separable); `api.rooms` → `api.conversations` on the FE; `RoomPanel` folds into
   `LanePanel` with cast + scope as props.
3. **Cast** — `lane_meta["agent"]` scalar → `conversation_members` rows; Agent-invite live in
   any conversation; addressing generalizes (it already works in rooms).
4. **Fork** — human-invite into a private conversation performs the settle-seeded fork.
5. **Falsifier repair** — `services/falsifiers.py:97` filters `.eq("slug","lane")` and joins
   `chat_sessions`; the fold changes what it sees. The W0 instrument is updated in the same wave
   so the ADR-492 §7 per-phase comparison stays honest against the recorded pre-rooms baseline
   (`docs/analysis/w0-falsifier-baseline-pre-rooms-2026-07-28.md`).

Gates: the ADR-492 rooms gate is rewritten as the conversation gate (the invariants it asserts —
never-ambient, attribution verbatim, grant-gated membership, no notification writes — all
survive the fold and must keep passing); ADR-411's lane gate must stay green throughout (private
conversations byte-identical); a new gate asserts scope append-only and the absence of any
scope-mutating write.

## 9. Ratification points

1. **D1** — one Conversation object; lane and room are scope states, not objects.
2. **D2** — the store is `chat_sessions` grown; `conversations`/`conversation_messages` dropped,
   `conversation_members` retained and re-pointed.
3. **D3.1** — the DP35 amendment: `chat_sessions` becomes scope-bearing, with scope explicit and
   append-only rather than implied by table identity.
4. **D3** — the two invites distinguished; Agent-invite implemented in private conversations
   (closing the ADR-492 D6.c canon/code contradiction).
5. **D4** — the human invite FORKS via settle distillate; scope is append-only; no retroactive
   disclosure is representable. *(Aligned in-discourse 2026-07-29; listed for the record.)*
6. **D5** — the noun collapses to "conversation"; `session_type='lane'` and the table name are
   grandfathered slugs.
7. **D6** — the non-goals, in particular notifications deferred to post-stabilization.
8. The **supersession** of ADR-492 D2's two-store consequence and the **amendment** of D6.b/D6.c,
   as declared in the header.
9. **Open, not closed here:** whether the fork may seed from a chosen point forward in addition
   to the settle distillate (D4's sub-question).
