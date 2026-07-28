# ADR-489: Attention Weight — the Third Axis of the One Derivation

**Status:** Accepted (2026-07-28) — implemented same day
**Dimensions:** Channel (primary — Axiom 6) + Substrate (transport cleanup)
**Amends:** ADR-410 (attention derives from the timeline), ADR-407 D7/D8 (the fold executed), ADR-405 D3 (the outbound seam becomes real)
**Supersedes:** the remaining live surface of ADR-040 (notification service) — the `in_app` channel, the chat-echo insert, and `user_notification_preferences`
**Gates:** `api/test_adr489_attention_weight.py` (+ ADR-410 gate D3 assertion amended, intent preserved)

## 1. Context — the symptom and the audit

The operator's bell showed, as its ACTIVITY head: *"System updated `_recent_execution.md`"*,
*"System updated `_schedule_index.md`"*, *"System updated `_watch_signal.yaml`"* — scheduler
and radar bookkeeping, counted in the red badge as if a peer had acted. The felt wrongness:
"what is and isn't a notification here?"

The 2026-07-28 audit found the architecture is *more* conformant than it feels. Derived-never-
stored is real (the bell + Notifications workbench both mount `GET /api/workspace/timeline`,
DP29); self-suppression exists (ADR-405 D4, `!who.isSelf` at the bell); the read cursor is
per-member (`member_state['attention']`, ADR-407 D7). What is missing is an axis canon already
names but no code implements:

> *"Every invocation emits a narrative entry; rendering weight (**material / routine /
> housekeeping**) is UI policy, logging is complete."* — FOUNDATIONS Axiom 9
>
> *"what demands the operator now is derived from substrate — pending `action_proposals`,
> **the narrative weight taxonomy (material/routine/housekeeping)**, budget runway"* — DP29

The timeline derivation ships **actor** (who) and **cursor** (since when) but not **weight**
(what grade of act). So an idempotent index regeneration ranks equal to a teammate rewriting
the mandate. ADR-405 D2/D3 defines a notification as an *after-witness consequential act* —
the consequence test was never applied to the feed.

Secondary findings the same audit surfaced (fixed here under the singular-implementation
discipline):

