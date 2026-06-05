# Memory & Client Lifecycle — Canonical Reference

**Version**: 1.0
**Created**: 2026-06-05
**Status**: Canonical — single authoritative reference for Supabase/httpx client lifecycle and process memory discipline on the always-on services.

---

## Why this doc exists

`yarnnn-api` (`srv-d5sqotcr85hc73dpkqdg`) runs on the Render **starter plan — a 512 MiB hard
memory cap, single uvicorn worker**. It has OOM-restarted at least twice from slow RSS creep:

- **2026-06-01** — first OOM. Partial fix in `services/supabase.py::get_user_client`
  (disable gotrue auto-refresh timer + close the postgrest pool in `finally`).
- **2026-06-04 21:40 UTC** — **recurred.** The partial fix was incomplete and missed the
  largest offender. This doc records the full diagnosis and the complete fix.

The class of bug is **per-request Supabase client construction without teardown**. Every
`create_client()` eagerly builds **two** httpx connection pools (postgrest **and** the gotrue
auth client). On a 512 MiB box under threaded request churn, abandoning those pools inflates
the process plateau until it crosses the ceiling.

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

## Discipline rule (going forward)

**Never construct a Supabase client per-request without teardown.** Two sanctioned patterns:

1. **Reused singleton** — `get_service_client()` for service-key reads. Default choice.
2. **Per-request / per-thread, closed in `finally`** — when RLS requires the operator JWT
   (`get_user_client`) or when thread-safety forces a fresh client (`build_working_memory`).
   The teardown is `services.supabase.close_supabase_client(client)`, never a hand-rolled
   `.session.close()`.

A regression test (`api/test_client_lifecycle.py`) asserts `build_working_memory` closes every
client it opens and that `close_supabase_client` releases both sub-clients.
