# ADR-492: Chat Is the Communication App — Rooms, Mentions, Comments on One Conversation Grammar

**Status:** Proposed (drafted 2026-07-28 from the communication-layer discourse; locks on operator
ratification — the ratification points are enumerated in §8)
**Dimensions:** Channel (primary — Axiom 6) + Identity (addressing) + Substrate (scope flip)
**Relates to:** ADR-457 (Think·Make — D2 divergence amendment applied here), ADR-460 (Agents =
named hands; the cast model rooms inherit), ADR-411 (the lane contract rooms extend), ADR-408
(D1 coworking contract; D6 narrowly amended per the three-axes §6), ADR-405/410/489 (the attention
rails this ADR deliberately does NOT duplicate), ADR-440/450 (the binding pattern comments
consume), ADR-436 (app = renderer; window = surface)
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
- **No change to the sequencing already ruled**: W0 falsifiers → settle → Agent registry → cast
  in a room → the object ADR (ADR-460 §8). Rooms/mentions/comments land inside that program —
  this ADR is the direction they land *into*, not a schedule jump.

## 7. The build shape (when the waves reach it)

Indicative, not binding: the scope flip (D2) is the schema delta; mentions (D3) are conversation
metadata + one To-do derivation source in the kernel; comments (D4) are a binding kind + a Studio
mount. Each rides existing rails (grants for access, ledgers for legibility, ADR-489 for weight,
settle for record). Nothing requires a new kernel primitive; the shared Conversation store is the
one genuinely new substrate object, and it enters the DP35 registry as workspace content.

## 8. Ratification points

1. D1 ownership (Chat owns the grammar; mounts elsewhere) — the operator's stated thesis.
2. D2 scope-decides-store-class (shared conversations are workspace content).
3. D3 mention split (content = Chat; attention = OS; second To-do source; material-to-the-
   mentioned weight rule).
4. D4 closing ruling (c) on the inversion's side — this is the one previously held-open ruling.
5. §6 non-goals as written.
