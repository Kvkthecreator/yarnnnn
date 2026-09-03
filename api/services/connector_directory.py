"""The connector directory — consumed from the ecosystem, never authored
(ADR-635 D1; FOUNDATIONS DP27 enacted for discovery).

Two upstream sources, one normalized shape:

  the MCP registry      live: `GET {REGISTRY}/v0/servers?search=&version=latest`,
                        remote streamable-HTTP entries only, cached per
                        process for an hour. An outage degrades to the seed.
  the official seed     `connector_directory_seed.json` — DERIVED from
                        `anthropics/knowledge-work-plugins` by
                        `scripts/refresh_connector_directory.py` (every
                        `.mcp.json` server, the category its plugin's
                        CONNECTORS.md assigns it), stamped with the upstream
                        repository and commit. Data with provenance in the
                        ADR-376 sense: a raw observation of upstream,
                        re-derivable. Not a list yarnnn curates.

What this is NOT: curation (no rankings), and not a store. ADR-412 D3 and
ADR-420 §10 rules 1 and 3 stand. A member may also paste any URL — the
directory is a discovery affordance in front of the attach seam, not a
precondition of it.

Entry shape: {name, title, description, url, category, source, key}
  source ∈ {"official-plugins", "registry"}; `key` is the short slug the
  attach uses when the seed has one (`notion`, `linear`), else None.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

REGISTRY_URL = "https://registry.modelcontextprotocol.io"
SEED_PATH = Path(__file__).resolve().parent / "connector_directory_seed.json"
_SEED_REQUIRED_KEYS = ("source_repo", "source_commit", "derived_at", "servers")
_CACHE_TTL_S = 3600.0
_HTTP_TIMEOUT = httpx.Timeout(8.0, connect=4.0)

_seed_cache: Optional[dict] = None
_registry_cache: dict[str, tuple[float, list[dict]]] = {}


def load_seed() -> dict:
    """The seed with its provenance. Raises if the stamp is missing — a seed
    with no upstream is an authored catalog, which this module refuses to be."""
    global _seed_cache
    if _seed_cache is not None:
        return _seed_cache
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    missing = [k for k in _SEED_REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"connector directory seed lacks provenance: {missing}")
    for s in data["servers"]:
        if not s.get("url") or not s.get("key"):
            raise ValueError(f"seed entry without url/key: {s}")
    _seed_cache = data
    return data


def seed_entries() -> list[dict]:
    return [
        {
            "name": s["key"],
            "key": s["key"],
            "title": s.get("title") or s["key"],
            "description": s.get("description") or "",
            "url": s["url"],
            "category": s.get("category"),
            "source": "official-plugins",
            "plugins": s.get("plugins") or [],
        }
        for s in load_seed()["servers"]
    ]


def _matches(entry: dict, q: str) -> bool:
    if not q:
        return True
    hay = " ".join(str(entry.get(k) or "") for k in ("name", "title", "description", "category", "url")).lower()
    return all(tok in hay for tok in q.lower().split())


def _registry_search_sync(q: str, limit: int) -> list[dict]:
    """One registry call, normalized. Only entries with a remote streamable-
    HTTP URL are connectors yarnnn can attach; the rest are local packages."""
    params = {"search": q or "", "version": "latest", "limit": str(max(1, min(limit, 50)))}
    with httpx.Client(timeout=_HTTP_TIMEOUT) as http:
        r = http.get(f"{REGISTRY_URL}/v0/servers", params=params,
                     headers={"Accept": "application/json"})
        r.raise_for_status()
        data = r.json()
    out = []
    for server in (data.get("servers") or []):
        meta = server.get("_meta") or {}
        official = meta.get("io.modelcontextprotocol.registry/official") or {}
        if official.get("status") and official.get("status") != "active":
            continue
        remotes = server.get("remotes") or []
        url = next(
            (rm.get("url") for rm in remotes
             if rm.get("type") in ("streamable-http", "http") and rm.get("url")),
            None,
        )
        if not url:
            continue
        out.append({
            "name": server.get("name") or url,
            "key": None,
            "title": server.get("title") or (server.get("name") or "").split("/")[-1],
            "description": (server.get("description") or "")[:300],
            "url": url,
            "category": None,
            "source": "registry",
            "version": server.get("version"),
        })
    return out


def registry_search(q: str, limit: int = 20) -> list[dict]:
    """Cached; never raises — a registry outage is an empty list, and the
    seed still answers."""
    key = f"{q.strip().lower()}|{limit}"
    hit = _registry_cache.get(key)
    now = time.monotonic()
    if hit and now - hit[0] < _CACHE_TTL_S:
        return hit[1]
    try:
        rows = _registry_search_sync(q, limit)
    except Exception as exc:  # noqa: BLE001
        logger.info("[DIRECTORY] registry search failed (%s): %s", q, exc)
        rows = []
    _registry_cache[key] = (now, rows)
    return rows


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def search(q: str = "", *, limit: int = 30, include_registry: bool = True) -> list[dict]:
    """Seed hits first (vendor-official endpoints), then registry hits not
    already present by URL host. Empty query = the whole seed."""
    q = (q or "").strip()
    seed = [e for e in seed_entries() if _matches(e, q)]
    seen = {_host(e["url"]) for e in seed}
    out = list(seed)
    if include_registry and q:
        for e in registry_search(q, limit):
            h = _host(e["url"])
            if h in seen:
                continue
            seen.add(h)
            out.append(e)
    return out[:limit]


def seed_entry_for_url(url: str) -> Optional[dict]:
    """The seed entry whose URL matches, so an attach by URL still gets the
    short key and category the seed knows."""
    for e in seed_entries():
        if e["url"].rstrip("/") == (url or "").rstrip("/"):
            return e
    return None


def categories() -> list[str]:
    """The category vocabulary the seed carries — suggestions for a member
    naming a pasted server's category, never a closed list."""
    return sorted({e["category"] for e in seed_entries() if e.get("category")})


__all__ = [
    "REGISTRY_URL", "SEED_PATH", "load_seed", "seed_entries", "registry_search",
    "search", "seed_entry_for_url", "categories",
]
