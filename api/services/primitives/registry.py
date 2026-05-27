"""
Primitive Registry — ADR-146: Primitive Hardening

Central registry for all primitives and their handlers.
Two explicit mode registries (P4): CHAT_PRIMITIVES and HEADLESS_PRIMITIVES.

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
from .search import SEARCH_ENTITIES_TOOL, handle_search_entities
from .list import LIST_ENTITIES_TOOL, handle_list_entities
from .web_search import WEB_SEARCH_PRIMITIVE, handle_web_search
from .system_state import GET_SYSTEM_STATE_TOOL, handle_get_system_state
from .coordinator import MANAGE_AGENT_TOOL, handle_manage_agent
# ADR-231 Phase 3.7: ManageTask DELETED. Lifecycle dissolves into
# UpdateContext(target='recurrence', ...) and FireInvocation per D5.
from .fire_invocation import FIRE_INVOCATION_TOOL, handle_fire_invocation
# ADR-235: UpdateContext DISSOLVED. Targets sort into:
#   - Inference-merged writes → InferContext / InferWorkspace
#   - Direct substrate writes  → WriteFile (with scope='workspace', ADR-235 Option A)
#   - Lifecycle action          → ManageRecurrence
from .infer_context import INFER_CONTEXT_TOOL, handle_infer_context
from .infer_workspace import INFER_WORKSPACE_TOOL, handle_infer_workspace
from .schedule import SCHEDULE_TOOL, handle_schedule  # ADR-261 §3 — renamed from ManageRecurrence
from .manage_hook import MANAGE_HOOK_TOOL, handle_manage_hook  # ADR-296 v2 D2 — substrate-event hook lifecycle
from .compose import COMPOSE_TOOL, handle_compose  # ADR-262 D4 — callable primitive wrapping render engine
from .dispatch_specialist import (  # ADR-261 D7 — Reviewer-loop specialist sub-call
    DISPATCH_SPECIALIST_TOOL,
    handle_dispatch_specialist,
)
from .scaffold import MANAGE_DOMAINS_TOOL, handle_manage_domains
from .workspace import (
    READ_FILE_TOOL, handle_read_file,
    WRITE_FILE_TOOL, handle_write_file,
    SEARCH_FILES_TOOL, handle_search_files,
    QUERY_KNOWLEDGE_TOOL, handle_query_knowledge,
    LIST_FILES_TOOL, handle_list_files,
    DISCOVER_AGENTS_TOOL, handle_discover_agents,
    READ_AGENT_FILE_TOOL, handle_read_agent_file,
)
# ADR-209 Phase 3: revision-aware read primitives (Authored Substrate).
from .revisions import (
    LIST_REVISIONS_TOOL, handle_list_revisions,
    READ_REVISION_TOOL, handle_read_revision,
    DIFF_REVISIONS_TOOL, handle_diff_revisions,
)
from .runtime_dispatch import RUNTIME_DISPATCH_TOOL, handle_runtime_dispatch
# ADR-264: substrate-canonical-world primitive — mirrors external state into substrate
# via deterministic Python (no LLM). Dispatched by mechanical-mode recurrences
# per ADR-263 D5 + ADR-264 D2 via the @primitive: ... convention.
from .sync_platform_state import SYNC_PLATFORM_STATE_TOOL, handle_sync_platform_state
# ADR-281: derivative-compaction substrate primitive — mirrors per-signal
# state files into a compact summary substrate file. Mechanical-only
# (not in any LLM tool surface); dispatched by mechanical-mode recurrences.
from .mirror_signal_state import handle_mirror_signal_state
# ADR-301: Reviewer pulse envelope substrate mirrors. Kernel-maintenance
# primitives that project the workspace's `tasks` scheduling index +
# `execution_events` ledger into compact substrate files the Reviewer
# reads at every wake. Dispatched per scheduler tick via
# services.kernel_mirrors (NOT via @primitive: directives — these are
# kernel maintenance, not workspace recurrences). Registered here so the
# canonical HANDLERS map remains the single execute-by-name surface.
from .mirror_schedule_index import handle_mirror_schedule_index
from .mirror_recent_execution import handle_mirror_recent_execution
# ADR-271 Thread A: deterministic trading primitives — dispatched ONLY by the
# mechanical-mode dispatcher via @primitive: directives. Not in CHAT/HEADLESS/
# REVIEWER tool surfaces per ADR-264 D3 (operators don't directly invoke
# mechanical primitives — they author recurrences that name them).
from .track_universe import handle_track_universe
from .track_regime import handle_track_regime
from .repurpose import REPURPOSE_OUTPUT_TOOL, handle_repurpose_output
from .propose_action import (
    PROPOSE_ACTION_TOOL, handle_propose_action,
    EXECUTE_PROPOSAL_TOOL, handle_execute_proposal,
    REJECT_PROPOSAL_TOOL, handle_reject_proposal,
)
from services.platform_tools import (
    is_platform_tool, handle_platform_tool, get_platform_tools_for_agent,
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

CLARIFY_TOOL = {
    "name": "Clarify",
    "description": """Ask the user for input before proceeding.

