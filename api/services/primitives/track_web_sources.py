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
    CHAT_PRIMITIVES, HEADLESS_PRIMITIVES, or FREDDIE_PRIMITIVES.

Attribution:
    write_revision(authored_by="system:track-web-sources") per ADR-209.

ADR-153 discipline: feed entries are already summaries; we distill
further and CAP (max sources, max entries, max summary chars). This is
bounded observation, never raw mirroring.

ADR-376 / FOUNDATIONS DP32 (the ledger-intake axiom — `retain + attribute
+ cite`): the distilled signal is the workspace's *derived understanding*
of the web; the fetched feed bodies are the *raw observations* it was built
from. DP32's retention clause requires the raw be retained (per its
transport's mechanism — here, a file) and the derived cite it. So this
primitive now RETAINS each successfully-fetched feed body in the raw lane —
``inbound/web/{source}/{observed_at}.xml`` (immutable, attributed
``system:track-web-sources``, sibling to ``uploads/`` and ``inbound/mcp/``,
outside the topology cut) — and the distilled ``_watch_signal.yaml`` carries
a ``derived_from`` block list pointing at the raws it cited. Retention is
bounded to the observations the signal CITES (DP32 D5 — evidence, not a
crawl archive): a source that fails to fetch is NOT retained (there is no
observation behind it; its error is the record). This makes a watch
*falsifiable* — a judgment that fires on a signal can re-read the very feed
body the distillation was built from, and ``trace`` walks the signal back to
its raw observations.
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

# ADR-376/DP32 raw lane: the fetched feed body is the cited raw observation.
# Sibling to inbound/mcp/ (foreign LLM) — outside the constitution/operation/
# governance topology cut, immutable, attributed system:track-web-sources.
INBOUND_WEB_PREFIX = "inbound/web/"
_MAX_RAW_BODY_CHARS = 2_000_000  # a fetched feed body is bounded; guard runaway pages

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


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
    raw_stamp = now.strftime("%Y-%m-%dT%H%M%SZ")  # path-safe (no colons) for the raw filename
    blocks: list[dict] = []
    errors: list[str] = []
    raw_paths: list[str] = []  # ADR-376/DP32: the cited raw observations the signal derives from
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
            # ADR-376/DP32 retain-clause: keep the raw observation this distillation
            # CITED — the fetched feed body — in the raw lane, immutably + attributed.
            # Bounded to a CITED observation (a successful fetch we distilled), never
            # every fetched byte; a failed source has no observation to retain.
            raw_path = _write_raw_observation(
                client, user_id, source_id=sid, source_ref=url,
                attestation=attestation, observed_at=observed_at,
                raw_stamp=raw_stamp, body=body,
            )
            blocks.append({"id": sid, "source_ref": url, "attestation": attestation,
                           "observed_at": observed_at, "status": "ok",
                           "derived_from": raw_path, "entries": entries})
            raw_paths.append(raw_path)
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
        derived_from=raw_paths,
    )

    return {
        "success": True,
        "items_processed": processed,
        # the derived signal first, then the raw observations it cites (ADR-376)
        "paths_written": [path_written, *raw_paths],
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

def _slug(text: str) -> str:
    """Path-safe slug for a source id (lowercase, hyphen-joined)."""
    return _SLUG_RE.sub("-", (text or "").strip().lower()).strip("-") or "source"


def _ws_path(p: str) -> str:
    return p if p.startswith("/workspace/") else f"/workspace/{p.lstrip('/')}"


def _write_raw_observation(
    client: Any,
    user_id: str,
    *,
    source_id: str,
    source_ref: str,
    attestation: str,
    observed_at: str,
    raw_stamp: str,
    body: str,
) -> str:
    """Retain ONE fetched feed body as an immutable raw observation (ADR-376/DP32).

    Lands at ``inbound/web/{source}/{observed_at}.xml`` — sibling to ``inbound/mcp/``
    and ``uploads/``, outside the topology cut, attributed ``system:track-web-sources``.
    This is the raw observation the distilled signal CITES (the evidence behind a
    judgment); never rewritten. Returns the absolute workspace path so the signal
    can carry it as a ``derived_from`` citation.

    A small attribution header precedes the verbatim feed body so the raw file is
    self-describing (source_ref + attestation + observed_at — the ADR-335 D3
    observation contract carried onto the raw object itself); the body below it is
    the fetched payload, bounded by ``_MAX_RAW_BODY_CHARS`` against a runaway page.
    """
    from services.authored_substrate import write_revision

    path = _ws_path(f"{INBOUND_WEB_PREFIX}{_slug(source_id)}/{raw_stamp}.xml")
    truncated = body[:_MAX_RAW_BODY_CHARS]
    header = (
        "<!-- raw web observation (ADR-376/DP32 ledger-intake raw lane).\n"
        f"     source_ref: {source_ref}\n"
        f"     attestation: {attestation}\n"
        f"     observed_at: {observed_at}\n"
        "     Immutable; the cited evidence behind a distilled signal. The distilled\n"
        "     _watch_signal.yaml is the derived understanding; this is its source. -->\n"
    )
    if len(body) > _MAX_RAW_BODY_CHARS:
        header += f"<!-- body truncated to {_MAX_RAW_BODY_CHARS} chars (was {len(body)}) -->\n"
    write_revision(
        client,
        user_id=user_id,
        path=path,
        content=header + truncated,
        authored_by="system:track-web-sources",
        message=f"raw web observation: {source_ref} @ {observed_at}",
        revision_kind="observation",  # ADR-423: retained raw intake (inbound/web/)
    )
    return path


def _write_signal(
    client: Any,
    user_id: str,
    distills_to: str,
    *,
    watch_declaration: str,
    observed_at: str,
    blocks: list[dict],
    derived_from: Optional[list[str]] = None,
) -> str:
    from services.authored_substrate import write_revision

    path = _ws_path(distills_to)
    payload = {
        # The observation-contract envelope (ADR-335 D3, convention-first):
        # watch_id is the declaration pointer; each block carries source_ref +
        # attestation + observed_at + distilled entries + its own derived_from
        # (the per-source raw observation it distilled). The top-level
        # derived_from is the UNION the signal cites — the ADR-376/DP32 D3
        # structured back-reference `trace` walks raw↔derived (a LIST: one signal
        # synthesizes N raw observations — the first multi-cite case, §9 DECIDED).
        # Top-of-payload so it lands in the header region the reader scans.
        "derived_from": list(derived_from or []),
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
        "# derived_from (ADR-376/DP32): the raw observations in inbound/web/ this\n"
        "# distillation CITES — the evidence a judgment can re-read; trace walks it.\n"
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
