"""
Admin routes — the operator console (ADR-655).

Endpoints:
- GET  /stats            — platform totals: workspaces, grants, sessions, messages
- GET  /execution-stats  — spend this month / today, the daily ceiling, scheduler health
- GET  /workspaces       — the workspace list: tier, balance, grants, 7d events, 7d spend
- POST /workspace/{id}/billing-exempt — the comp toggle (ADR-429 §12.3a)

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
    balance_usd: float = 0.0
    grant_count: int = 0
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

        return AdminOverviewStats(
            total_workspaces=workspaces.count or 0,
            total_grants=grants.count or 0,
            total_sessions=sessions.count or 0,
            total_messages=messages.count or 0,
            workspaces_7d=workspaces_7d.count or 0,
            sessions_7d=sessions_7d.count or 0,
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
            .select("cost_usd, created_at")\
            .gte("created_at", month_start)\
            .limit(_EVENT_CAP)\
            .execute().data or []

        spend_usd_this_month = sum(float(r.get("cost_usd") or 0) for r in spend_rows)
        daily_spend_today = sum(
            float(r.get("cost_usd") or 0)
            for r in spend_rows
            if (r.get("created_at") or "") >= today_utc
        )
        if len(spend_rows) >= _EVENT_CAP:
            logger.warning(
                "[ADMIN] month spend hit the %d-row cap — the figure is a FLOOR, raise the cap",
                _EVENT_CAP,
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
                      .select("workspace_id, cost_usd, created_at")
                      .gte("created_at", cutoff_7d)
                      .order("created_at", desc=True)
                      .limit(_EVENT_CAP).execute().data or []):
                wid = e.get("workspace_id")
                if not wid:
                    continue
                events_7d[wid] += 1
                spend_7d[wid] += float(e.get("cost_usd") or 0)
                # Rows arrive newest-first, so the first sighting is the latest.
                if wid not in last_activity and e.get("created_at"):
                    last_activity[wid] = e["created_at"]
        except Exception as exc:  # noqa: BLE001 — activity is best-effort
            logger.warning("[ADMIN] 7d event rollup failed: %s", exc)

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
                grant_count=grant_counts.get(wid, 0),
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
