"""
Primitive Registry — ADR-146: Primitive Hardening

Central registry for all primitives and their handlers.
One dispatch table (HANDLERS); the live surfaces declare their own tool sets (ADR-632).

ADR-050: Platform tools are routed via handle_platform_tool.
ADR-080: Mode-gated primitives — chat vs. headless.
ADR-146: Consolidated from 27 → 19 primitives.
ADR-231 Phase 3.7: ManageTask dissolved into ManageRecurrence + FireInvocation.
ADR-235: UpdateContext dissolved into InferContext / InferWorkspace /
ManageRecurrence / WriteFile(scope="workspace"). ManageAgent action enum
tightened — no chat-surface 'create'.
"""

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Imports — only live primitives
# ---------------------------------------------------------------------------
from .read import LOOKUP_ENTITY_TOOL, handle_lookup_entity
from .edit import EDIT_ENTITY_TOOL, handle_edit_entity
from .list import LIST_ENTITIES_TOOL, handle_list_entities
from .web_search import WEB_SEARCH_PRIMITIVE, handle_web_search
# ADR-568 D3: the second kernel-resolved capability (see capabilities.py).
from .generate_image import GENERATE_IMAGE_TOOL, handle_generate_image
# ADR-231 Phase 3.7: ManageTask DELETED. Lifecycle dissolves into
# UpdateContext(target='recurrence', ...) and FireInvocation per D5.
# ADR-235: UpdateContext DISSOLVED. Targets sort into:
#   - Inference-merged writes → InferContext / InferWorkspace
#   - Direct substrate writes  → WriteFile (with scope='workspace', ADR-235 Option A)
#   - Lifecycle action          → ManageRecurrence
# ADR-324: InferContext primitive DELETED (infer_context.py removed). Identity/
# brand authoring is the `context_inference.author_identity` workflow helper
# (MCP path) + inline WriteFile (chat path) — not a primitive.
# ADR-325: Embed — make-AI-ready as an explicit, autonomy-governed step.
from .embed import EMBED_TOOL, handle_embed
# ADR-314 D4: InferWorkspace DELETED. The first-act-scaffold path (ADR-235 D1.a)
# was dissolved by Direction A (bundle-fork is the constitution-creation event,
# no conversational /init); the primitive went invocation-dead when the chat
# agent was removed (ADR-257) and is now removed. (A stale clause here claimed
# InferContext survived "via MCP remember_this" — both are gone: InferContext
# deleted per ADR-324 above; the ADR-169 intent tools deleted per ADR-368. The
# live MCP surface is open/remember/recall/trace per ADR-512.)
# ADR-417 follow-on: DispatchSpecialist NOT imported — removed from the LLM
# registry (its only role, designer, is retired; module stays dormant as a seam).
from .scaffold import MANAGE_DOMAINS_TOOL, handle_manage_domains
from .workspace import (
    READ_FILE_TOOL, handle_read_file,
    WRITE_FILE_TOOL, handle_write_file,
    # ADR-337 — working-tree verbs (the rm/mv/Edit half of the repo analogy;
    # YARNNN names + safety semantics, Claude Code parameter contracts).
    EDIT_FILE_TOOL, handle_edit_file,
    DELETE_FILE_TOOL, handle_delete_file,
    MOVE_FILE_TOOL, handle_move_file,
    DUPLICATE_FILE_TOOL, handle_duplicate_file,
    SEARCH_FILES_TOOL, handle_search_files,
    QUERY_KNOWLEDGE_TOOL, handle_query_knowledge,
    LIST_FILES_TOOL, handle_list_files,
)
# ADR-337 amended (2026-08-21) — the FOLDER verbs: the fan-out half of the
# working-tree analogy. Declared in their own module because they bind a
# SERVICE (`services/folder_organize.py`, the same fan-out the Files surface
# calls) rather than a single `workspace_files` row.
from .folder import (
    DELETE_FOLDER_TOOL, handle_delete_folder,
    MOVE_FOLDER_TOOL, handle_move_folder,
    # Restore — the inverse of the two deletes. Trash-not-erase is only half a
    # contract without it: we shipped `rm` with no Put Back.
    RESTORE_TOOL, handle_restore,
)
# ADR-209 Phase 3: revision-aware read primitives (Authored Substrate).
from .revisions import (
    LIST_REVISIONS_TOOL, handle_list_revisions,
    READ_REVISION_TOOL, handle_read_revision,
    DIFF_REVISIONS_TOOL, handle_diff_revisions,
)
# ADR-417: RuntimeDispatch (render-service asset generation) retired — generation
# is rented, not owned. yarnnn hosts no generation engine.
# ADR-264: substrate-canonical-world primitive — mirrors external state into substrate
# via deterministic Python (no LLM). Dispatched by mechanical-mode recurrences
# per ADR-263 D5 + ADR-264 D2 via the @primitive: ... convention.
from .sync_platform_state import SYNC_PLATFORM_STATE_TOOL, handle_sync_platform_state
from .extract_text_from_blob import EXTRACT_TEXT_FROM_BLOB_TOOL, handle_extract_text_from_blob  # ADR-395 — derive text projection from a raw blob
# ADR-281: derivative-compaction substrate primitive — mirrors per-signal
# state files into a compact summary substrate file. Mechanical-only
# (not in any LLM tool surface); dispatched by mechanical-mode recurrences.
# ADR-301: Reviewer pulse envelope substrate mirrors. Kernel-maintenance
# primitives that project the workspace's `tasks` scheduling index +
# `execution_events` ledger into compact substrate files the Reviewer
# reads at every wake. Dispatched per scheduler tick via
# services.kernel_mirrors (NOT via @primitive: directives — these are
# kernel maintenance, not workspace recurrences). Registered here so the
# canonical HANDLERS map remains the single execute-by-name surface.
# ADR-271 Thread A: deterministic trading primitives — dispatched ONLY by the
# mechanical-mode dispatcher via @primitive: directives. Not in CHAT/HEADLESS/
# REVIEWER tool surfaces per ADR-264 D3 (operators don't directly invoke
# mechanical primitives — they author recurrences that name them).
from .track_universe import handle_track_universe
from .track_regime import handle_track_regime
# ADR-336 (enacts ADR-335 D7): generic web/RSS standing-watch transport.
from .track_web_sources import handle_track_web_sources
# ADR-335 Crawl-B Increment B (enacts ADR-335 D4/D5): generic MCP-transport
# standing-watch executor (the first binding reads a repo via GitHub MCP).
from .propose_action import (
    PROPOSE_ACTION_TOOL, handle_propose_action,
    EXECUTE_PROPOSAL_TOOL, handle_execute_proposal,
    REJECT_PROPOSAL_TOOL, handle_reject_proposal,
)
from services.platform_tools import (
    is_platform_tool, handle_platform_tool, get_platform_tools_for_agent,
    is_consequential_platform_tool, consequential_platform_family,
)

