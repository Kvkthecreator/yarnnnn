"""Harvest — the "bring in your reality" invocation (ADR-331 D3 + D4).

The catch-up door for a new operator's pre-YARNNN context. NOT a subsystem,
NOT continuous sync (ADR-153 stands), NOT a new primitive or permission mode.
Harvest is an ordinary bounded invocation: it reads the operator's connected
sources (via the EXISTING platform read tools), curates them with an LLM, and
writes attributed substrate (`agent:harvest`) into context domains. Its only
trace is the files it writes — "what's been brought in = the files that exist,
attributed and dated" (ADR-331 §4 dual-tracking retraction).

Two surfaces, both fired from the `/setup` "bring in reality" step:

  harvest_dry_run(auth, scope)
      Metadata-only. Calls the EXISTING list tools (platform_*_list_*) for
      counts; maps sources → likely context domains. NO LLM, NO writes.
      Powers the picker's inline "~N items → these domains" estimate (D4).

  harvest_run(auth, scope)
      The curated invocation. A headless LLM call (same machinery as
      DispatchSpecialist per ADR-261 D7) with the scoped read tools +
      WriteFile, prompted to read the picked sources, curate (drop noise,
      summarize, route each piece to the right context domain), and write
      `agent:harvest` files. Bounded tool-use loop. Selection scope is
      ephemeral (passed in, never persisted — ADR-331 D4 no-stored-state).

Scope shape (from the picker, ephemeral component state → request body):
  {
    "sources": [
      {"provider": "slack",  "id": "C123", "label": "#decisions", "range_days": 30},
      {"provider": "notion", "id": "<page-uuid>", "label": "Roadmap"},
      {"provider": "github", "id": "owner/repo", "label": "owner/repo"},
    ]
  }
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


#: Caller-identity attribution for every harvest write (ADR-209 + ADR-288 D1).
#: The `agent:` prefix is in VALID_AUTHOR_PREFIXES — harvest adds no new prefix.
HARVEST_CALLER_IDENTITY = "agent:harvest"

#: Harvest reuses the specialist bounded-loop model + budget (ADR-260 D8).
_HARVEST_MODEL = "claude-sonnet-4-6"
_HARVEST_MAX_TOKENS = 4096
_HARVEST_MAX_ROUNDS = 12  # multi-source curation needs more rounds than a single specialist output

#: Per-provider list tool used for the metadata-only dry-run count. These are
#: the EXISTING read tools (ADR-331: no new read capability).
_LIST_TOOL = {
    "slack": "platform_slack_list_channels",
    "notion": "platform_notion_search",
    "github": "platform_github_list_repos",
}

#: Coarse source-provider → likely context-domain mapping for the dry-run
#: estimate (ADR-331 §5 v1: "a coarse source→domain mapping; refine if
#: operators find the estimate misleading"). The LLM does the real per-piece
#: routing at run time; this is only the picker's pre-fire hint.
_PROVIDER_DOMAIN_HINT = {
    "slack": ["relationships", "signals"],
    "notion": ["projects", "market"],
    "github": ["projects", "signals"],
}

#: Kernel-universal context domains, used when the directory registry can't be
#: read. The harvest LLM routes into whichever set it's given.
_FALLBACK_DOMAINS = ["relationships", "projects", "market", "signals", "content"]


async def harvest_dry_run(auth: Any, scope: dict) -> dict:
    """Metadata-only estimate for the picker (ADR-331 D4). NO writes, NO LLM.

    Returns:
      {
        "success": True,
        "estimate": {"item_count": int, "source_count": int},
        "per_source": [{"provider","id","label","item_count","note"?}],
        "target_domains": ["relationships","projects",...],
      }
    """
    sources = _normalize_sources(scope)
    if not sources:
        return {
            "success": True,
            "estimate": {"item_count": 0, "source_count": 0},
            "per_source": [],
            "target_domains": [],
        }

    from services.platform_tools import handle_platform_tool

    per_source: list[dict] = []
    total_items = 0
    target_domains: set[str] = set()

    for src in sources:
        provider = src["provider"]
        list_tool = _LIST_TOOL.get(provider)
        item_count = 0
        note: str | None = None

        if list_tool is None:
            note = f"no list tool for provider {provider!r}"
        else:
            try:
                # Reuse the EXISTING capability-gated platform bridge. The list
                # tools return counts in their result shape (channels/results/
                # repos arrays) — we count, never read content (no writes).
                res = await handle_platform_tool(auth, list_tool, {})
                item_count = _count_from_list_result(provider, res)
                if not res.get("success"):
                    note = res.get("error") or "list failed"
            except Exception as exc:  # noqa: BLE001 — dry-run must never raise
                logger.warning("[HARVEST] dry-run list failed provider=%s: %s", provider, exc)
                note = "list failed"

        total_items += item_count
        for d in _PROVIDER_DOMAIN_HINT.get(provider, []):
            target_domains.add(d)
        entry = {
            "provider": provider,
            "id": src.get("id"),
            "label": src.get("label") or src.get("id"),
            "item_count": item_count,
        }
        if note:
            entry["note"] = note
        per_source.append(entry)

    return {
        "success": True,
        "estimate": {"item_count": total_items, "source_count": len(sources)},
        "per_source": per_source,
        "target_domains": sorted(target_domains),
    }


async def harvest_run(auth: Any, scope: dict) -> dict:
    """Fire the curated harvest invocation (ADR-331 D3).

    A headless LLM call with the scoped read tools + WriteFile, attributed
    `agent:harvest`. Reads the picked sources, curates, routes each piece to
    the right context domain, writes attributed substrate. Bounded loop.

    Returns:
      {
        "success": True/False,
        "files_written": [<path>, ...],
        "rounds_used": int,
        "tools_called": [<tool_name>, ...],
        "summary": "<harvest agent's closing note>",
        "error": "..." (only on failure),
      }
    """
    user_id = getattr(auth, "user_id", None)
    db_client = getattr(auth, "client", None)
    if not user_id or db_client is None:
        return {"success": False, "error": "auth_required"}

    sources = _normalize_sources(scope)
    if not sources:
        return {"success": False, "error": "empty_scope", "message": "No sources selected."}

    # Resolve the harvest tool surface: the read tools the picked providers
    # need + WriteFile (in HEADLESS_PRIMITIVES). We reuse
    # get_headless_tools_for_agent with the provider capabilities so only
    # connected-platform read tools surface.
    from services.primitives.registry import (
        HeadlessAuth,
        execute_primitive,
        get_headless_tools_for_agent,
    )

    required_capabilities = _capabilities_for_sources(sources)
    try:
        tools = await get_headless_tools_for_agent(
            db_client, user_id,
            agent={"role": "researcher"},  # universal read role; harvest is a read+curate task
            task_required_capabilities=required_capabilities,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[HARVEST] tool resolution failed: %s", exc)
        return {"success": False, "error": "tool_resolution_failed", "message": str(exc)}

    # Harvest-specific auth: attribute writes as `agent:harvest`, not
    # specialist:researcher. caller_identity flows to WriteFile's authored_by
    # (workspace.py reads auth.caller_identity per ADR-288 D1). We execute
    # primitives directly against THIS auth (not create_headless_executor,
    # which would close over its own specialist:researcher-attributed auth).
    harvest_auth = HeadlessAuth(db_client, user_id, agent={"role": "researcher"})
    harvest_auth.caller_identity = HARVEST_CALLER_IDENTITY

    allowed_tool_names = {t["name"] for t in tools if t.get("name")}

    async def executor(tool_name: str, tool_input: dict) -> dict:
        if tool_name not in allowed_tool_names:
            return {
                "success": False, "error": "not_available",
                "message": f"Tool {tool_name} not in harvest surface",
            }
        try:
            return await execute_primitive(harvest_auth, tool_name, tool_input)
        except Exception as exc:  # noqa: BLE001 — harvest tool errors never raise the loop
            logger.error("[HARVEST] tool %s failed: %s", tool_name, exc)
            return {"success": False, "error": "tool_failed", "message": str(exc)}

    available_domains = _available_context_domains(db_client, user_id)
    system_prompt = _compose_harvest_prompt(available_domains)
    brief = _compose_harvest_brief(sources, available_domains)

    # Bounded tool-use loop. Mirrors the canonical headless pattern in
    # services/primitives/dispatch_specialist.py + agents/freddie_agent.py:
    # ChatResponse exposes `.tool_uses` (list[ToolUseBlock] with .id/.name/
    # .input), `.stop_reason`, `.text`; assistant turns are reconstructed as
    # dict-shaped content for the next API call.
    from services.anthropic import chat_completion_with_tools

    messages: list[dict] = [{"role": "user", "content": brief}]
    tools_called: list[str] = []
    files_written: list[str] = []
    final_text = ""
    rounds = 0

    for round_idx in range(_HARVEST_MAX_ROUNDS):
        rounds = round_idx + 1
        try:
            response = await chat_completion_with_tools(
                messages=messages,
                system=system_prompt,
                tools=tools,
                model=_HARVEST_MODEL,
                max_tokens=_HARVEST_MAX_TOKENS,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("[HARVEST] LLM call failed round=%d: %s", rounds, exc)
            return {
                "success": False, "error": "llm_call_failed", "message": str(exc),
                "rounds_used": rounds, "files_written": files_written,
            }

        # Telemetry (unified cost ledger, ADR-291; attributed per ADR-373/445).
        from services.supabase import resolve_principal_id
        _record_harvest_cost(user_id, response, rounds, resolve_principal_id(auth))

        # Reconstruct the assistant turn as dict-shaped content (round-trip
        # tool_use blocks back to the API).
        if response.tool_uses:
            assistant_content: list[dict] = []
            for block in (response.content or []):
                btype = getattr(block, "type", None)
                if btype == "text":
                    assistant_content.append({"type": "text", "text": getattr(block, "text", "")})
                elif btype == "tool_use":
                    assistant_content.append({
                        "type": "tool_use",
                        "id": getattr(block, "id", ""),
                        "name": getattr(block, "name", ""),
                        "input": getattr(block, "input", {}),
                    })
            messages.append({"role": "assistant", "content": assistant_content})
        else:
            final_text = (response.text or "").strip()
            messages.append({"role": "assistant", "content": final_text})

        if response.stop_reason != "tool_use" or not response.tool_uses:
            break  # agent produced its closing note — terminal

        tool_results: list[dict] = []
        for tu in response.tool_uses:
            tname = tu.name or ""
            tinput = tu.input or {}
            tools_called.append(tname)
            try:
                result = await executor(tname, tinput)
            except Exception as exc:  # noqa: BLE001
                result = {"success": False, "error": "tool_raised", "message": str(exc)}
            if tname == "WriteFile" and result.get("success"):
                path = (tinput.get("path") or result.get("path") or "").strip()
                if path:
                    files_written.append(path)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id or "",
                "content": _stringify_tool_result(result),
            })
        messages.append({"role": "user", "content": tool_results})
    else:
        logger.warning(
            "[HARVEST] user=%s exhausted %d rounds without terminal text",
            user_id[:8], _HARVEST_MAX_ROUNDS,
        )

    logger.info(
        "[HARVEST] user=%s sources=%d rounds=%d files=%d",
        user_id[:8], len(sources), rounds, len(files_written),
    )
    return {
        "success": True,
        "files_written": files_written,
        "rounds_used": rounds,
        "tools_called": tools_called,
        "summary": final_text or f"Harvested {len(files_written)} file(s) from {len(sources)} source(s).",
    }


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


def _normalize_sources(scope: dict) -> list[dict]:
    """Validate + normalize the picker's ephemeral scope into source dicts."""
    if not isinstance(scope, dict):
        return []
    raw = scope.get("sources")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for s in raw:
        if not isinstance(s, dict):
            continue
        provider = (s.get("provider") or "").strip().lower()
        if provider not in _LIST_TOOL:
            continue
        out.append({
            "provider": provider,
            "id": (s.get("id") or "").strip() or None,
            "label": (s.get("label") or "").strip() or None,
            "range_days": _safe_int(s.get("range_days")),
        })
    return out


