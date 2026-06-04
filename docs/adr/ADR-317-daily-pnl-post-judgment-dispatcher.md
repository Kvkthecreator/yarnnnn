# ADR-317: Daily P&L Post-Judgment Dispatcher — Reviewer Triggers, Dispatcher Sends

> **Status**: **Implemented + live-validated** 2026-06-04. Phase 1 (dispatcher + wake-hook + test gate) shipped; the first live trader-suite run (kvk) confirmed the email **arrives in the operator's inbox composed correctly** (headline + windows match `_money_truth.md`). That run also surfaced two defects, both fixed same-day (§Defects-found-in-production). Test gate 18/18.
> **Date**: 2026-06-04
> **Authors**: KVK, Claude
> **Extends**: ADR-202 (External Channel Discipline — expository pointers), ADR-299 D5 (operator-addressing observability opt-ins), ADR-195 (money-truth substrate), FOUNDATIONS Axiom 6 (Channel) + Derived Principle 12 (channel legibility gates autonomy)
> **Depends on**: ADR-040 + ADR-202 (system Resend wire — `jobs/email.py`, `RESEND_API_KEY` already on API + Unified Scheduler), ADR-260/261 (real-time Reviewer loop + recurrences-as-prompts), ADR-281 (reconciler folds fills into `_money_truth.md`)
> **Honors (does not amend)**: the ADR-299 architectural commitment that `platform_email_send_to_operator` is **permanently excluded** from `REVIEWER_PRIMITIVES`

---

## Context

The alpha-trader bundle's `_preferences.yaml` declares an `operator_notifications.daily_pnl_reconciliation` opt-in:

> *"End-of-day email summarizing today's outcome-reconciliation: realized + unrealized P&L, fills count, signal attribution, calibration deltas vs declared expectancy. Reviewer composes from `/workspace/context/trading/_money_truth.md` after the @market_close + 1h outcome-reconciliation fire."*

This is the operator-facing half of the full-autonomy requirement: **the Reviewer runs the daily P&L confirmation alone, and the operator receives it without intervention.** But the opt-in described a dispatcher that **did not exist** — `operator_notifications.daily_pnl_reconciliation` had zero live consumers in `api/services/` or `api/jobs/` (only canary scripts + a forward-looking comment in `registry.py` referenced it). The opt-in was a promise with no machinery behind it.

The naïve fix — "let the Reviewer send the email" — is **structurally forbidden**. `platform_email_send_to_operator` is deliberately and permanently excluded from `REVIEWER_PRIMITIVES` (`api/services/primitives/registry.py` ~L431). The 2026-05-25 v4 canary proved that adding it to the Reviewer's 21-tool surface collapsed verdict output by ~74% and produced empty `stand_down` verdicts — tool-list size is empirically corrosive to judgment quality for the Reviewer surface. Reverting (v5) restored substantive judgment. The registry comment names the correct alternative: *"Operator notifications tied to Reviewer verdicts should reach operators via a post-judgment dispatcher hook ... — same shape as services/notifications.py ADR-040 pattern. NOT here."* This ADR builds that dispatcher.

## Decision

**The Reviewer triggers; a post-judgment dispatcher sends.** The Reviewer runs the `outcome-reconciliation` judgment (the deterministic reconciler folds fills into `_money_truth.md`; the Reviewer closes the cycle with a forward-looking verdict). A new dispatcher fires **after** that judgment completes, reads the substrate the judgment produced, and sends the daily P&L email out-of-band via the system Resend wire.

### D1 — New service `api/services/daily_pnl_email.py`

Mirrors `daily_update_email.py` (ADR-202): deterministic windows read from `_money_truth.md` frontmatter → **expository-pointer** HTML (deep-link CTA, never an action-on-email button per FOUNDATIONS Axiom 6) → `jobs.email.send_email`. The email is the invitation back to the cockpit, not a replacement UX.

`maybe_send_daily_pnl_email(client, user_id)` gates in order: (1) operator opted in (`operator_notifications.daily_pnl_reconciliation.active: true`); (2) `_money_truth.md` exists (the judgment produced substrate to summarize); (3) operator email resolvable. Empty/bootstrap windows degrade to honest copy ("calibration begins from zero") rather than fabricating numbers.

### D2 — Post-judgment hook in `wake.py::_invoke_recurrence_wake`

