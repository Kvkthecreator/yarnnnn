# ADR-650 — Account email: the always-on class

**Status**: Accepted + Implemented · 2026-09-12 (operator ask: *"check if we have email system for say new
users, or when they leave or do some settings level changes. i don't believe we do"*; ruling on the findings:
*"aligned in full … ensure singular streamlined discipline with code and docs, scoping in deletion and
clean-up of code where warranted"*).
**Amends** [ADR-593](ADR-593-apps-declare-semantics-the-kernel-derives-emission.md) — D1 (the registry gains
a FIXED kind), D3 (a third named exemption), §6 (the Layer-2 opt-in rule does not govern account
correspondence).
**Relates to** ADR-498 (one email shell), ADR-202 (pointer-only), ADR-465 D2 (the mint), ADR-386/431
(eviction), ADR-608 (membership on the timeline), ADR-561 (an account deletion names what it removed).
**Hat**: A. **Gate**: `api/test_adr650_account_email.py`.

---

## 1. The audit — a working wire that nothing lifecycle-shaped ever touched

The belief was "we have no email system". Half right. What exists:

- the system Resend wire, `api/jobs/email.py`, sending as `noreply@yarnnn.com`, keyed on the API and
  the scheduler;
- ONE chokepoint for mailing a principal, `send_notification` in `api/services/notifications.py`
  (ADR-593 D3): dial → transport row → send; kinds `decisions · reports · mentions · direct`;
- ONE house shell, `api/services/email_shell.py` (ADR-498 D2);
- two named exemptions to the chokepoint: the workspace invite (recipient is a raw address) and the
  operator's test-email door;
- Supabase Auth's own mail (confirmation, recovery, email change) — not our code; its SMTP and
  templates live in the dashboard, unverifiable from the tree.

What the live database said (read-only probe, 2026-09-12):

| receipt | value |
|---|---|
| emails ever sent through the chokepoint | 1 — a mention, 2026-08-25 |
| members who ever set a notification dial | 0 |
| accounts | 17 (9 Google, 8 email/password) |
| Google sign-ups, who have therefore never received one email from yarnnn | 9 |
| email sign-ups still unconfirmed | 1, created that day |
| invites ever issued | 8 (6 accepted) |

So: a new owner got nothing at genesis (`ensure_owner_workspace`); a joiner got nothing at
`accept_invite`; `DELETE /account/deactivate` dropped the auth user silently; a member the owner revoked
heard nothing; no self-leave door exists at all. The one email a majority of accounts could ever have
received was the invite — and only if someone invited them.

## 2. The ruling that binds, and the distinction it needs

ADR-593 §6 (operator-ruled 2026-08-25): outbound email is **Layer 2** — *"machinery a member turns on,
never a default the system assumes; every kind's dial is opt-in-or-quiet."* That rule is correct for what
it governs: **notifications about workspace activity**, where the member is being told about acts that
happened around them and can reasonably choose silence.

A welcome cannot be opt-in — no preference exists before the account. A farewell cannot be opt-in — no
principal exists after it. A revoked membership is the end of the relationship the preference lived in.
These are not notifications about activity; they are **the account's own correspondence**, and the
consent is the relationship itself. ADR-593 D3 already carried this reasoning for the invite: *"the
recipient is a raw email address — no principal exists yet to hold a pref."* This ADR generalises the
exemption into a class instead of adding exemptions one by one.

> **Account correspondence is consent-by-relationship. It is never dialled, always recorded, and the
> kernel owns it.**

## 3. Decisions

### D1 — A fifth kind, `account`, kernel-owned and FIXED

`NOTIFICATION_KINDS` gains `{key: "account", owner: "kernel", email_default: "all", fixed: True}`. A
**fixed** kind has no dial:

- `FIXED_KINDS` is derived from the registry beside `EMAIL_DIAL_DEFAULTS`, which now **excludes** fixed
  kinds — so `validate_notification_prefs` refuses a stored pref for it (no silence can be stored), and
  the served registry (`GET /api/notification-kinds`) carries `fixed` so the pane renders the fact.
- `_pref_allows` returns true for a fixed kind before the store is consulted; `send_notification` does not
  read the store at all for one. The fail-closed rule (ADR-593 D3) guards **dials**, not the
  relationship: an unreadable store can silence a dialled kind and cannot silence a welcome.
- Every account send still writes its transport row (`source_type='account'`), so `/api/emissions` stays
  honest and the suppression/audit surfaces see it.

The Notifications pane renders a fixed row as **"Always sent"** in the slot where a dialled kind shows a
select — the ADR-572 D10 lesson (a deliberate absence is stated where it is felt), now applied to a
deliberate constant.

### D2 — Four events, one hook site each, at the SERVICE layer where the act is

| event | hook site | recipient | gate |
|---|---|---|---|
| **welcome** | the `inserted` branch of `ensure_owner_workspace` (`services/supabase.py`), after the owner grant | the new owner | fires once per account by construction — every later call short-circuits on the re-check, so no idempotency key is needed |
| **welcome_joined** | `accept_invite` (`services/workspace_invites.py`), after the accept | the joiner | `is_first_membership` — no owned workspace and no other active human grant; an established member's later joins are on the timeline (ADR-608) and get no mail |
| **removed** | `evict_principal` (`services/principal_grants.py`), after the status flip | the evicted human | `role == "member"` — the ADR-431 D5 AI-connection cascade re-enters with non-human roles and sends nothing |
| **account_deleted** | `DELETE /account/deactivate` (`routes/account.py`) | the raw address | resolved from the JWT (else `auth.admin`) BEFORE `delete_user`; sent only AFTER it succeeds, so the mail never claims what did not happen |

The hook is the service, not the route, because the route is one door among several (the ADR-465 D2
lesson: a genesis door on a route is only as live as its caller). The route-level exception is the
farewell, whose act (`auth.admin.delete_user`) is inline in the route.

### D3 — The farewell is the third named exemption; the roster does not grow

`notifications.user_id` is NOT NULL and cascades on auth delete, so no transport row can outlive the
principal. The farewell therefore goes over `jobs.email` directly, like the invite. It is **composed** by
the one composer (`services/account_email.py::compose_account_deleted`) and **sent** from
`routes/account.py`, which is already on the ADR-593 D3 import roster — the roster is unchanged and the
composer never imports the wire.

### D4 — One composer, one shell, pointer-only

`api/services/account_email.py` is the only module that names `kind="account"`. Every event renders
through `email_shell.render_email` with one CTA into the product (ADR-202) and a footer that says why the
mail arrived and where workspace-activity mail is governed. User-supplied strings (a workspace name, an
address) are escaped. The mint-default workspace name is never leaked ("your workspace" instead —
`display_workspace_name`, the ADR-498 rule).

### D5 — Inline, non-blocking, never load-bearing for the act

`account_email.dispatch` schedules a send on the running loop when there is one (an async route calling
the service) and on a daemon thread with its own loop when there is not (`get_user_client` is a sync
dependency run in a threadpool). No worker, no queue, no Redis — the platform rule holds. The act that
triggered the mail never waits on it and never fails for it; a failed send is a log line.

### D6 — Cleanup executed under the same discipline

- `notifications._send_notification_email` still carried its own inline HTML — the "sixth private
  variant" ADR-498 D2 was written to end. It now renders through the shell, and the plain `message` (a
  mention label, a witness line — user-controlled strings) is **escaped**; a caller with composed HTML
  passes `html=`.