Use when you need more information or want to offer choices.
Appears as a focused prompt.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question to ask"
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of choices"
            }
        },
        "required": ["question"]
    }
}


async def handle_clarify(auth: Any, input: dict) -> dict:
    """Handle Clarify primitive."""
    question = input.get("question", "")
    options = input.get("options", [])
    return {
        "success": True,
        "question": question,
        "options": options,
        "ui_action": {
            "type": "CLARIFY",
            "data": {"question": question, "options": options},
        },
    }


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
CHAT_PRIMITIVES = [
    # Entity layer (4) + Introspection (1)
    LOOKUP_ENTITY_TOOL,
    LIST_ENTITIES_TOOL,
    SEARCH_ENTITIES_TOOL,
    EDIT_ENTITY_TOOL,
    GET_SYSTEM_STATE_TOOL,
    # File layer (4) — ADR-234 Chat File Layer Reach
    # Workspace-absolute reads/writes/search/list. Chat reaches workspace_files
    # directly so YARNNN can answer content-shape questions about substrate
    # without delegating. Path convention (not primitive gating) keeps chat
    # out of /agents/{slug}/ private paths — see prompts/chat/tools_core.py.
    # QueryKnowledge stays headless-only (semantic-rank composition over
    # context domains; chat reaches that surface via working memory + ReadFile).
    # ReadAgentFile stays headless-only (inter-agent coordination per ADR-116).
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    SEARCH_FILES_TOOL,
    LIST_FILES_TOOL,
    # External (ADR-153: RefreshPlatformContent removed)
    WEB_SEARCH_PRIMITIVE,
    LIST_INTEGRATIONS_TOOL,
    # ADR-235 D1.a: Inference-merged writes — explicit Infer* primitives.
    # Cognitive shape is "LLM merge over text + docs + URLs"; named honestly.
    INFER_CONTEXT_TOOL,
    INFER_WORKSPACE_TOOL,
    # ADR-155: Domain scaffolding (TP-driven)
    MANAGE_DOMAINS_TOOL,
    # Agent lifecycle (1, was 2 pre-ADR-231; ADR-235 D2: action enum drops 'create').
    # No chat-surface pathway for creating user-authored Agents — see ADR-235 R4.
    MANAGE_AGENT_TOOL,
    # ADR-235 D1.c: ManageRecurrence — recurrence-declaration lifecycle.
    # Mirrors ManageAgent / ManageDomains shape.
    SCHEDULE_TOOL,
    # ADR-296 v2 D2: ManageHook — substrate-event hook lifecycle.
    # Sibling to Schedule (recurrences) for the substrate-event wake source.
    MANAGE_HOOK_TOOL,
    # ADR-231 D5: FireInvocation — manual fire of a recurrence declaration.
    # Replaces ManageTask(action="trigger"). All other lifecycle actions
    # (create/update/pause/resume/archive) flow through Schedule.
    FIRE_INVOCATION_TOOL,
    # ADR-262 D4: Compose — callable primitive wrapping render engine.
    # Operator/Reviewer/specialist may direct mid-session composition.
    # Also runs as opt-out structural default at session-close (separate hook).
    COMPOSE_TOOL,
    # ADR-261 D7: DispatchSpecialist — Reviewer's chat-mode loop dispatches
    # focused-prompt specialist sub-LLM-calls (researcher, analyst, writer,
    # tracker, designer, reporting). Identical shape to Claude Code sub-agents.
    DISPATCH_SPECIALIST_TOOL,
    # Repurpose (ADR-148 Phase 4)
    REPURPOSE_OUTPUT_TOOL,
    # Asset rendering (1) — Gemini image gen, charts, mermaid diagrams
    RUNTIME_DISPATCH_TOOL,
    # Approval loop (3) — ADR-193
    PROPOSE_ACTION_TOOL,
    EXECUTE_PROPOSAL_TOOL,
    REJECT_PROPOSAL_TOOL,
    # Interaction (1)
    CLARIFY_TOOL,
    # Authored Substrate — revision-aware reads (ADR-209 Phase 3)
    LIST_REVISIONS_TOOL,
    READ_REVISION_TOOL,
    DIFF_REVISIONS_TOOL,
]  # 27 tools — ADR-296 v2 D2 added ManageHook (substrate-event hook lifecycle)

