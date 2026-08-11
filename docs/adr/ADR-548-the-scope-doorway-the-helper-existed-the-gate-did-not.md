# ADR-548: The scope doorway — the helper existed, the gate did not

> **Status**: **Accepted + Implemented** (2026-08-11) — found by auditing the
> noun/verb scope split at the operator's request, against a **12/12 green**
> ADR-373 sweep battery. The fix is small; the *reason it was invisible* is the
> decision this ADR records.
> **Date**: 2026-08-11
> **Dimension**: **Substrate** (what a workspace-content read is keyed by) primary,
> with **Identity** consequences (whether a member sees the commons they hold a
> grant on).
> **Authors**: KVK (operator) + Claude (collaborator)
> **Relates to**:
> - **ADR-407 D1** (the three-scope taxonomy) — **enforced, not amended.** Every
>   decision here restores a rule ADR-407 already wrote.
> - **ADR-373** (the `user_id → workspace_id` re-key) — this closes a piece of its
>   own named remainder: "route-level `.eq('user_id')` filters".
> - **ADR-501 §6a lesson 4** ("the explicit binding must be PASSED, not inferred")
>   — the lesson this lane re-learned in a new layer; `_scope_filter` now passes it.
> - **ADR-425 D1/D3** (the credential is an account object) — **upheld and
>   sharpened.** Its `sync_registry` nuance was being flattened by a helper
>   docstring; D4 records the accurate reading.
> - **ADR-495** (one conversation, one cast) — unchanged; its dropped tables are
>   removed from the scope manifest here as hygiene.
> - **ADR-414 ratchet #5** (the DP35 scope-manifest gate) — **widened**, and found
>   to have been structurally blind (§2.2).
> - **FOUNDATIONS DP35** — unchanged. This is its CI form reaching one more layer.

---

## 1. Context — a member searches the commons and gets nothing

The operator asked a scoping question in product terms: *nouns and commons are
workspace-level; chats are verbs and user-based.* That framing is already canon —
it is ADR-407 D1 almost word for word. So the audit was not "is the model right"
but **"where has the code drifted from a model that already exists."**

### 1.1 The verb axis was already correct

ADR-495 deleted the private/shared distinction on purpose: there is no `scope`
column anywhere in the schema. `services/lane_runner.py` states the doctrine in
the operator's own terms — *"lanes are isolated conversations; the workspace is
the shared memory."* Transcripts are per-lane; durable output lands in
workspace-scoped files. Nothing to fix.

### 1.2 The noun axis was correct everywhere except one file

Routes, MCP compositions, and the `UserMemory`/`AgentWorkspace` data layer all
key workspace content on `workspace_id` via the one shared helper. The primitive
layer did not. Eight substrate reads in
`services/primitives/workspace.py` keyed the **bare caller** — including
`ListFiles` and `SearchFiles`.

The consequence is not an error. It is an **incorrect success**: a member
searching the commons gets `[]` for every owner-authored file, with HTTP 200,
an empty console, and nothing in Sentry. That is the exact signature the
member-read-path arc already recorded.

Three details make it a law rather than a typo:

1. **The correct helper was in the same file, used once.** `_scope_filter` (a
   thin wrapper over `substrate_scope_filter`) had exactly one call site — the
   binary-notice probe in `handle_read_file`. So `ReadFile` was workspace-keyed
   and `ListFiles` was not, *within one module*.
2. **It was half-fixed.** `handle_search_files` and `handle_query_knowledge`
   already resolved a workspace for their **RPC** branch. Only the table-query
   fallbacks beside them stayed user-keyed — someone swept one path and missed
   its neighbour.
3. **A correct duplicate existed.** `mcp_composition.py::compose_list` is a
   near-verbatim copy of the broken query — same table, same select, same
   `.like`/`.in_` — differing *only* in the scope-filter line.

## 2. Why 22 green gates could not see it

### 2.1 The gates tested the helper, not its callers

