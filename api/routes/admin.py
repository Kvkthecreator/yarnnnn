"""
Admin routes — the operator console (ADR-655).

Endpoints:
- GET  /stats            — platform totals + the engagement funnel
- GET  /execution-stats  — spend this month / today, the daily ceiling, scheduler health
- GET  /workspaces       — the workspace list: tier, balance, grants, engagement, 7d events/spend
- POST /workspace/{id}/billing-exempt — the comp toggle (ADR-429 §12.3a)

AM.2 (2026-09-18) — DID THEY GET ANYWHERE. The console answered "what is the
platform doing and what does it cost" and could not answer "did this member get
anywhere", because EVERY activity figure on it derives from `execution_events` —
the COST ledger. A member who opened a lane, typed three messages and never
triggered a billable scheduled run reads 0 events / $0.00 spend / last-active
"—": byte-identical to a member who signed up and closed the tab. With real
people trying the product that is the one question the console owes, so three
engagement columns and a four-band funnel were added, each verified non-empty
against prod before it was drawn (D2's rule: a figure with no live source is
deleted, not carried at zero).

Receipts, probed live 2026-09-18 over 22 live workspaces: 12 never opened a
lane · 1 opened one and never spoke · 9 sent a message · 11 authored a file.
Writers: `chat_sessions` inserts at `routes/lanes.py::create_lane`;
`session_messages` through its SINGLE write path `services/narrative.py`;
`workspace_files` at `services/authored_substrate.py::write_revision`.

⚠️ A RAW FILE COUNT IS FURNITURE, AND WAS FALSIFIED BEFORE IT SHIPPED. The
first cut of `authored_file_count` counted `workspace_files` outright and read
17–18 for EVERY workspace including the 12 with zero lanes and zero messages —
the mirrored kernel substrate under `system/` (398 rows, present in 22/22
workspaces). It could not have distinguished a bounced member from a working
one, which is exactly the defect D2 exists to prevent, and it is the same fact
migration 256 relied on when it deleted 9 duplicate workspaces as holding "0
authored files — all 17 paths per row were mirrored kernel artifacts". Excluding
`system/` (`_is_authored_path`) the figure separates real work (11, 14) from a
first touch (1) from nothing (0). Non-system files live in 11 workspaces, not 22.

ADR-655 keys this console on the WORKSPACE, because the workspace is the
substrate's binding unit (ADR-373/378). What it deleted, and why, so the shapes
are not rebuilt by someone reading only the survivors:

  * The `tasks` stat card and the per-user Tasks column. `tasks` is ADR-639's
    drain index, live at 0 rows. A zero that cannot become non-zero is furniture.
  * `workspaces.owner_email`. One reader (here), zero writers anywhere, NULL on
    every live row — so the Users table's identifying column rendered "unknown"
    for all 21 workspaces. The column is DROPPED by migration 257; identity
    resolves from `owner_id` through the one resolver (D3 below).
  * "Users", which was `count(workspaces)` wearing a user label. A workspace
    count is now labelled as one.
  * `/accounts` + `/accounts/{slug}` — the eval-persona forensics, with
    `_load_personas` and seven `Account*` models. They read the Hat-B registry
    at docs/alpha/personas.yaml through a Hat-A door and shared an auth gate
    with real operators' money. A developer probe belongs in
    api/scripts/operator/ (CLAUDE.md, the two hats). Their headline metric
    counted `authored_by LIKE 'freddie:%'` — the seat ADR-632 retired, 1 row in
    30 days against 1,024 `system` — and `action_proposals`, last written
    2026-07-05.
  * `/export/users` + `/export/report`, which exported the Users table's shape.
    An export of a fiction is a fiction in a spreadsheet. The `openpyxl` import
    they alone justified goes with them.

⚠️ THIS MODULE COMPUTES NO COST, AND MUST NOT START AGAIN (2026-08-21).
`GET /token-usage` lived here and was DELETED for two independent reasons: it
aggregated `agent_runs.metadata` + `session_messages.metadata`, neither of which
has an INSERT site left in `api/`; and its cost math was a SECOND implementation
that halved every rate under a retired 2x markup and hardcoded Anthropic's cache
arithmetic for every provider (~2x under-report, compounding). Both failures are
INVISIBLE — a wrong cost number looks exactly like a right one, and an empty
dashboard looks like a quiet month. Spend here is read, never computed: it is
the `cost_usd` column of `execution_events` (ADR-291, written only by
`telemetry.record_execution_event`). The per-model surface is
`GET /user/usage-detail`; the sole canonical cost function is
`compute_cost_usd_inclusive`. Never a local rate table.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.admin_auth import AdminAuth

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================

class AdminOverviewStats(BaseModel):
    """Platform totals. Every field has a live writer — ADR-655 D2: a figure
    with no live source is deleted, not carried at zero."""
    total_workspaces: int
    total_grants: int
    total_sessions: int
    total_messages: int
    # Growth (7d)
    workspaces_7d: int
    sessions_7d: int
    #: The engagement funnel over LIVE workspaces (ADR-655 am.2). Volume and
    #: money cannot tell a member who bounced from one who is working: every
    #: activity figure on this console derives from `execution_events`, the COST
    #: ledger, so a member who opened a lane and typed three messages without
    #: triggering a billable run reads 0 events / $0.00 / last-active "-" --
    #: identical to someone who closed the tab. These four bands are disjoint
    #: stages of the same 22 workspaces, each verified non-empty against prod.
    ws_never_opened_lane: int = 0
    ws_lane_no_message: int = 0
    ws_sent_message: int = 0
    ws_authored: int = 0


class AdminEngineRow(BaseModel):
    """One engine's share of platform spend over the window.

    `model` is NULL on older rows (1426 of 1597 carry it), so the roster is
    what the ledger actually recorded, never a hardcoded list of the engines we
    believe we run — a spelled set cannot report an engine it omits.
    """
    model: str
    runs: int
    billed_usd: float


class AdminExecutionStats(BaseModel):
    """Scheduler health + spend, from `execution_events` and `activity_log`.

    ADR-655 D7 drops `spend_usd_limit` — it was a hardcoded 20.0 labelled "Pro
    default" against an aggregate figure it did not bound. `daily_spend_ceiling`
    stays: a real guard reads DAILY_SPEND_CEILING_USD.
    """
    spend_usd_this_month: float
    daily_spend_today: float = 0.0
    daily_spend_ceiling: float = 10.0
    last_scheduler_heartbeat: Optional[str]
    heartbeats_24h: int
    #: Where the month's money actually went, biggest first.
    engines: list[AdminEngineRow] = []


class AdminWorkspaceRow(BaseModel):
    """One workspace — the binding unit (ADR-373/378), shown as itself.

    `owner_label` is resolved through `principal_display.resolve_member_names`
    (the ONE resolver, TTL-cached), never read from a column. It is a display
    NAME — `user_metadata.full_name`, else the email's local part — not an
    address, which is why the field is not called `owner_email`: the resolver
    deliberately returns a handle, and a field promising an address that holds
    a handle is the `owner_email` defect again in a new spelling. When it does
    not resolve the row still identifies itself by `name` + short id rather
    than rendering "unknown", which reads as data loss when it is a missing join.
    """
    id: str
    name: Optional[str] = None
    owner_id: str
    owner_label: Optional[str] = None
    created_at: str
    tier: str
    #: The GRANTED total — every credit ever banked, never debited (ADR-396:
    #: "balance IS the currency"; spend is netted at READ time by the RPC).
    #: Shown as "Granted", never as "Balance" — see `effective_balance_usd`.
    balance_usd: float = 0.0
    #: What the member actually has left: (allowance + balance) − spend since
    #: the anchor, from the `get_effective_balance` RPC — the SAME figure their
    #: own billing pane reads. The console shipped showing the raw column and
    #: so read $124.21 where the member's UI said "$17.84 left".
    effective_balance_usd: float = 0.0
    grant_count: int = 0
    #: Lanes ever opened in this workspace (`chat_sessions`, written at
    #: `routes/lanes.py::create_lane`). Zero is the honest "never started".
    lane_count: int = 0
    #: Messages ever sent, both roles (`session_messages`, whose SINGLE write
    #: path is `services/narrative.py`). A lane with 0 messages is a member who
    #: opened the door and did not speak -- a real, observed state (1 of 22).
    message_count: int = 0
    #: Files authored, EXCLUDING the mirrored kernel substrate under `system/`.
    #: The raw count is furniture: every workspace carries 17-18 mirrored kernel
    #: artifacts, so an untouched workspace and a working one both read ~17 --
    #: the same fact migration 256 relied on when it deleted 9 duplicates as
    #: holding "0 authored files". Excluding `system/` the figure separates real
    #: work (11, 14) from a first touch (1) from nothing (0).
    authored_file_count: int = 0
    events_7d: int = 0
    spend_7d: float = 0.0
    last_activity: Optional[str] = None
    billing_exempt: bool = False


class BillingExemptRequest(BaseModel):
    exempt: bool


class BillingExemptResponse(BaseModel):
    workspace_id: str
    billing_exempt: bool


# =============================================================================
# Helpers
# =============================================================================

#: Row cap on the windowed `execution_events` fetch. The busiest live workspace
#: ran 43 events in 7d and the platform 1,176 in 30d, so this is ~4x headroom;
#: `events_truncated` is not modelled because a cap hit would silently undercount
#: spend — instead the cap is logged loudly and raised deliberately.
_EVENT_CAP = 5000


def _get_date_threshold(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


#: Row cap on the windowed `workspace_files` path fetch. 764 active rows platform
#: wide at ADR-655 am.2, so this is ~13x headroom; like `_EVENT_CAP` a hit is
#: logged loudly rather than modelled, because a truncated count reads as a
#: quieter member.
_FILE_CAP = 10000

#: The mirrored kernel substrate. `system/` holds the skills mirror and the
#: kernel artifacts every workspace is minted with -- 398 rows across all 22 live
#: workspaces, 17-18 per workspace, authored by nobody in that workspace. A file
#: count that includes them cannot distinguish a member who bounced from one who
#: is working (both read ~17), which is why `authored_file_count` excludes them.
#: Probed live: `system/` is present in 22/22 workspaces, everything else in 11.
_KERNEL_FILE_PREFIXES = ("system/", "/workspace/system/")


def _is_authored_path(path: Optional[str]) -> bool:
    """Is this path a member's authored work, rather than mirrored kernel substrate?

    Both spellings are tested because the substrate stores paths in both forms
    (`workspace_files.path` carries the bare and the `/workspace/`-prefixed
    shape depending on the write door -- the same normalization hazard
    `_normalize_workspace_rel` exists for at the write side). Matching only one
    spelling would silently count kernel files as authored work for whichever
    door wrote them.
    """
    if not path:
        return False
    return not path.startswith(_KERNEL_FILE_PREFIXES)


def _billed_draw(event: dict) -> float:
    """What an execution event actually DREW from the workspace's balance.

    `COALESCE(billed_usd, cost_usd)` — the ADR-490 rule every balance/spend
    reader follows (`platform_limits._spend_since_anchor`,
    `telemetry.spend_since`). `cost_usd` is the truthful provider cost;
    `billed_usd` is that × USAGE_BILLING_MULTIPLIER (1.30), stamped at the same
    single write site, and it is the figure the balance is debited by.

    The console shipped reading raw `cost_usd` and so UNDER-REPORTED every
    spend figure by the margin: the busiest workspace read $4.11 for 7 days
    against a real draw of $5.34. A console beside a Balance column must report the
    same dollars that column moves, or the two invite a reconciliation that
    cannot come out. Both are coerced with `or 0` — either may be NULL on a
    mechanical/skipped wake.
    """
    billed = event.get("billed_usd")
    if billed is not None:
        return float(billed)
    return float(event.get("cost_usd") or 0)


def _engagement_rollup(client) -> dict[str, dict[str, int]]:
    """Per-workspace engagement: lanes, messages, authored files.

    ONE implementation, called by both `/stats` (which folds it into the funnel)
    and `/workspaces` (which renders it per row) -- never two copies of the same
    counting rule, or the funnel and the table disagree about one fact the way
    the granted/effective balance pair did (am.1).

    THREE fetches total, constant in the number of workspaces (ADR-655 D4). The
    message count needs a lane -> workspace hop because `session_messages` has no
    `workspace_id`; that map comes from the same lanes fetch, in memory, rather
    than a per-row join.

    Returns `{workspace_id: {"lanes": n, "messages": n, "authored": n}}`,
    defaulting missing keys to 0 -- a workspace absent from a fetch has none of
    that thing, which is the honest zero, not a missing row.
    """
    lanes: dict[str, int] = defaultdict(int)
    messages: dict[str, int] = defaultdict(int)
    authored: dict[str, int] = defaultdict(int)

    # --- lanes, and the lane -> workspace map the messages need --------------
    lane_ws: dict[str, str] = {}
    try:
        for row in (client.table("chat_sessions")
                    .select("id, workspace_id")
                    .limit(_EVENT_CAP).execute().data or []):
            wid = row.get("workspace_id")
            if not wid:
                continue
            lane_ws[row["id"]] = wid
            lanes[wid] += 1
    except Exception as exc:  # noqa: BLE001 — engagement is best-effort
        logger.warning("[ADMIN] lane rollup failed: %s", exc)

    # --- messages, bucketed through that map --------------------------------
    # Counted for BOTH roles deliberately: the question this answers is "did
    # anything happen in here", and a lane where the member spoke and the agent
    # answered is the same engagement fact from either side.
    try:
        for row in (client.table("session_messages")
                    .select("session_id")
                    .limit(_EVENT_CAP).execute().data or []):
            wid = lane_ws.get(row.get("session_id") or "")
            if wid:
                messages[wid] += 1
    except Exception as exc:  # noqa: BLE001
        logger.warning("[ADMIN] message rollup failed: %s", exc)

    # --- authored files, kernel mirror excluded ------------------------------
    try:
        file_rows = (client.table("workspace_files")
                     .select("workspace_id, path")
                     .eq("lifecycle", "active")
                     .limit(_FILE_CAP).execute().data or [])
        if len(file_rows) >= _FILE_CAP:
            logger.warning(
                "[ADMIN] file rollup hit the %d-row cap — counts are a FLOOR, raise the cap",
                _FILE_CAP,
            )
        for row in file_rows:
            wid = row.get("workspace_id")
            if wid and _is_authored_path(row.get("path")):
                authored[wid] += 1
    except Exception as exc:  # noqa: BLE001
        logger.warning("[ADMIN] authored file rollup failed: %s", exc)

    out: dict[str, dict[str, int]] = {}
    for wid in set(lanes) | set(messages) | set(authored):
        out[wid] = {
            "lanes": lanes.get(wid, 0),
            "messages": messages.get(wid, 0),
            "authored": authored.get(wid, 0),
        }
    return out


def _engagement_funnel(client) -> dict[str, int]:
    """The funnel over LIVE workspaces — four disjoint bands, not four filters.

    Each workspace lands in exactly one of the first three bands (a member either
    never opened a lane, opened one without speaking, or spoke), so those three
    sum to the live workspace count. `authored` is deliberately NOT disjoint from
    `sent_message`: authoring is a deeper stage of the same journey, and against
    prod it is 11 while `sent_message` is 9 -- two workspaces authored files
    without a surviving message, which a disjoint band would have hidden.

    The denominator is live workspaces, matching the `/workspaces` list: a
    soft-deleted workspace is not a member who bounced.
    """
    try:
        live = (client.table("workspaces")
                .select("id")
                .is_("deleted_at", "null")
                .limit(500).execute().data or [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("[ADMIN] funnel workspace fetch failed: %s", exc)
        return {"never_opened_lane": 0, "lane_no_message": 0, "sent_message": 0, "authored": 0}

    rollup = _engagement_rollup(client)
    bands = {"never_opened_lane": 0, "lane_no_message": 0, "sent_message": 0, "authored": 0}
    for w in live:
        e = rollup.get(w["id"], {"lanes": 0, "messages": 0, "authored": 0})
        if e["messages"] > 0:
            bands["sent_message"] += 1
        elif e["lanes"] > 0:
            bands["lane_no_message"] += 1
        else:
            bands["never_opened_lane"] += 1
        if e["authored"] > 0:
            bands["authored"] += 1
    return bands


# =============================================================================
# GET /stats — platform totals
# =============================================================================

@router.get("/stats", response_model=AdminOverviewStats)
async def get_overview_stats(admin: AdminAuth):
    """Platform totals. Counts are server-side (`count="exact"`, no rows moved)."""
    try:
        client = admin.client
        seven_days_ago = _get_date_threshold(7)

        workspaces = client.table("workspaces").select("id", count="exact").execute()
        workspaces_7d = client.table("workspaces")\
            .select("id", count="exact")\
            .gte("created_at", seven_days_ago).execute()

        # Reach is a grant, never an ownership column (ADR-405) — so the honest
        # "how much principal activity does this platform hold" figure is the
        # grant count, not a user count.
        grants = client.table("principal_grants").select("id", count="exact").execute()

        sessions = client.table("chat_sessions").select("id", count="exact").execute()
        sessions_7d = client.table("chat_sessions")\
            .select("id", count="exact")\
            .gte("created_at", seven_days_ago).execute()

        messages = client.table("session_messages").select("id", count="exact").execute()

        funnel = _engagement_funnel(client)

        return AdminOverviewStats(
            total_workspaces=workspaces.count or 0,
            total_grants=grants.count or 0,
            total_sessions=sessions.count or 0,
            total_messages=messages.count or 0,
            workspaces_7d=workspaces_7d.count or 0,
            sessions_7d=sessions_7d.count or 0,
            ws_never_opened_lane=funnel["never_opened_lane"],
            ws_lane_no_message=funnel["lane_no_message"],
            ws_sent_message=funnel["sent_message"],
            ws_authored=funnel["authored"],
        )
    except Exception as e:
        logger.error("[ADMIN] Overview stats query failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


# =============================================================================
# GET /execution-stats — spend + scheduler health
# =============================================================================

@router.get("/execution-stats", response_model=AdminExecutionStats)
async def get_execution_stats(admin: AdminAuth):
    """Spend this month / today and the scheduler heartbeat.

    One fetch over the month covers both figures — today's spend is a slice of
    it, not a second round trip (ADR-655 D4).
    """
    try:
        client = admin.client
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        today_utc = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        cutoff_24h = (now - timedelta(hours=24)).isoformat()

        # ADR-291: execution_events is the canonical cost ledger. `cost_usd` is
        # NULL on mechanical/skipped wakes — coerce with `or 0`, not `, 0`
        # (the present-but-null trap that 500'd this route once before).
        spend_rows = client.table("execution_events")\
            .select("cost_usd, billed_usd, created_at, model")\
            .gte("created_at", month_start)\
            .limit(_EVENT_CAP)\
            .execute().data or []

        spend_usd_this_month = sum(_billed_draw(r) for r in spend_rows)
        daily_spend_today = sum(
            _billed_draw(r)
            for r in spend_rows
            if (r.get("created_at") or "") >= today_utc
        )
        if len(spend_rows) >= _EVENT_CAP:
            logger.warning(
                "[ADMIN] month spend hit the %d-row cap — the figure is a FLOOR, raise the cap",
                _EVENT_CAP,
            )

        # Where the month's money went — bucketed from the fetch above, so the
        # engine mix costs no extra round trip. Derived from what the ledger
        # recorded: an engine we start running appears here without a code
        # change, and one we stop running disappears.
        engine_runs: dict[str, int] = defaultdict(int)
        engine_spend: dict[str, float] = defaultdict(float)
        for r in spend_rows:
            model = r.get("model")
            if not model:
                continue
            engine_runs[model] += 1
            engine_spend[model] += _billed_draw(r)
        engines = sorted(
            (
                AdminEngineRow(
                    model=m, runs=engine_runs[m], billed_usd=round(engine_spend[m], 4)
                )
                for m in engine_runs
            ),
            key=lambda e: e.billed_usd,
            reverse=True,
        )

        hb = client.table("activity_log")\
            .select("created_at")\
            .eq("event_type", "scheduler_heartbeat")\
            .order("created_at", desc=True)\
            .limit(1).execute()
        last_heartbeat = hb.data[0]["created_at"] if hb.data else None

        hb_24h = client.table("activity_log")\
            .select("id", count="exact")\
            .eq("event_type", "scheduler_heartbeat")\
            .gte("created_at", cutoff_24h).execute()

        return AdminExecutionStats(
            spend_usd_this_month=round(spend_usd_this_month, 4),
            daily_spend_today=round(daily_spend_today, 4),
            daily_spend_ceiling=float(os.getenv("DAILY_SPEND_CEILING_USD", "10.0")),
            last_scheduler_heartbeat=last_heartbeat,
            heartbeats_24h=hb_24h.count or 0,
            engines=engines,
        )
    except Exception as e:
        logger.error("[ADMIN] Execution stats query failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch execution stats: {str(e)}")


# =============================================================================
# GET /workspaces — the workspace list
# =============================================================================

@router.get("/workspaces", response_model=list[AdminWorkspaceRow])
async def list_workspaces(admin: AdminAuth):
    """Every live workspace with its tier, balance, reach and 7d activity.

    ADR-655 D4 — the query count is CONSTANT in the number of workspaces. The
    predecessor issued 4 queries per row inside a Python loop (85 round trips
    for 21 workspaces, growing linearly with signups). Here: one workspaces
    fetch, one grants fetch, one events fetch, one batched email resolution —
    everything else is bucketed in memory.
    """
    try:
        client = admin.client
        cutoff_7d = _get_date_threshold(7)

        # Soft-deleted workspaces are not live workspaces (ADR-478's trash
        # contract) — the console lists what is running.
        workspaces = client.table("workspaces")\
            .select("id, name, owner_id, created_at, balance_usd, "
                    "subscription_tier, billing_exempt, deleted_at")\
            .is_("deleted_at", "null")\
            .order("created_at", desc=True)\
            .limit(500)\
            .execute().data or []

        if not workspaces:
            return []

        ws_ids = [w["id"] for w in workspaces]

        # --- grants per workspace (one fetch) -------------------------------
        grant_counts: dict[str, int] = defaultdict(int)
        try:
            for g in (client.table("principal_grants")
                      .select("workspace_id")
                      .in_("workspace_id", ws_ids)
                      .limit(_EVENT_CAP).execute().data or []):
                if g.get("workspace_id"):
                    grant_counts[g["workspace_id"]] += 1
        except Exception as exc:  # noqa: BLE001 — reach count is best-effort
            logger.warning("[ADMIN] grant count lookup failed: %s", exc)

        # --- 7d activity per workspace (one fetch, bucketed) ----------------
        # `execution_events.workspace_id` is populated on every live row
        # (1597/1597 at ADR-655), so the cost ledger keys on the binding unit
        # directly — no owner-resolution hop.
        events_7d: dict[str, int] = defaultdict(int)
        spend_7d: dict[str, float] = defaultdict(float)
        last_activity: dict[str, str] = {}
        try:
            for e in (client.table("execution_events")
                      .select("workspace_id, cost_usd, billed_usd, created_at")
                      .gte("created_at", cutoff_7d)
                      .order("created_at", desc=True)
                      .limit(_EVENT_CAP).execute().data or []):
                wid = e.get("workspace_id")
                if not wid:
                    continue
                events_7d[wid] += 1
                spend_7d[wid] += _billed_draw(e)
                # Rows arrive newest-first, so the first sighting is the latest.
                if wid not in last_activity and e.get("created_at"):
                    last_activity[wid] = e["created_at"]
        except Exception as exc:  # noqa: BLE001 — activity is best-effort
            logger.warning("[ADMIN] 7d event rollup failed: %s", exc)

        # --- effective balance (ADR-655 am.1) ------------------------------
        # `workspaces.balance_usd` is the GRANTED total and is never debited —
        # ADR-396's "balance IS the currency", with spend netted at READ time by
        # the `get_effective_balance` RPC. The console shipped rendering the raw
        # column under a "Balance" header, so it read **$124.21** for the
        # workspace whose own billing pane said **"Free · $17.84 left"** — two
        # numbers for one fact, at the same moment.
        #
        # This calls the RPC rather than re-deriving its arithmetic. The first
        # cut DID re-derive it — bucketing spend-since-anchor from one capped
        # fetch to stay O(1) — and was WRONG on 3 of 21 workspaces, the busiest
        # by $47: the `_EVENT_CAP` row limit truncated its ledger, so the netted
        # spend was a floor and the balance read high. The cap is a real hazard
        # (this module's own `_EVENT_CAP` note says a cap hit silently
        # undercounts spend) and re-deriving a money function is how you meet
        # it. One RPC per workspace is a genuine per-row call, which D4 exists
        # to forbid — but D4 forbids re-fetching data we already hold, not
        # asking the database for the ONE figure only it can compute correctly.
        # At 21 live workspaces this is 21 cheap STABLE calls; if the roster
        # grows past a few hundred, the fix is a set-returning RPC, never a
        # second copy of the formula here.
        effective: dict[str, float] = {}
        for wid in ws_ids:
            try:
                val = client.rpc(
                    "get_effective_balance", {"p_workspace_id": wid}
                ).execute().data
                effective[wid] = round(float(val), 4) if val is not None else 0.0
            except Exception as exc:  # noqa: BLE001 — one row never breaks the page
                logger.warning("[ADMIN] effective balance failed for %s: %s", wid[:8], exc)

        # --- engagement: lanes, messages, authored files (am.2) -------------
        # Three fetches, bucketed in memory — the SAME function the funnel in
        # /stats folds, so the two surfaces cannot disagree about one fact.
        engagement = _engagement_rollup(client)

        # --- owner labels (ADR-655 D3: the ONE resolver, batched) -----------
        # `auth.users` is the writer of record for an account identity
        # (ADR-650); `workspaces.owner_email` was dropped by migration 257
        # precisely because it had no writer. `resolve_member_names` is
        # TTL-cached, so a page refresh does not re-hammer the auth admin API.
        owner_labels: dict[str, str] = {}
        try:
            from services.principal_display import resolve_member_names
            owner_ids = sorted({w["owner_id"] for w in workspaces if w.get("owner_id")})
            owner_labels = {
                k: v for k, v in resolve_member_names(client, owner_ids).items() if v
            }
        except Exception as exc:  # noqa: BLE001 — humanization is best-effort
            logger.warning("[ADMIN] owner label resolution failed: %s", exc)

        rows: list[AdminWorkspaceRow] = []
        for w in workspaces:
            wid = w["id"]
            rows.append(AdminWorkspaceRow(
                id=wid,
                name=w.get("name"),
                owner_id=w.get("owner_id") or "",
                # None, never "unknown" — the client renders name + short id.
                owner_label=owner_labels.get(w.get("owner_id") or ""),
                created_at=w["created_at"],
                tier=w.get("subscription_tier") or "free",
                balance_usd=float(w.get("balance_usd") or 0),
                # Absent (an RPC failure) degrades to the granted total rather
                # than to 0, which would read as an empty wallet.
                effective_balance_usd=effective.get(
                    wid, float(w.get("balance_usd") or 0)
                ),
                grant_count=grant_counts.get(wid, 0),
                lane_count=engagement.get(wid, {}).get("lanes", 0),
                message_count=engagement.get(wid, {}).get("messages", 0),
                authored_file_count=engagement.get(wid, {}).get("authored", 0),
                events_7d=events_7d.get(wid, 0),
                spend_7d=round(spend_7d.get(wid, 0.0), 4),
                last_activity=last_activity.get(wid),
                billing_exempt=bool(w.get("billing_exempt", False)),
            ))

        # Busiest first — what the operator is looking for at 8am (ADR-655 D7).
        rows.sort(key=lambda r: (r.events_7d, r.spend_7d), reverse=True)
        return rows

    except Exception as e:
        logger.error("[ADMIN] Workspace list query failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch workspaces: {str(e)}")


@router.post("/workspace/{workspace_id}/billing-exempt", response_model=BillingExemptResponse)
async def set_billing_exempt(workspace_id: str, body: BillingExemptRequest, admin: AdminAuth):
    """Toggle a workspace's billing-exempt state (ADR-429 §12.3a — comp/override).

    When exempt, the workspace pays nothing (base + seats forced $0), regardless
    of tier/headcount. Operator-only (AdminAuth); the intended use is holding test
    workspaces out of billing + the permanent comped-account capability. Dormant-
    safe: with the seat fee at $0 today this changes no billing outcome yet — it is
    the rail the eventual seat activation honors."""
    try:
        result = admin.client.table("workspaces")\
            .update({"billing_exempt": body.exempt})\
            .eq("id", workspace_id)\
            .execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return BillingExemptResponse(workspace_id=workspace_id, billing_exempt=body.exempt)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[ADMIN] Billing exempt toggle failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to set billing exempt: {str(e)}")
