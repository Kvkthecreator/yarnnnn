"""Deep-Link URL Builder — ADR-202 Phase 2.

Single source of truth for cockpit-surface URLs emitted into external
notifications (email / SMS / platform posts). External Channels carry
expository-pointer content per FOUNDATIONS v6.0 Axiom 6 (Channel) and
ADR-202 §4 — a headline + deep-link, not a full-content replacement
UX.

APP_URL env var is the base. Defaults to `https://yarnnn.com` (prod).
Override in local/dev via APP_URL.

Naming convention (operator-native, per ADR-201):
  /overview  — HOME (Overview surface, ADR-199)
  /team      — roster surface (ADR-201; replaces legacy /agents)
  /work      — tasks (Work surface, ADR-180)
  /context   — filesystem / knowledge browser (ADR-180)
  /review    — Reviewer stream + queue (ADR-200)

All helpers return absolute URLs. Query params are the deep-link
shape (`?focus=queue`, `?since=<iso>`, `?agent=<slug>`). Anchors
were considered and rejected — query params are URL-safe, bookmark-
friendly, and simpler for email clients to preserve through link-
rewriter proxies.
"""

from __future__ import annotations

import os
from typing import Optional
from urllib.parse import quote, urlencode


def app_url() -> str:
    """Return the cockpit base URL (no trailing slash)."""
    return os.environ.get("APP_URL", "https://yarnnn.com").rstrip("/")


def overview_url(
    *,
    focus: Optional[str] = None,
    since: Optional[str] = None,
) -> str:
    """Overview surface (HOME) deep-link.

    Args:
        focus: Optional pane focus. Recognized values per ADR-199:
            "queue" — pending proposals pane
            "alerts" — alert/notification pane
            "performance" — money-truth slice
        since: Optional ISO timestamp — filter to events since.
    """
    params = {}
    if focus:
        params["focus"] = focus
    if since:
        params["since"] = since
    return _build("/overview", params)


def review_url(
    *,
    identity: Optional[str] = None,
    decision: Optional[str] = None,
    since: Optional[str] = None,
    proposal: Optional[str] = None,
) -> str:
    """Review surface (ADR-200) deep-link.

    Args:
        identity: "ai" | "human" | "impersonated" — filter Stream by filler identity.
        decision: "approve" | "reject" | "defer" — filter by decision outcome.
        since: Optional ISO timestamp — filter to decisions since.
        proposal: Optional proposal UUID — scroll to / highlight this proposal.
    """
    params = {}
    if identity:
        params["identity"] = identity
    if decision:
        params["decision"] = decision
    if since:
        params["since"] = since
    if proposal:
        params["proposal"] = proposal
    return _build("/review", params)


def team_url(*, agent: Optional[str] = None) -> str:
    """Team surface (ADR-201) deep-link.

    Args:
        agent: Agent slug — open this agent's detail pane.
    """
    params = {}
    if agent:
        params["agent"] = agent
    return _build("/team", params)


def work_url(
    *,
    task: Optional[str] = None,
    agent: Optional[str] = None,
) -> str:
    """Work surface (ADR-180) deep-link.

    Args:
        task: Task slug — open this task's detail pane.
        agent: Agent slug — pre-filter list by agent.
    """
    params = {}
    if task:
        params["task"] = task
    if agent:
        params["agent"] = agent
    return _build("/work", params)


def context_path_url(path: str) -> str:
    """Context surface pointing at a specific workspace file.

    Example: context_path_url("/workspace/context/_performance_summary.md")
    """
    # path is URL-encoded to preserve slashes + any unusual chars
    return _build("/context", {"path": path})


def context_domain_url(domain: str) -> str:
    """Context surface pointing at a domain folder (e.g., 'trading')."""
    return _build("/context", {"domain": domain})


def chat_url() -> str:
    """Chat surface root — conversation with YARNNN."""
    return _build("/chat", {})


# ---------------------------------------------------------------------------
# internal
# ---------------------------------------------------------------------------


def _build(path: str, params: dict) -> str:
    """Compose base + path + optional query string."""
    base = app_url()
    if not path.startswith("/"):
        path = "/" + path
    if not params:
        return f"{base}{path}"
    # urlencode + quote_via=quote keeps path-like slashes readable when echoed
    qs = urlencode(params, doseq=True, quote_via=quote)
    return f"{base}{path}?{qs}"
