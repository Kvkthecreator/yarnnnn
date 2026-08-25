# ADR-593: Apps Declare Semantics, the Kernel Derives Emission — notifications get their management pane

**Status**: Accepted (2026-08-21, operator-ruled after the notifications-domain audit)
**Dimension**: Channel (Axiom 6 — where attention routes) + Substrate (transport cleanup)
**Amends**: ADR-489 (D4's pref shape is re-cut per-kind; D5's store and keying are preserved exactly), ADR-405 D3 (the emission/management reading made explicit)
**Preserves**: ADR-405 D5 (routing derived, never configured; no subscription matrix), ADR-410 (one derivation, N mounts; `notifications` = pure outbound transport), ADR-492 D5 (no app-owned notifications — now precisely scoped to EMISSION), ADR-202 (pointer-only out-of-band channels), DP29/DP35
**Gate**: `api/test_adr593_notifications_management.py`

---

## 1. The axiom — why mainstream OSes split it the other way, and why we don't

macOS/iOS/Windows/Android all run one split: **apps own emission and semantics;
the OS owns routing, presentation, and management** (System Settings →
Notifications → one row per app). They hold it out of *necessity*: their kernels
cannot see inside an opaque app, so an app posting an event is the only way the
OS learns anything happened. Their pathologies follow from the same fact — a
notification is a second copy of app state that drifts from it, and emission is
vendor-controlled, so the per-app management plane is fundamentally a defense
against adversarial over-notification.

YARNNN's kernel is the inverse condition: every act by every principal lands in
the attributed ledgers. When the OS can read everything that happened,
derivation beats emission — an emitted notification would be a second, forkable
store of what the ledger already says (DP29), it can miss acts, and it
reintroduces the spam vector. This is why ADR-405 could define a notification
as nothing but the after-witness setting of the dial.

**The YARNNN spelling of the split, one word moved:**

> **Apps declare semantics. The kernel derives emission. The OS routes,
> presents, and manages.**