# ---------------------------------------------------------------------------
# Deleted imports (ADR-146 — absorbed into UpdateContext / ManageTask):
# - save_memory.py → UpdateContext(target="memory")
# - shared_context.py → UpdateContext(target="identity"|"brand")
# - workspace.py: WRITE_AGENT_FEEDBACK_TOOL → UpdateContext(target="agent")
# - workspace.py: WRITE_TASK_FEEDBACK_TOOL → UpdateContext(target="task")
# - task.py: TRIGGER_TASK_TOOL → ManageTask(action="trigger")
# - task.py: UPDATE_TASK_TOOL → ManageTask(action="update")
# - task.py: PAUSE_TASK_TOOL → ManageTask(action="pause")
# - task.py: RESUME_TASK_TOOL → ManageTask(action="resume")
#
# Deleted imports (ADR-168 Commit 2 — finish ADR-146 Phase 3):
# - execute.py → Execute primitive dissolved entirely
#     agent.generate    → ManageTask(task_slug=..., action="trigger")
#     agent.acknowledge → UpdateContext(target="agent", agent_slug=..., text=...)
#     platform.publish  → delivery is a task property (ManageTask update)
#     agent.schedule    → ManageTask(task_slug=..., action="update", schedule=...)
#
# Deleted imports (ADR-168 Commit 3 — CreateTask folded into ManageTask):
# - task.py → CreateTask primitive dissolved entirely
#     CreateTask(title=..., type_key=..., ...) →
#       ManageTask(action="create", title=..., type_key=..., ...)
#   Symmetric with ManageAgent which already covers agent creation.
# ---------------------------------------------------------------------------


