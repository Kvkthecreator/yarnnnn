"""ADR-294 — Operator-Proxy Capability.

The operator's voice materialized as a workspace-agnostic, importable
capability. The same code path drives:
- Internal evaluation (Claude running scenarios)
- Future MCP-as-operator (external LLMs with scoped delegation per ADR-169)
- Future workspace-delegated agents (operator's personal assistant LLM)
- Scripted scenario players for behavioral regression

Public API:
    from services.operator_proxy import OperatorProxy

    proxy = OperatorProxy(user_id, email, caller="claude-sonnet-4-7")

    # Operator's voice via the feed (addressed trigger per ADR-260)
    response = await proxy.send_message("Reviewer, what's your read?")

    # Read what came back (Reviewer + System Agent bubbles)
    messages = await proxy.read_feed(since_message_id=last_seen)

    # Approve/reject proposals (cockpit-Queue equivalent)
    await proxy.approve_proposal(proposal_id, reasoning="...")
    await proxy.reject_proposal(proposal_id, reason="...")

    # Write to substrate as operator (Phase-4 click equivalent — ADR-293 D10)
    await proxy.write_substrate(path, content, message)

    # Inspect (read-only)
    text = await proxy.read_file(path)
    recurrences = await proxy.list_recurrences()
    proposals = await proxy.list_pending_proposals()

Caller-identity discipline per ADR-294 D2:
    Every substrate write through this proxy carries:
        authored_by = f"operator-proxy:{caller}:acting-as-{persona_slug}"

    Where `caller` is the proxy's *real* identity and `persona_slug` (or
    user_id when no persona registered) names the workspace acted upon.
    Examples:
        operator-proxy:claude-sonnet-4-7:acting-as-alpha-trader-2
        operator-proxy:scenario-runner:acting-as-kvk
        operator-proxy:external:chatgpt-5:acting-as-yarnnn-author
"""

from .client import OperatorProxy, ProxyConfig, ProxyError

__all__ = ["OperatorProxy", "ProxyConfig", "ProxyError"]
