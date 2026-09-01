"""
WordPress.com API client (ADR-628 phase (a) — the first outbound tenant).

Speaks the WordPress.com REST API (public-api.wordpress.com/rest/v1.1) with a
member's own OAuth2 bearer token. One client covers wordpress.com sites AND
Jetpack-connected self-hosted sites — the coverage that made WordPress the
first tenant.

Deliberately TWO verbs. `list_sites` answers "where could this publish?"
(the site is chosen at the PUBLISH ACT, never stored on the connection —
ADR-594 D1, no per-connection settings). `create_post` is the outbound write,
reached ONLY through the `services/publish.py` seam (ADR-628 D5; the gate
pins this). No delete, no update, no media upload — a verb arrives when a
member act needs it, not because the platform offers it.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_API_BASE = "https://public-api.wordpress.com/rest/v1.1"
_TIMEOUT_S = 30.0


class WordPressError(Exception):
    """A WordPress.com API call failed. Carries the platform's own message."""


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def list_sites(access_token: str) -> list[dict[str, Any]]:
    """The sites this member can publish to — [{id, name, url}], possibly [].

    An empty list is a REAL state (the three-state connect story, ADR-628
    amendment: a WordPress.com login with no site yet) — the caller renders
    the create-a-free-site guidance, never an error.
    """
    async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
        resp = await client.get(
            f"{_API_BASE}/me/sites",
            headers=_headers(access_token),
            params={"fields": "ID,name,URL"},
        )
    if resp.status_code != 200:
        raise WordPressError(f"me/sites failed ({resp.status_code}): {resp.text[:200]}")
    sites = (resp.json() or {}).get("sites") or []
    return [
        {
            "id": str(s.get("ID")),
            "name": (s.get("name") or "").strip() or (s.get("URL") or ""),
            "url": s.get("URL") or "",
        }
        for s in sites
        if s.get("ID")
    ]


async def create_post(
    access_token: str,
    site_id: str,
    *,
    title: str,
    content: str,
    status: str = "publish",
) -> dict[str, Any]:
    """Create a post on one site. Returns {post_id, url, status}.

    `status` is `publish` or `draft` — the member's choice at the act
    (ADR-628 D2: member-clicked, so the member decides how far it goes).
    """
    if status not in ("publish", "draft"):
        raise WordPressError(f"unsupported post status: {status!r}")
    async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
        resp = await client.post(
            f"{_API_BASE}/sites/{site_id}/posts/new",
            headers=_headers(access_token),
            json={"title": title, "content": content, "status": status},
        )
    if resp.status_code != 200:
        raise WordPressError(
            f"posts/new failed ({resp.status_code}): {resp.text[:200]}"
        )
    data = resp.json() or {}
    return {
        "post_id": str(data.get("ID") or ""),
        "url": data.get("URL") or "",
        "status": data.get("status") or status,
    }


async def get_me(access_token: str) -> dict[str, Any]:
    """The connected account's identity — used once, at OAuth callback, to
    label the connection (`connection_target` reads `account_label`)."""
    async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
        resp = await client.get(
            f"{_API_BASE}/me", headers=_headers(access_token),
            params={"fields": "ID,username,display_name,primary_blog,primary_blog_url"},
        )
    if resp.status_code != 200:
        raise WordPressError(f"me failed ({resp.status_code}): {resp.text[:200]}")
    return resp.json() or {}
