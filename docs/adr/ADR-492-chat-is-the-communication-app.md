# ADR-492: Chat Is the Communication App — Rooms, Mentions, Comments on One Conversation Grammar

**Status:** Proposed (drafted 2026-07-28 from the communication-layer discourse; **discourse pass
applied 2026-07-28 second session** — implementation audit receipts confirmed the ADR-460 §8 wave
program stands at step 4 [W0 instrumented `services/falsifiers.py` + migration 216; settle shipped
`POST /lanes/{id}/settle`; Agent registry shipped `services/agents_registry.py` + ADR-467], the
amendment surface was declared, and agenda item C closed as §8 point 6. **Third pass same day
(operator live):** the front-end grammar scoped in as §6b D6 — person-first door, scope-at-birth
with the settle-bridge (operator-ruled), engines-by-invitation, the invite·keep·share triad with
the settle re-home (operator-ruled: verb stays, bookmark costume retired — shipped to
`LanePanel.tsx` same session). **Fourth pass same day (operator-ordered): the rooms build jumped
forward — rooms v1 SHIPPED** (operator chose "jump straight to human rooms" over the staged
sequence; W0 pre-rooms baseline recorded first per §7 —
`docs/analysis/w0-falsifier-baseline-pre-rooms-2026-07-28.md`). In: migration 225
(`conversations`/`conversation_members`/`conversation_messages`, content scope, DP35 manifest);
`routes/rooms.py` (born-shared create · grant-gated membership · plain turns fire nothing ·
addressed Agent turns via the lane runner, `ledger_slug="room"`, draw-gated); the door's People
section (picking a person starts a room); `RoomPanel` (attributed transcript, Ask chips =
addressing, invite popover); gate `api/test_adr492_rooms.py` 12/12. **Owed fast-follows, declared
not built:** the D3 attention wiring (mentions → To-do source; shared-scope conversation acts →
timeline + ADR-489 weight rows — rooms currently write NO attention surface, honest per D3's
"Chat never sends a notification"); human-mention parsing; streaming room turns; the D6.b
"start a room from here" settle-bridge affordance; D4 comment-thread mounts (the store carries
`binding`/`resolved_at` from birth). Ratification of §8 still open — the build followed the
operator's explicit order, not a status flip.
**FIFTH PASS 2026-07-29 — D2 SUPERSEDED by [ADR-495](ADR-495-the-conversation-one-object-scope-and-cast.md).**
The operator's lifecycle question ("a member is in a lane and wants to invite another Agent or a
person — shouldn't there be one approach?") exposed that D6.b stated ONE reason for TWO walls,
and covers only one of them: the privacy ratchet is real, but it never justified blocking
**Agent**-invite, which D6.c explicitly permits and the code contradicted from day one
(`lane_meta["agent"]` is a scalar, `routes/lanes.py:287`). ADR-495 collapses lanes and rooms into
**one Conversation object** (`scope` + `cast`) living in `chat_sessions`; the migration-225 tables
`conversations`/`conversation_messages` are **dropped** (prod read 2026-07-29: 0 rows, never used
— the collapse is delete-the-empty-one, not a two-way merge), `conversation_members` is retained
and re-pointed. D6.b's *concern* is preserved absolutely and promoted: a human invite into a
private conversation **FORKS** (settle-seeded child, private turns never exposed) instead of
being refused — the member's intuitive gesture now yields the disclosure-safe outcome by
construction. The rooms build is not wasted: it proved the shape, shipped the cast table ADR-495
keeps, and validated never-ambient + addressing-as-selection, all of which survive the fold.
This ADR's D1 (Chat owns the grammar), D3 (the mention split), D4 (binding-capable from birth),
§6 non-goals, and D6.a/c/d/e all stand unchanged.)
**Dimensions:** Channel (primary — Axiom 6) + Identity (addressing) + Substrate (scope flip)
**Relates to:** ADR-457 (Think·Make — D2 divergence amendment applied here), ADR-460 (Agents =
named hands; the cast model rooms inherit), ADR-411 (the lane contract rooms extend), ADR-408
(D1 coworking contract; D6 narrowly amended per the three-axes §6), ADR-405/410/489 (the attention
rails this ADR deliberately does NOT duplicate), ADR-440/450 (the binding pattern comments
consume), ADR-436 (app = renderer; window = surface), ADR-467 (chat is the open surface with the
cast, no resident — owning the Conversation *grammar* is object-level ownership and does not make
chat a one-job app; the two claims compose)
**Amends (locks with ratification):**
- **ADR-408 D6, final clause** — the "shared multi-user chatrooms are explicitly NOT built"
  rejection is superseded as direction. Its own revisit condition ("on demonstrated demand, as
  sessions with N participant grants") is exactly the D2 shape; the transcript-isolation rule
  stays as narrowly amended by the three-axes §6, and ADR-407 §5's rejection *rationale* is
  honored: the timeline's system-of-record for commons work remains the attributed ledgers — a
  room is a commons object, never the narrative's source of truth (the transcript is never the
  system of record, ADR-457 D2).
