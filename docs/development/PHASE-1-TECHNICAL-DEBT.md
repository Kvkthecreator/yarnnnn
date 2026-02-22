# Phase 1: Technical Debt Clearance

> Pure technical fixes — bugs, error handling, performance, code hygiene.
> These are independent of YARNNN workflow/product decisions and can be executed immediately.
> Ref: CLAUDE.md Execution Disciplines #2 (Singular Implementation), #4 (Code Quality Checks)

**Status**: Complete (3 sessions)
**Estimated sessions**: 3 focused sessions
**Approach**: Fix in priority order. Each session = commit when complete.

---

## Session 1: Critical Bugs (Runtime Failures)

These will crash in production. Fix first.

### 1.1 Undefined `ephemeral_stored` variable

- **Files**: `api/jobs/import_jobs.py` ~lines 399, 800
- **Bug**: `ephemeral_stored` used in return dicts for `process_slack_import()` and `process_gmail_import()` but never defined. Both paths hit `NameError` at runtime.
- **Fix**: Either define the variable from the batch store result, or remove it from the return dict if it's no longer needed post-refactor. Check callers to see if anything reads this key.

### 1.2 Token retrieval inconsistency across platforms

- **File**: `api/workers/platform_worker.py`
- **Bug**: Four platforms, three different token retrieval patterns in the same file:
  - Slack (~line 189): Tries `settings`, `metadata`, then decrypts `credentials_encrypted` via `TokenManager`
  - Gmail (~line 294): Reads plain `refresh_token` — no decryption
  - Calendar (~line 531): Reads plain `refresh_token` — no decryption
  - Notion (~line 412): Decrypts `credentials_encrypted` via `TokenManager`
- **Fix**: Standardize all four to use the same pattern. The Slack/Notion path (decrypt via `TokenManager`) is the correct one. Gmail/Calendar should decrypt `refresh_token_encrypted`, matching what `signal_extraction.py` and `delivery.py` do.
- **Verify**: Check `platform_connections` schema to confirm column names (`credentials_encrypted`, `refresh_token_encrypted`).

### 1.3 Environment variable name mismatch