def _safe_int(v: Any) -> int | None:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _count_from_list_result(provider: str, res: dict) -> int:
    """Pull an item count out of a list tool's result shape. Tolerant."""
    if not isinstance(res, dict):
        return 0
    result = res.get("result") or {}
    if not isinstance(result, dict):
        return 0
    if provider == "slack":
        return int(result.get("count") or len(result.get("channels") or []) or 0)
    if provider == "notion":
        # notion_search returns a results array
        return len(result.get("results") or result.get("pages") or [])
    if provider == "github":
        return len(result.get("repos") or result.get("repositories") or [])
    # Generic fallback: any list-valued field
    for v in result.values():
        if isinstance(v, list):
            return len(v)
    return 0


def _capabilities_for_sources(sources: list[dict]) -> list[str]:
    """Map picked providers → the read capabilities harvest needs.

    The connected-platform gate in get_platform_tools_for_agent ensures only
    actually-connected providers surface their tools; this just declares the
    intent so the capability resolver includes them.
    """
    caps: set[str] = set()
    cap_for = {"slack": "read_slack", "notion": "read_notion", "github": "read_github"}
    for s in sources:
        c = cap_for.get(s["provider"])
        if c:
            caps.add(c)
    return sorted(caps)


def _available_context_domains(client: Any, user_id: str) -> list[str]:
    """List the context domains the harvest can route into (ADR-331 §5).

    Reads the kernel + active-bundle context domains (directory_registry).
    The harvest prompt names these so the LLM routes pieces correctly rather
    than inventing domains. user_id is accepted for signature stability but
    list_directories is workspace-agnostic at the registry layer (kernel +
    all active bundles); per-workspace bundle scoping is a refine-later
    concern (the LLM only routes into the named set either way).
    """
    try:
        from services.directory_registry import list_directories
        domains = list_directories(dir_type="context")
        keys = [d.get("key") for d in domains if d.get("key")]
        # Normalize bundle keys like "operation/customers" → leaf "customers"
        # so the prompt's slug guidance stays consistent.
        return sorted({str(k).rsplit("/", 1)[-1] for k in keys}) or _FALLBACK_DOMAINS
    except Exception:
        return _FALLBACK_DOMAINS