# =============================================================================
# Inline tool definitions (small enough to live here)
# =============================================================================

LIST_INTEGRATIONS_TOOL = {
    "name": "list_integrations",
    "description": """List the user's connected platform integrations and their metadata.

Call this first when about to use a platform tool, to get:
- Which platforms are active (slack, notion, github, commerce, trading)
- Slack: authed_user_id — use as channel_id when sending DMs to self
- Trading: provider, paper mode, account_number
- Notion: designated_page_id — use as page_id when writing to user's YARNNN page

AGENTIC BEHAVIOR: Don't ask "are you connected to Slack?" — call list_integrations and find out.
If not connected, suggest connecting in Settings.""",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}


async def handle_list_integrations(auth: Any, input: dict) -> dict:
    """List user's connected platform integrations."""
    result = auth.client.table("platform_connections")\
        .select("id, platform, status, metadata, created_at, updated_at")\
        .eq("user_id", auth.user_id)\
        .execute()

    integrations = result.data or []
    items = []
    for i in integrations:
        metadata = i.get("metadata") or {}
        item = {
            "platform": i["platform"],
            "status": i["status"],
            "connected_at": i["created_at"],
            "last_updated": i["updated_at"],
            "workspace_name": metadata.get("team_name") or metadata.get("workspace_name"),
            "email": metadata.get("email"),
        }
        if i["platform"] == "slack" and metadata.get("authed_user_id"):
            item["authed_user_id"] = metadata["authed_user_id"]
        if i["platform"] == "notion" and metadata.get("designated_page_id"):
            item["designated_page_id"] = metadata["designated_page_id"]
        if i["platform"] == "commerce":
            item["provider"] = metadata.get("provider", "")
            item["store_name"] = metadata.get("store_name", "")
        if i["platform"] == "trading":
            item["provider"] = metadata.get("provider", "")
            item["paper"] = metadata.get("paper", True)
            item["account_number"] = metadata.get("account_number", "")
        if str(i["platform"]).startswith("mcp:"):
            # ADR-635 — an ATTACHED connector: the inventory names the server
            # and how much of it the member exposed. Seeing it is still not
            # reaching it: only tools in the aperture are on the surface.
            aperture = metadata.get("aperture") or {}
            item["kind"] = "attached"
            item["title"] = metadata.get("title") or metadata.get("name")
            item["server_url"] = metadata.get("server_url")
            item["category"] = metadata.get("category")
            item["tools_exposed"] = sorted(
                t for t, m in aperture.items() if m in ("direct", "propose")
            )
        items.append(item)

    return {
        "success": True,
        "integrations": items,
        "count": len(items),
    }


# =============================================================================
# ADR-146: Explicit Mode Registries (P4)
# =============================================================================

# Chat mode: YARNNN-the-orchestration-surface in user-facing conversation.
# ADR-632: the three LLM tool ROSTERS (CHAT_PRIMITIVES / HEADLESS_PRIMITIVES /
# FREDDIE_PRIMITIVES) and `get_tools_for_mode` are DELETED with the steward —
# they were its tool declarations. The two live LLM surfaces declare their own
# sets from this module's tool constants: `services/lane_runner.LANE_TOOL_NAMES`
# (+ `LANE_SURFACE_EXTRA`) and `mcp_server` (`_INTEROP_VERBS`). HANDLERS below
# is the dispatch table `execute_primitive` reads for every surface.

#: Every tool definition this module holds — the dispatch-side list the
#: package re-exports (`services.primitives.PRIMITIVES`) and the gates read to
#: check that every declared tool has a handler and a permission class. It is
#: NOT an LLM surface (ADR-632: the rosters that were are deleted); the lane and
#: interop surfaces pick their names from `lane_runner.LANE_TOOL_NAMES` and
#: `mcp_server._INTEROP_VERBS`. Derived from the module's `*_TOOL` constants so
#: a new tool cannot be declared and forgotten here.
PRIMITIVES: list[dict] = list({
    v["name"]: v
    for k, v in list(globals().items())
    if k.endswith("_TOOL") and isinstance(v, dict) and v.get("name")
}.values())