# Headless mode: background agent execution.
# Base registry only. Provider-native platform tools are added dynamically per
# agent capability bundle via `get_headless_tools_for_agent()`.
HEADLESS_PRIMITIVES = [
    # Entity layer (3) + Introspection (1)
    LOOKUP_ENTITY_TOOL,
    LIST_ENTITIES_TOOL,
    SEARCH_ENTITIES_TOOL,
    GET_SYSTEM_STATE_TOOL,
    # External (ADR-153: RefreshPlatformContent removed)
    WEB_SEARCH_PRIMITIVE,
    # ADR-264: substrate-canonical-world primitive — mirrors external state
    # into substrate via deterministic Python. Primary surface for use in
    # mechanical-mode recurrences (ADR-263); also LLM-callable for the rare
    # case a specialist needs to refresh substrate before reasoning.
    SYNC_PLATFORM_STATE_TOOL,
    # File layer (5)
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    SEARCH_FILES_TOOL,
    QUERY_KNOWLEDGE_TOOL,
    LIST_FILES_TOOL,
    # Inter-agent (2)
    DISCOVER_AGENTS_TOOL,
    READ_AGENT_FILE_TOOL,
    # Lifecycle (ADR-235 D2: ManageAgent action enum drops 'create' — chat parity)
    MANAGE_AGENT_TOOL,
    # ADR-235 D1.c: ManageRecurrence — agents may pause/resume/update their
    # own declarations on outcome signals. Chat parity.
    SCHEDULE_TOOL,
    # ADR-296 v2 D2: ManageHook — substrate-event hook lifecycle. Chat parity.
    MANAGE_HOOK_TOOL,
    # ADR-231 D5: FireInvocation — recurrence-aware dispatch.
    FIRE_INVOCATION_TOOL,
    # ADR-262 D4: Compose — specialists may compose mid-session for handoff.
    COMPOSE_TOOL,
    # ADR-261 D7: DispatchSpecialist — recurrence prompts that orchestrate
    # multi-step specialist sequences may chain sub-calls.
    DISPATCH_SPECIALIST_TOOL,
    MANAGE_DOMAINS_TOOL,
    # Asset rendering — writes to task output folder when task_slug set on auth
    RUNTIME_DISPATCH_TOOL,
    # Approval loop (ADR-193) — headless agents must propose when action is
    # soft/irreversible; autonomous execution without approval is unsafe.
    PROPOSE_ACTION_TOOL,
    # Authored Substrate — revision-aware reads (ADR-209 Phase 3).
    # Agents can inspect prior revisions of their own memory, upstream
    # context domains, or delivered outputs to track their own drift and
    # reason about accumulated change. Chat parity.
    LIST_REVISIONS_TOOL,
    READ_REVISION_TOOL,
    DIFF_REVISIONS_TOOL,
]  # 23 static tools + dynamic platform_* — ADR-296 v2 D2 added ManageHook

