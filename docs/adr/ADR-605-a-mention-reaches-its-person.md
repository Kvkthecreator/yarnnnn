# ADR-605: A Mention Reaches Its Person — the attention half of the @ gesture, built

**Status**: Accepted (2026-08-25, operator-aligned in-discourse) — implemented same session.
**Amended same day (operator-ruled): mentions email is OPT-IN (`email_default: "none"`)** — see D3. The sequencing rule the amendment ratifies: **internal (in-app, derived) notifications stabilize to a comprehensive level BEFORE outbound expansion**; email is machinery a member turns on, never a default the system assumes. The first cut shipped default-`all` for one deploy — an unflagged upgrade of the discourse's own "if they've opted in" wording, corrected here.
**Dimension**: Channel (Axiom 6 — where attention routes) + Identity (species-blind addressing)
**Builds**: ADR-492 D3 (the mention split — content is Chat's, attention is the kernel's), closing the ADR-495 D6 standing gap ("a mention routing nowhere is theatre" — the routing now exists)
**Amends**: ADR-593 D1 (the `mentions` kind flips declared-unwired → wired), ADR-489 D1 (mention-of-viewer is material to that viewer — the amendment ADR-492's header declared, landed here as the To-do source rather than a timeline weight row)
**Preserves**: ADR-405 D5 (no subscription matrix — tags-as-routing refused, §5), ADR-410 (one derivation, N mounts; no inbox table), ADR-495 (species-blind cast; the visibility window is the read floor), ADR-593 D3 (one email chokepoint, fails closed), never-ambient (a human mention fires nothing)
**Gate**: `api/test_adr605_mentions_attention.py`

---

## 1. Context — the aligned framing this executes

The 2026-08-25 discourse re-audited the notifications domain against the
agents-as-beings architecture (ADR-596→603) and settled the species-agnostic
frame:

> **The primitive is attention routing; the mount differs by how the
> recipient attends.** A human attends when away — their mounts are the bell
> and email. An agent's attention exists only during an invocation — its
> mount IS the turn (a mention fires it now) or a standing declaration.
> "@agent answers now; @human gets flagged" is not species law: it is the
> same routed attention arriving through the transport each recipient class
> actually has (the ADR-405 §5 test: which grant, which act-class, which
> dial).

Three rungs of the vocabulary, only the middle one new:

| Rung | Plain meaning | Status |
|---|---|---|
| **Activity** | everyone can see what happened | shipped (ADR-410 — automatic, workspace-wide) |
| **Mention** | I'm asking *this person* for something | **this ADR** |
| **@everyone** | asking all of the cast at once | deferred (§5) |

Everything below the mention was already built and waiting: the parser
(`services/addressing.py`), the species-blind cast (ADR-495), the kind
registry with `mentions` declared-unwired (ADR-593 D1), and the discarded
`resolve_address()["humans"]` list at the one consumer — the exact seam.

## 2. D1 — The mention fact is stamped at write time, on the message row

`routes/lanes.py` stamps `session_messages.metadata.mentions =
[principal_id, …]` when a turn is persisted — parsed-once addressing
metadata living WITH the content it derives from, exactly as
`agent_slug`/`responder_reason` already do. Not a second store: the message
IS the substrate (DP29 holds). The @token stays verbatim in the text.

- **Both row kinds stamp.** A member's turn and an agent's reply mention
  people the same way — the derivation never asks who authored the
  mentioning turn. Species-agnostic senders cost nothing; they are the
  default.
- **The acting member is excluded at stamp time** (ADR-405 D4 — they are
  present; being told what they just did or watched is not attention).
- **Handles**: humans match on the resolved label (full name or email
  local-part, via `principal_display.resolve_member_names` — the ONE
  resolver), its space-squashed form (the mention grammar is one token), and
  the raw local-part. The FE menu emits the squashed form, so menu and
  parser agree. A bare first name deliberately does NOT match — two Kevins
  and first-wins would silently address the wrong person, the exact failure
  the agent side refuses. An unmatched handle stays `unresolved` and renders
  un-chipped: no claimed delivery that never happened.
- **Mentioning a non-participant never invites.** Cast membership scopes who
  can be addressed; adding a participant is an explicit disclosure decision
  with a visibility window (ADR-495 D2), never a mention's side effect.

## 3. D2 — The attention surface is derived per viewer; resolution is not scroll-by

`GET /api/mentions` (per viewer, per acting workspace) derives unresolved
mentions from: cast membership ∩ the visibility window (ADR-495's read
floor, applied to the viewer's own mentions like any other read) ∩ the D1
stamp. No inbox table, no per-mention read flags (ADR-492 D3 verbatim).

ADR-492 §7's two-facts rule is implemented literally:

- **The badge keys on the read cursor** (`member_state['attention']`,
  unchanged): opening the bell quiets the count.
- **To-do membership keys on RESOLUTION**: a mention stays listed until the
  viewer *deals with it* — they spoke in that conversation after it
  (derivable), or they hit **Done**, which advances a per-conversation
  resolution cursor (`member_state['mention_resolutions']` =
  `{conversation_id: resolved_up_to_sequence}`, monotonic, server-merged via
  `POST /api/mentions/resolve`). This is viewer presentation state in the
  ADR-407 cursor lineage — per (workspace, principal), never authorization,
  never a per-mention flag.

Mounts (one derivation, N mounts — ADR-410): the bell's To-do section leads
with mention rows (click lands in the conversation); the Notifications
window's To-do pane mounts `MentionQueue` (Open conversation · Done) above
the proposal queue.

## 4. D3 — The email consequence rides the one chokepoint; the kind is wired

`NOTIFICATION_KINDS['mentions']` flips to wired with **`email_default:
"none"` — opt-in** (amended same day, operator-ruled; the first cut's `"all"`
lasted one deploy). The dial (`Every mention` / `Never` — no "urgent only":
nothing grades a mention's urgency, the reports precedent) appears in the
settings pane automatically because the pane is backend-driven (ADR-593 D5).
The in-app surface (D2) is the canonical mention channel and is always on;
email is the member's own escalation, per workspace.

- Emission is `send_notification(kind="mentions")` — gate by the recipient's
  per-(workspace, principal) dial → transport row → send; fails closed
  (ADR-593 D3 unchanged). Called from the kernel seam
  (`services/mentions.py::notify_mentioned`), fired off the turn's critical
  path — the witness-email shape (ADR-489 D4): the app writes the addressed
  act, the kernel derives and sends.
- **Suppression, derived from the transport ledger**: at most one mention
  email per (recipient, conversation) per `EMAIL_SUPPRESSION_MINUTES` (60) —
  an active back-and-forth must not become a drip, and an agent that says
  @you every turn must not become a loop. No new state: the `notifications`
  rows ARE the memory.
- Pointer-only (ADR-202): who and where, never the content.

## 5. What this ADR deliberately does not do

- **No `@everyone` / `@channel`.** Workspace-wide awareness already exists
  for free (the Activity derivation); a broadcast mention adds only badge
  pressure on everyone — the spam vector this architecture exists to avoid.
  If real demand shows: it is a grammar token expanding to the cast's
  humans, scoped to the conversation, and it must not fire every agent (one
  human act, one responding turn — the addressing ladder is unchanged).
- **No tags-as-routing.** A followable topic-tag is a stored subscription —
  the per-path matrix ADR-405 D5 bans with the word "never".
  `workspace_files.tags` stays search metadata.
- **No agent notification rows.** An agent recipient's mount is the turn
  (@agent fires now — shipped, ADR-495 D3) or a standing declaration
  (ADR-603); its "witness surface is the substrate itself" (witness.py
  doctrine, kept). The `notifications` table stays a transport receipt for a
  transport only humans have — its `user_id → auth.users` FK is correct, not
  a gap.
- **No auto-invite on mention of a non-participant** (§2). The FE may later
  offer "add them?" — the offer is the honest shape; this ADR ships without
  it.
- **No mention parsing anywhere but the one grammar** (`_MENTION` in
  `services/addressing.py`) — the FE transcript chip-matcher mirrors it and
  marks only handles that resolve.
- **No change to never-ambient, responder selection, or the cast/visibility
  model.**

## 6. Files

Backend: `services/mentions.py` (new — stamp helpers, derivation, resolution
cursor, email seam), `services/addressing.py` (human handle map widened:
squashed + local-part; docstring recut), `routes/lanes.py` (cast label
enrichment, the two stamps, the two fire-and-forget notifies),
`routes/mentions.py` (new — list + resolve), `services/notifications.py`
(kind wired), `main.py` (mount).

Frontend: `MentionMenu.tsx` (people become live targets; refusal chrome
retired), `ChatSurface.tsx` (squashed human handles), `LanePanel.tsx` (human
chips mark), `AttentionCenter.tsx` (mentions in To-do + badge),
`components/notifications/MentionQueue.tsx` (new), `notifications/page.tsx`
(mount), `settings/page.tsx` (dial options), `lib/api/client.ts`
(`api.mentions`).

Re-anchored gates: `test_adr593_notifications_management.py` (mentions pref
now accepted; `runs` is the unwired probe), `test_adr495_addressing.py`
(route-nowhere → never-fires-a-turn).