- **`user_notification_preferences` has one consumer surface** (the Settings → Account
  "Email Notifications" toggles — initially missed by the audit's grep). ADR-407 D7 already
  ordered its fold into `member_state`, and migration 202's comment reserved the
  `notification_prefs` key for exactly this; the Settings section rewires onto it.
- **`emit_after_witness` derives its recipient roster and discards it.** ADR-410 D3 reserved
  the seam for outbound transport ("its per-recipient send loop lands HERE"); nothing landed.
- **`send_notification` still carries ADR-040 fossils**: an `in_app` channel that nothing
  displays (retired by ADR-410 D3), and a "📧 I sent you an email" echo written into the
  viewer's *private* chat thread — a second attention surface, exactly the shape ADR-410 §1
  retired.
- **Suspected "caused-by-me" gap verified a non-gap** (§5).

## 2. Decision D1 — weight is classified at derivation time, in the kernel

A pure classifier, `api/services/attention.py::classify_weight(...)`, stamps every
`TimelineEntry` with `weight ∈ {material, routine, housekeeping}` at read time. No new
storage, no new column — weight is *derived* from facts the ledgers already carry
(attribution, path, `revision_kind` [ADR-423], invocation `mode`/`status`):

| Entry kind | Rule (first match wins) | Weight |
|---|---|---|
| proposal | always — a witness event | **material** |
| invocation | `status == 'failed'` — failures demand attention | **material** |
| invocation | `mode == 'judgment'` — the run is legibility; its *output* surfaces separately as a revision | routine |
| invocation | else (`mechanical`) — sync/capture/index machinery | housekeeping |
| revision | basename starts `_` (machine-parsed state, §9 file discipline) | housekeeping |
| revision | top-level root's `WORKSPACE_ROOTS` group is `system` | housekeeping |
| revision | `revision_kind == 'observation'` (retained raw arrival, DP32) | routine |
| revision | else — authored acts and derivations, by any principal | **material** |

The write door is untouched: logging stays complete (Axiom 9); weight is rendering policy,
computed where rendering is served. A Researcher radar brief (`revision_kind='derivation'`,
non-underscore path) is **material** — ADR-486's "notification after-witness by default"
holds; the raw XML it derived from is routine; the `_watch_signal.yaml` bookkeeping around it
is housekeeping.

## 3. Decision D2 — the mounts pick their depth by weight

- **Bell (glance):** ACTIVITY shows **material** peer acts only; badge = pending proposals +
  unseen **material** peer acts. (ADR-410 D1's peer-first filter is kept; weight composes
  with it.)
- **Notifications workbench (breadth):** gains a weight lens — **"What matters"** (default:
  material + routine) / **"Everything"** (the complete attributed record, one click away).
  The complete record remains the workbench's job (ADR-415); the default stops making the
  operator wade through index regenerations to find it. The raw mirror stays Files/revisions.
- Missing/unknown weight renders as material (fail-open — a new entry kind is never silently
  hidden).

## 4. Decision D3 (finding, no code) — "caused by me" is already covered

The audit suspected system writes triggered by the viewer's own gesture would echo back as
peer activity. Verified: upload projections attribute the uploading member
(`documents.py` passes the acting principal; `revision_kind='observation'`), so the viewer
layer resolves them as self; the remaining `system:*` synchronous byproducts are underscore/
system-zone writes — housekeeping under D1. Radar briefs deliberately stay material even when
the sweep rides the member's route completion: the brief is *new information the member did
not author* — being told is correct (ADR-486).

One label improvement rides along: `system:radar` gets the resident face **"Researcher"** in
the FE attribution labeler (ADR-486 D2 "the face is the resident, the fact is the ledger" —
`authored_by` unchanged).

## 5. Decision D4 — the outbound witness seam becomes real (and stays quiet by default)

`emit_after_witness` stops discarding its roster. For each derived recipient (grant-holders
minus the actor, ADR-405 D5) it consults the recipient's `member_state['notification_prefs']`
and, where allowed, sends an email via the one send path and records the transport row —
`notifications` in its sanctioned transport-only role (ADR-405 D3), now stamped with
`workspace_id` (ADR-407 D8 "addressed per recipient principal" — the row's `user_id` IS the
recipient; the workspace stamp says which commons the act happened in).

Pref shape (presentation-layer, never authorization — ADR-405 D5):

```json
{ "delivery_email": true, "failure_email": true, "witness_email": "high" }
```

`witness_email ∈ 'all' | 'high' | 'none'`, **default `'high'`** — and the existing call
sites (proposal lifecycle) emit at `normal`, so default behavior is byte-identical quiet:
the in-app bell remains the canonical after-witness channel; email push is opt-in
(`'all'`) or reserved for future `high`-urgency emissions. Transport rows are written only
when a send actually happens (a transport record records transport, not decisions not to).

## 6. Decision D5 — one prefs store, one writer, the fossils deleted

Singular implementation (the cleanup this ADR was asked to carry):

- **`member_state['notification_prefs']` is the ONLY notification-preference store**
  (per `(workspace_id, principal_id)` — mute one commons, not all; the shape migration 202
  reserved). Served by the existing `GET/PUT /api/member-state/{key}` — no new routes.
- **Deleted:** `user_notification_preferences` table + `get_notification_preferences` RPC
  (migration 223, carrying any non-default rows into `member_state` keyed by the user's
  owner workspace); `GET/PATCH /api/account/notification-preferences` + Pydantic models +
  the `client.ts` methods. The Settings → Account "Email Notifications" section rewires
  onto `api.memberState.get/put('notification_prefs')` and gains the witness dial control
  (Urgent only / Every action / Never). Preference *gating* moves from
  `jobs/unified_scheduler.py::should_send_email` into `services/notifications.py` reading
  the new store.
- **Deleted from `send_notification`:** the `in_app` channel branch (nothing has displayed
  those rows since ADR-410 D3 — historical rows stand, the code path dies; the
  delivered-via-email audit duplicate is dropped entirely — `destination_delivery_log`
  already records that fact for the Out lens); the `_insert_chat_notification` private-
  thread echo (the email itself + the emissions ledger are the record; a chat echo is a
  second attention store in narrative costume).
- `scope_manifest.yaml` updated (`user_notification_preferences` → dropped; `notifications`
  note gains the workspace stamp); purge scripts updated.

## 7. What this does NOT do

- No push transport, no digest batching (the pref enum leaves room; DP29 keeps them
  presentation-layer when they come).
- No per-path subscription matrix — **never** (ADR-405 D5).
- No stored weight, no stored read receipts, no second attention store. The diagnostic
  tests in DP29/DP35 all still pass by construction.
- No change to what is *logged* — Axiom 9's completeness is untouched; Files/revisions
  remain the raw truth.

## 8. Gate

`api/test_adr489_attention_weight.py` — behavioral where the code is pure (the classifier is
imported and CALLED on the audit's literal symptom rows: `_recent_execution.md` must classify
housekeeping, a radar brief derivation material, a failed run material), text-gated where the
wiring is FE. The ADR-410 gate's D3 assertion (`send_notification not in witness.py`) is
amended to its actual intent — *no in-app rows from the witness path* — which D4 preserves.
