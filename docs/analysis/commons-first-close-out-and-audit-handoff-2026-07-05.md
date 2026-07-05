# Commons-First Close-Out + the User-vs-Workspace Audit Handoff (2026-07-05)

> **Purpose**: cleanly close the ADR-404/405/406 implementation session and hand a
> precise boundary to the parallel **multi-user / multi-agent data-architecture
> audit** (operator thesis: the user-specific vs workspace-shared distinction —
> the Slack/Notion model — is not yet thought through across the full data
> surface). This doc separates (§2) what is SETTLED and should not be
> re-litigated, (§3) the audit's genuine open field with an objective inventory,
> and (§4) the deferred-items ledger with each item's owner.
>
> **Hat**: B (session close-out + audit input). The audit's findings land as
> Hat-A ADRs in the parallel session.

---

## 1. What this session closed (all on main, migrations 197/198/199 in prod)

The full ADR-404 §5 sequence — pivot docs (404/405/406) · capture lane dormant
(`CONNECTOR_CAPTURE_ENABLED` default OFF) · stale-parent CAS + DB linearity
guard · the ADR-373 sweep spine (workspace-keyed substrate core, grant-aware
resolution, `X-Workspace-Id` fail-closed) · **member invites live and proven by
a real member walk** (grant minted for a second human) · GTM copy re-center —
plus the three live-walk fixes (accept page escapes the shell; roster emails;
clean shell boot on accept) and the **completing substrate-read sweep**
(2026-07-05): every route-level `workspace_files` / `workspace_file_versions`
read now scopes through the ONE helper
(`services.workspace_context.substrate_scope_filter`) — 13 sites in
`routes/workspace.py` + 17 sites across `feed / documents / sources / agents /
authored / alpha_trader / recurrences`.

**Deliberately NOT swept** (destructive flows, audit-adjacent): the
`account.py` / `admin.py` wipe paths stay keyed to the user's OWN data — what
account-deletion means for a *member of someone else's commons* is an audit
question (§3.4).

Gates at close: 373-spine 26/26 · 406 22/22 · 404-invites 25/25 ·
404-dormancy 28/28 · 373-rekey 0 fail.

## 2. Settled — the audit builds ON this, not against it

Ratified + implemented + live; re-litigating these is re-deriving canon:

1. **The substrate (Layer-1 authored files) is workspace-keyed.**
   `workspace_files` + `workspace_file_versions` bind to `workspace_id`
   (ADR-373; live-row identity `UNIQUE(workspace_id, path)`, migration 198;
   legacy `UNIQUE(user_id, path)` retired, migration 199). The commons is
   shared content — this IS the Slack/Notion "workspace level" for files, and
   it is done. Rows keep `user_id` as an immutable *creator fact*; who wrote
   what lives in the revision chain (`authored_by` + `principal_id`).
2. **Authorization is per-principal grants** (`principal_grants`, ADR-373 D2 +
   ADR-386 lifecycle), never species. Permission = grant · autonomy = witness
   timing · notification = the after-witness channel (ADR-405).
3. **Concurrency is stale-parent rejection, not merge/CRDT** (ADR-406,
   ADR-286/378 reaffirmed).
4. **One workspace = the outermost commons** (ADR-378); the launch product is
   the multi-principal shared workspace (ADR-404 D1).

## 3. The audit's open field — the per-user experience layer

The operator's thesis, sharpened into the auditable question: **for every
`user_id` key in the system, which of three meanings does it carry?**

- **(a) attribution** — who did it (correct to keep per-user forever);
- **(b) personal experience** — this user's own view/session/preferences
  (correct to keep per-user, Slack/Notion style);
- **(c) workspace data mis-keyed on a user** — actually belongs to the
  commons and only works today because N=1 made user ≙ workspace.

The re-key so far fixed (c) for the substrate only. Everything below is
unresolved. **Objective inventory (prod `information_schema`, 2026-07-05)** —
tables with `user_id` and NO `workspace_id`, grouped by our best prior of
their class (the audit should verify, not trust, these priors):