HANDLERS: dict[str, Callable] = {
    # Entity layer (ADR-168 Commit 4: renamed from Read/List/Search/Edit)
    "LookupEntity": handle_lookup_entity,
    "EditEntity": handle_edit_entity,
    "ListEntities": handle_list_entities,
    # "Execute": DELETED (ADR-168 Commit 2 — finish ADR-146 Phase 3)
    # "RefreshPlatformContent": DELETED (ADR-153)
    "WebSearch": handle_web_search,
    "GenerateImage": handle_generate_image,
    "list_integrations": handle_list_integrations,
    # "CreateTask": DELETED (ADR-168 Commit 3 — folded into ManageTask action="create")
    # "ManageTask": DELETED (ADR-231 Phase 3.7 — replaced by ManageRecurrence + FireInvocation per D5)
    # "UpdateContext": DELETED (ADR-235 — dissolved into InferContext / InferWorkspace / ManageRecurrence / WriteFile scope='workspace')
    # ADR-231 D5: FireInvocation — recurrence-aware dispatch.
    # "InferContext": DELETED (ADR-324 — dissolved; identity/brand authoring is
    # context_inference.author_identity (MCP) + inline WriteFile (chat))
    # ADR-235 D1.c: Lifecycle management for recurrence declarations
    # ADR-296 v2 D2: Substrate-event hook lifecycle
    # ADR-262 D4: Compose — callable primitive wrapping render engine
    # ADR-264: SyncPlatformState — substrate-canonical-world primitive
    # (mirrors external state into substrate; primary surface for use in
    # mechanical-mode recurrences per ADR-263).
    "SyncPlatformState": handle_sync_platform_state,
    # ADR-395: ExtractTextFromBlob — derive a model-consumable text projection
    # from a retained raw blob, citing the raw via derived_from (DP34). Runs
    # inline on upload arrival (zero-LLM); the derive-registry's first entry.
    "ExtractTextFromBlob": handle_extract_text_from_blob,
    # ADR-281: MirrorSignalState — derivative-compaction substrate primitive
    # (projects per-signal substrate into a compact summary substrate file
    # so the Reviewer's wake envelope reads substrate instead of computing
    # at prompt-assembly time per Derived Principle 19). Mechanical-only;
    # not in any LLM tool surface.
    # ADR-301: Reviewer pulse envelope mirrors. Kernel maintenance —
    # dispatched per scheduler tick via services.kernel_mirrors, not via
    # @primitive: directives. Not in any LLM tool surface.
    # ADR-271 Thread A: trading-specific deterministic primitives.
    # Fetch-plus-compute pattern that SyncPlatformState's pure-mirror shape
    # doesn't cover (multi-bar walk + derived indicator math). ADR-264
    # §"Reconciliation half" reserved this primitive class. Dispatcher-only
    # surface; not LLM-callable.
    "TrackUniverse": handle_track_universe,
    "TrackRegime": handle_track_regime,
    # ADR-336 (enacts ADR-335 D7): the generic web/RSS standing-watch
    # transport — fetches declared sources (_sources.yaml), distills
    # deterministically into signal substrate per the ADR-335 D3 observation
    # contract. Program-agnostic: paths arrive as directive kwargs
    # (declaration= / distills_to=). Dispatcher-only; not LLM-callable.
    "TrackWebSources": handle_track_web_sources,
    # ADR-335 Crawl-B Increment B (enacts ADR-335 D4/D5): the generic
    # MCP-transport standing-watch executor — reads declared foreign-source
    # paths (_repo_sources.yaml) through a watch-bound MCP connection, distills
    # into signal substrate per the D3 observation contract. Every foreign call
    # routes through the metered executor (read_foreign_tool). First binding:
    # repo file reads via GitHub MCP get_file_contents. Dispatcher-only; not
    # LLM-callable.
    "ManageDomains": handle_manage_domains,
    # File layer (ADR-168 Commit 4: renamed from ReadWorkspace/WriteWorkspace/etc.)
    "ReadFile": handle_read_file,
    "WriteFile": handle_write_file,
    # ADR-337 — working-tree verbs
    "EditFile": handle_edit_file,
    "DeleteFile": handle_delete_file,
    "MoveFile": handle_move_file,
    "DeleteFolder": handle_delete_folder,
    "MoveFolder": handle_move_folder,
    "Restore": handle_restore,
    "DuplicateFile": handle_duplicate_file,
    "SearchFiles": handle_search_files,
    "QueryKnowledge": handle_query_knowledge,
    "ListFiles": handle_list_files,
    # ADR-325: Embed — explicit make-AI-ready (consequential, gate-queueable).
    "Embed": handle_embed,
    # ADR-193: Approval loop
    "ProposeAction": handle_propose_action,
    "ExecuteProposal": handle_execute_proposal,
    "RejectProposal": handle_reject_proposal,
    # ADR-209 Phase 3: Authored Substrate revision-aware reads
    "ListRevisions": handle_list_revisions,
    "ReadRevision": handle_read_revision,
    "DiffRevisions": handle_diff_revisions,
}