- `jobs.email.send_test_email` wore raw `<h1>` markup. It wears the shell.
- The manage link (`/settings?settings.pane=notification-settings`) was hand-built in the template; it is
  now `deep_links.notification_settings_url()`, the single URL source of truth (ADR-202), used by both
  footers. The gate refuses a hand-built copy anywhere under `services/`.

### D7 — The gate

`api/test_adr650_account_email.py` (48 checks): the kind is fixed and refused by the validator; the four
hook sites exist in the right order (welcome after the grant, joined after the accept and behind the
first-membership predicate, removed after the revoke and behind the human-role predicate, farewell
resolved-before/sent-after the delete); the composer never imports the wire and only it names the kind;
**driven** — a fixed send writes one transport row and reaches the wire with the prefs store DOWN, while a
dialled kind under the same fault still fails closed; dispatch is non-blocking on both paths; the pane
renders the fact; the shell is singular and the manage link has one home. `test_adr593` is amended (D1
derivation excludes fixed kinds; `_pref_allows(None, "account")` is true; the roster comment names the
third exemption) and stays green at 41/41.

## 4. What this does NOT do

- **Security-change mail** — a new AI connection authorised (`_ensure_foreign_llm_grant`, the OAuth code
  path), a credential connected or removed on Reach, BYOK set or cleared. These are the next tenants of
  the `account` kind: same composer, same class, one hook each. Deferred to their own commit so this one
  ships the lifecycle spine.
- **Supabase Auth mail parity.** Confirmation, recovery, magic-link and email-change mail is Supabase's.
  Whether the project uses custom SMTP through the Resend domain or Supabase's default sender is a
  dashboard fact this tree cannot see; the ADR-498 lesson (the first contact was the least branded thing
  we sent) applies exactly. Open item in `docs/SESSION-HANDOFF.md`.
- **Resend webhook reconciliation of notification rows.** `routes/webhooks.py` matches delivery events
  only against `export_log` (zero rows exist), so a bounce on any notification email is logged and
  dropped. Storing the Resend message id on the transport row would close it; not taken here.
- No self-leave door for a member; no digest; no push; no per-path matrix (ADR-405 D5, never).

## 5. Verification

Gates run green after the change: ADR-650 48/48 · ADR-593 41/41 · ADR-498 · ADR-489 52/52 · ADR-465
15/15 · genesis 38/38 · ADR-410 44/44 · ADR-431 7/7 · ADR-605 55/55. `next build` clean.

**Live receipt (2026-09-13 00:3x UTC, deploy `dep-daiurf5ckfvc739d70o0` on `yarnnn-api`, commit `96b54b9`
carrying `e5a27a6`).** `probe_cold_user_genesis.py --email delivered@resend.dev` against production: a
genuinely cold principal (`ca558a76…`) → one ordinary authenticated call minted the workspace and the owner
grant → the lane opened with its cast → and the ADR-650 step:

```
PASS  5 the mint dispatched the welcome (ADR-650: one account transport row)
      row={'status': 'sent', 'message': 'Welcome to yarnnn', 'error_message': None}
ALL PASS — 7/7
```

The row was cascaded away with the probe user at teardown, as D3 predicts; the probe is the only reader that
sees it, which is why the probe carries the check.