`test_adr373_sweep_spine.py` passes 12/12. What it proves is that
`substrate_scope_filter` **behaves correctly when called** — workspace-keyed
when a workspace resolves, `user_id` fallback when not. It never asserts that
substrate readers call it.

This is the repo's recurring lesson in its purest form: **the gates tested the
room, not the doorway.**

### 2.2 The scope manifest gate was structurally blind

The ADR-414 ratchet discovers stores by scanning for the `.table("X")` string
literal. Stores reached through a **variable** table name — `_delete_rows(client,
"integration_sync_config", user_id)`, or a literal list iterated into a purge
loop — are invisible to it.

Two live stores (`integration_sync_config`, `user_admin_flags`) were undeclared
for exactly that reason. Worse, the gate's *phantom* check would have called them
stale once declared: it would have demanded the removal of a declaration for a
table that genuinely exists. Widening discovery immediately surfaced a **third**
undeclared store, `event_trigger_log` — evidence that the blindness was hiding
real drift, not a lone oversight.

The gate was also **red on `main`** at `7a18bd7` on a clean tree, declaring two
tables (`conversations`, `conversation_messages`) that ADR-495's migration 226
dropped.

### 2.3 The first fix was necessary and NOT sufficient — the contextvar never arrives

The primitive-layer fix (D1) shipped and deployed live at 10:48. The operator
then checked prod and **the member still saw one document instead of four.**
That is the honest sequence, and the second root cause is the more important
finding.

`GET /studio/artifacts` already carried a `[SCOPE]` diagnostic. It printed:

```
[SCOPE] artifacts user=2be30ac5 ws=d5b9029b
        scope=workspace_id=4ca9c664 rows=1 returned=1
```