# =============================================================================
# ADR-146: Mode-aware tool resolution (replaces PRIMITIVE_MODES dict)
# =============================================================================

# Derived from explicit registries — no separate PRIMITIVE_MODES dict to drift


def _platform_write_preview(name: str, input: dict) -> dict:
    """A compact, operator-legible effect preview for an external-write
    proposal's decision_context. Family-shaped (external-write): the WHO + the
    WHAT, never a file diff. Strips dispatch-layer underscore keys."""
    visible = {k: v for k, v in (input or {}).items() if not k.startswith("_")}
    if name.startswith("mcp__"):
        # ADR-635 — an attached connector's call: server + tool + the
        # arguments the member is approving, in the external-write shape the
        # queue card already renders (title + preview).
        from services.attached_connectors import write_preview
        return write_preview(name, input)
    if name == "platform_slack_send_to_channel":
        return {
            "channel": visible.get("channel_id") or visible.get("channel"),
            "preview": (visible.get("text") or "")[:280],
        }
    if name == "platform_notion_create_page":
        return {
            "parent": visible.get("parent_page_id") or visible.get("parent"),
            "title": visible.get("title"),
            "preview": (visible.get("content") or "")[:280],
        }
    if name == "platform_notion_append_block":
        return {
            "page": visible.get("page_id") or visible.get("block_id"),
            "preview": (visible.get("content") or visible.get("text") or "")[:280],
        }
    if name in ("platform_email_send", "platform_email_send_bulk"):
        return {
            "to": visible.get("to") or visible.get("recipients"),
            "subject": visible.get("subject"),
            "preview": (visible.get("body") or visible.get("text") or "")[:280],
        }
    return {k: v for k, v in visible.items()}


def _write_effect_preview(auth: Any, name: str, input: dict) -> dict:
    """The effect preview for an external-write proposal. An ATTACHED
    connector's call (ADR-635) resolves the SERVER tool name through the
    member's row, so the queue card names what will actually run — not the
    lane's derived `mcp__…` handle."""
    if name.startswith("mcp__"):
        from services.attached_connectors import write_preview

        return write_preview(
            name, input,
            client=getattr(auth, "client", None), user_id=getattr(auth, "user_id", None),
        )
    return _platform_write_preview(name, input)