# Combined list — for handler registration and backwards compatibility
PRIMITIVES = list({t["name"]: t for t in CHAT_PRIMITIVES + HEADLESS_PRIMITIVES}.values())


# =============================================================================
# ADR-258 (revised 2026-05-08) + ADR-296 v2 D3: REVIEWER_PRIMITIVES — curated subset
# =============================================================================
# The Reviewer is the operator's installed judgment character — personified
# to act on the operator's behalf. Like a human supervisor, the Reviewer:
#   - Reads any report directly (observation is unmediated)
#   - Writes its own notebook (decisions, reflections, notes within /workspace/review/)
#   - Submits proposals for capital actions (ProposeAction)
#   - Asks the operator when in doubt (Clarify)
#
# What the Reviewer does NOT do directly (operator-authorship territory —
# requested via Clarify, surfaced as concern in reasoning, or escalated):
#   - Restructure the operation: ManageDomains, ManageAgent (create/update/archive),
#     InferContext, InferWorkspace
#   - Run asset renders or repurpose deliverables: RuntimeDispatch, RepurposeOutput
#   - Bind execution downstream of someone else's verdict: ExecuteProposal, RejectProposal
#     (the dispatcher executes ExecuteProposal/RejectProposal on Reviewer's verdict —
#      Reviewer doesn't call them itself)
#   - Mutate entity-layer rows: EditEntity (Reviewer reasons against files, not rows)
#
# ADR-296 v2 D3 — FireInvocation REMOVED from REVIEWER_PRIMITIVES.
# The Reviewer's authority is over cadence preference + standing intent; not
# over invoking itself or commissioning unit-of-work fires. When upstream
# substrate is stale, the Reviewer authors:
#   (a) cadence — Schedule the next mechanical mirror's run, or
#   (b) standing intent — update /workspace/review/standing_intent.md to
#       declare interest in the substrate transition that would unblock it.
# It does not dispatch its own next wake by name. FireInvocation remains in
# CHAT_PRIMITIVES for operator-initiated manual fire (operator presence is
# itself a wake-warrant).
#
# What the Reviewer DOES do that is structurally Reviewer-territory (ADR-261 D4):
#   - Schedule its own future wake-ups via Schedule (renamed from ManageRecurrence).
#     A recurrence is a self-scheduled future Reviewer session, so authoring one
#     is the Reviewer's own tool. Structurally safe because every wake-up runs
#     another bounded session that itself passes through AUTONOMY for capital gates.
#
# This is NOT access control — it's *role discipline*. The mechanism is
# explicit allowlist instead of broad chat-mode access. Operator can extend
# via _locks.yaml unlocked_paths if they want a more permissive Reviewer.

