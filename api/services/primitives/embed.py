"""Embed primitive — make-AI-ready as an explicit, autonomy-governed step (ADR-325).

Pre-ADR-325, embedding was a buried fire-and-forget side-effect of
`WriteFile(scope='context')` only — applied inconsistently across the three
doors files enter (author / ingest / derive). ADR-325 promotes it to a
first-class `Embed` primitive that flows through the existing ADR-307
permission gate with ZERO new mechanism:

  - NOT in READ_ONLY_PRIMITIVES → consequential → passes the gate.
  - IN GATE_QUEUEABLE_PRIMITIVES → manual/bounded QUEUE, autonomous APPLY.
    The autonomy mode IS the embed policy (no separate config).
  - Carries an orthogonal cost ceiling (embedding API calls) like Schedule's
    pace cap — an additive check, not the autonomy gate.

NOT a 100%-embed principle (the operator's explicit nuance vs Claude-Code-
selective): embed is *selective by content-kind* (D5 eligibility) AND *chosen
by autonomy* (D3 gate). Embedding `governance/_pace.yaml` is pointless; embedding
accumulated domain context / uploaded reference material / authored prose is the
point.

The embedding mechanism itself is the surviving `_embed_workspace_file` helper
(from workspace.py — orphaned by ADR-321 when scope='context' was deleted, now
the Embed handler's call target). The read side (QueryKnowledge semantic search
over workspace_files.embedding) is unchanged.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Content-kind eligibility (ADR-325 D5) — embed is selective, not 100%.
# ---------------------------------------------------------------------------
# Embed-eligible: semantic-search targets — accumulated domain context, uploaded
# reference material, authored prose the operator wants discoverable.
# Embed-INeligible: machine config / structured state / tiny files read by path,
# never semantically ranked (governance yaml, recurrence yaml, signal yaml).

# Roots whose prose content is a semantic-search target.
#   operation/          — accumulated domain context (seat-derived understanding)
#   uploads/            — legacy operator reference material (pre-ADR-395)
#   inbound/uploads/    — ADR-395 upload TEXT PROJECTIONS (.extracted.md). The raw
#                         blob beside them is NOT a search target (it has no text
#                         body — it's reached via content_url); its DERIVED text
#                         projection IS (DP34: the projection is the model-
#                         consumable object). Scoped to inbound/uploads/ only —
#                         the machine raw lanes (inbound/{slack,mcp,web}/) are raw
#                         observations reached by deterministic key, not ranked.
_EMBED_ELIGIBLE_ROOTS = ("operation/", "uploads/", "inbound/uploads/")
# Extensions that are machine config / structured state — never embed.
_EMBED_INELIGIBLE_EXTS = (".yaml", ".yml", ".json")
# Roots that are machine/runtime/ceiling substrate — never embed regardless of ext.
_EMBED_INELIGIBLE_ROOTS = ("governance/", "system/")
# Minimum content length worth embedding (bytes) — tiny files aren't search targets.
_EMBED_MIN_CHARS = 200


def _normalize_rel(path: str) -> str:
    """Strip a leading /workspace/ (or workspace/) so we test against roots."""
    p = path.strip().lstrip("/")
    if p.startswith("workspace/"):
        p = p[len("workspace/"):]
    return p


def is_embed_eligible(path: str, content: str | None = None) -> tuple[bool, str]:
    """Return (eligible, reason). Content-kind selectivity per ADR-325 D5.

    A path is embed-eligible iff it is under an eligible root, is not a machine
    config/structured-state extension, is not under an ineligible root, and (when
    content is given) is long enough to be a meaningful search target.
    """
    rel = _normalize_rel(path)
    lower = rel.lower()

    if any(rel.startswith(r) for r in _EMBED_INELIGIBLE_ROOTS):
        return False, f"ineligible_root:{rel.split('/', 1)[0]}/ (machine/runtime substrate)"
    if lower.endswith(_EMBED_INELIGIBLE_EXTS):
        return False, "ineligible_kind: machine config / structured state (read by path, not ranked)"
    if not any(rel.startswith(r) for r in _EMBED_ELIGIBLE_ROOTS):
        return False, (
            "not_a_search_target: only operation/ (domain context), uploads/ "
            "(reference material) and inbound/uploads/ (upload text projections) "
            "are embed-eligible"
        )
    if content is not None and len(content.strip()) < _EMBED_MIN_CHARS:
        return False, f"too_short: < {_EMBED_MIN_CHARS} chars (not a meaningful search target)"
    return True, "eligible"


def is_searchable_root(path: str) -> bool:
    """True iff `path` lives under a semantic-search root (ADR-325 / ADR-395).

    The path-only companion to `is_embed_eligible` (no content-length / extension
    check — those govern whether a file gets embedded; this governs whether a
    result-row belongs in an unscoped QueryKnowledge sweep). Singular source of
    truth for "what is a search target" — reused by handle_query_knowledge's
    default (no-domain) sweep so the upload-projection lane (inbound/uploads/) is
    reachable alongside operation/, without a second hardcoded root list drifting.
    """
    rel = _normalize_rel(path)
    if any(rel.startswith(r) for r in _EMBED_INELIGIBLE_ROOTS):
        return False
    return any(rel.startswith(r) for r in _EMBED_ELIGIBLE_ROOTS)


# ---------------------------------------------------------------------------
# Cost ceiling (ADR-325 D4) — additive resource check, like Schedule's pace cap.
# ---------------------------------------------------------------------------
# Per-workspace daily embed-call cap. Embedding is cheap but an autonomous
# workspace could run it up; the cap is a backstop, not a tight budget.
# (Reuses the same "additive check, not the autonomy gate" shape as Schedule's
# pace cap — ADR-307 permission.py:126-128.)
_EMBED_DAILY_CAP = int(os.environ.get("EMBED_DAILY_CAP", "500"))


def _embed_calls_today(client: Any, user_id: str) -> int:
    """Best-effort count of Embed calls in the trailing 24h from execution_events.
    Returns 0 on any error (fail-open on the count — the gate already governs
    whether the call applies; this is a backstop)."""
    try:
        from datetime import datetime, timedelta, timezone
        since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        res = (
            client.table("execution_events")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("slug", "embed")
            .gte("created_at", since)
            .execute()
        )
        return res.count or 0
    except Exception:
        return 0


EMBED_TOOL = {
    "name": "Embed",
    "description": """Make a file AI-ready: compute its embedding so QueryKnowledge can semantically rank it (ADR-325).