async def _enqueue_platform_write_proposal(
    auth: Any, name: str, input: dict, reason: str
) -> dict:
    """ADR-307 (2026-06-19): a consequential platform write the uniform gate
    ruled QUEUE becomes a family-shaped action_proposals row. ONE gate
    decision, family-shaped enqueue — never one queue forcing every effect into
    a file-diff shape.

      capital        — trading/commerce money movers. decision_context carries
                       {rationale, expected_effect, reversibility,
                       risk_warnings} so the cockpit renders the order-ticket
                       card and the outcome reconciler keys identically to a
                       ProposeAction-originated capital proposal. (In practice
                       the capital path reaches the broker via ProposeAction →
                       ExecuteProposal; this branch is the safety floor for any
                       non-proposal direct capital call under bounded/manual.)
      external-write — audience-addressing sends. decision_context carries the
                       effect preview (channel/recipient/title + content
                       preview) — the operator approves a *send*, not a diff.

    On approve, ExecuteProposal replays execute_primitive(name, inputs) with
    `_proposal_id` injected — recognized by the gate as an approved replay and
    applied without re-gating (no loop).
    """
    from .propose_action import enqueue_gated_action, build_trading_expected_effect

    family = consequential_platform_family(name) or "external-write"
    source = getattr(auth, "caller_identity", "") or None
    task_slug = getattr(auth, "task_slug", None)
    agent_slug = getattr(auth, "agent_slug", None)

    if family == "capital":
        # action_type label for audit/reconciler continuity (the platform-tool
        # primitive name minus the `platform_<provider>_` prefix, dotted).
        parts = name.split("_", 2)  # platform / provider / verb
        provider = parts[1] if len(parts) > 1 else ""
        verb = parts[2] if len(parts) > 2 else name
        action_type = f"{provider}.{verb}"
        decision_context = {
            "rationale": input.get("rationale") or f"Gated {action_type} ({reason}).",
            "expected_effect": (
                build_trading_expected_effect(action_type, input)
                if provider == "trading"
                else f"{action_type}: {_platform_write_preview(name, input)}"
            ),
            "reversibility": "irreversible",
            "risk_warnings": [],
            "gate_reason": reason,
        }
        ttl_hours = 1  # capital family: short TTL (matches DEFAULT_TTL_HOURS)
    else:
        decision_context = {
            "effect": _write_effect_preview(auth, name, input),
            "gate_reason": reason,
        }
        ttl_hours = 6  # external-write: soft-reversible default window

    enq = await enqueue_gated_action(
        auth,
        primitive=name,
        inputs=input,
        family=family,
        decision_context=decision_context,
        source=source,
        task_slug=task_slug,
        agent_slug=agent_slug,
        ttl_hours=ttl_hours,
    )
    if not enq.get("success"):
        return {"success": False, "error": "queue_failed", "message": str(enq), "primitive": name}
    return {
        "success": True,
        "queued": True,
        "proposal_id": enq["proposal_id"],
        "family": family,
        "message": (
            f"{name} requires operator approval under the current autonomy mode "
            f"({reason}). Queued as a {family} proposal — the operator approves "
            f"it from the cockpit. The action runs on approval."
        ),
        "primitive": name,
    }


async def _enqueue_substrate_proposal(auth: Any, name: str, input: dict, reason: str) -> dict:
    """ADR-307 D4: a Reviewer consequential call the gate ruled QUEUE becomes a
    family='substrate' action_proposals row. The operator approves later; on
    approve, ExecuteProposal replays execute_primitive(name, input).

    decision_context is family-shaped (substrate): {diff, message}. The diff
    previews the pending change (best-effort — current vs proposed content for a
    WriteFile); the message is the write's intent. The Reviewer's full reasoning
    lives in its concurrent judgment_log/standing_intent; reversibility is a
    property of the substrate layer (ADR-209 retains every revision), not a
    per-action field.

    source="reviewer:<occupant>" so the reactive dispatcher skips re-judging
    the Reviewer's own queued write (ADR-307 D6 — closes the self-wake loop).
    """
    from .propose_action import enqueue_gated_action

    # Build the substrate decision_context. For WriteFile, preview a diff.
    decision_context: dict = {"gate_reason": reason}
    message = input.get("message") or f"Reviewer {name}"
    if name == "WriteFile":
        from .workspace import _resolve_workspace_path_for_gate
        path = _resolve_workspace_path_for_gate(input) or input.get("path", "")
        proposed = input.get("content", "")
        current = ""
        try:
            from services.workspace import UserMemory
            current = await UserMemory(auth.client, auth.user_id).read(path) or ""
        except Exception:
            current = ""
        decision_context.update({
            "path": path,
            "mode": input.get("mode", "overwrite"),
            "diff": {
                "path": path,
                "before": current,
                "after": (current + ("\n" if current else "") + proposed)
                          if input.get("mode") == "append" else proposed,
            },
            "message": message,
        })
    else:
        decision_context["message"] = message

    caller_identity = getattr(auth, "caller_identity", "") or "reviewer:unknown"
    source = caller_identity if caller_identity.startswith("freddie:") else "reviewer:unknown"

    enq = await enqueue_gated_action(
        auth,
        primitive=name,
        inputs=input,
        family="substrate",
        decision_context=decision_context,
        source=source,
        task_slug=getattr(auth, "task_slug", None),
        agent_slug=getattr(auth, "agent_slug", None),
        ttl_hours=72,  # substrate writes: fixed family TTL (ADR-307 risk #3)
    )
    if not enq.get("success"):
        return {"success": False, "error": "queue_failed", "message": str(enq), "primitive": name}
    return {
        "success": True,
        "queued": True,
        "proposal_id": enq["proposal_id"],
        "message": (
            f"{name} requires operator approval under the current autonomy mode "
            f"({reason}). Queued as a proposal — the operator approves it from "
            f"the cockpit. The write applies on approval."
        ),
        "primitive": name,
    }


