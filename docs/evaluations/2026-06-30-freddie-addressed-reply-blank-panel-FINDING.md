# FINDING — Freddie's addressed reply persists to a blank panel: the role CHECK constraint never learned `freddie`

**Date**: 2026-06-30. **Hat**: B (discovered) → A (fixed, same session). **Workspace**: live operator (`U=2abf3f96`, kvk). **Trigger**: operator asked Freddie in chat "can you see my Slack connector… check the daily-work channel, give me the last item." A reply appeared once ("it didn't work"), then the chat pane showed nothing on re-render.

> **Verdict**: **CONFIRMED bug, fixed.** The addressed wake SUCCEEDED (`execution_events`: status=success, 675 output tokens, 21s) and the SSE frame rendered Freddie's reply live ONCE — but the reply was **never persisted** to `session_messages`. Root cause: the actor-identity unification (2026-06-30) renamed the narrative role `reviewer` → `freddie` in `services/narrative.py::VALID_ROLES` (whose comment claims it "Mirrors the session_messages.role CHECK constraint") — but **no migration updated the DB constraint**. Migration 167's `session_messages_role_check` permitted `reviewer`, not `freddie`. So `write_freddie_message → write_narrative_entry(role='freddie')` hit the constraint (code 23514) on BOTH the RPC and the direct-insert fallback; `write_freddie_message` is best-effort (swallows the error, returns None) → the reply was lost. On any re-render the pane reads `session_messages`, finds the operator's question and no reply row → **blank panel**. Fixed by migration 191 (adds `freddie` to the constraint) + a regression guard so VALID_ROLES and the constraint can't drift again.

---

## Receipts

- **The wake succeeded but left no reply row.** `execution_events` for `U=2abf3f96`, trigger `addressed`, 2026-06-30T23:38 → `status=success`, `output_tokens=675`. The session (`6116c65d`) contains only the operator's `[user]` message — no `freddie`/`system_agent` reply, in that session or any session, in the wake window.
- **Reproduced the exact failing write.** Calling `write_narrative_entry(role='freddie', pulse='addressed', weight='material')` against the live DB surfaced:
  > `new row for relation "session_messages" violates check constraint "session_messages_role_check" (code 23514) — Failing row contains (…, freddie, …)`
- **The live constraint** (authoritative, pre-fix): `CHECK (role = ANY (ARRAY['user','assistant','system','reviewer','agent','external','system_agent']))` — has `reviewer`, lacks `freddie`. Last defined in migration 167; the app layer (`VALID_ROLES`) carries `freddie` but not the DB.

## Why it was invisible

Two compounding factors made a broken reply look like a healthy system:
1. **The wake records success.** The reply generates and the SSE frame renders it live — the operator sees it once. `execution_events` logs `status=success` (the generation worked; the persist is downstream and best-effort). From the audit layer, nothing is wrong.
2. **The persist is best-effort + silent.** `write_freddie_message` is documented "never raises… write-and-forget"; `write_narrative_entry` logs the constraint violation at WARNING and returns None. No surface, no failed execution_event. The reply silently evaporates between the live frame and the persisted record.

This is the same "looked healthy from the audit-log layer" class the `_validate_context_shape` validator was built to catch — a shape mismatch nothing asserted on.

## The fix

- **Migration 191** (`191_session_messages_freddie_role.sql`): `session_messages_role_check` gains `freddie` (keeps `reviewer` for historical rows + the `reviewer:` attribution lineage). Applied to the live DB; verified the constraint now includes `freddie`; re-ran the exact write → succeeds.
- **Regression guard** (`api/test_session_role_constraint_sync.py`, 3/3): asserts `VALID_ROLES ⊆ the latest migration's role constraint`, so the app layer and the DB can never drift again. (This drift was *caused* by VALID_ROLES claiming to mirror a constraint it didn't — the guard makes that claim enforceable.)

## Not in scope (separate, correctly-behaving)

- **Slack content.** Slack shows "Connected · never synced · 0 sources." Freddie reads *substrate*, not live Slack APIs (ADR-153/264 — platform data enters substrate via `SyncPlatformState` on a mechanical recurrence, which this workspace has not run). So Freddie genuinely had no Slack content to read — its "it didn't work" was an honest report, not a defect. (Whether a bare workspace should *offer* to set up Slack sync is a product question, not this bug.)
- **The best-effort silent-swallow.** Worth considering whether an addressed-cycle reply persist should fail loudly (it's the operator's conversation, not an autonomous narrative entry where a missing session is normal). Noted, not changed here — it's a judgment call orthogonal to the constraint fix, and the regression guard removes the recurrence risk that made the silence costly.

## Reproduce

```
# the failing write (pre-191), against any session:
write_narrative_entry(client, session_id, role='freddie', summary='x', pulse='addressed', weight='material')
#   → session_messages_role_check violation (code 23514)
# after 191: succeeds. Guard: cd api && ../.venv/bin/python test_session_role_constraint_sync.py  (3/3)
```