- **ADR-410 §2** — the closed two-source rule ("nothing else may feed an attention surface")
  widens when rooms land: "what wants me" gains unresolved mentions of the viewer (D3, the second
  To-do source), and the timeline derivation gains the shared conversation store as a source for
  **shared-scope conversation acts only** (private lanes stay off the timeline, unchanged).
- **ADR-489 D1** — the weight table gains conversation-entry rules (D3): mention-of-viewer →
  material *to that viewer*; undirected room talk → routine; a room settle → material like any
  derived act.
**Closes:** three-axes discourse pending ruling **(c)** — the comments inversion. **Leaves open:**
(a) the unified-object schema (DEFER stands — amend `lane_meta` from evidence), (f) bound-lane
homing, (g) `prd` landing format.

## 1. Context — the question this settles

The multi-user communication discourse (2026-07-28) asked where member↔member communication
lives. The audit found: it doesn't, yet — lanes are member-private (ADR-407, correct), the rail
is the steward's voice, and collaboration happens only through attributed acts on the commons
(ADR-408 D1). The Naver-Works-class objects — rooms, mentions, comments — are ratified-direction
but homeless.

The operator's thesis, checked against canon and confirmed: **communication is app-layer;
attention is OS-layer.** Naver Works bundles the two because it is a closed suite. This OS
cleaves them: DP29 makes attention-routing a kernel responsibility (one derivation, N mounts —
just hardened by ADR-489); ADR-436 makes a medium an app (a renderer over commons substrate).
Messages, comments, and rooms are authored substrate plus a renderer. That app is Chat.

## 2. D1 — Chat owns the Conversation grammar; other apps mount it

The Conversation object family — private lanes today; shared rooms and artifact-bound comment
threads when they land — is **one grammar with one owner: the Chat app.** Chat defines the
object's contract (turns, attribution, addressing, cast, bindings, settle); every communication
concept in the product is an instance of it.

Ownership is at the object-and-contract level, not the window level. A comment thread renders in
Studio's margin bound to a block — that is Studio **mounting** a Conversation view (the
ADR-440/450 binding pattern), not Studio owning comments. Same as every app: one file type, many
mount points; one contract, one owner.

What this forbids (the singular-implementation edge): no second messaging object, ever — no
separate "comment" table, no separate "room" object, no per-app discussion widgets. A surface
that wants discussion mounts a bound Conversation.

## 3. D2 — Scope is the seam, and scope decides the store's class

> **SUPERSEDED 2026-07-29 by [ADR-495](ADR-495-the-conversation-one-object-scope-and-cast.md) D1/D2.**
> The seam-is-scope finding STANDS and is the foundation ADR-495 builds on. What is superseded is
> the *substrate consequence* drawn below — that scope decides which **store** a conversation
> lives in. ADR-495 makes scope an explicit, indexed, append-only **column** on one store
> (`chat_sessions`) rather than a property of table identity, which satisfies DP35's actual
> concern (no row silently mixes classes, no row changes class mid-life) without a second object.
> The invariants listed at the end of this section — never-ambient, attribution verbatim,
> no merge/CRDT — carry forward unchanged.

The three-axes discourse already found that once the lane's model pin dissolves, lane-vs-room
collapses to one seam: **scope**. This ADR names the substrate consequence:

- **`private` (a lane)** — the member's first-person working context. Member-experience scope
  (DP35), exactly as ADR-407 classified it. Not on the workspace timeline; peers never see it.
- **`shared` (a room, or a comment thread)** — a **workspace-content object**: part of the
  commons, attributed, readable by grant-holders, and its acts land on the attributed ledgers
  like any other commons act.