REVIEWER_PRIMITIVES = [
    # All read primitives — observation is unmediated (supervisor reads any report)
    READ_FILE_TOOL,
    LIST_FILES_TOOL,
    SEARCH_FILES_TOOL,
    LIST_REVISIONS_TOOL,
    READ_REVISION_TOOL,
    DIFF_REVISIONS_TOOL,
    GET_SYSTEM_STATE_TOOL,
    SEARCH_ENTITIES_TOOL,
    LOOKUP_ENTITY_TOOL,
    LIST_ENTITIES_TOOL,
    LIST_INTEGRATIONS_TOOL,
    WEB_SEARCH_PRIMITIVE,
    QUERY_KNOWLEDGE_TOOL,
    # Self-substrate writes — own notebook (lock check enforces /workspace/review/ + non-locked paths)
    WRITE_FILE_TOOL,
    # ADR-296 v2 D3: FireInvocation REMOVED. Reviewer does not self-invoke.
    # Direction primitive (Reviewer says, System Agent executes)
    PROPOSE_ACTION_TOOL,
    # Self-scheduling (ADR-261 D4) — Reviewer authors its own future wake-ups
    SCHEDULE_TOOL,
    # ADR-296 v2 D3: ManageHook — Reviewer authors substrate-event hooks as
    # part of its standing-intent authority. Declaring interest in a substrate
    # transition is the substrate-event analog of authoring cadence via Schedule.
    MANAGE_HOOK_TOOL,
    # Composition (ADR-262 D4) — Reviewer may direct mid-session composition
    COMPOSE_TOOL,
    # Specialist dispatch (ADR-261 D7) — Reviewer hands focused briefs to
    # researcher / analyst / writer / tracker / designer / reporting roles
    # for production work the Reviewer's context shouldn't carry.
    DISPATCH_SPECIALIST_TOOL,
    # ADR-299 (rewrite 2026-05-27): EMAIL_SEND_TO_OPERATOR_TOOL is
    # deliberately NOT in REVIEWER_PRIMITIVES. Under the rewrite,
    # `platform_email_send_to_operator` is operator-addressing system
    # infrastructure (the system Resend wire, exposed as an LLM-invokable
    # tool via SYSTEM_INFRASTRUCTURE_TOOLS in platform_tools.py). The
    # agent path surfaces it unconditionally via the
    # get_platform_tools_for_capabilities merge; the Reviewer path gates
    # it through REVIEWER_PRIMITIVES (this list). The question of whether
    # the Reviewer should invoke system infrastructure that speaks *as the
    # system* to the operator-identity is open pending the v5 canary
    # outcome — see ADR-299 §"Reviewer authority — open question."
    # Tool absence here is the Path A revert (2026-05-25, Canary v4
    # produced `stand_down` instead of expected `defer`/`reject` —
    # hypothesis A: tool perturbation). If v5 confirms hypothesis A,
    # re-introduction protocol is documented in ADR-299 D8.
    # Substrate refresh (ADR-264) — rare mid-loop case where the Reviewer
    # needs to refresh external state into substrate before judging.
    # Primary use is dispatched by mechanical-mode recurrences; LLM-callable
    # surface here is for the override case.
    SYNC_PLATFORM_STATE_TOOL,
    # Conversation
    CLARIFY_TOOL,
]  # 21 tools — ADR-296 v2 D2 added ManageHook; ADR-299 Discovery 4 reverted Path A 2026-05-25


# =============================================================================
# Handler mapping — all unique handlers
# =============================================================================