ADR-492 D5's "no app-owned notifications" is hereby read precisely: it governs
**emission** ("Chat never sends a notification. It writes addressed acts; the
OS routes attention"). It does not forbid the *management surface* speaking
per-app vocabulary — mainstream OSes are decades of evidence that it should.
The operator experience is the learned mobile-OS pattern (one central
Notifications settings pane, one notification center); the plumbing underneath
stays derivation.

## 2. The audit this executes (2026-08-21)

The full audit is on record (the operator's artifact + this ADR's gate). The
findings that force code:

- **F1 (critical)** — the outbound seam was dead. `delivery_email` /
  `failure_email` gated `notify_agent_delivered`/`notify_agent_failed`: **zero
  callers** — the toggles were dials wired to nothing. `witness_email`
  defaulted `'high'` while both live call sites emit `'normal'`. Production
  measured 2026-08-21: **zero rows have ever been written to
  `notifications`**, zero `member_state['notification_prefs']` rows exist. The
  seam never sent. (The audit's secondary claim that `source_type="agent"`
  would violate the 041 CHECK was **wrong against the live schema** — an
  out-of-band rename already added `'agent'`; recorded here so the repo's 041
  file is known to under-describe production. The zero-callers finding
  stands.)
- **F2** — four senders bypassed the gate and the transport ledger entirely
  (invite, daily P&L, `platform_email_send_to_operator`, test email), so
  `/api/emissions` under-reported and no global quiet existed.
- **F3** — `get_notification_prefs` failed *open* (a store outage emails
  opted-out members) and the member-state PUT accepted any JSON (a typo'd enum
  became permanent silence with no error).
- **F6** — a second live pref store: the daily-P&L opt-in in
  `contract/_preferences.yaml` `operator_notifications`, violating ADR-489 D5's
  "one store."
- **F7** — the only management UI was an `<h3>` inside User Settings → Account,
  below the Danger Zone; neither the bell nor the Notifications window linked
  to it.
- **F9** — schema residue: `scheduled_messages`, `email_delivery_log`
  (write-only by construction — its RLS joins through the dead parent),
  `workspaces.digest_*`, the `in_app`/`source_type` CHECK fossils,
  `daily_update_email.py` (zero callers), `test_delivery_email_rendering.py`
  (imports a deleted module). All measured empty/dead in production.

## 3. Decisions

### D1 — The kind registry: declared semantics, one owner per kind

`api/services/notifications.py::NOTIFICATION_KINDS` is the singular registry of
notification kinds — each `{key, owner, label, description, email_default,
email_note}`. `owner` is `kernel` or an app slug; **a kind has exactly one
owner**, which resolves the lens problem (Files, Text, and Studio all display
the same file edit, so *file changes* belongs to the substrate/kernel and
appears once — no per-app double-counting, no per-path matrix). Kinds at
ratification:

| key | owner | email | note |
|---|---|---|---|
| `decisions` | kernel | dial, default `high` | proposals awaiting you + peer/agent workspace acts (was `witness_email`) |
| `reports` | kernel | dial, default `none` | recurring reports addressed to you (today: the daily P&L reconciliation) — opt-in preserved |
| `mentions` | chat | **declared, unwired** *(WIRED 2026-08-25 by [ADR-605](ADR-605-a-mention-reaches-its-person.md): default `all`, on/off dial)* | the ADR-495 D6 standing gap; the pane names the absence instead of hiding it |
| `runs` | agents | **declared, unwired** | failures already reach the bell as `material` via the weight derivation; email lands only when a real send path exists |

The registry is served (`GET /api/notification-kinds`) so the pane renders
backend-driven vocabulary — a hand-kept FE copy is the drift ADR-592 exists to
prevent. In-app is not a column: it is always-on derivation, and the pane says
so. A kind with no wired email path renders as a **named refusal** (the ADR-572
D10 lesson: a deliberate absence must be stated where it is felt), never as a
live toggle — the F1 sin was dials wired to nothing.

### D2 — The pref shape, re-cut per kind; store and keying unchanged

`member_state['notification_prefs']` (per **(workspace, principal)** — ADR-489
D5 verbatim, "mute one commons, not all") holds:

```json
{ "email": { "decisions": "all|high|none", "reports": "all|none" } }
```

Only **wired** kinds are accepted. `validate_notification_prefs()` lives beside
the registry; the member-state PUT calls it for this key and 422s on unknown
keys or bad enum values — a typo is refused at the door, not stored as silence.
The legacy 3-key shape (`delivery_email`/`failure_email`/`witness_email`) is
**deleted, not dual-read**: production carries zero prefs rows, so there is
nothing to migrate (migration 245 clears any stragglers defensively).

### D3 — One chokepoint; the gate fails CLOSED

`send_notification(kind=…)` is the one path for system-Resend email to a
**principal**: it gates by the recipient's dial, writes the transport row only
on an actual send, then sends. Two amendments:

- **Fail closed**: a prefs-store read failure now *skips the send* (logged).
  Emailing someone who chose `none` because the store hiccuped is a correctness
  violation; a missed courtesy email is a degradation.
- **`kind="direct"`**: ungated by policy but always recorded. Used by
  `platform_email_send_to_operator` (the operator's own agent addressing them
  under explicit instruction — the instruction is the consent; the transport
  row makes `/api/emissions` honest) and available to callers with caller-side
  consent. `send_notification` accepts `subject`/`html`/`text` overrides so
  composed emails ride the same chokepoint.

**Exemptions, named**: the workspace invite (the recipient is a raw email
address — no principal exists yet to hold a pref or key a transport row) and
`POST /api/account/test-email` (an explicitly requested diagnostic to self).
The gate enforces the roster: `jobs.email` is importable only by
`services/notifications.py`, `services/workspace_invites.py`,
`routes/account.py`, and the email-shell/test scaffolding.

### D4 — The daily P&L opt-in folds into the one store

`daily_pnl_email.py` stops reading `contract/_preferences.yaml` and routes
through `send_notification(kind="reports")` — default `none` preserves the
opt-in posture; the sent-marker dedup stays (it is send-idempotency, not a
preference). The `operator_notifications` block in `_preferences.yaml` is
retired; an operator who had opted in re-opts via the pane (production check
2026-08-21: acceptable — the send path's own gate chain had it quiet).

### D5 — The Notifications pane, on the User Settings door

A pane-grade registry row (`slug: notification-settings`, `pane_of: settings`,
`pane_group: "Notifications"`) + the FE pane in the settings page. "What should
I be told" is a personal question — DP35 member-experience scope, never
authorization — which is the account door's identity; the pane **names the
acting workspace** it governs, because the store is per-commons. The pane
renders the D1 registry grouped by owner face: each wired kind gets its email
dial; in-app is described as always-on-derived; unwired kinds print their
refusal. The Account pane's "Email Notifications" `<h3>` is deleted. The bell
popover and the Notifications window each gain a "Notification settings" door.
Save failures surface through `FeedbackContext.toast` (ADR-400), not
`console.error`.

### D6 — Residue swept (migration 245 + code)

`scheduled_messages` + `email_delivery_log` dropped (both empty; the Resend
webhook stops writing the latter — `export_log`/`agent_runs.delivery_status`
remain the delivery-outcome record); `workspaces.digest_*` columns dropped
(`owner_email` **stays** — `routes/admin.py` reads it; the audit's
zero-reference claim was wrong there and was caught by re-verification);
`cleanup_old_trigger_logs()` dropped; the `notifications` CHECKs re-cut
(`channel = 'email'` only; the decorative `source_type` CHECK dropped — the
column is a code-controlled label); `daily_update_email.py` and
`test_delivery_email_rendering.py` deleted; `scope_manifest.yaml` and the
ADR-582 doc-drift in `routes/integrations.py` corrected.

## 4. What this does NOT do

- No mention wiring (Phase 3 — ADR-492's ruled shape, its own build). The
  `mentions` kind is declared so the pane can name the gap. *(Phase 3 landed
  2026-08-25 as [ADR-605](ADR-605-a-mention-reaches-its-person.md).)*
- No push transport, no digest batching (both remain named future mounts;
  the dial enum keeps headroom).
- No per-path subscription matrix — never (ADR-405 D5). No second attention
  store, no stored read state, no change to the bell/timeline derivation.
- No change to who *may* be told: routing stays derived from grants; prefs
  stay presentation-layer.

## 5. Sequencing

One arc, three commits: (1) this ADR; (2) backend re-cut + migration 245 +
gate; (3) the pane + FE doors. Render parity: no env-var changes; the
scheduler's only touchpoint is `daily_pnl_email`, which keeps its trigger and
changes only its send path.

## 6. Layer sequencing — the internal-first rule and the Layer-1 scope (amended 2026-08-25, operator-ruled)

Ratified in-discourse after ADR-605's opt-in amendment: **the system-internal
(derived, in-app) notification surfaces stabilize to a comprehensive level
BEFORE outbound expansion.** Email/push/digest are Layer 2 — machinery a
member turns on, never a default the system assumes; every kind's dial is
opt-in-or-quiet until Layer 2 opens as its own deliberate arc.

**Layer 1 scope** (from the comprehensiveness audit,
`docs/evaluations/2026-08-25-notifications-layer1-comprehensiveness-audit.md`
— receipts there). Stable core, verified: decisions · mentions (lane path)
· peer/agent acts with weight · run receipts+failures · inbound arrivals ·
balance runway · per-(workspace, principal) scoping with the cross-device
cursor. Remaining Layer-1 work, ordered:

1. **G1** — the mention stamp moves to the ONE conversation-write chokepoint
   (today only `routes/lanes.py` stamps; five other `write_narrative_entry`
   callers — including live MCP-authored rows — do not, so a connected AI's
   @mention routes nowhere).
2. **G2** — membership changes become visible ("X joined the workspace"):
   `accept_invite` touches no ledger, and the timeline's closed source list
   (ADR-410 §2) needs an ADR-level widening to carry grant events.
3. **G3** — realtime bell (this ADR's named phase 4): replace the 60s poll
   on the ADR-575 realtime primitive.
4. **G4** — mention polish: the viewer's own chip · DM display-name in
   mention rows · the "add them?" OFFER on mentioning a non-participant
   (never auto-invite).
5. **G5** — verification debt: suppression live-proof.

**Out of Layer 1, recorded**: email defaults/digest/push (Layer 2) · `runs`
email · `@everyone` · tags-as-routing (ADR-405 D5) · per-path subscriptions
· stored read receipts.