The scope flip is therefore a *taxonomy crossing*, which is why rooms are honestly "a new object
and a schema delta" (three-axes §8) and not a flag on `chat_sessions`. The ADR-457 D2 amendment
held since the discourse applies from here on: *divergence may be private (lanes) or shared
(rooms); settling is always public; the transcript is never the system of record.*

Invariants that cross the seam unchanged:
- **Never-ambient** (three-axes §3.3): a model turn fires only on a human act — in a room with
  three humans and four Agents exactly as in a solo lane. What varies is who *selects* the
  responder, never whether something speaks unaddressed.
- **Attribution verbatim**: human turns as the member; engine turns as `member:{id} via {model}`
  (ADR-411 D4); Agents are named hands, not principals (ADR-460 — the registry row has no field
  for consequential authority).
- **No merge/CRDT** anxiety: rooms are append-only conversations; the Studio 409 problem does
  not exist here (three-axes §8 note, preserved).

## 4. D3 — A mention is two facts, split across the OS/app line

A mention (`@member`, `@agent`) is **addressing metadata inside the Conversation grammar** —
authored content, Chat's object, species-blind by construction (you address a person or a named
hand with the same gesture; addressing an Agent *is* the human act that fires its turn, per the
never-ambient invariant).

This addressing grammar is also the entire surviving remainder of the three-axes routing ladder
(§4 there; largely dissolved by ADR-460 D4): rung (a) "pick who answers" *is* who you address;
rung (c) gestures compose addressed turns. **No per-turn engine picker exists or arrives.** The
ADR-411 D1 model pin did not dissolve — it moved *behind the Agent name* (the registry resolves
agent → model at creation, `routes/lanes.py::create_lane`) and persists in a private lane as the
degenerate case: a cast of one, where every turn is implicitly addressed to the lane's Agent. In
a room it generalizes to "the addressed member answers." Multi-engine-in-one-thread is therefore
not a picker feature; it is a room with two Agents invited.

The attention consequence is **not Chat's to deliver.** A mention of a member is an attributed
act on a shared-scoped object; the kernel's attention derivation picks it up:

- "What wants me" (the To-do derivation) gains its **second source**: pending proposals (ADR-410)
  + **unresolved mentions of the viewer**. Derived at read time from the conversation substrate —
  no mention inbox table, no per-mention read flags (the member's existing attention cursor +
  the thread's resolution state are the facts).
- Weight (ADR-489): a mention of the viewer is **material** to that viewer. Undirected room talk
  is **routine** — legible in the workbench and the room itself, never badge pressure. A settle
  from a room is a material revision like any other derived act.
- The witness-email dial (`witness_email`, ADR-489 D4) covers push, untouched.

Chat never sends a notification. It writes addressed acts; the OS routes attention. This is the
whole point of the split, and it is why communication lands with its notification story already
built.

## 5. D4 — The comments inversion, ratified: binding-capable from birth

Pending ruling (c) closes on the inversion's side. **The Conversation object is binding-capable
from birth** (the ADR-440/450 pattern that already exists as `lane_meta` bindings): a comment
thread = a shared-scoped Conversation **bound to an artifact (+ block anchor)**. There is no
separate comments object, and the "comments ADR" owed by ADR-457 §10.2 is discharged **by this
section** — whenever the Studio multi-user wave (ADR-457 D7 P2) needs comments, it consumes this
contract.

Consequences:
- Anchors ride the ADR-480 grain: a comment binds to the artifact (attribution grain = file) and
  anchors to a block id (addressing grain = structure). An anchor whose block disappears degrades
  to an artifact-level comment — never lost, never blocking an edit.
- Resolution ("resolve thread") is a state transition on the Conversation — an attributed act,
  therefore on the timeline, therefore in the mentioned member's attention derivation.
- Studio's margin is a mount; the same thread is reachable in Chat (it is a conversation), which
  keeps plank 3 of the seam contract ("conversation follows scope/binding") coherent rather than
  contradicted.

## 6. D5 — What this ADR deliberately does not do

- **No unified-object schema now.** ADR-460 §7's DEFER stands: `cast` waits for the Agent
  registry; `scope: shared` waits for rooms; `lane_meta` amends in place from evidence. This ADR
  fixes the *ownership and the seams*, not the migration.
- **No presence, no typing indicators, no read receipts** beyond the existing single-timestamp
  cursor. Presence-lite is Phase-D scope (three-axes §8) and stored per-row read state is a named
  DP29 violation.
- **No app-owned notifications** — restated because it is the failure mode every chat product
  normalizes.
- **No per-turn engine picker** — responder selection is addressing (D3); engines stay behind
  Agent names (ADR-460). A model dropdown on the composer would resurrect the spec-sheet the
  registry retired.
- **No mid-life scope flip** — private stays private; the lane→room bridge is settle (D6.b).
- **No "remember"/bookmark premise in chat chrome** — the act on a conversation is keep (settle)
  or share (D6.e); a message-bookmark feature, if ever wanted, is a separate premise approached
  on its own.
- **No change to the sequencing already ruled**: W0 falsifiers → settle → Agent registry → cast
  in a room → the object ADR (ADR-460 §8). Rooms/mentions/comments land inside that program —
  this ADR is the direction they land *into*, not a schedule jump.

## 6b. D6 — The operator flow: the door, invite, engines, and the keep·share triad (scoped in 2026-07-28)

The second discourse pass scoped the front-end grammar in as first-class (the operator's
correction: the expected user flow is part of the refactoring plan, not a build detail). Two of
these carry in-discourse operator rulings (2026-07-28), noted where they land.

**D6.a — The door is person-first.** "New chat" = pick *whom* you are talking to — the Agent
roster today (`NewChatModal`), widening to **one species-blind picker** of Agents + human members
when rooms land. Membership at birth decides scope by construction: any human peer present ⇒ the
conversation is born **shared** (a room — the peer can read it, so it is workspace content by
definition); you + Agents only ⇒ a private lane. The "composed-create vs create-then-invite"
question collapses: creation is always composed (you pick at least one interlocutor — the live
door already works this way), *and* invite remains a room-level act afterwards.

**D6.b — Scope is set at birth and never flips** *(operator-ruled 2026-07-28; **AMENDED 2026-07-29
by [ADR-495](ADR-495-the-conversation-one-object-scope-and-cast.md) D4** — the rule below stated
one reason for two walls and justified only one. The **privacy ratchet is preserved absolutely**:
no human ever reads a private conversation's prior turns, and ADR-495 makes retroactive disclosure
structurally unrepresentable [scope is append-only]. What changes: the settle-bridge stops being a
separate verb the member must think of and **becomes the semantics of the invite gesture itself** —
inviting a human to a private conversation FORKS a settle-seeded shared child. And the wall on
**Agent**-invite falls entirely; it was never justified by this rule, and D6.c below says so.
The store-crossing dividend claimed in the last sentence is retired — it was an implementation
consequence of a layout ADR-495 removes)*. A human is never
invited into an existing private lane. The lane→room bridge is **settle**: "start a room from
here" creates a *new* shared conversation seeded with the settled distillate — never the raw
transcript. This is ADR-457 D2 made mechanical (diverge privately, settle publicly; the
transcript is never the system of record), and it dissolves the DP35 store-crossing migration:
no conversation row ever changes store class mid-life.

**D6.c — Agents are always additive.** *(**IMPLEMENTED 2026-07-29 by
[ADR-495](ADR-495-the-conversation-one-object-scope-and-cast.md) D3** — this clause was correct
canon the code contradicted from the day it was written: `lane_meta["agent"]` is a SCALAR fixed at
creation [`routes/lanes.py:287`], so no lane could ever hold a second Agent. ADR-495 retires the
scalar into the cast, making this rule real.)* Inviting an Agent into a private lane crosses no scope
boundary — the Agent is the member's hands (ADR-460), so the lane stays private; this *is* the
multi-engine thread of D3. Membership changes involving humans exist only on shared objects and
are attributed acts on the timeline.

**D6.d — Engines change by invitation, never by swap.** The Agent is the unit; its engine is a
configuration fact in the registry. There is no in-chat model-mutation gesture (§6's picker
refusal, applied mid-life): wanting another engine's view means inviting the colleague that runs
it. Editing a member-authored Agent's engine in its *configuration* is allowed and affects future
turns everywhere it is addressed — per-turn attribution (`member:{id} via {model}`, verbatim)
keeps history honest either way.

**D6.e — The act vocabulary is invite · keep · share** (the layman triad the composer area had
been missing a frame for):
- **Invite** — membership of the conversation (D6.a–c).
- **Keep** — the settle verb (ADR-457 D3). *Operator-ruled 2026-07-28*: the verb **stays**; the
  composer bookmark costume goes. The live affordance (an unlabeled `BookmarkPlus` beside the
  composer, `LanePanel.tsx`) proved illegible enough that the operator read it as a "remember"
  bookmark — settle re-homes as a **labeled conversation-level act** ("Keep this", header/menu),
  and the "remember"/bookmark framing retires from chat chrome entirely.
- **Share** — the ADR-465 membership primitive, *mounted* in chat context (share the kept
  artifact or the workspace outward; the MCP `share` verb) — chat mounts it, never owns it.

The first-class statement this triad serves (the operator's crystallization, and D1's product
sentence): **chat's first-class capability is the multi-human × multi-LLM conversation over the
commons — and then doing something fundamental with the room's product: keep it, share it, build
on it.**

## 7. The build shape (when the waves reach it)

Indicative, not binding: the scope flip (D2) is the schema delta; mentions (D3) are conversation
metadata + one To-do derivation source in the kernel; comments (D4) are a binding kind + a Studio
mount. Each rides existing rails (grants for access, ledgers for legibility, ADR-489 for weight,
settle for record). Nothing requires a new kernel primitive; the shared Conversation store is the
one genuinely new substrate object, and it enters the DP35 registry as workspace content.

The store's *shape* stays deliberately deferred (§6, ADR-460 §7), but the constraint set the
build must satisfy is recordable now: one scope per store (DP35 — `chat_sessions` is declared
member-experience, which is why D2 says "not a flag on `chat_sessions`"); one grammar one owner
(D1 — enforced at the contract level: one runner, one turn shape, one binding mechanism, whatever
the table layout); append-only, no CAS precondition (ADR-406 appender rule); access by grant;
mention resolution as an attributed state transition (D4) — To-do membership keys on *resolution*,
the unseen count on the *cursor*; the two facts stay distinct so a mention never silently clears
by scroll-by. ADR-408 D6's own revisit language ("sessions with N participant grants") is the
oldest sketch of this shape and remains a fair starting point.

One sequencing guard rides here: the W0 instrument (`services/falsifiers.py`) is read and
recorded as a **pre-rooms baseline** before the room build starts — shipping rooms changes what
chat *is* mid-observation (three-axes §8), so falsifiers are evaluated per-phase against a
snapshot, never on one clock.

## 8. Ratification points

> **2026-07-29 status:** points **2** and **8** are superseded/amended by
> [ADR-495](ADR-495-the-conversation-one-object-scope-and-cast.md) and ratify there instead
> (one object, scope-as-column, invite-that-forks). Every other point below stands as written
> and is still open. Points 9 and 11 remain operator-ruled in-discourse.

1. D1 ownership (Chat owns the grammar; mounts elsewhere) — the operator's stated thesis.
2. ~~D2 scope-decides-store-class (shared conversations are workspace content).~~ **→ ADR-495 D1/D2**
   (the seam-is-scope finding stands; the two-store consequence does not).
3. D3 mention split (content = Chat; attention = OS; second To-do source; material-to-the-
   mentioned weight rule).
4. D4 closing ruling (c) on the inversion's side — this is the one previously held-open ruling.
5. §6 non-goals as written (including the per-turn-picker refusal added by the 2026-07-28
   discourse pass).
6. The addressing-as-selection ruling (D3, second paragraph): the routing-ladder remainder closes
   — rung (a) = whom you address, the ADR-411 D1 pin persists behind the Agent name in private
   lanes and generalizes to addressed-member-answers in rooms; multi-engine-in-one-thread arrives
   as a room, sequenced in the ADR-460 §8 wave program (step 4), not as a picker feature absorbed
   here.
7. The declared amendment surface (header **Amends** block): ADR-408 D6's rooms rejection
   superseded as direction; ADR-410 §2's closed source-list widened on rooms landing; ADR-489 D1
   weight rows for conversation entries.
8. D6.a person-first door (stands) + ~~scope-at-birth~~ **→ ADR-495 D4** (scope is set at birth and
   a row's scope never mutates — that much holds; what changes is that a human invite into a
   private conversation FORKS rather than being refused).
9. D6.b settle-bridge — *already operator-ruled in-discourse 2026-07-28* (no human invite into a
   private lane; "start a room from here" seeds the distillate); listed for the record.
10. D6.d engines-by-invitation (no in-chat engine swap; registry config edits allowed, per-turn
    attribution keeps history honest).
11. D6.e the invite·keep·share triad — settle re-home *already operator-ruled in-discourse
    2026-07-28* (verb stays, bookmark costume + "remember" framing retire); share is the ADR-465
    primitive mounted, never owned.