HANDLERS: dict[str, Callable] = {
    # Entity layer (ADR-168 Commit 4: renamed from Read/List/Search/Edit)
    "LookupEntity": handle_lookup_entity,
    "EditEntity": handle_edit_entity,
    "SearchEntities": handle_search_entities,
    "ListEntities": handle_list_entities,
    # "Execute": DELETED (ADR-168 Commit 2 — finish ADR-146 Phase 3)
    # "RefreshPlatformContent": DELETED (ADR-153)
    "WebSearch": handle_web_search,
    "GetSystemState": handle_get_system_state,
    "Clarify": handle_clarify,
    "list_integrations": handle_list_integrations,
    "ManageAgent": handle_manage_agent,
    # "CreateTask": DELETED (ADR-168 Commit 3 — folded into ManageTask action="create")
    # "ManageTask": DELETED (ADR-231 Phase 3.7 — replaced by ManageRecurrence + FireInvocation per D5)
    # "UpdateContext": DELETED (ADR-235 — dissolved into InferContext / InferWorkspace / ManageRecurrence / WriteFile scope='workspace')
    # ADR-231 D5: FireInvocation — recurrence-aware dispatch.
    "FireInvocation": handle_fire_invocation,
    # ADR-235 D1.a: Inference-merged writes
    "InferContext": handle_infer_context,
    "InferWorkspace": handle_infer_workspace,
    # ADR-235 D1.c: Lifecycle management for recurrence declarations
    "Schedule": handle_schedule,
    # ADR-296 v2 D2: Substrate-event hook lifecycle
    "ManageHook": handle_manage_hook,
    # ADR-262 D4: Compose — callable primitive wrapping render engine
    "Compose": handle_compose,
    # ADR-261 D7: DispatchSpecialist — Reviewer-loop sub-LLM-call
    "DispatchSpecialist": handle_dispatch_specialist,
    # ADR-264: SyncPlatformState — substrate-canonical-world primitive
    # (mirrors external state into substrate; primary surface for use in
    # mechanical-mode recurrences per ADR-263).
    "SyncPlatformState": handle_sync_platform_state,
    # ADR-281: MirrorSignalState — derivative-compaction substrate primitive
    # (projects per-signal substrate into a compact summary substrate file
    # so the Reviewer's wake envelope reads substrate instead of computing
    # at prompt-assembly time per Derived Principle 19). Mechanical-only;
    # not in any LLM tool surface.
    "MirrorSignalState": handle_mirror_signal_state,
    # ADR-301: Reviewer pulse envelope mirrors. Kernel maintenance —
    # dispatched per scheduler tick via services.kernel_mirrors, not via
    # @primitive: directives. Not in any LLM tool surface.
    "MirrorScheduleIndex": handle_mirror_schedule_index,
    "MirrorRecentExecution": handle_mirror_recent_execution,
    # ADR-271 Thread A: trading-specific deterministic primitives.
    # Fetch-plus-compute pattern that SyncPlatformState's pure-mirror shape
    # doesn't cover (multi-bar walk + derived indicator math). ADR-264
    # §"Reconciliation half" reserved this primitive class. Dispatcher-only
    # surface; not LLM-callable.
    "TrackUniverse": handle_track_universe,
    "TrackRegime": handle_track_regime,
    "ManageDomains": handle_manage_domains,
    # File layer (ADR-168 Commit 4: renamed from ReadWorkspace/WriteWorkspace/etc.)
    "ReadFile": handle_read_file,
    "WriteFile": handle_write_file,
    "SearchFiles": handle_search_files,
    "QueryKnowledge": handle_query_knowledge,
    "ListFiles": handle_list_files,
    "DiscoverAgents": handle_discover_agents,
    "ReadAgentFile": handle_read_agent_file,
    "RuntimeDispatch": handle_runtime_dispatch,
    "RepurposeOutput": handle_repurpose_output,
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
_CHAT_TOOL_NAMES = {t["name"] for t in CHAT_PRIMITIVES}
_HEADLESS_TOOL_NAMES = {t["name"] for t in HEADLESS_PRIMITIVES}


async def execute_primitive(auth: Any, name: str, input: dict) -> dict:
    """
    Execute a primitive by name.

    ADR-050: Platform tools (platform_*) are routed to MCP Gateway.
    """
    if is_platform_tool(name):
        try:
            return await handle_platform_tool(auth, name, input)
        except Exception as e:
            return {
                "success": False,
                "error": "platform_tool_error",
                "message": str(e),
                "tool": name,
            }

    handler = HANDLERS.get(name)
    if not handler:
        return {
            "success": False,
            "error": "unknown_primitive",
            "message": f"Unknown primitive: {name}",
            "available": list(HANDLERS.keys()),
        }

    try:
        return await handler(auth, input)
    except Exception as e:
        return {
            "success": False,
            "error": "execution_error",
            "message": str(e),
            "primitive": name,
        }


def get_tools_for_mode(mode: str) -> list[dict]:
    """
    Get tool definitions for a specific mode.

    ADR-146: Returns from explicit registries, not filtered from a combined list.
    """
    if mode == "chat":
        return list(CHAT_PRIMITIVES)
    elif mode == "headless":
        return list(HEADLESS_PRIMITIVES)
    else:
        return list(CHAT_PRIMITIVES)  # Default to chat


class HeadlessAuth:
    """Minimal auth context for headless execution.

    ADR-288 D1: ``caller_identity`` carries the ADR-209 attribution string
    for substrate writes performed through this auth. Headless callers are
    specialist sub-LLM dispatches (per ADR-261 D7 DispatchSpecialist);
    caller_identity defaults to ``f"specialist:{role}"`` when an agent
    context with a role is available, else ``"specialist:unknown"`` as a
    telemetry tripwire (logged by the substrate primitive on use). Note:
    specialist writes that the primitive itself asserts (e.g., output-folder
    writes carrying a more specific authored_by) override this default.
    """

    def __init__(
        self,
        client,
        user_id,
        agent_sources=None,
        coordinator_agent_id=None,
        agent=None,
        task_slug=None,
    ):
        self.client = client
        self.user_id = user_id
        self.headless = True
        self.agent_sources = agent_sources
        self.coordinator_agent_id = coordinator_agent_id
        self.agent = agent
        self.task_slug = task_slug
        self.pending_renders: list[dict] = []
        if agent:
            from services.workspace import get_agent_slug
            self.agent_slug = get_agent_slug(agent)
        else:
            self.agent_slug = None

        # ADR-288 D1: caller_identity derived from agent role when present.
        role = (agent or {}).get("role") if isinstance(agent, dict) else None
        self.caller_identity = f"specialist:{role}" if role else "specialist:unknown"


async def get_headless_tools_for_agent(
    client: Any,
    user_id: str,
    agent: Optional[dict] = None,
    agent_sources: Optional[list] = None,
    coordinator_agent_id: Optional[str] = None,
    task_required_capabilities: Optional[list[str]] = None,
) -> list[dict]:
    """
    Resolve the full headless tool surface for an agent.

    Headless execution always gets the base primitive registry. Platform tools
    are added dynamically when, and only when:
    1. the agent's role bundle grants them, OR (per ADR-227) the recurrence's
       `required_capabilities:` block declares them (YAML recurrence body per
        ADR-231 / ADR-261), AND
    2. the user has the provider connected.

    The two sources merge: roles declare universal identity (ADR-176),
    recurrences declare ICP-specific needs (ADR-188 + ADR-207 P4b). Without
    the merge, universal-role agents on program-specific recurrences never
    receive program-specific platform tools.
    """
    tools = list(HEADLESS_PRIMITIVES)
    if not client or not user_id or not agent:
        return tools

    auth = HeadlessAuth(client, user_id, agent_sources, coordinator_agent_id, agent)
    platform_tools = await get_platform_tools_for_agent(
        auth, agent, task_required_capabilities=task_required_capabilities,
    )
    if platform_tools:
        tools.extend(platform_tools)
    return tools


def create_headless_executor(
    client: Any,
    user_id: str,
    agent_sources: Optional[list] = None,
    coordinator_agent_id: Optional[str] = None,
    agent: Optional[dict] = None,
    dynamic_tools: Optional[list[dict]] = None,
    task_slug: Optional[str] = None,
):
    """
    Create a tool executor function for headless mode.

    Returns an async callable (tool_name, tool_input) -> result_dict
    that dispatches to primitive handlers with headless-appropriate
    error handling (log + return error dict, never raise).
    """
    auth = HeadlessAuth(client, user_id, agent_sources, coordinator_agent_id, agent, task_slug=task_slug)
    allowed_tool_names = set(_HEADLESS_TOOL_NAMES)
    if dynamic_tools:
        allowed_tool_names.update(tool["name"] for tool in dynamic_tools if tool.get("name"))

    async def executor(tool_name: str, tool_input: dict) -> dict:
        # Headless execution gets the base registry plus capability-scoped
        # platform tools resolved for this agent.
        if tool_name not in allowed_tool_names:
            logger.warning(
                f"[HEADLESS] Tool {tool_name} not available in headless mode, skipping"
            )
            return {
                "success": False,
                "error": "not_available",
                "message": f"Tool {tool_name} is not available in headless mode",
            }

        try:
            return await execute_primitive(auth, tool_name, tool_input)
        except Exception as e:
            logger.error(f"[HEADLESS] Tool {tool_name} failed: {e}")
            return {
                "success": False,
                "error": "execution_error",
                "message": f"Tool execution failed: {e}",
            }

    executor.auth = auth  # type: ignore[attr-defined]
    return executor