| Table | Prior | Notes for the audit |
|---|---|---|
| `chat_sessions` (+ `session_messages` via FK) | (b) personal? | Slack model says DMs personal, channels shared. Is the operator↔seat narrative per-user or the workspace's? Member chat is currently invisible to the owner. |
| `notifications`, `user_notification_preferences` | (b) | Per-user delivery is right; but *emission* should derive from workspace events (ADR-405 after-witness — unbuilt). |
| `action_proposals` | (c)? | Proposals gate WORKSPACE acts; a member arguably should see/approve per their grant. Today only the owner sees the queue. |
| `wake_queue`, `execution_events`, `activity_log`, `agent_context_log`, `trigger_event_log`, `event_trigger_log` | (c) for scope, (a) for actor | The seat serves the WORKSPACE; ledgers should scope to workspace with per-principal attribution (`execution_events.principal_id` already exists, migration 192). |
| `tasks` (scheduling index), `agents` | (c)? | Recurrences + agents are workspace operation, not personal. Reconstructable from filesystem (ADR-231) — cheap to re-key. |
| `platform_connections`, `integration_sync_config`, `sync_registry`, `slack_user_cache` | (c)? | Connectors are workspace peripherals (ADR-401) but OAuth tokens are granted by a PERSON — dual nature worth naming. |
| `destination_delivery_log`, `export_log`, `scheduled_messages`* | (c) | Outbound is the workspace's boundary (ADR-370). *`scheduled_messages` already workspace-keyed. |
| `mcp_oauth_*` | (b)/(a) | Tokens are per-human-authorizer; the grant they map to is per-workspace (ADR-373 D2.a). Already coherent. |
| `user_admin_flags`, `user_interaction_patterns`, `user_platform_styles` | (b) | Likely fine. |
| `render_usage`, `workspaces.balance_usd`/tier | ADR-391 | Balance = workspace's, allocation = principal's, metering attributed — ratified architecture, partially implemented. |

**Non-DB user-keyed state** (same question applies): FE shell/window state
(`yarnnn:shell:*` localStorage, per-user — the member landed on a stale window
because it isn't per-(user, workspace)); the commons binding itself
(`yarnnn.active-workspace`, one per browser, no switcher); `_budget.yaml`
(per-user file → per-principal per ADR-391); Layer-2 search RPCs
(`search_workspace` / `match_workspace_files`, `p_user_id`-keyed — deferred
here BECAUSE search visibility is an experience-layer question the audit may
reshape; Layer 2 is reconstructable cache, ADR-328, so re-keying is cheap
whenever the semantics are settled).

**§3.4 Named audit questions** (from this session's live walk):
1. What does a member SEE of: the proposal queue, the narrative/feed, Home
   slots, notifications? (Today: their own empty per-user rows.)
2. What does the OWNER see of member activity beyond the revision feed?
3. Does the seat (Freddie) serve members — and how do member asks attribute
   and meter? (Adjacent: ADR-382/383, ADR-391 allocation-per-principal.)
4. Account deletion / grant revocation semantics for a member whose
   *creator-fact* `user_id` is on commons rows (rows must survive; the
   attribution must remain resolvable after the auth user is gone).
5. Per-(user, workspace) window state + the workspace switcher.

## 4. Deferred-items ledger (who owns what)

**→ The parallel audit** (do not build here first): member visibility of
queue/feed/notifications · member↔seat semantics · after-witness emission ·
per-(user, workspace) window state + switcher · Layer-2 RPC re-key ·
account-deletion semantics for members · any migration the audit ratifies.

**→ Other named triggers** (unchanged): ADR-396 pricing re-cut → invite
adoption evidence · capture-lane re-entry → flag flip when perception earns
its place (its two live bugs are already fixed on main: `um.list()` +
capture↔wake decoupling) · SITE-COPY-SPEC v2 → next full marketing pass ·
proof-excerpt block → real substrate pull (pre-existing).

**→ Nothing else is open from this session.** The commons-first sequence
(ADR-404 §5) is complete; the member flow is proven e2e; all gates green.