async def _run_platform_tool(auth: Any, name: str, input: dict) -> dict:
    """Dispatch a platform tool to its provider handler with uniform error
    shaping. The gate (resolve_permission below) runs BEFORE this for
    consequential platform writes; reads reach here on the fast path."""
    try:
        return await handle_platform_tool(auth, name, input)
    except Exception as e:
        return {
            "success": False,
            "error": "platform_tool_error",
            "message": str(e),
            "tool": name,
        }


async def execute_primitive(auth: Any, name: str, input: dict) -> dict:
    """
    Execute a primitive by name.

    ADR-307 (2026-06-19): the platform-tool path no longer unconditionally
    bypasses the uniform permission gate. Platform READS (and operator-
    addressing infrastructure) keep the fast early-return — they are non-
    consequential and the gate would only add latency. Consequential platform
    WRITES (capital / external-write per `consequential_platform_family`) fall
    through to `resolve_permission` so the autonomy decision is made in the ONE
    place (no primitive hand-rolls its own autonomy branch — submit_order's
    bespoke branch is deleted). On QUEUE the gate routes to the family-shaped
    enqueue (capital → capital proposal; external-write → external-write
    proposal). The operator-approved replay (ExecuteProposal injects
    `_proposal_id`) is recognized and applied without re-gating.
    """
    from .permission import resolve_permission, PermissionDecision

    # ADR-635 D6 — an attached connector's tool. The gate reads the member's
    # aperture: DENY is a refusal the model can read, QUEUE is the existing
    # external-write proposal (the first producer since the steward retired),
    # APPLY reaches the server under the member's own credential.
    from services.attached_connectors import is_attached_tool, run_attached_tool
    if is_attached_tool(name):
        decision, reason = await resolve_permission(auth, name, input)
        if decision == PermissionDecision.DENY:
            return {
                "success": False,
                "error": "attached_tool_denied",
                "message": (
                    f"{name} is not in the member's aperture for that server "
                    f"({reason}). They choose which tools you may call in "
                    "Settings → Connectors; say so rather than retrying."
                ),
                "primitive": name,
            }
        if decision == PermissionDecision.QUEUE:
            return await _enqueue_platform_write_proposal(auth, name, input, reason)
        return await run_attached_tool(auth, name, input)

    if is_platform_tool(name):
        # Reads + operator-addressing infra: never gate (fast path, unchanged).
        if not is_consequential_platform_tool(name):
            return await _run_platform_tool(auth, name, input)
        # Consequential platform write: pass the uniform gate.
        decision, reason = await resolve_permission(auth, name, input)
        if decision == PermissionDecision.DENY:
            return {
                "success": False,
                "error": "governance_locked",
                "message": (
                    f"{name} is not permitted under the current autonomy mode "
                    f"({reason})."
                ),
                "primitive": name,
            }
        if decision == PermissionDecision.QUEUE:
            return await _enqueue_platform_write_proposal(auth, name, input, reason)
        return await _run_platform_tool(auth, name, input)

    handler = HANDLERS.get(name)
    if not handler:
        return {
            "success": False,
            "error": "unknown_primitive",
            "message": f"Unknown primitive: {name}",
            "available": list(HANDLERS.keys()),
        }

    # ADR-307 D1: the single uniform permission gate, above all primitives.
    # Resolves apply / queue / deny from (autonomy × read_only × action_class ×
    # locks) at this one chokepoint — no primitive gates itself.
    from .permission import resolve_permission, PermissionDecision
    decision, reason = await resolve_permission(auth, name, input)
    if decision == PermissionDecision.DENY:
        # ADR-352: a denied Clarify under `autonomous` is the ask-gate telling
        # the seat to ACT, not a governance-locked path. Give it forward
        # guidance (ADR-318: reason forward from a denied call) instead of the
        # path-lock message.
        if name == "Clarify" and reason == "ask_denied:autonomous_default_is_act":
            return {
                "success": False,
                "error": "ask_denied",
                "message": (
                    "Asking is not available under `autonomous` delegation — the "
                    "operator delegated this work to you. Do NOT enumerate options. "
                    "Pick the most disciplined action your framework names and "
                    "execute it (propose, author standing_intent, refresh, research). "
                    "If you genuinely cannot produce what your mandate owes — a "
                    "declared output with no organ to originate it, or a floor/"
                    "mandate change only the operator can authorize (ADR-344 (B)) — "
                    "re-call Clarify with structural_gap=true, naming the missing "
                    "organ. That is the only ask `autonomous` permits."
                ),
                "primitive": name,
            }
        return {
            "success": False,
            "error": "governance_locked",
            "message": (
                f"{name} to a governance-locked path is not permitted "
                f"regardless of autonomy mode ({reason}). The operator authors "
                f"governance directly; surface a Clarify if you need the change."
            ),
            "primitive": name,
        }
    if decision == PermissionDecision.QUEUE:
        # ADR-307 D4: enqueue the gated call as a family='substrate' proposal
        # instead of running it. The operator approves later; on approve,
        # ExecuteProposal replays execute_primitive(name, inputs) with
        # operator/execution auth (not freddie_caller → no re-gate, no loop).
        return await _enqueue_substrate_proposal(auth, name, input, reason)

    try:
        return await handler(auth, input)
    except Exception as e:
        return {
            "success": False,
            "error": "execution_error",
            "message": str(e),
            "primitive": name,
        }


