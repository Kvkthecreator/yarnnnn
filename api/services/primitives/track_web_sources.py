"""TrackWebSources Primitive — ADR-336 (enacts ADR-335 D7).

Deterministic mechanical primitive that fetches declared web/RSS/Atom
sources and distills them into attributed signal substrate per the
ADR-335 D3 observation contract. The generic standing-watch transport for
connectionless workspaces — the web sibling of ``TrackUniverse``.

Zero LLM cost. Stdlib XML parsing (no new dependency — render-parity
across all 4 services untouched). Semantic reading happens at judgment
wakes; this primitive only mirrors + distills deterministically.

Surface:
    @primitive: TrackWebSources(declaration="<path>/_sources.yaml",
                                distills_to="<path>/_watch_signal.yaml")

Paths arrive as directive kwargs — the kernel hardcodes no program's
topology (ADR-224 boundary). The declaration substrate is the operator's
watch declaration (the web analog of ``_universe.yaml``):

    sources:
      - id: stereogum
        url: https://www.stereogum.com/feed/
        attestation: platform   # optional; default platform — a first-party
                                # publisher feed attests its own publication facts
        max_entries: 8          # optional; default 8

Behavior:
    1. Read the declaration yaml (yaml.safe_load; zero regex).
    2. For each source (capped — a portfolio of attention, not a crawler):
       fetch with httpx (15s timeout, honest UA), parse RSS 2.0 / Atom via
       xml.etree, keep the newest N entries, truncate summaries (<=280
       chars, HTML stripped).
    3. Write ONE distilled signal file at ``distills_to`` with per-source
       blocks {source_ref, attestation, observed_at, status, entries}.
       Per-source failure isolates: a dead feed gets status=error in the
       record (absence/error is perceivable per ADR-335 D5-governance —
       no freshness table).
    4. Return {success, items_processed, paths_written, errors}.

Dispatch surface:
    Mechanical recurrence dispatcher only (HANDLERS). Not in
    CHAT_PRIMITIVES, HEADLESS_PRIMITIVES, or REVIEWER_PRIMITIVES.

Attribution:
    write_revision(authored_by="system:track-web-sources") per ADR-209.

ADR-153 discipline: feed entries are already summaries; we distill
further and CAP (max sources, max entries, max summary chars). This is
bounded observation, never raw mirroring.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Optional

import yaml as _yaml

logger = logging.getLogger(__name__)

_MAX_SOURCES = 12          # portfolio of attention, not a crawler
_DEFAULT_MAX_ENTRIES = 8
_MAX_SUMMARY_CHARS = 280
_FETCH_TIMEOUT_S = 15.0
_USER_AGENT = "yarnnn-watch/1.0 (+https://yarnnn.com; standing-watch reader)"

_VALID_ATTESTATIONS = ("platform", "operator", "agent")

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


async def handle_track_web_sources(auth: Any, input: dict) -> dict:
    """Fetch + distill every declared web source into the signal substrate.

    Required directive kwargs:
        declaration — workspace-relative path of the operator's _sources.yaml
        distills_to — workspace-relative path of the distilled signal file
    """
    user_id = getattr(auth, "user_id", None)
    client = getattr(auth, "client", None)
    if not user_id or not client:
        return {"success": False, "error": "auth_required", "items_processed": 0,
                "paths_written": [], "errors": ["missing auth.user_id or auth.client"]}

    declaration = (input or {}).get("declaration") or ""
    distills_to = (input or {}).get("distills_to") or ""
    if not declaration or not distills_to:
        return {"success": False, "error": "missing_args", "items_processed": 0,
                "paths_written": [],
                "errors": ["TrackWebSources requires declaration= and distills_to= directive args"]}

    sources = _read_sources(client, user_id, declaration)
    if sources is None:
        return {"success": False, "error": "declaration_missing", "items_processed": 0,
                "paths_written": [],
                "errors": [f"watch declaration not found or unparseable: {declaration}"]}
    if not sources:
        # Empty declaration = deliberate no-op (the lean shape stays valid —
        # perception is a flow, never a gate). Not an error.
        return {"success": True, "items_processed": 0, "paths_written": [],
                "errors": [], "note": "no sources declared — no-op"}

    now = datetime.now(timezone.utc)
    observed_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    blocks: list[dict] = []
    errors: list[str] = []
    processed = 0

    for src in sources[:_MAX_SOURCES]:
        sid = str(src.get("id") or src.get("url") or "unnamed")
        url = src.get("url")
        attestation = src.get("attestation") or "platform"
        if attestation not in _VALID_ATTESTATIONS:
            attestation = "platform"
        max_entries = src.get("max_entries") or _DEFAULT_MAX_ENTRIES
        try:
            max_entries = max(1, min(int(max_entries), 20))
        except (TypeError, ValueError):
            max_entries = _DEFAULT_MAX_ENTRIES

        if not url or not isinstance(url, str) or not url.startswith(("http://", "https://")):
            blocks.append({"id": sid, "source_ref": str(url), "attestation": attestation,
                           "observed_at": observed_at, "status": "error",
                           "error": "invalid_url", "entries": []})
            errors.append(f"{sid}: invalid url")
            continue

        try:
            body = await _fetch(url)
            entries = parse_feed(body)[:max_entries]
            blocks.append({"id": sid, "source_ref": url, "attestation": attestation,
                           "observed_at": observed_at, "status": "ok",
                           "entries": entries})
            processed += 1
        except Exception as exc:  # per-source isolation — a dead feed is a recorded fact
            logger.warning("[TRACK_WEB_SOURCES] %s fetch/parse failed: %s", sid, exc)
            blocks.append({"id": sid, "source_ref": url, "attestation": attestation,
                           "observed_at": observed_at, "status": "error",
                           "error": str(exc)[:200], "entries": []})
            errors.append(f"{sid}: {exc}")

    if len(sources) > _MAX_SOURCES:
        errors.append(
            f"declaration lists {len(sources)} sources; cap is {_MAX_SOURCES} — "
            f"{len(sources) - _MAX_SOURCES} skipped (no silent caps)"
        )

    path_written = _write_signal(
        client, user_id, distills_to,
        watch_declaration=declaration, observed_at=observed_at, blocks=blocks,
    )

    return {
        "success": True,
        "items_processed": processed,
        "paths_written": [path_written],
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Declaration read
# ---------------------------------------------------------------------------

def _read_sources(client: Any, user_id: str, declaration: str) -> Optional[list[dict]]:
    """Read sources list from the declaration yaml. None = missing/unparseable;
    [] = declared-empty (deliberate no-op)."""
    path = declaration if declaration.startswith("/workspace/") else f"/workspace/{declaration.lstrip('/')}"
    try:
        res = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", path)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning("[TRACK_WEB_SOURCES] declaration read failed: %s", exc)
        return None
    content = (res.data or [{}])[0].get("content")
    if not content:
        return None
    # Strip ADR-226 tier frontmatter if present before yaml parse
    body = content
    m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    if m:
        body = content[m.end():]
    try:
        parsed = _yaml.safe_load(body) or {}
    except _yaml.YAMLError:
        return None
    sources = parsed.get("sources")
    if sources is None:
        return []
    if not isinstance(sources, list):
        return None
    return [s for s in sources if isinstance(s, dict)]


# ---------------------------------------------------------------------------
# Fetch + parse (stdlib only)
# ---------------------------------------------------------------------------

async def _fetch(url: str) -> str:
    import httpx
    async with httpx.AsyncClient(
        timeout=_FETCH_TIMEOUT_S,
        headers={"User-Agent": _USER_AGENT},
        follow_redirects=True,
    ) as http:
        resp = await http.get(url)
        resp.raise_for_status()
        return resp.text


def _strip_html(text: str) -> str:
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", text or "")).strip()


def _local(tag: str) -> str:
    """Element tag without XML namespace."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def parse_feed(body: str) -> list[dict]:
    """Parse RSS 2.0 or Atom into distilled entries (newest-first as served).

    Deterministic distillation: title / url / published / summary(<=280).
    Raises on unparseable XML (caller isolates per source).
    """
    root = ET.fromstring(body.strip())
    root_tag = _local(root.tag).lower()

    items: list[ET.Element] = []
    if root_tag == "rss":
        channel = next((c for c in root if _local(c.tag).lower() == "channel"), None)
        if channel is not None:
            items = [e for e in channel if _local(e.tag).lower() == "item"]
    elif root_tag == "feed":  # Atom
        items = [e for e in root if _local(e.tag).lower() == "entry"]
    else:
        raise ValueError(f"unrecognized feed root <{root_tag}>")

    entries: list[dict] = []
    for item in items:
        title, link, published, summary = "", "", "", ""
        for child in item:
            tag = _local(child.tag).lower()
            text = (child.text or "").strip()
            if tag == "title":
                title = _strip_html(text)
            elif tag == "link":
                # RSS: text body; Atom: href attribute (prefer rel=alternate/absent)
                if text:
                    link = text
                elif child.get("href") and (child.get("rel") in (None, "alternate")):
                    link = child.get("href", "")
            elif tag in ("pubdate", "published", "updated", "date") and not published:
                published = text
            elif tag in ("description", "summary", "content") and not summary:
                summary = _strip_html(text)
        if not (title or link):
            continue
        entries.append({
            "title": title[:200],
            "url": link,
            "published": published[:64],
            "summary": summary[:_MAX_SUMMARY_CHARS],
        })
    return entries