A fourth best-effort, non-fatal post-judgment side-effect alongside the existing `render_lineage_entry_if_material` + `surface_reviewer_actions` + `_maybe_auto_compose` hooks. **Slug-gated** on `recurrence.slug == "outcome-reconciliation"` so it costs nothing for any other recurrence. Wrapped in try/except — a notification failure must never break dispatch.

### D3 — Observability, not consequential action (ADR-299 D5)

The opt-in IS the standing approval. AUTONOMY `delegation` does NOT gate this — it is the operator's own inbox, no third-party write, same model ADR-040 + ADR-202 already use for the operator-addressing channel. **Default-off** in the bundle (`active: false`); the operator flips it on per workspace. No `platform_connections` gate — the system Resend wire is kernel plumbing.

### D4 — No new env var, no Render parity drift

The dispatcher rides the existing system Resend wire (`RESEND_API_KEY`, already required on API + Unified Scheduler for the ADR-040/202 notification + daily-update paths). The dispatcher runs in the scheduler tick (`wake_drainer` → `_invoke_recurrence_wake`), which already has the key.

## What this ADR does NOT do

- Does NOT add any tool to `REVIEWER_PRIMITIVES`. The commitment that the Reviewer's tool surface stays minimal is honored, not amended. Test gate locks it.
- Does NOT make the Reviewer aware of the email. The Reviewer runs its judgment; the dispatcher is downstream and invisible to the judgment loop.
- Does NOT introduce a new recurrence. The dispatcher hangs off the existing `outcome-reconciliation` wake completion.
- Does NOT change the substrate. It reads `_money_truth.md` (written by the reconciler) + `_preferences.yaml` (operator-authored opt-in); it writes nothing.

## Consequences

- The `operator_notifications.daily_pnl_reconciliation` opt-in is now real. Flipping it `active: true` in a workspace's `_preferences.yaml` produces a daily P&L email after the @market_close+1h outcome-reconciliation fire.
- The pattern generalizes: `operator_notifications.signal_fire_alert` + `regime_state_change_alert` (also default-off in the bundle) can adopt the same post-judgment-dispatcher shape in follow-on work, each gated on the relevant wake/event.
- The eval suite can now assert the **full** compose-and-send EOD artifact end-to-end (see the alpha-trader autonomous-loop suite), not just the Reviewer's composition.

## Defects found in production (2026-06-04 first live run, fixed same-day)

The first live trader-suite run validated the happy path (email arrived, composed correctly) AND surfaced two defects — the value of a live run over unit tests:

- **D-fix-1 — double-fire.** The `outcome-reconciliation` recurrence can fire more than once per day (manual_fire + cron, or — as in the eval — fired twice across two evals). The dispatcher had no idempotency guard, so each fire sent a duplicate email (two identical P&L emails in the operator's inbox). **Fix:** a once-per-UTC-day guard — `_already_sent_today()` reads a substrate marker `/workspace/review/_daily_pnl_sent.yaml` (written `authored_by="system:daily-pnl-dispatcher"` AFTER a confirmed send, so a failed send stays retryable). The send-time date is read from the runtime clock (Axiom 4 — time is perceived, not stored); the marker records *which* date was last sent (auditable, restart-safe).

- **D-fix-2 — stale CTA URL.** The email's "Open cockpit" CTA pointed at `https://yarnnn.com/overview`, a dead redirect stub. `overview_url()` (the shared deep-link helper, also used by `daily_update_email` + `notifications`) was built around the defunct `/overview` surface. **Fix:** repointed `overview_url()` to `/desktop` (`HOME_ROUTE` per ADR-297 D17 — the authenticated landing route where auth-callback + middleware land operators). Source-level fix heals the stale CTA across all three notification surfaces in one place (Singular Implementation). Function name retained (3 callers) — a slight misnomer post-ADR-297, documented in the helper.

Both fixes are Hat-A (the email ships to operators). Test gate extended to 18/18 (idempotency 4 checks + CTA-target check).

## Files

- `api/services/daily_pnl_email.py` (new) — dispatcher + opt-in gate + windows parse + expository-pointer email.
- `api/services/wake.py` (`_invoke_recurrence_wake`) — slug-gated post-judgment hook.
- `api/test_adr317_daily_pnl_dispatcher.py` (new) — 13-assertion regression gate (opt-in default-off, windows render, REVIEWER_PRIMITIVES stays clean, slug-gated hook).
- `docs/programs/alpha-trader/reference-workspace/context/_shared/_preferences.yaml` — `daily_pnl_reconciliation` opt-in (pre-existing; this ADR builds its consumer).