# ─────────────────────────────────────────────────────────────────────────
# ADR-626 D4.b (2026-09-01) — THE HEADLESS-DISPATCH STACK IS DELETED.
# ─────────────────────────────────────────────────────────────────────────
# `HeadlessAuth`, `get_headless_tools_for_agent` and `create_headless_executor`
# lived here (~138 lines) and are gone, with `primitives/dispatch_specialist.py`
# (~545 lines), their only caller.
#
# NOT decayed — SUPERSEDED. The mechanism answered "who does this work?" with a
# ROLE ON A BEING (`role="designer"` / `role="researcher"`), the exact shape
# ADR-596→610 spent five ADRs dismantling. The live answer: capability lives at
# the APP, a declaration names the app (ADR-601, ADR-603 D2), and the being is
# DERIVED — never summoned. ADR-272 narrowed the roles to one, ADR-417's
# follow-on removed that one, `services/harvest.py` (the last direct dispatcher)
# was deleted, and `VALID_SPECIALIST_ROLES` was left the EMPTY SET — so the
# primitive refused on every input.
#
# ⭐ THE TELL, and why this is a delete rather than an evolve: every live
# unattended lane grew its OWN narrow auth instead of reaching for the general
# one sitting right here — strings runs a plain service client through
# `run_bounded_derive_turn`, capture on `_CaptureAuth`, kernel mirrors on
# `_MirrorAuth`. Three independent lanes voted against the abstraction.
#
# ⭐ UNATTENDED WORK IS AXIOMATIC (ADR-603 D1's standing declaration); THIS
# MECHANISM WAS NOT. If mid-task delegation is ever built, extend
# `services/derive_turn.py::run_bounded_derive_turn` — already bounded,
# tool-less, routed, and the path standing work actually runs on.
#
# ⭐⭐ The `specialist:` ATTRIBUTION PREFIX SURVIVES, untouched: live vocabulary
# in `authored_substrate.py`, `narrative.py`, `supabase.py` and
# `platform_credentials.py` (ADR-577 D1.a's agent-caller guard, which keys on
# the PREFIX). A prefix is a VOCABULARY; the class that stamped it was a
# MECHANISM. Only the second went. The two identities it emitted
# (`specialist:{role}` and the `specialist:unknown` tripwire) are pinned by
# `test_adr577_credential_claim.py` §2b, so a future headless caller must stamp
# one of them to be refused a human's token.
# Gates: test_adr626_the_room_is_multi_party.py §6 · test_adr577 §2b4.
