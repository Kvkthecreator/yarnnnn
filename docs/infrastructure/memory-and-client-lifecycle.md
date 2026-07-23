# Memory & Client Lifecycle — Canonical Reference

**Version**: 1.1
**Created**: 2026-06-05 · **Updated**: 2026-07-23 (Anthropic client — fourth occurrence: the call sites outside the module)
**Status**: Canonical — single authoritative reference for Supabase/httpx **and Anthropic**/httpx client lifecycle and process memory discipline on the always-on services.

---

## Why this doc exists

`yarnnn-api` (`srv-d5sqotcr85hc73dpkqdg`) runs on the Render **starter plan — a 512 MiB hard
memory cap, single uvicorn worker**. It has OOM-restarted four times from slow RSS creep:

- **2026-06-01** — first OOM. Partial fix in `services/supabase.py::get_user_client`
  (disable gotrue auto-refresh timer + close the postgrest pool in `finally`).
- **2026-06-04 21:40 UTC** — **recurred.** The partial fix was incomplete and missed the
  largest offender. This doc records the full diagnosis and the complete fix.
- **2026-07-01** — **recurred a third time, on the un-audited Anthropic client.** Same bug
  class, different SDK: `AsyncAnthropic()` was constructed per-call in all 7
  `services/anthropic.py` wrappers and never closed. See "The 2026-07-01 OOM" below.
- **2026-07-22 23:47 UTC** — **recurred a fourth time, on the same client, from the two call
  sites *outside* that module.** The 2026-07-01 fix and the gate defending it both stopped at
  the `services/anthropic.py` boundary. Killed a lane turn mid-SSE. See "The 2026-07-22 OOM" below.

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

## The 2026-07-22 OOM — the same client, the call sites nobody scanned (fourth occurrence)

The 2026-07-01 fix was correct **and** incomplete: it fixed every call site *in
`services/anthropic.py`*, and so did the gate written to defend it. Two callers live
elsewhere, and both were still bare.

### Receipts

Render `memory_usage` for instance `nxnp5`, 2026-07-22 (UTC) — the same monotonic ramp:

| Time | RSS | % of 512 MiB |
|------|-----|--------------|
| 12:00 | 307 MB | 57% |
| 17:00 | 373 MB | 70% |
| 21:00 | 437 MB | 81% |
| 23:30 | 488 MB | 91% |
| **23:47:00** | **535 MB** | **99.7%** |
| 23:47:13 | — | a lane turn opens its SSE stream (`POST /api/lanes/…/messages` → 200) |
| **23:47:27** | — | **`Instance nxnp5 restarted`** — OOM-killed mid-stream |
| 23:48:00 | 115 MB (restarted) | 22% |

~18 MB/hour, linear, never reclaimed. Two other instances show the identical slope
(`g6v6l` +211 MB/11.5h, `x56n7` +129 MB/5.5h). The operator-visible symptom was
`net::ERR_FAILED 502` and "The lane turn failed — try again" — the turn that happened
to be in flight when the cap was reached, not the turn that caused it.

### Root cause

Two callers of `get_anthropic_client()` outside `services/anthropic.py`, both bare:

- `services/primitives/web_search.py:296` — **the load-bearing one.** `WebSearch` is on the
  uniform lane surface (`LANE_SURFACE_EXTRA`, `services/lane_runner.py`), so every chat turn
  that searched abandoned a 1000-connection pool.
- `services/recurrence_prompt_inference.py:109` — lower frequency (back-office, gated on ≥2
  feedback entries), same mechanism.

### Why the gate did not catch it

`test_client_lifecycle.py` checked the leak by reading **one file's text** and counting
occurrences in it:

```python
anth_src = (… / "services" / "anthropic.py").read_text()
check(…, anth_src.count("client = get_anthropic_client()") == 1 and …)
```

A call site in any other file was structurally invisible. The gate passed for three weeks
while the leak ran. **A gate that greps one file cannot see the call site that matters.**

### The fix

Both call sites now use `async with get_anthropic_client() as client:`. The gate was replaced
with an **AST walk over every `api/**/*.py`**: it finds each `get_anthropic_client()` call and
requires it to be the context-expression of an `async with`, with exactly one sanctioned
exception (the streaming generator in `services/anthropic.py`, which closes in a `finally`).
It also asserts it *saw* ≥8 call sites, so a scan that silently matches nothing fails loudly.

Verified by reverting the two fixes with the new gate in place: **FAIL — 5 guarded, 2 bare**.
The gate catches the bug it claims to catch.

### The step-ladder — reading the shape

At 1-minute resolution the growth is **discrete steps separated by flat plateaus**, never a
slope and never a decline:

```
16:00–16:07  314.8 MB   flat, 8 min
16:08        316.2 MB   +1.4 MB step
16:22        322.0 MB   +2.9 MB step
16:23–16:34  322.0 MB   flat, 12 min
18:39        376.8 MB   +7.1 MB step
```

Each step is one abandoned pool (or a small batch of them); each flat is a stretch with no
leaking request. The steps are MB-sized rather than KB-sized because of the glibc arena
amplification measured above (475 KB/client threaded vs 0 KB single-threaded).

**The diagnostic value is in what the shape rules out.** Memory *stops* climbing when traffic
stops — on 2026-07-20, RSS plateaued at 461 MB and held flat across 23:30→01:00 as requests
fell 127 → 4 per 30 min. So: request-driven accumulation, **not** a background task, timer, or
gradual heap creep. When triaging the next one, read the shape first — it tells you where to
look before you read any code.

---

## Baseline (resident-at-boot) — the other half of the headroom

A leak is only lethal relative to the headroom it eats. The 2026-07-22 OOM was made lethal by a
baseline of **~112 MB against a 512 MiB cap** — barely 4x headroom before the first request.
Auditing it found two heavy SDKs imported at **module scope** on the boot path, each for a
symbol used inside exactly one function:

| Import | Cost | Used by |
|---|---|---|
| `services/primitives/web_search.py` → `from services.anthropic import …` | ~861 `anthropic.types.*` modules | one call in `_execute_web_search` |
| `routes/mcp.py` → `from mcp.server.auth.provider import …` | ~600 modules | one helper on the OAuth callback |

Both deferred to call time. Measured, subprocess-booting the real app:

| | RSS | modules |
|---|---|---|
| bare interpreter | 13.0 MB | 53 |
| `import main` — before | 112.2 MB | 2132 |
| `import main` — after | **81.2 MB** | **932** |

**−31 MB / −28% baseline, −1200 modules**, and a correspondingly faster cold start (which matters:
Render restarts the process on every deploy). `litellm` was already correctly deferred — its
`services/model_router.py` call sites carry the comment *"~3s cold import must not tax API boot"*.
The `supabase` + `fastapi` + `pydantic` floor (~70 MB) is structural and stays.

Deferring an import moves failure from boot time to request time, so both were proven to resolve
**at call time**, not merely to boot: `_execute_web_search` was driven end-to-end and reached
Anthropic's API, failing only on a stub key (401) — not on `NameError`/`ImportError`.

Guarded by `api/test_boot_import_cost.py`, which **measures** rather than greps: it boots the app
in a subprocess and asks the live `sys.modules` whether each heavy SDK is resident, plus a module-
count ceiling to catch a new dependency not on the named list. A grep could not defend this — the
two offending files never name `anthropic` or `mcp` in a form a naive import-grep would flag; the
cost arrives transitively. Falsified: reverting both deferrals turns the gate red (3 failed,
113.0 MB / 2133 modules).

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
3. **`async with` (or `try/finally: await client.close()`)** — for **every** `get_anthropic_client()`
   call **anywhere in `api/`**, not merely those in `services/anthropic.py`. (Scoping this rule to
   one module is what produced the fourth occurrence: the fix and its gate both stopped at the
   module boundary while two callers outside it leaked for weeks.) For long-lived streaming
   generators, the `finally` must run on `GeneratorExit` so a client disconnect releases the pool.

**And the gate rule the fourth occurrence bought:** a leak gate must scan **call sites**, not one
file's text. Prove it by reverting the fix and watching the gate go red — a gate never seen failing
is a claim, not evidence.

**Second rule — keep heavy SDKs off the boot path.** An import needed inside one function belongs
*in* that function. The convention is already the codebase norm (`litellm`, `openai`, `PyPDF2`,
`docx`, `markdown`, and four of the five `anthropic` call sites defer); the exceptions are what
cost 31 MB. Before adding a module-scope import of a large third-party SDK to anything reachable
from `main.py`, check whether the symbol is call-time-only — and run
`python3 test_boot_import_cost.py`, which will tell you in one line.

Two regression gates guard this doc's claims — run both from `api/` as scripts (not pytest):

- **`python3 test_client_lifecycle.py`** — teardown. `build_working_memory` closes every Supabase
  client it opens; `close_supabase_client` releases both sub-clients; **every** `get_anthropic_client()`
  call site anywhere in `api/` is `async with`-guarded (AST walk), including on mid-stream disconnect.
- **`python3 test_boot_import_cost.py`** — baseline. The heavy SDKs (`anthropic`, `mcp`, `litellm`,
  `openai`) are **not resident** after `import main`, plus a module-count ceiling for the general case.