- **Files**: `api/services/supabase.py` (~line 63), `api/jobs/scheduler.py` (~line 142), workers
- **Bug**: `SUPABASE_SERVICE_KEY` vs `SUPABASE_SERVICE_ROLE_KEY` used interchangeably. `scheduler.py` uses bare `os.environ[]` — crashes if only one is set.
- **Fix**: Pick one canonical name (`SUPABASE_SERVICE_ROLE_KEY` is Supabase's standard). Find-and-replace across codebase. Add fallback where needed during transition.
- **Check**: Render env vars, `.env.example`, any deployment docs.

### 1.4 Encryption key auto-generation

- **File**: `api/integrations/core/tokens.py` ~lines 38-42
- **Bug**: Missing `INTEGRATION_ENCRYPTION_KEY` silently generates a new Fernet key. On server restart, all previously encrypted tokens become undecryptable. Silent data loss — all OAuth connections break.
- **Fix**: Raise `RuntimeError` at startup if key is not set. Remove the auto-generate fallback. This is a security and data integrity issue.
- **Related**: Add to startup validation (see 2.5).

---

## Session 2: Error Handling & Resilience

Silent failures that hide bugs and make debugging impossible.

### 2.1 Unsafe `.single()` calls in signal extraction

- **File**: `api/services/signal_extraction.py` (~lines 173, 263, 351, 474)
- **Bug**: `.single()` raises an unhandled exception if 0 or >1 rows match. If a user has no active Google connection, the entire signal extraction crashes.
- **Fix**: Replace `.single()` with `.maybe_single()` at all four locations. Add explicit `if not conn_result.data: return None` guard after each.

### 2.2 Bare `except:` handlers

- **Files**:
  - `api/routes/documents.py` ~line 172 — `except: pass` swallows storage cleanup failures
  - `api/services/signal_processing.py` ~line 509 — `except:` on date parsing catches all exceptions
- **Fix**: Replace with `except Exception as e:` minimum. Add `logger.warning()` with context. For the date parsing case, use `except (ValueError, TypeError)`.

### 2.3 Silent query failures in working_memory.py

- **File**: `api/services/working_memory.py` (12 instances, lines ~84-444)
- **Bug**: Pattern `except Exception: return []` with no logging. Schema mismatches, RLS errors, connection failures — all invisible.
- **Fix**: Add `logger.warning(f"[WORKING_MEMORY] Query failed: {e}")` to each handler. Keep the graceful fallback (return empty) but make failures visible.

### 2.4 Missing decrypt error handling in signal extraction

- **File**: `api/services/signal_extraction.py` (~lines 187, 277, 359, 481)
- **Bug**: `token_manager.decrypt()` called without try/except. One corrupted token crashes signal extraction for that entire user.
- **Fix**: Wrap each decrypt in try/except. On failure, log error with user_id and platform, return `None` for that platform's content (let others continue).

### 2.5 No startup environment validation

- **File**: `api/main.py`
- **Bug**: App starts successfully with missing env vars, then fails mid-request. No fail-fast behavior.
- **Fix**: Add a `validate_environment()` function called at import time or in `startup` event. Required vars:
  - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
  - `ANTHROPIC_API_KEY`
  - `INTEGRATION_ENCRYPTION_KEY`
- Log warnings for optional vars (`REDIS_URL`, Lemon Squeezy keys).

---

## Session 3: Performance, Scaling & Code Hygiene

Not breaking today, but will break at growth. Plus quick cleanups.

### 3.1 Google token refresh — no caching

- **File**: `api/integrations/core/google_client.py` (~lines 52-78)
- **Issue**: Every Google API call does a full OAuth token exchange. Google tokens are valid for 1 hour. 50 Gmail messages = 51 unnecessary token refresh calls.
- **Fix**: Cache the access token with its expiry. Return cached token if `expires_at > now + 60s`. Simple in-memory cache per `refresh_token` is sufficient.

### 3.2 No rate limiting / backoff on Google API

- **File**: `api/integrations/core/google_client.py`
- **Issue**: 429 (rate limited) or 403 (quota exceeded) from Google raises generic `RuntimeError`, killing the entire sync job.
- **Fix**: Add retry with exponential backoff for 429/5xx responses. For 403 quota errors, log and skip (don't retry). Use `tenacity` or a simple manual retry loop (3 attempts, 1s/2s/4s backoff).

### 3.3 No timeouts on external API calls

- **Files**: `api/integrations/core/google_client.py`, `api/services/signal_processing.py` (~line 139)
- **Issue**: Neither Google API calls nor Anthropic LLM calls have timeouts. Can hang indefinitely, blocking the scheduler.
- **Fix**: Set `timeout=httpx.Timeout(30.0)` on Google httpx clients. Wrap LLM calls in `asyncio.wait_for(coro, timeout=60.0)`.

### 3.4 Unbounded queries in unified scheduler

- **File**: `api/jobs/unified_scheduler.py`
- **Issues**:
  - ~line 1000: Loads ALL users with no pagination
  - ~lines 1087, 1208: Joins `deliverable_versions` with no `.limit()` — can return 1000+ rows per user
- **Fix**:
  - Add `.limit(100)` pagination for user queries (process in batches)
  - Add `.limit(5)` on the deliverable versions join (only need most recent for signal reasoning)

### 3.5 Duplicate signal processing blocks

- **File**: `api/jobs/unified_scheduler.py` (~lines 1036-1277)
- **Issue**: Calendar vs non-calendar signal processing are copy-pasted 50+ line blocks. Bug fix in one won't propagate.
- **Fix**: Extract shared logic into a helper function. Pass `signals_filter` as parameter.

### 3.6 Deprecated `datetime.utcnow()`

- **Files**: `api/services/signal_extraction.py` (~line 90), `api/services/delivery.py` (~lines 325, 350, 600)
- **Issue**: Returns naive datetime (no timezone info). Rest of codebase correctly uses `datetime.now(timezone.utc)`. Mixing causes `TypeError` on comparison. Deprecated in Python 3.12+.
- **Fix**: Find and replace all `datetime.utcnow()` with `datetime.now(timezone.utc)`. Verify `timezone` is imported from `datetime`.

### 3.7 Model name mismatch

- **File**: `api/services/signal_processing.py` (~line 46)
- **Issue**: Comment says "Haiku for cost efficiency" but code uses `claude-sonnet-4-20250514`. Comment on line 45 says "using sonnet as haiku-4 is not yet available" — but `claude-haiku-4-5-20251001` exists.
- **Fix**: Either switch to Haiku (if cost is the priority for signal reasoning) or update the comments to reflect intentional Sonnet usage. Don't leave the mismatch.

### 3.8 Dead code removal

- **File**: `api/routes/deliverables.py` (~line 35)
- **Issue**: `_trigger_domain_recomputation()` is a no-op per ADR-059, never called.
- **Fix**: Delete the function entirely per CLAUDE.md Discipline #2 (Singular Implementation — delete legacy code).

### 3.9 OAuth state in-memory (document, don't fix yet)

- **File**: `api/integrations/core/oauth.py` (~line 138)
- **Issue**: `_oauth_states` dict lives in process memory. Server restart kills in-flight OAuth flows. Can't scale to multiple instances.
- **Action**: Document as known limitation. Not blocking for single-instance Render deployment. Flag for Phase 2 if multi-instance scaling becomes relevant.

---

## Verification Checklist (Post-Execution)

All items verified across 3 sessions:

- [x] `import_jobs.py` — `ephemeral_stored` → `items_stored` (Session 1, commit 4046c56)
- [x] `platform_worker.py` — Gmail/Calendar use TokenManager decryption (Session 1)
- [x] Env vars — Standardized to `SUPABASE_SERVICE_KEY` across 7 files (Session 1)
- [x] `tokens.py` — Missing encryption key raises `ValueError` (Session 1)
- [x] `signal_extraction.py` — `.maybe_single()` × 4, decrypt wrapped × 4 (Session 2, commit e15d8b1)
- [x] No bare `except:` in `documents.py`, `signal_processing.py` (Session 2)
- [x] `working_memory.py` — All 12 exception handlers now log (Session 2)
- [x] `main.py` — Startup env validation with `_validate_environment()` (Session 2)
- [x] `google_client.py` — Token caching, `_request_with_retry` (backoff on 429/5xx), `_GOOGLE_API_TIMEOUT` (Session 3)
- [x] `unified_scheduler.py` — Bounded user query (activity_log), `.limit(20)` on deliverables join, signal blocks deduplicated into shared loop (Session 3)
- [x] `datetime.utcnow()` fixed in: `signal_extraction.py`, `delivery.py`, `google_client.py`, `oauth.py` (Sessions 2-3). Note: other files (`deliverable_pipeline.py`, `integrations.py`, etc.) still have occurrences — tracked as follow-up
- [x] `signal_processing.py` — Model changed to `claude-haiku-4-5-20251001`, comment updated (Session 3)
- [x] `deliverables.py` — `_trigger_domain_recomputation` removed + `BackgroundTasks` import cleaned (Session 3)
- [x] `oauth.py` — In-memory limitation documented in comment block (Session 3)

---

## What This Does NOT Cover

The following are **intentionally excluded** — they require the holistic workflow conversation in Phase 2:

- Source selection enforcement (`selected_sources` not flowing to sync)
- Monetization tier enforcement at sync level
- `platform_content` read/write lifecycle (ADR-072 completion)
- Missing platform coverage (Calendar sync, Notion signals)
- Sync frequency interaction with signal processing cadence
- Incremental sync / sync tokens (product decision on full vs delta)

See: `docs/development/PHASE-2-WORKFLOW-HARDENING.md`
