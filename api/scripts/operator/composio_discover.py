"""Composio discovery — the systematic developer tool for connector decisions.

ADR-353 §15: connections are added Hat-A (developer-explicit), in service of
program demand. To make that call WELL, a developer needs to know what Composio
actually offers for a named platform — which toolkit, what auth (managed vs
bring-your-own-credentials), which specific verbs. This tool answers that
systematically (repeatable, structured) instead of ad-hoc doc-reading.

This is the SUPPLY-CHECK half of §15. It does NOT browse the catalog cold to
invent demand — it surveys a platform a program (or a developer evaluating a
program-shape decision, e.g. author-publishing) has NAMED, so the kernel-vs-bundle
mapping + the add-or-not call is made with data.

It is a DISCOVERY tool only: read-only against Composio's catalog API. It creates
no connections, no auth configs, executes no actions. No tenant state.

Usage:
  cd api && COMPOSIO_API_KEY=ak_xxx ./venv/bin/python -m scripts.operator.composio_discover linkedin twitter
  # optionally filter the action list to verbs you care about:
  cd api && COMPOSIO_API_KEY=ak_xxx ./venv/bin/python -m scripts.operator.composio_discover linkedin --grep post,share,create

Output per platform: toolkit slug + name, auth scheme, managed-vs-BYO, tool count,
and the matching action slugs — everything needed to decide (a) does Composio
cover the verbs the program needs, (b) is it managed-OAuth or BYO-credentials
(the §7 per-connector wrinkle), (c) kernel-universal or bundle-specific home.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import httpx

BASE = os.getenv("COMPOSIO_API_BASE", "https://backend.composio.dev")
_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _headers() -> dict[str, str]:
    key = os.getenv("COMPOSIO_API_KEY")
    if not key:
        print("COMPOSIO_API_KEY not set. Supply it transiently at invocation.", file=sys.stderr)
        raise SystemExit(1)
    return {"x-api-key": key}


def _get(path: str, params: dict | None = None) -> Any:
    r = httpx.get(f"{BASE}{path}", headers=_headers(), params=params or {}, timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


def find_toolkit(term: str) -> dict | None:
    """Resolve a platform term to its toolkit (exact slug match preferred)."""
    items = _get("/api/v3/toolkits", {"search": term, "limit": 10}).get("items", [])
    if not items:
        return None
    exact = next((i for i in items if (i.get("slug") or "").lower() == term.lower()), None)
    return exact or items[0]


def toolkit_detail(slug: str) -> dict:
    return _get(f"/api/v3/toolkits/{slug}")


def toolkit_tools(slug: str, limit: int = 200) -> list[dict]:
    return _get("/api/v3/tools", {"toolkit_slug": slug, "limit": limit}).get("items", [])


def survey(term: str, grep_terms: list[str]) -> None:
    print(f"\n{'='*72}\nPLATFORM QUERY: {term!r}\n{'='*72}")
    tk = find_toolkit(term)
    if not tk:
        print(f"  NO toolkit found for {term!r}. Composio may not cover this platform.")
        return
    slug = tk.get("slug")
    name = tk.get("name") or slug
    exact = (slug or "").lower() == term.lower()
    print(f"  toolkit: {slug}  ({name}){'' if exact else '  [NEAREST MATCH — not exact]'}")

    detail = toolkit_detail(slug)
    auth = detail.get("auth_config_details") or detail.get("composio_managed_auth_schemes") or detail.get("auth_schemes")
    if isinstance(auth, list):
        schemes = [a.get("mode") or a.get("name") or a for a in auth] if auth and isinstance(auth[0], dict) else auth
    else:
        schemes = auth
    managed = detail.get("is_composio_managed", detail.get("composio_managed"))
    meta = detail.get("meta", {}) or {}
    tools_count = meta.get("tools_count") or detail.get("tools_count")
    print(f"  auth scheme(s): {schemes}")
    print(f"  composio-managed OAuth: {managed}   (False/None ⇒ likely BRING-YOUR-OWN dev credentials — §7 wrinkle)")
    print(f"  total tools: {tools_count}")

    tools = toolkit_tools(slug)
    slugs = sorted(t.get("slug") for t in tools if t.get("slug"))
    if grep_terms:
        matched = [s for s in slugs if any(g.lower() in s.lower() for g in grep_terms)]
        print(f"  action slugs matching {grep_terms} ({len(matched)} of {len(slugs)} shown):")
        for s in matched:
            print(f"    {s}")
        if not matched:
            print("    (none matched — widen --grep or inspect the full list)")
    else:
        print(f"  action slugs (first 40 of {len(slugs)}):")
        for s in slugs[:40]:
            print(f"    {s}")


def main(argv: list[str]) -> int:
    grep_terms: list[str] = []
    terms: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--grep" and i + 1 < len(argv):
            grep_terms = [t.strip() for t in argv[i + 1].split(",") if t.strip()]
            i += 2
            continue
        terms.append(a)
        i += 1

    if not terms:
        print("Usage: composio_discover <platform> [<platform> ...] [--grep verb1,verb2]")
        return 1

    for term in terms:
        try:
            survey(term, grep_terms)
        except httpx.HTTPError as e:
            print(f"  ERROR surveying {term!r}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
