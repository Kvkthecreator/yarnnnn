# ADR-655 — The console shows what is true

**Status**: Accepted + Implemented · 2026-09-17 (operator ask: *"can you audit the existing admin
page, dashboard at large. i'm thinking actually it maybe better to re-approach from first principles
and scratch."* — then, on the audit: *"yes, aligned in full … ensure singular streamlined discipline
with code and docs, scoping in deletion and clean-up of code where warranted to avoid future
ambiguity."*)
**Relates to** ADR-596 (the agent is identity ⊕ character ⊕ engine), ADR-632 (the seat retires),
ADR-405/373 (reach is a grant), ADR-652 (the balance ledger), ADR-250/291 (`execution_events` is the
canonical cost ledger), ADR-639 (`tasks` as the drain index).
**Hat**: A for the console; the persona forensics it deletes were Hat B wearing a Hat-A shell.
**Gate**: `api/test_adr655_console.py` (script-shaped — read the count).

---

## 1. The audit — a dashboard for a product we no longer run

`/admin` was 2,282 lines across three panes (Overview, Accounts, Account detail) behind an
`ADMIN_ALLOWED_EMAILS` allowlist. The allowlist holds: probed live, an unauthenticated call 401s and
a malformed bearer 401s. Nothing was exposed. What was wrong is that the surface **counted the wrong
nouns**, and had been amputated twice rather than rethought — two comment blocks in the shipped page
narrate prior deletions ("*DELETED 2026-08-26 … rendered blank forever*").

Read-only probe of live prod, 2026-09-17:

| what the console showed | where it read | live reality |
|---|---|---|
| **Tasks** stat card + Tasks 7d + a per-user Tasks column | `tasks` | **0 rows.** Rendered `0` forever |
| **Email** column, the Users table's identifying field | `workspaces.owner_email` | **NULL on all 21 rows.** Every row rendered `"unknown"` |
| **Users** | `count(workspaces)` | 21 — that is a workspace count wearing a user label |
| Reviewer edits ("the tenure signal") | `authored_by LIKE 'freddie:%'` | **1 row in 30 days**, against 1,024 `system` / 563 `operator` / 249 `member` |
| Sessions / Messages / Spend / Heartbeat | `chat_sessions`, `session_messages`, `execution_events`, `activity_log` | live (175 / 775 / $3.47 on 09-16 / 120 beats per 24h) |

Three findings are the ADR:

**`owner_email` has one reader and zero writers.** Added by migration 003 and again by 010, the
column is written by nothing in the tree. `api/routes/admin.py:398` was its only consumer anywhere.
The Users table — the console's centerpiece — was a column of `unknown`.

**The Accounts pane was built on retired vocabulary.** Its headline "tenure" metric counted the
`freddie:` prefix, which CLAUDE.md preserves *only* as a display-resolved attribution on historical
revisions (ADR-632). Of the 9 personas in `docs/alpha/personas.yaml`, **3 user_ids have woken in
7 days**, and one account that IS waking (`4251862e`) is not in the registry at all. The registry is
a Hat-B artifact read out of `docs/`, which `_load_personas` already concedes may not ship with the
API build — it degrades to an empty list by design.

**Nothing held it.** No `test_admin*.py` existed; this surface had never been held to any gate. And
`list_users` issued **4 queries per workspace inside a Python loop** — 85 round-trips for 21
workspaces, plus a 5th for the tier — an N+1 that grows linearly with signups.

### 1a. Why repair was the wrong shape

Every defect above is individually a small fix. But the surface's *model* predates ADR-596 (agents),
ADR-632 (the seat), ADR-405 (grants) and ADR-652 (billing). It counted **tasks** and **users** —
nouns from the pre-kernel product. The nouns this system actually has are **workspaces, principals,
grants, execution events, balance**. Patching the columns would have left a console that answers a
question the platform stopped asking.

Meanwhile the good data was already there and unread: `balance_transactions` (ADR-652),
`subscription_events` (10 rows), `principal_grants` (40 rows across 21 workspaces — the real reach
model). And the deciding receipt: **`execution_events.workspace_id` is populated on 1597 of 1597
rows** (100%, all time; `principal_id` on 1176/1176 over 30d). The current model's key was already
written on every row of the cost ledger. The rebuild costs no migration.

## 2. Decisions

**D1 — The console keys on the workspace, because the workspace is the binding unit.**
One pane, `/admin`, listing workspaces — not "users". Per row: name, tier, balance, grant count,
7d events, 7d spend, last activity, comp toggle. This is ADR-373/378's outermost scope shown as
itself. A workspace count is never again labelled "Users": the two differ (21 workspaces, and a
principal may hold grants on several), and conflating them is what made the old Users table a
fiction.

**D2 — A figure with no live source is deleted, not carried at zero.** The `tasks` stat card, the
per-user Tasks column and `total_tasks`/`tasks_7d` go. `tasks` is ADR-639's drain index at 0 rows —
a real table with a real purpose that is not a console metric. A zero that cannot become non-zero is
not a measurement; it is furniture. Same ruling for `owner_email`: the column is **dropped** from
`workspaces` (migration 257), not backfilled. Its one reader is deleted in this ADR, so a backfill
would be inventing a writer to feed a consumer that no longer exists. Identity resolves from
`owner_id` against the auth records, which is where it actually lives.

**D3 — The email that identifies a workspace is resolved, once, from the one place that holds it.**
`auth.users` is the writer of record for an account email (ADR-650). The console resolves owner
emails in **one batched admin call** for the whole page, never per row, and a workspace whose owner
cannot be resolved renders its **name and short id** — never the string `"unknown"`, which reads as
data loss when it was only a missing join.

**D4 — One round trip per pane, not one per row.** The N+1 is deleted: the console aggregates
`execution_events` over the window in a single fetch and buckets in Python by `workspace_id`, the
same shape `/accounts` already used correctly for its 7d window. Grants likewise. The page's query
count is now constant in the number of workspaces.

**D5 — The persona forensics leave the console; they were never Hat A.** `/admin/accounts` and
`/admin/accounts/{slug}` — the persona list, the wake curve, the failure triage, the reviewer trail,
the proposal mix, the substrate footprint, the perf buckets — are **deleted** from the web surface
and from `api/routes/admin.py`, together with `_load_personas` and the seven `Account*` response
models. They read a gitignored-adjacent Hat-B registry through a Hat-A door, and shared an auth gate
and a header with real operators' money. Per CLAUDE.md's two hats, a developer probe belongs in
`api/scripts/operator/`; `alpha_ops` already holds the harness that drives these personas. Nothing
is preserved by copying: the deleted panes' only live inputs were `execution_events` slices the new
console shows workspace-side, and `action_proposals` (last row **2026-07-05**, ten weeks stale).

**D6 — The exports go with the table they exported.** `/export/users` and `/export/report` served
the Users table's shape — the one built on `owner_email` and `tasks`. They are deleted rather than
re-pointed, along with the `openpyxl` import they alone justified. An export of a fiction is a
fiction in a spreadsheet. If an export is wanted again it is a new decision against the new shape,
not a survivor of the old one.

**D7 — What the console shows is what the operator needs at 8am**: is the scheduler alive, what did
it cost, which workspaces are live, who is stuck. Three of those were already live in
`execution_events` + `activity_log` and stay. `spend_usd_limit` — a hardcoded `20.0` labelled "Pro
default" against an aggregate figure it does not bound — is deleted; the daily ceiling
(`DAILY_SPEND_CEILING_USD`) is real and stays, because a real guard reads it.

**D8 — The surface is gated.** `api/test_adr655_console.py` holds, by **derivation not enumeration**
(the `feedback_a_gate_hardcoding_a_set_cannot_fail_on_what_it_omits` class): every table the console
reads exists and is non-empty on live; no route reads a retired name (`tasks` as a metric,
`owner_email`, `freddie:` as a signal); the AST carries no per-row query inside a row loop (D4); and
the deleted routes are absent from the router.

## 2a. Amendment 1 — the dollars are the member's dollars (2026-09-17)

Operator, on the shipped console beside their own account menu: *"the $ figures don't look
consistent."* They were not. Two defects, one class — **the console showed dollars that no other
surface agrees with**:

**am.1 D1 — spend is the BILLED draw, not the raw provider cost.** The console summed `cost_usd`.
Every other spend reader in the system (`platform_limits._spend_since_anchor`,
`telemetry.spend_since`, the `get_effective_balance` RPC) reads `COALESCE(billed_usd, cost_usd)` —
cost × `USAGE_BILLING_MULTIPLIER` (1.30, ADR-490), stamped at the same single write site. So the
console under-reported every figure by the margin: the busiest workspace read **$4.11** for 7 days
against a real draw of **$5.34**. One helper, `_billed_draw`, now serves the month, today and the
per-workspace 7d figure.

**am.1 D2 — `balance_usd` is the GRANTED total, and is never debited.** ADR-396's "balance IS the
currency": spend is netted at READ time by `get_effective_balance`. The console rendered the raw
column under a **"Balance"** header and so read **$124.21** for the workspace whose own account menu,
open in the next window, said **"Free · $17.84 left"** — two numbers for one fact at the same moment.
The row now carries both under honest names: **Left** (the RPC, what the member sees) and **Granted**
(the raw total, muted). A negative Left renders red — `SK Personal` is at **−$0.15**, overdrawn,
which the old console had no way to express.

⭐**The first cut of D2 re-derived the RPC's arithmetic** to stay O(1) — bucketing spend-since-anchor
from one capped fetch. It was **wrong on 3 of 21 workspaces, the busiest by $47**: `_EVENT_CAP`
truncated that workspace's ledger, so the netted spend was a floor and the balance read high. This
module's own `_EVENT_CAP` comment warns that a cap hit silently undercounts spend; re-deriving a
money function is how you walk into it. The console now **asks the RPC**. That is a genuine per-row
database call, which D4 exists to forbid — and D4 is narrowed rather than bent: it forbids
**re-fetching per row data we already hold**, not asking the database for the one figure only it can
compute correctly. At 21 workspaces this is 21 cheap `STABLE` calls; past a few hundred the fix is a
**set-returning RPC, never a second copy of the formula**. The gate asserts both halves — the RPC is
called, and the formula's give-away shape is absent from the module.

**am.1 D3 — the engine mix, because it answers "where did the money go".** `execution_events.model`
is recorded on 1,426 of 1,597 rows and nothing surfaced it. The month's spend now breaks down by
engine, bucketed from the fetch `/execution-stats` already makes (no extra round trip) and **derived
from what the ledger recorded** — an engine we start running appears without a code change, one we
stop running disappears. Live at ratification: `claude-sonnet-5` 810 runs / **$69.46**,
`claude-sonnet-4-6` 43 / $4.51, `claude-opus-5` 4 / $0.20, `claude-haiku-4-5` 41 / $0.13,
`gemini-2.5-flash-image` 1 / $0.05.

**Considered and not built** (operator-declined, named so the evidence is not re-gathered): the
**activation split** — 14 of 21 live workspaces have never run a single execution event, and they
average **1.0 authored file** against 59.7 for the 7 that did. It is the sharpest operator fact the
probe turned up and the console is still silent on it.

Receipts, driven over the real routes: month spend **$74.36**; `yarnnn workspace` 7d spend **$5.34**
(was $4.11), Left **$17.84** (was $124.21), Granted $124.21; `SK Personal` Left **−$0.15**. Gate
**22/23** (⑯ is migration 257, still unapplied), `next build` exit 0.

## 3. What this does not do

Named, not silently skipped:

- **No new table, no new column.** The rebuild is a read-shape change over ledgers that already hold
  what it needs; migration 257 only **drops** `owner_email`.
- **The allowlist model is unchanged.** `ADMIN_ALLOWED_EMAILS` + `NEXT_PUBLIC_ADMIN_EMAILS`, checked
  in `api/services/admin_auth.py` and `web/lib/supabase/middleware.ts`. Moving operator access onto
  `principal_grants` is a real question and a different ADR; this one does not touch authorization.
- **Per-workspace drill-down is not rebuilt.** The old detail pane was persona-shaped; a
  workspace-shaped one is a later decision once the list proves what is worth drilling into.
- **`subscription_events` and `balance_transactions` stay unread by the console.** ADR-652 serves
  the member their own history; a cross-workspace revenue view is a billing decision, not a health
  one.

## 4. Receipts

| claim | receipt |
|---|---|
| `tasks` is empty | `SELECT count(*) FROM tasks` → **0** |
| `owner_email` is unwritten | `count(owner_email)` → **0** of 21; `grep owner_email` → 1 reader (`admin.py:398`), 0 writers |
| the tenure signal is retired | `authored_by` prefixes, 30d: `system` 1024, `operator` 563, `member` 249, `yarnnn` 87, **`freddie` 1** |
| the persona registry is stale | 9 personas; **3** have events in 7d; 1 active waker (`4251862e`) is unregistered |
| `action_proposals` is stale | `max(created_at)` → **2026-07-05** |
| the workspace key is available | `execution_events`: `workspace_id` **1597/1597** all-time, `principal_id` 1176/1176 over 30d |
| the console's live inputs | `activity_log` 120 beats/24h; `execution_events` $3.47 on 09-16; `principal_grants` 40 rows / 21 workspaces |
| the allowlist holds | live `GET /api/admin/stats`: no auth → **401**, bad bearer → **401** |