# ---------------------------------------------------------------------------
# Signal write (the observation contract, ADR-335 D3)
# ---------------------------------------------------------------------------

def _write_signal(
    client: Any,
    user_id: str,
    distills_to: str,
    *,
    watch_declaration: str,
    observed_at: str,
    blocks: list[dict],
) -> str:
    from services.authored_substrate import write_revision

    path = distills_to if distills_to.startswith("/workspace/") else f"/workspace/{distills_to.lstrip('/')}"
    payload = {
        # The observation-contract envelope (ADR-335 D3, convention-first):
        # watch_id is the declaration pointer; each block carries source_ref +
        # attestation + observed_at + distilled entries. Never raw payloads.
        "watch": watch_declaration,
        "observed_at": observed_at,
        "sources": blocks,
    }
    header = (
        "# _watch_signal.yaml — distilled standing-watch observations (ADR-336)\n"
        "# Written by TrackWebSources (mechanical, deterministic, zero-LLM).\n"
        "# Judgment reads this file; it never fetches the web for perception.\n"
        "# Observation contract per ADR-335 D3: source_ref + attestation +\n"
        "# observed_at + distilled entries. Bounded per ADR-153.\n"
    )
    content = header + _yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    write_revision(
        client,
        user_id=user_id,
        path=path,
        content=content,
        authored_by="system:track-web-sources",
        message=f"standing-watch observation: {sum(len(b.get('entries', [])) for b in blocks)} entries across {len(blocks)} sources",
    )
    return path