def _compose_harvest_prompt(available_domains: list[str]) -> str:
    """The harvest agent's system frame — curate, route, attribute (ADR-331)."""
    domains_line = ", ".join(available_domains) if available_domains else "(none declared yet)"
    return (
        "You are the workspace's harvest agent. Your one job: bring the "
        "operator's pre-YARNNN reality into the workspace as CURATED, attributed "
        "substrate — not a raw dump.\n\n"
        "Discipline (ADR-331):\n"
        "- READ the named sources with the platform read tools available to you.\n"
        "- CURATE: keep what carries durable signal (decisions, commitments, "
        "facts, relationships, open threads). Drop noise (chatter, acks, bot "
        "messages, ephemeral coordination).\n"
        "- ROUTE each kept piece into the RIGHT context domain. Available "
        f"domains: {domains_line}. Write to "
        "/workspace/operation/context/{domain}/{descriptive-slug}.md. Do NOT "
        "invent domains outside the available set.\n"
        "- SUMMARIZE in the operator's interest: a harvested file is a distilled "
        "note, not a transcript paste. One file per coherent topic/entity, not "
        "one file per message.\n"
        "- WRITE via WriteFile. Every write is attributed agent:harvest and "
        "dated automatically — you do not set attribution.\n"
        "- When you have curated and written everything worth keeping, STOP and "
        "produce a one-paragraph closing note: what you brought in, into which "
        "domains, and anything you deliberately skipped.\n\n"
        "You are not a judgment seat. You do not propose actions or change "
        "governance. You read, curate, and write context. Nothing else."
    )


