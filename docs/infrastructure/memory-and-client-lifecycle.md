# Memory & Client Lifecycle — Canonical Reference

**Version**: 1.1
**Created**: 2026-06-05 · **Updated**: 2026-07-02 (Anthropic client — third occurrence)
**Status**: Canonical — single authoritative reference for Supabase/httpx **and Anthropic**/httpx client lifecycle and process memory discipline on the always-on services.

---

## Why this doc exists

`yarnnn-api` (`srv-d5sqotcr85hc73dpkqdg`) runs on the Render **starter plan — a 512 MiB hard
memory cap, single uvicorn worker**. It has OOM-restarted at least twice from slow RSS creep:

- **2026-06-01** — first OOM. Partial fix in `services/supabase.py::get_user_client`
  (disable gotrue auto-refresh timer + close the postgrest pool in `finally`).
- **2026-06-04 21:40 UTC** — **recurred.** The partial fix was incomplete and missed the
  largest offender. This doc records the full diagnosis and the complete fix.
- **2026-07-01** — **recurred a third time, on the un-audited Anthropic client.** Same bug
  class, different SDK: `AsyncAnthropic()` was constructed per-call in all 7
  `services/anthropic.py` wrappers and never closed. See "The 2026-07-01 OOM" below.

The class of bug is **per-call construction of an httpx-pool-owning client without teardown**.
Every Supabase `create_client()` eagerly builds **two** httpx pools (postgrest + gotrue auth);
every `AsyncAnthropic()` eagerly builds **one** httpx pool (`max_connections=1000`). On a 512
MiB box, abandoning those pools inflates the process plateau until it crosses the ceiling.

---

## The 2026-06-04 OOM — receipts

Render `memory_usage` metric for instance `ct5bm`, 2026-06-04 (UTC):

| Time | RSS | Note |
|------|-----|------|
| 12:00 | 291 MB | healthy baseline after a fresh start |
| 14:40 | 529 MB | first near-OOM, GC narrowly clawed it back |
| 15:00–16:50 | ~470 MB | plateau — **never returned to baseline** |
| 21:10–21:35 | 535.8 MB | pinned against the 536,870,900-byte (512 MiB) limit |
| **21:40** | **237 MB** | **OOM-kill + automatic restart** (≈06:40 KST — the email) |

Signature: a **slow monotonic creep with each plateau settling higher than the last**
(290 → 470 → 535). That is unbounded accumulation, **not** a traffic spike. Render's three
suggested causes — traffic spike / undersized instance / memory leak — resolve to the third.

---

## Root cause

The API process has **no background loop** (`main.py` — no lifespan, no `create_task`), so all
growth is request-driven. Two offenders, ranked:

### 1. `services/working_memory.py::build_working_memory` — 23 clients per call, zero teardown (primary)

`build_working_memory` is on the hot feed/chat path (`routes/feed.py`). It parallelizes its DB
reads across the default thread pool and — to dodge the sync-httpx-pool thread-safety hazard —
gave **each of 23 parallel queries its own fresh `create_client()`**. None were ever closed.
Worse, the client was constructed on the **event-loop thread** and handed into a worker thread
via `asyncio.to_thread`, so the client object crossed threads (a latent thread-safety bug on
top of the leak).

23 clients/request × 2 httpx pools each, abandoned to GC, across a 7-thread pool, is what drove
the production plateau up.

### 2. `services/supabase.py::get_user_client` — incomplete teardown (secondary)

The 2026-06-01 fix closed `client.postgrest.session` in `finally` but **leaked the gotrue auth
httpx pool**, which `create_client` opens eagerly whether or not auth is used. Verified in the
installed library (supabase 2.27.3):

- `supabase/_sync/client.py:87` — `__init__` eagerly builds `self.auth`.
- `supabase_auth/_sync/gotrue_base_api.py:25` — the auth client opens its own `httpx.Client`.
- `supabase_auth/_sync/gotrue_base_api.py:38` — that auth client exposes `close()` — **nobody called it.**
- The `Client` class has **no unified `close()`** — each sub-client must be closed individually.

---

## Empirical proof (reproduced 2026-06-05)

A tight loop constructing `create_client()` repeatedly, measuring real RSS via `psutil`:

| Scenario | Result |
|----------|--------|
| `gc.get_objects()` count of live `Client` after 300 iters | **0** — no reference leak; objects ARE collected |
| Sync loop, close both sub-clients | flattens after ~250 iters → **0 KB/client** forever |
| **Threaded loop (the `build_working_memory` pattern), real network** | **+111 MB first batch (475 KB/client)**, plateau **~178 MB vs ~100 MB sync** |

Key reads:
- It is **not a Python reference leak** — `gc` reclaims the client objects.
- The retained cost is **httpx connection pools + TLS buffers + HTTP/2 hpack state held across
  the thread pool**, amplified by **glibc malloc arena retention** (Render is glibc Linux;
  glibc is notoriously reluctant to return per-thread arenas to the OS under threaded churn —
  which is why production kept climbing where a single-thread macOS probe flattens).

---

## The fix (three layers)

### Fix 1 — `build_working_memory`: per-thread client, created AND closed on its own thread

