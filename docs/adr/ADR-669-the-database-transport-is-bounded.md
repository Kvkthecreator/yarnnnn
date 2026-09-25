# ADR-669 — The database transport is bounded: HTTP/1.1, one socket per request, fifteen seconds per call

> **Status**: **Accepted** (2026-09-25; operator, on the diagnosis: *"yes, aligned in full. would like to delegate
> implementation details as we're aligned. ensure singular streamlined discipline with code and docs, scoping in
> deletion and clean-up of code where warranted"*). Implemented with this document; §6 is the census, §7 the
> verification on Render.
> **Date**: 2026-09-25
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Mechanism** — how every request in the three services reaches the
> database. No product change: nothing a member sees is worded or shaped differently; what changes is how long the
> worst case can last, and how many requests it can take with it.
> **Gate**: `api/test_adr669_the_database_transport_is_bounded.py`.

**Amends** — the 2026-09-15 note on `_retry_once_on_transport` in `services/supabase.py`, which named the cure
("not sharing one pool across threads … a client-lifecycle change with its own ADR"): this is that ADR, and the
cure is narrower than the note guessed. **Preserves** — the memory discipline of
[memory-and-client-lifecycle.md](../infrastructure/memory-and-client-lifecycle.md) (no auth auto-refresh timer,
no persisted session, every per-request client closed through `close_supabase_client`) · ADR-373's reach
semantics (`ReachUndecidable` stays a 503, never a 403; the once-retry stays once).

## 1. The problem — measured

2026-09-25, 07:45:08Z (16:45 local). The operator opened the Supervisor in the desktop app and it sat on
*Loading… still working*. Receipts, all from `yarnnn-api` (`srv-d5sqotcr85hc73dpkqdg`, instance `tlzhb`, up since
the 02:39Z deploy, no restart):

| Time (UTC) | What the record shows |
|---|---|
| 07:45:07.7 | the pane's preflights arrive (`OPTIONS /api/supervisor/state`, `/api/standing`, `/api/programs/surfaces`) |
| 07:45:07.97 | the last log line of any kind — a `runs` read completing |
| 07:45:08 → 07:47:08 | **no log line for 120.2 s**; CPU at 0.00004 (idle is 0.008); the request count for the minute is 0 |
| 07:47:08.2 | the first line after the gap: `GET …/workspaces?select=owner_id…` returning 200 — the lookup that begins every authenticated request |
| 07:47–07:48 | 34 requests end as **499** (the client gave up), the pane's reads among them; a CPU spike as the backlog drains; polls resume at 07:47:16 |

Not a slow query, not a deploy (the last was five hours earlier and served the Supervisor normally at 02:39:03),
not the code shipped that day (nothing in it touches the client), not auth. **One socket stalled and the whole
process waited on it**, because of three facts about the client the stack builds by default:

1. `get_service_client()` is one `lru_cache`d client per process, and `supabase-py` opens it on **one HTTP/2
   connection** — every request in the process multiplexed over the same socket. A stalled socket is a stalled
   service. This is also why the shared pool threw `[Errno 11]` under thread concurrency (seven bursts on
   2026-09-12→13, the 2026-09-15 note) and `ConnectionTerminated` on 09-23: HTTP/2 over one connection, reached
   from several threads.
2. The PostgREST client's default read timeout is **120 s** — the length of the gap, to the tenth of a second.
3. The API is a single uvicorn worker; its handlers call the sync client. Nothing else could proceed.

The retry helper of 2026-09-15 was the mitigation for the dropped-socket case; it named the cure and deferred it.
A stalled socket is the case it could not help with: nothing raised until the 120 s ran out.

## 2. Decisions

### D1 — One builder: `client_options()`, passed by every `create_client` in every service

`services/supabase.py::client_options()` is the ONE way a Supabase client is configured. It carries the memory
discipline that was already there (`auto_refresh_token=False`, `persist_session=False`) and the transport below,
as an `httpx.Client` of our own handed to the stack — which is the stack's own supported way to configure a
transport (its `timeout`/`verify`/`proxy` parameters are deprecated in favour of it). `get_service_client()`,
`get_user_client()` and, through the former, the MCP server's `_build_client` all pass it. The scheduler's
private `create_client(url, key)` in `jobs/unified_scheduler.py` is **deleted**; it calls `get_service_client()`.
The gate scans every deployed tree for a `create_client` that does not, and for a `ClientOptions(` anywhere
but inside the builder.

### D2 — HTTP/1.1: one socket per in-flight request

`http2=False`, with `httpx.Limits(max_connections=20, max_keepalive_connections=10)`. A dead socket now takes
down the request holding it and nothing else; the next request takes another socket. This is the cure the 09-15
note reached for — it is not "stop sharing the pool" but "make the shared pool one that a single dead connection
cannot poison".

### D3 — Fifteen seconds per call, five to connect

`DB_CALL_TIMEOUT_S = 15.0`, `DB_CONNECT_TIMEOUT_S = 5.0`, on PostgREST, storage and auth alike. No honest query
takes this long; the slowest read on record — the 23 s mentions scan the Supervisor's own note records from
2026-09-19 — is its own defect, and a bound that accommodated it would be the wrong bound. The worst case a
member can meet from a stalled socket is now fifteen seconds plus one retry, not two minutes for everyone.

### D4 — A cut at the bound is a transient the once-retry answers

`httpx.ReadTimeout` / `WriteTimeout` / `PoolTimeout` / `ConnectTimeout` join `_TRANSIENT_TRANSPORT_MARKERS`, so
`_retry_once_on_transport` runs the operation once more on a fresh socket — the very call whose success the
stall ended with. Named by httpx class, never the bare word: a PostgREST *"statement timeout"* is the database's
answer, not a dropped socket, and is not retried. Still exactly one retry (ADR-373's posture: a real outage stays
fast and loud).

### D5 — Teardown is unchanged in shape and simpler in fact

The supabase client hands the one supplied `httpx.Client` to postgrest, storage and auth, so
`close_supabase_client`'s first close releases everything; its second close is idempotent and keeps the helper
correct for any client built without the options. Every per-request client still closes through it.

## 3. What this does not do

- Rewrite the API on the async client, or move the sync calls off the event loop. A single stalled socket no
  longer stalls the process; a single slow *query* still occupies its handler for up to fifteen seconds, and the
  worker serves other requests meanwhile only where handlers already yield. That is the next bound, if it is ever
  measured to matter.
- Touch the one-shot and operator scripts under `api/scripts/` that build their own clients: they are Hat B
  instruments, not services, and none runs on Render.
- Change any product word or shape. The Supervisor's three independent reads (ADR-658/667) stay as they are.

## 4. Canon tensions, resolved

| Tension | Resolution |
|---|---|
| memory-and-client-lifecycle.md — never build a pool-owning client without teardown | held: the builder is called once per `create_client`, and the same `close_supabase_client` releases it |
| ADR-373 — the once-retry, fail-closed reach | held: the retry is still one; a cut at the bound is classed transient, a database answer is not |
| Render parity (CLAUDE.md) — every service that reads a setting | the builder lives in the module all three services import; the scheduler's private copy is deleted so it cannot drift |

## 5. Gate

`api/test_adr669_the_database_transport_is_bounded.py`: every `create_client` in the deployed trees passes
`client_options()` and `ClientOptions` is constructed nowhere else; the scheduler and the MCP server build through
the one builder; the built client is HTTP/1.1 with the 15 s / 5 s bounds and the sized pool; the service client
shares the one httpx client across postgrest, storage and auth; **driven** — a local socket that accepts and never
answers is given up at the bound as `ReadTimeout`, which the classifier calls transient and the once-retry
recovers from, while a "statement timeout" answer is not retried; the retry helper's docstring names this ADR as
the landed cure; the ledger row, the lifecycle reference and ACCESS.md say so.

## 6. Implementation census

| Where | What |
|---|---|
| `api/services/supabase.py` | `DB_CONNECT_TIMEOUT_S` · `DB_CALL_TIMEOUT_S` · `DB_POOL_LIMITS` · `bounded_http_client()` · `client_options()`; `get_service_client` / `get_user_client` pass it; the four timeout markers; the retry helper's and the teardown's docstrings corrected |
| `api/jobs/unified_scheduler.py` | DELETED its own `create_client(url, key)`; `get_service_client()` |
| `api/mcp_server/auth.py` | unchanged — already builds through `get_service_client()` |
| `docs/infrastructure/memory-and-client-lifecycle.md` · `docs/database/ACCESS.md` | the stall recorded; the rule: every client through the builder |

Proven before landing, read-only against production: a client built with the options answered PostgREST, storage
(`list_buckets`) and auth admin (`get_user_by_id`) over `HTTP/1.1 200 OK` through one shared session, pool
`http2=False`, timeout `connect=5.0, read=15.0, write=15.0, pool=15.0`.

## 7. Verified on Render (2026-09-25)

`3d9fc0d` deployed on push (08:07:59Z): the API `dep-dar2no0ae00c73e1m7ag` live 08:09:47Z (instance `mml9z`; the old
`tlzhb` shut down 08:10:46Z), the scheduler `dep-dar2nogae00c73e1m8gg` live 08:08:59Z, the MCP server
`dep-dar2no0ae00c73e1m890` live 08:09:49Z (instance `tb6ss`).

| Service | Receipt |
|---|---|
| `yarnnn-api` | every Supabase call on `mml9z` logs `HTTP/1.1 200 OK` (the previous instance's lines read `HTTP/2`); the shell's polls, the runs reads and the mentions scan all answered; root TTFB 0.22–0.30 s from Seoul |
| `yarnnn-unified-scheduler` | the 08:09:39Z tick on `t2z7c` — every workspace's skills and agents manifests, discovery, the drain — all `HTTP/1.1 200 OK`; `[SCHED] tick complete` 08:09:40Z |
| `yarnnn-mcp-server` | `tb6ss`: the reconnecting client's token and workspace lookups over `HTTP/1.1 200 OK`; `whoami` answered (binding `chosen`, the read tier's sentence naming `runs`); `runs(limit=3)` answered three of the operator's browser runs with their steps |

⚠️ A deploy restarts the API, and the API holds an in-flight browser turn's pending acts in memory (ADR-662 D6):
the operator's chat run `34512742` (x.com, started 08:09:12Z) was in flight when `tlzhb` shut down. That hazard
predates this ADR (the handoff's item 6 records the first instance, `13af65c`) and is unchanged by it.