def _compose_harvest_brief(sources: list[dict], available_domains: list[str]) -> str:
    """The per-run brief naming the picked sources + ranges (ephemeral scope)."""
    lines = ["Harvest these sources into curated context substrate:\n"]
    for s in sources:
        rng = f" (last {s['range_days']} days)" if s.get("range_days") else ""
        label = s.get("label") or s.get("id") or "(unnamed)"
        lines.append(f"- {s['provider']}: {label}{rng}  [id: {s.get('id')}]")
    lines.append(
        "\nRead each with the appropriate platform read tool, curate, route to "
        "the right domain, and write. Begin."
    )
    return "\n".join(lines)


def _stringify_tool_result(result: Any) -> str:
    import json
    try:
        return json.dumps(result, default=str)[:8000]
    except Exception:
        return str(result)[:8000]


def _record_harvest_cost(
    user_id: str, response: Any, rounds: int, principal_id: Optional[str] = None
) -> None:
    try:
        from services.supabase import get_service_client
        from services.telemetry import record_execution_event
        usage = getattr(response, "usage", None) or {}
        if not isinstance(usage, dict):
            usage = {}
        record_execution_event(
            get_service_client(),
            user_id=user_id,
            # ADR-373/445: attribute the harvest's cost to the principal who
            # asked for it (falls back to user_id upstream when unresolvable).
            principal_id=principal_id,
            slug="agent:harvest",
            mode="judgment",
            trigger_type="addressed",
            status="success",
            tool_rounds=rounds,
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
            cache_read_tokens=int(usage.get("cache_read_input_tokens", 0) or 0),
            cache_create_tokens=int(usage.get("cache_creation_input_tokens", 0) or 0),
            model=_HARVEST_MODEL,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[HARVEST] cost ledger record failed: %s", exc)