Replace the "construct-on-loop-thread, leak-after-use" pattern with a wrapper that constructs
the client **inside the worker thread**, runs the query, and **closes both sub-clients in a
`finally`** before the thread returns. This simultaneously:
- eliminates the leak (every pool is released),
- fixes the latent thread-safety bug (the client never crosses threads),
- keeps all 23 helper signatures `(user_id, …, client)` unchanged.

Single shared teardown helper `close_supabase_client(client)` in `services/supabase.py` closes
postgrest + gotrue auth (Singular Implementation — one teardown, every call site uses it).

### Fix 2 — `get_user_client`: complete the teardown

Route the `finally` block through the same `close_supabase_client(client)` helper so the gotrue
auth pool is released alongside postgrest. The hand-rolled `postgrest.session.close()` is deleted.

### Fix 3 — glibc allocator mitigation (safety net)

Set `MALLOC_TRIM_THRESHOLD_=100000` on the always-on services so glibc returns freed arenas to
the OS aggressively, turning "slow climb to OOM" into a stable sawtooth. Applied to the API and
the unified scheduler (the scheduler does its own client churn). This is defense-in-depth, not
the cure — Fixes 1 + 2 are the cure.

> The `get_service_client()` singleton (`@lru_cache`'d in `services/supabase.py`) is **safe** —
> one reused instance per process, never per-request. All 53 of its callers are fine. The leak
> was only ever in the **direct `create_client()` callers**.

---

## The 2026-07-01 OOM — the Anthropic client (third occurrence)

The Supabase fixes above held. The next OOM came from the **Anthropic** client, which nobody had
audited for the same discipline.

### Receipts

Render `memory_usage` for instance `jf54d`, 2026-07-01 (UTC) — a clean monotonic ramp on
**flat/declining traffic** (591 → ~190 req/30min) and **trivial CPU** (~0.01–0.02 core):

| Time | RSS | % of 512 MiB |
|------|-----|--------------|
| 07:30 | 203 MB | 40% |
| 09:00 | 369 MB | 69% |
| 10:30 | 452 MB | 84% |
| 11:00 | 495 MB | 92% |
| **11:30** | **537 MB** | **100% → OOM** |
| 12:00 | 234 MB (restarted) | 44% — with 11× HTTP 502 (the restart window) |

Memory rising while load falls, no CPU correlation — the leak signature. Frequent deploys had
been *masking* it (each redeploy recycled the process before it reached the cap); a quiet no-deploy
window let it breach. The kill left no app-log death message (Render OOM-kills at the cgroup level
with SIGKILL); the 502s are the only externally-visible symptom.

### Root cause

`services/anthropic.py::get_anthropic_client()` returns `AsyncAnthropic(...)`, which **eagerly**
builds an `httpx.AsyncClient` pool (`DEFAULT_CONNECTION_LIMITS = max_connections=1000`) in
`__init__`. All **7** wrappers (`chat_completion`, `chat_completion_with_usage`,
`chat_completion_with_tools`, `chat_completion_with_tools_stream`, `chat_completion_stream`,
`chat_completion_stream_with_tools`, + the max-rounds summary call) did `client =
get_anthropic_client()`, used it, and **never closed it**. The SDK's only cleanup is a best-effort
`__del__` finalizer that schedules `close()` on the running loop and swallows all errors — it does
**not** release the pool synchronously at drop time.

Amplifier: the Reviewer/Freddie loop calls the tool wrappers **once per tool round** inside a
`for _round in range(max_rounds)` loop, so a single multi-round wake abandoned **N** pools. And on
an SSE **client disconnect mid-stream** (the 502s), an orphaned streaming generator would leak the
full remainder of that wake's per-round clients.

### The fix

Every wrapper now uses `async with get_anthropic_client() as client:` (the SDK's `__aexit__` calls
async `close()`, releasing the pool). The one long-lived generator
(`chat_completion_stream_with_tools`) holds the client and releases it in a `try/finally: await
client.close()` around its body — so the pool is freed on normal return, on exception, **and on
`GeneratorExit`** (the disconnect case). Note the installed SDK (anthropic 0.86.0) exposes async
`close()`, **not** `aclose()`.

> The Anthropic client has no reused-singleton path today; per-call-with-teardown is the sanctioned
> pattern (a process-wide shared client is also valid — the SDK is coroutine-safe — but per-call is
> the lower-risk change and matches the Supabase discipline).

---

## Discipline rule (going forward)

**Never construct an httpx-pool-owning client per-call without teardown.** This covers Supabase
`create_client()` **and** `AsyncAnthropic()` (and any future SDK that builds a pool in `__init__`).
Sanctioned patterns:

1. **Reused singleton** — `get_service_client()` for service-key reads. Default choice for Supabase.
2. **Per-request / per-thread, closed in `finally`** — when RLS requires the operator JWT
   (`get_user_client`) or when thread-safety forces a fresh client (`build_working_memory`).
   The teardown is `services.supabase.close_supabase_client(client)`, never a hand-rolled
   `.session.close()`.
3. **`async with` (or `try/finally: await client.close()`)** — for every `AsyncAnthropic()` in
   `services/anthropic.py`. For long-lived streaming generators, the `finally` must run on
   `GeneratorExit` so a client disconnect releases the pool.

A regression test (`api/test_client_lifecycle.py`) asserts: `build_working_memory` closes every
Supabase client it opens; `close_supabase_client` releases both sub-clients; **and every
`services/anthropic.py` wrapper closes the Anthropic client it opens, including on mid-stream
disconnect.**