`ws=` is the workspace **the request bound to** (the owner's). `scope=` is the
workspace **the query actually read** (the member's own). They disagree — beside
a comment asserting they "can never disagree."

**Why.** `substrate_scope_filter(auth.user_id)` — with no second argument — has
three fallback rungs: explicit → request contextvar → owner-resolution. The
call sites relied on rung 2. But `get_user_client` is a **sync generator**
(`def`, not `async def`), so FastAPI executes it in a **threadpool**. The
contextvar is set in the worker thread's context; the async handler runs in a
different one and sees `None`. Resolution falls to rung 3, and
`resolve_workspace_for_principal` returns the caller's OWN workspace.

Reproduced locally in isolation: setting the contextvar inside
`run_in_executor` and reading it from the awaiting coroutine yields `None`,
while setting it in the same async context propagates correctly.

**This makes the module docstring's premise false.** `workspace_context.py`
says the contextvar exists so the data layer can key on `workspace_id`
"WITHOUT threading a new parameter through the ~118 historical call sites."
For any route using the sync `UserClient` dependency, that never worked.

The fix is not to make the dependency `async` — its body does blocking I/O
(`create_client`, JWT decode, a resolution query) and would stall the event
loop. The fix is to pass the binding, which `auth.workspace_id` always
carries correctly. `routes/workspace.py` had a local wrapper doing exactly this
since the ADR-373 sweep; the other 46 sites did not.

**The lesson generalizes past this bug**: a fallback chain that degrades
silently to a *plausible* value is worse than one that fails. Rung 3 returns a
real workspace, so every query succeeded, every gate passed, and the only
visible symptom was a member seeing less than they should.

## 3. Decisions

| D | Decision |
|---|---|
| **D1** | **Workspace content is never keyed on the caller alone.** Every `workspace_files` / `agents` read in `services/primitives/workspace.py` routes through `_scope_filter`. The helper now passes `auth.workspace_id` EXPLICITLY (ADR-501 lesson 4), rather than letting resolution be inferred. |
| **D2** | **The doorway is gated, not just the room.** A new ratchet (`test_adr548_primitive_scope_doorway.py`) walks the **AST** of every production module and fails on `.eq("user_id", …)` applied to a manifest-declared content store. AST, not grep: a text scan matches its own explanatory comments — the failure mode this repo has hit before. |
| **D3** | **The gate's carve-out is a scope boundary, not a blessing.** Modules whose `user_id` is already workspace-derived (the radar/wake/outcomes stack keys by `acting_workspace_owner` per ADR-501 D2), the Hat-B toolchain, and the cross-workspace admin console are exempted BY NAME, with a companion check that fails when an exemption goes stale. The list shrinks; it never accretes silently. |
| **D4** | **`sync_registry` stays `content` and reads by `user_id` — on purpose.** ADR-425 D3 reserves it for the future agent-owned connection; every row today is a human's. The helper docstring that lumped it with `platform_connections` is corrected rather than the working code. When D3 lands, the gate exception is deleted and those sites become real violations. |
| **D5** | **Discovery sees variable-name table access.** The DP35 ratchet additionally harvests the purge-helper and purge-list shapes (via `ast`, after a regex was proven to truncate on a bracket inside a trailing comment). The loose shape may only *satisfy* the phantom check, never *demand* a declaration — a loose matcher that could demand declarations would manufacture phantoms of its own. |
| **D6** | **Dropped tables leave the manifest.** `conversations` + `conversation_messages` are removed, not tombstoned — the tables do not exist, so a declaration would be the very phantom the ratchet checks for. `conversation_members` stays (migration 228 hardened it). |
| **D7** | **A pane cross-link uses the namespaced param.** The shell reads only `{windowSlug}.pane=`; three shipped links used a bare `?pane=`. One of them genuinely misrouted. |
| **D8** | **A scope call on an `auth` MUST pass `auth.workspace_id`.** `substrate_scope_filter(auth.user_id)` alone is not equivalent (§2.3) — it silently resolves to the CALLER'S OWN workspace inside a FastAPI async handler. All 46 such sites across 9 modules now pass the binding, and a gate holds the line. |

## 4. What this does NOT do

- **No new mechanism.** No new helper, no new column, no migration. Every fix
  routes through machinery ADR-373/ADR-407 already built.
- **No re-key of the ADR-407 D3 tail.** `event_trigger_log` and friends remain
  `user_id`-keyed in the database; they are now *declared*, which is what DP35
  asks. The re-key is separate work.
- **No claim about `chat_sessions.workspace_id`.** It is nullable in DDL while
  both the RLS policy and the app guard treat NULL as "skip the workspace
  check" — two conditional bypasses stacked. Real, inherited, and needs a data
  check before a constraint; §6 records it rather than fixing it blind.

## 5. Verification

- **The doorway gate was falsified.** Reverting `ListFiles` to its pre-fix
  spelling turns it red naming that exact line; restoring turns it green. The
  phantom check was falsified the same way with an injected fake store.
- **The staleness check fired on its author.** It immediately rejected two
  exemptions added speculatively, which were then verified as unnecessary and
  removed — the carve-out was wrong before it ever shipped.
- **41 scope/substrate tests green** run per-file. Note the ADR-407 phase-2/3
  suites fail when run in the SAME pytest process as `test_adr373_sweep_spine`
  — a pre-existing event-loop pollution, reproduced identically on a clean
  baseline with this lane's changes stashed. It is not this lane's.
- **`next build` exit 0** with this lane's frontend changes.
- **Two pre-existing reds confirmed unrelated**: the ADR-209 guard (2 hits, both
  in `ADR-LEDGER.md` prose) and a concurrent lane's in-progress `NewFolderModal`
  work, which was stashed, verified, and restored untouched.

## 6. Open

- **`chat_sessions.workspace_id SET NOT NULL`** — needs a live data check first.
- **The ADR-407 D3 re-key tail** — ~110 sites across the owner-resolved stack are
  correct-by-a-different-route today. They are exempted by name in D3, so the
  exemption list is now the honest, reviewable worklist for that re-key.
- **A click-pass on the Danger Zone cross-link.** The misroute is read off the
  code path; the 2026-07-31 settings click-pass verified those panes RENDER but
  reached them via the sidebar, never via the in-app link.