This is the EXPLICIT make-AI-ready step (not an automatic side-effect of writing).
Embed is consequential and autonomy-governed — under manual/bounded it queues for
operator approval; under autonomous it applies. Embedding is selective:

ELIGIBLE (semantic-search targets):
- operation/{domain}/** — accumulated domain context (entities, syntheses, landscapes)
- uploads/** — user-contributed reference material (legacy pre-ADR-395)
- inbound/uploads/**.extracted.md — upload text projections (ADR-395/DP34)

NOT ELIGIBLE (read by path, never ranked — Embed returns 'not eligible'):
- governance/** + system/** (machine/runtime substrate)
- *.yaml / *.yml / *.json (machine config / structured state)
- files under ~200 chars (not meaningful search targets)

Idempotent: re-embedding a current file is cheap and harmless. Use Embed after
writing accumulated domain context or after an upload you want discoverable via
QueryKnowledge. You usually do NOT need to embed reports, governance, or config.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Workspace-relative path to embed (e.g. 'operation/competitors/acme/profile.md', 'uploads/q2-report.md').",
            },
        },
        "required": ["path"],
    },
}


async def handle_embed(auth: Any, input: dict) -> dict:
    """Embed one file (ADR-325). Eligibility-checked + cost-ceilinged.

    The permission gate (ADR-307) has already resolved APPLY before this handler
    runs (Embed is gate-queueable; under bounded/manual a Reviewer call would have
    been QUEUE'd upstream). This handler is the pure execution arm: check
    content-kind eligibility, check the cost ceiling, compute + store the embedding.
    """
    user_id = getattr(auth, "user_id", None)
    client = getattr(auth, "client", None)
    if not user_id or client is None:
        return {"success": False, "error": "auth_required", "message": "user_id + client required"}

    path = (input or {}).get("path") or ""
    if not path:
        return {"success": False, "error": "missing_path", "message": "path is required"}

    rel = _normalize_rel(path)
    abs_path = f"/workspace/{rel}"

    # Read current content (also confirms the file exists).
    try:
        res = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", abs_path)
            .limit(1)
            .execute()
        )
        rows = res.data or []
    except Exception as e:
        return {"success": False, "error": "read_failed", "message": str(e)}

    if not rows:
        return {"success": False, "error": "not_found", "message": f"No file at {abs_path}"}

    content = rows[0].get("content") or ""

    # D5: content-kind eligibility.
    eligible, reason = is_embed_eligible(rel, content)
    if not eligible:
        return {"success": False, "error": "not_embed_eligible", "message": reason, "path": abs_path}

    # D4: cost ceiling (additive backstop).
    used = _embed_calls_today(client, user_id)
    if used >= _EMBED_DAILY_CAP:
        return {
            "success": False, "error": "embed_budget_exceeded",
            "message": f"Daily embed cap reached ({used}/{_EMBED_DAILY_CAP}).",
        }

    # Execute: compute + store the embedding (the surviving helper from ADR-321).
    from services.primitives.workspace import _embed_workspace_file
    await _embed_workspace_file(client, user_id, abs_path, content)

    # Cost-ledger marker (also feeds _embed_calls_today).
    try:
        from services.telemetry import record_execution_event
        from services.supabase import get_service_client
        record_execution_event(
            get_service_client(), user_id=user_id, slug="embed",
            mode="mechanical", trigger_type="addressed", status="success",
        )
    except Exception as e:
        logger.debug(f"[EMBED] ledger marker failed (non-fatal): {e}")

    return {"success": True, "path": abs_path, "message": f"Embedded {abs_path}"}
