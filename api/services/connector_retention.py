"""Connector raw-lane retention — the anti-bloat dial (ADR-392 D8).

Connectors are the first HIGH-VOLUME context-in transport, so the capture lane
(inbound/{platform}/) needs a retention answer that MCP + web never forced (their
volume never triggered ADR-376 §8's deferred raw-lane GC). This module un-defers
that GC as an operator DIAL:

  - a substrate-read `retention_days` policy (NOT a hard-coded enum) at a
    governance path; the 7/14/30 the UI offers are PRESETS over a dynamic value;
  - DERIVE-THEN-PRUNE: a raw observation is prunable only if (a) it is older than
    the window AND (b) a derived act already cites it (its understanding is
    captured). Never GC a raw no derived act has consumed — that would drop
    un-distilled evidence.

⭐ PRICING SEAM (ADR-391, wired in a LATER session — mechanic only here).
`resolve_retention_days` reads ONE value, so the pricing layer can gate the
MAXIMUM allowed window per subscription tier WITHOUT touching GC code:
retention-window is a natural commons-scale tier axis (parallel to ADR-391's
# principals · # connectors · autonomy-ceiling). The pricing session sets the
tier→max-window mapping by clamping the operator's declared value against a
tier ceiling BEFORE it reaches `resolve_retention_days`, or by having this reader
consult the tier ceiling. Either way the GC is untouched — it just honors the
resolved number. No pricing code lives here.

Axiom-1 / resume safety: like SyncPlatformState, the GC does NOT read the clock.
`now_iso` is passed in by the caller (the scheduler stamps it), and raw age is
computed from the {observed_at} segment already in the filename — deterministic,
replayable.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Governance path — operator config the steward reads-not-authors (ADR-254
# machine-parsed yaml, `_`-prefixed). governance/ is the GRANT root (locked to
# operator authorship; ADR-366), which is correct: retention is a spend/storage
# envelope, kin to _budget.yaml.
RETENTION_POLICY_PATH = "governance/_retention.yaml"

# Kernel default — generous so no operator loses raw silently before opting in.
DEFAULT_RETENTION_DAYS = 30

INBOUND_ROOT = "inbound/"


async def resolve_retention_days(
    client: Any,
    user_id: str,
    *,
    tier_max_days: Optional[int] = None,
) -> int:
    """Resolve the effective raw-lane retention window (days).

    Reads governance/_retention.yaml (`retention_days: <int>`); falls back to
    DEFAULT_RETENTION_DAYS when unset/unparseable. `tier_max_days` is the PRICING
    SEAM (ADR-391): when a subscription tier caps the window, the resolved value
    is clamped to it — the pricing session passes this; today's callers pass None
    and the operator's declared value stands. Never raises.
    """
    from services.workspace import UserMemory
    from services.review_policy import load_workspace_yaml

    declared = DEFAULT_RETENTION_DAYS
    um = UserMemory(client, user_id)
    try:
        body = await um.read(RETENTION_POLICY_PATH)
    except Exception:
        body = None
    if body:
        parsed = load_workspace_yaml(body)
        raw = parsed.get("retention_days")
        if isinstance(raw, bool):  # bool is an int subclass — reject explicitly
            raw = None
        if isinstance(raw, int) and raw > 0:
            declared = raw
        elif raw is not None:
            logger.warning(
                "[CONNECTOR_RETENTION] non-int retention_days=%r for user=%s; using default",
                raw, user_id[:8],
            )
    if tier_max_days is not None and tier_max_days > 0:
        return min(declared, tier_max_days)
    return declared


async def read_retention_days(client: Any, user_id: str) -> int:
    """The operator's DECLARED retention window (no tier clamp) — for the FE dial's
    current-state read. Returns DEFAULT_RETENTION_DAYS when unset. Never raises.

    Distinct from `resolve_retention_days`: that applies the pricing tier ceiling
    (the effective GC value); this returns the raw declared value the dial edits."""
    return await resolve_retention_days(client, user_id, tier_max_days=None)


async def write_retention_days(
    client: Any,
    user_id: str,
    days: int,
    *,
    authored_by: str = "operator",
) -> int:
    """Author governance/_retention.yaml with `retention_days: <days>` (ADR-392 D8).

    The single write path for the retention dial. Clamps to a sane floor (1 day)
    so a zero/negative can't disable retention silently. governance/ is the GRANT
    root (operator-authored; the steward reads-not-authors), so authored_by is
    'operator' by default. Returns the written value.
    """
    from services.workspace import UserMemory
    import yaml as _yaml

    clamped = max(1, int(days))
    content = _yaml.safe_dump(
        {"retention_days": clamped}, sort_keys=False, default_flow_style=False,
    )
    um = UserMemory(client, user_id)
    await um.write(
        RETENTION_POLICY_PATH,
        content,
        summary="retention-policy",
        authored_by=authored_by,
        message=f"set raw-capture retention window to {clamped} days",
    )
    logger.info("[CONNECTOR_RETENTION] user=%s set retention_days=%d", user_id[:8], clamped)
    return clamped


def _observed_at_from_path(path: str) -> Optional[str]:
    """Extract the {observed_at} stamp from inbound/{platform}/{selector}/{stamp}.{ext}."""
    # strip an optional /workspace/ prefix, then take the filename stem
    rel = path.split("/workspace/", 1)[-1]
    parts = rel.rstrip("/").split("/")
    if len(parts) < 4:
        return None
    stem = parts[-1].rsplit(".", 1)[0]
    return stem or None


def _age_days(observed_at: str, now: datetime) -> Optional[float]:
    """Days between an ISO observed_at stamp and now; None if unparseable."""
    s = (observed_at or "").strip().replace("Z", "+00:00")
    try:
        then = datetime.fromisoformat(s)
    except ValueError:
        return None
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return (now - then).total_seconds() / 86400.0


async def prune_raw_lane(
    client: Any,
    user_id: str,
    now_iso: str,
    *,
    retention_days: Optional[int] = None,
    cited_paths: Optional[set] = None,
    dry_run: bool = False,
) -> dict:
    """Derive-then-prune GC over the connector raw lane (ADR-392 D8).

    A raw file under inbound/{platform}/ is pruned iff:
      1. it is older than the retention window (age from the {observed_at}
         filename segment vs `now_iso` — no clock read), AND
      2. some derived act cites it (its path ∈ `cited_paths`) — its understanding
         is already captured, so the raw is safe to drop (DP32 evidence-bounded
         retention: keep raw only until distilled).

    `cited_paths` is the set of /workspace-absolute raw paths that appear in any
    derived file's `derived_from` — the caller supplies it (a GROUP BY over the
    revision/derivation metadata; see the walker note below). When None, NOTHING
    is pruned (fail-safe: without knowing what's cited, never drop).

    Only the connector lane is swept — inbound/mcp/ + inbound/web/ have their own
    retention governance (they are not connector context). Never raises.

    Returns {scanned, pruned, kept_uncited, kept_fresh, retention_days, dry_run}.
    """
    from services.workspace import UserMemory

    try:
        now = datetime.fromisoformat((now_iso or "").replace("Z", "+00:00"))
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
    except ValueError:
        logger.warning("[CONNECTOR_RETENTION] bad now_iso=%r; aborting prune", now_iso)
        return {"scanned": 0, "pruned": 0, "kept_uncited": 0, "kept_fresh": 0,
                "retention_days": 0, "dry_run": dry_run, "error": "bad_now_iso"}

    # ADR-396: clamp the declared window to the subscription tier's ceiling (gate 1).
    # An explicit retention_days arg (test/caller override) still wins as before.
    from services.billing_tiers import retention_max_days_for_user
    tier_max = retention_max_days_for_user(client, user_id)
    window = retention_days if isinstance(retention_days, int) and retention_days > 0 \
        else await resolve_retention_days(client, user_id, tier_max_days=tier_max)

    um = UserMemory(client, user_id)
    # List the connector raw lane. inbound/mcp/ + inbound/web/ are siblings we do
    # NOT touch — walk each connector platform sub-root only.
    try:
        all_inbound = await um.list(INBOUND_ROOT, recursive=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[CONNECTOR_RETENTION] list inbound/ failed user=%s: %s", user_id[:8], exc)
        return {"scanned": 0, "pruned": 0, "kept_uncited": 0, "kept_fresh": 0,
                "retention_days": window, "dry_run": dry_run}

    NON_CONNECTOR = ("mcp/", "web/")
    cited = cited_paths if cited_paths is not None else None

    scanned = pruned = kept_uncited = kept_fresh = 0
    for rel in all_inbound:
        # rel is relative to INBOUND_ROOT (e.g. "slack/daily-work/2026-07-01T...md")
        if rel.startswith(NON_CONNECTOR):
            continue
        scanned += 1
        full_rel = f"{INBOUND_ROOT}{rel}"
        abs_path = f"/workspace/{full_rel}"

        observed = _observed_at_from_path(full_rel)
        age = _age_days(observed, now) if observed else None
        if age is None or age < window:
            kept_fresh += 1
            continue

        # Derive-then-prune: only drop if a derived act cites it.
        if cited is None or abs_path not in cited:
            kept_uncited += 1
            continue

        if not dry_run:
            try:
                await um.delete(full_rel)
            except Exception as exc:  # noqa: BLE001
                logger.warning("[CONNECTOR_RETENTION] delete failed %s: %s", full_rel, exc)
                kept_uncited += 1
                continue
        pruned += 1

    logger.info(
        "[CONNECTOR_RETENTION] user=%s window=%dd scanned=%d pruned=%d kept_fresh=%d kept_uncited=%d dry=%s",
        user_id[:8], window, scanned, pruned, kept_fresh, kept_uncited, dry_run,
    )
    return {
        "scanned": scanned,
        "pruned": pruned,
        "kept_uncited": kept_uncited,
        "kept_fresh": kept_fresh,
        "retention_days": window,
        "dry_run": dry_run,
    }


async def gather_cited_raw_paths(client: Any, user_id: str) -> set:
    """The set of /workspace-absolute raw paths cited by any derived object.

    Derive-then-prune (ADR-394 D4) needs to know which raw observations a
    derived act already cites, so `prune_raw_lane` keeps only un-distilled
    evidence. A derived object carries `derived_from: <raw path(s)>` (ADR-376
    D3). This walks the derived homes (operation/) for content mentioning
    `derived_from` and collects every cited path — the "GROUP BY over
    derived_from" the prune step consumes.

    Reuses `mcp_composition._extract_derived_from_list` (the single on-wire
    parser for the three citation shapes — bare/inline/block). Returns an empty
    set on any error (fail-safe: an empty cited-set means prune_raw_lane drops
    nothing UNCITED, and with cited=set() it drops nothing at all — never a
    false prune). Best-effort; never raises.
    """
    from services.mcp_composition import _extract_derived_from_list

    cited: set = set()
    try:
        hits = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .like("path", "/workspace/operation/%")
            .ilike("content", "%derived_from%")
            .limit(500)
            .execute()
        ).data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[CONNECTOR_RETENTION] gather_cited_raw_paths query failed user=%s: %s",
            user_id[:8], exc,
        )
        return cited

    for h in hits:
        for ref in _extract_derived_from_list(h.get("content")):
            cited.add(ref)
    return cited


__all__ = [
    "RETENTION_POLICY_PATH",
    "DEFAULT_RETENTION_DAYS",
    "resolve_retention_days",
    "read_retention_days",
    "write_retention_days",
    "prune_raw_lane",
    "gather_cited_raw_paths",
]
