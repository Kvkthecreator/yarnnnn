"""TrackForeign Primitive — ADR-335 Crawl-B Increment B (enacts ADR-335 D4/D5).

Deterministic mechanical primitive that reads declared foreign-source paths
through an MCP transport binding and distills them into attributed signal
substrate per the ADR-335 D3 observation contract. The MCP-transport sibling of
``TrackWebSources`` (web/RSS) and ``TrackUniverse`` (Alpaca head driver).

This is the generic standing-watch executor for watches no hand-authored head
driver serves (ADR-335 D4: "transports are device drivers; MCP is USB"). The
first real binding is a code/doc repository read via the GitHub MCP server's
``get_file_contents`` tool — the perception path for a workspace whose SUBJECT
is a repo (e.g. a YARNNN-about-YARNNN author workspace authoring with verifiable
citations to its own ``docs/``).

Zero LLM cost. Every foreign call routes through ``read_foreign_tool`` (the ONE
metered mechanical executor, ADR-335 B3) — recorded to the ``execution_events``
cost ledger. Semantic reading happens at judgment wakes; this primitive only
mirrors + distills deterministically.

Surface (mechanical recurrence directive — paths arrive as kwargs; the kernel
hardcodes no program's topology, ADR-224):

    @primitive: TrackForeign(declaration="<path>/_repo_sources.yaml",
                             distills_to="<path>/_watch_signal.yaml",
                             tool="get_file_contents")

The declaration substrate is the operator/program watch declaration (the MCP
analog of ``_universe.yaml`` / ``_sources.yaml``):

    server: github            # the bound transport's platform key in
                              # platform_connections (watch_id-bound row)
    repo: "Kvkthecreator/yarnnnn"
    sources:
      - id: adr-354
        path: docs/adr/ADR-354-recurrence-prompt-collapse-and-perception-field-discipline.md
        attestation: platform   # optional; default platform (first-party repo)
      - id: foundations
        path: docs/architecture/FOUNDATIONS.md

Behavior:
    1. Read the declaration yaml (yaml.safe_load; zero regex).
    2. Resolve the watch-bound MCP connection (platform_connections row with a
       non-null watch_id for the declared ``server`` platform) — server_url from
       metadata, token decrypted via TokenManager.
    3. For each declared source (capped — a portfolio of attention, not a
       crawler): call read_foreign_tool(tool, {owner, repo, path}) and distill
       the file content (bounded, truncated) into an observation block.
       Per-source failure isolates (absence/error is perceivable, ADR-335 D5).
    4. Write ONE distilled signal file at ``distills_to`` with per-source blocks
       {id, source_ref, attestation, observed_at, status, content/excerpt}.
    5. Return {success, items_processed, paths_written, errors}.

Dispatch surface:
    Mechanical recurrence dispatcher only (HANDLERS). Not in CHAT_PRIMITIVES,
    HEADLESS_PRIMITIVES, or FREDDIE_PRIMITIVES.

Attribution:
    write_revision(authored_by="system:track-foreign") per ADR-209.

ADR-153 discipline: distilled + bounded (max sources, max chars per file).
Never raw mirroring — the signal carries excerpts the judgment reads, and the
source_ref so the judgment can cite the exact repo path.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

import yaml as _yaml

logger = logging.getLogger(__name__)

_MAX_SOURCES = 20            # portfolio of attention, not a crawler
_MAX_FILE_CHARS = 8000       # bounded per ADR-153; judgment reads excerpts, not raw dumps
_VALID_ATTESTATIONS = ("platform", "operator", "agent")


async def handle_track_foreign(auth: Any, input: dict) -> dict:
    """Read + distill every declared foreign source through the MCP binding.

    Required directive kwargs:
        declaration — workspace-relative path of the watch declaration yaml
        distills_to — workspace-relative path of the distilled signal file
    Optional:
        tool        — the foreign tool to call (default 'get_file_contents')
    """
    user_id = getattr(auth, "user_id", None)
    client = getattr(auth, "client", None)
    if not user_id or not client:
        return {"success": False, "error": "auth_required", "items_processed": 0,
                "paths_written": [], "errors": ["missing auth.user_id or auth.client"]}

    declaration = (input or {}).get("declaration") or ""
    distills_to = (input or {}).get("distills_to") or ""
    tool_name = (input or {}).get("tool") or "get_file_contents"
    if not declaration or not distills_to:
        return {"success": False, "error": "missing_args", "items_processed": 0,
                "paths_written": [],
                "errors": ["TrackForeign requires declaration= and distills_to= directive args"]}

    decl = _read_declaration(client, user_id, declaration)
    if decl is None:
        return {"success": False, "error": "declaration_missing", "items_processed": 0,
                "paths_written": [],
                "errors": [f"watch declaration not found or unparseable: {declaration}"]}
    sources = decl.get("sources") or []
    if not sources:
        # Declared-empty = deliberate no-op (perception is a flow, never a gate).
        return {"success": True, "items_processed": 0, "paths_written": [],
                "errors": [], "note": "no sources declared — no-op"}

    server_key = str(decl.get("server") or "github")
    repo = decl.get("repo")
    if not repo or not isinstance(repo, str) or "/" not in repo:
        return {"success": False, "error": "invalid_repo", "items_processed": 0,
                "paths_written": [],
                "errors": [f"declaration 'repo' must be 'owner/name', got: {repo!r}"]}
    owner, repo_name = repo.split("/", 1)

    binding = _resolve_binding(client, user_id, server_key)
    if binding is None:
        return {"success": False, "error": "binding_missing", "items_processed": 0,
                "paths_written": [],
                "errors": [f"no active watch-bound MCP connection for server={server_key!r} "
                           f"(platform_connections row with watch_id set)"]}
    server_url, access_token = binding

    now = datetime.now(timezone.utc)
    observed_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    watch_slug = _watch_slug_from_path(declaration)
    blocks: list[dict] = []
    errors: list[str] = []
    processed = 0

    from services.foreign_read import read_foreign_tool

    for src in sources[:_MAX_SOURCES]:
        sid = str(src.get("id") or src.get("path") or "unnamed")
        path = src.get("path")
        attestation = src.get("attestation") or "platform"
        if attestation not in _VALID_ATTESTATIONS:
            attestation = "platform"
        if not path or not isinstance(path, str):
            blocks.append({"id": sid, "source_ref": f"{repo}@{path}", "attestation": attestation,
                           "observed_at": observed_at, "status": "error",
                           "error": "invalid_path", "excerpt": ""})
            errors.append(f"{sid}: invalid path")
            continue

        source_ref = f"{repo}/{path}"
        try:
            result = await read_foreign_tool(
                client,
                user_id=user_id,
                watch_slug=watch_slug,
                server_url=server_url,
                access_token=access_token,
                tool_name=tool_name,
                arguments={"owner": owner, "repo": repo_name, "path": path},
            )
            if result is None or result.is_error:
                err = (result.text if result else "no result")[:200]
                blocks.append({"id": sid, "source_ref": source_ref, "attestation": attestation,
                               "observed_at": observed_at, "status": "error",
                               "error": err, "excerpt": ""})
                errors.append(f"{sid}: {err}")
                continue
            excerpt = _distill_file(result)
            blocks.append({"id": sid, "source_ref": source_ref, "attestation": attestation,
                           "observed_at": observed_at, "status": "ok",
                           "excerpt": excerpt})
            processed += 1
        except Exception as exc:  # per-source isolation — a failed read is a recorded fact
            logger.warning("[TRACK_FOREIGN] %s read failed: %s", sid, exc)
            blocks.append({"id": sid, "source_ref": source_ref, "attestation": attestation,
                           "observed_at": observed_at, "status": "error",
                           "error": str(exc)[:200], "excerpt": ""})
            errors.append(f"{sid}: {exc}")

    if len(sources) > _MAX_SOURCES:
        errors.append(
            f"declaration lists {len(sources)} sources; cap is {_MAX_SOURCES} — "
            f"{len(sources) - _MAX_SOURCES} skipped (no silent caps)"
        )

    path_written = _write_signal(
        client, user_id, distills_to,
        watch_declaration=declaration, repo=repo, observed_at=observed_at, blocks=blocks,
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

def _read_declaration(client: Any, user_id: str, declaration: str) -> Optional[dict]:
    """Read the watch declaration yaml. None = missing/unparseable."""
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
        logger.warning("[TRACK_FOREIGN] declaration read failed: %s", exc)
        return None
    content = (res.data or [{}])[0].get("content")
    if not content:
        return None
    body = content
    m = re.match(r"^---\s*\n.*?\n---\s*\n", content, re.DOTALL)
    if m:
        body = content[m.end():]
    try:
        parsed = _yaml.safe_load(body) or {}
    except _yaml.YAMLError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _watch_slug_from_path(declaration: str) -> str:
    """Derive a stable watch slug from the declaration filename (for the ledger)."""
    leaf = declaration.rstrip("/").rsplit("/", 1)[-1]
    return leaf.removeprefix("_").removesuffix(".yaml") or "foreign"


# ---------------------------------------------------------------------------
# Binding resolution (the watch-bound MCP connection, ADR-335 D5 + §268)
# ---------------------------------------------------------------------------

def _resolve_binding(client: Any, user_id: str, server_key: str) -> Optional[tuple[str, str]]:
    """Resolve (server_url, decrypted_token) for the watch-bound MCP connection.

    A watch binding is a platform_connections row with watch_id set (NULL =
    capability binding per ADR-207; set = watch binding per ADR-335 D5). The
    server_url lives in metadata; the token is decrypted via TokenManager.
    Returns None when no active watch-bound row exists for this server key.
    """
    try:
        from integrations.core.tokens import get_token_manager
        res = (
            client.table("platform_connections")
            .select("credentials_encrypted, metadata, watch_id, status")
            .eq("user_id", user_id)
            .eq("platform", server_key)
            .eq("status", "active")
            .execute()
        )
    except Exception as exc:
        logger.warning("[TRACK_FOREIGN] binding read failed: %s", exc)
        return None
    rows = res.data or []
    # Prefer a watch-bound row (watch_id set); a foreign watch must not borrow a
    # bare capability connection's auth (the watch/capability boundary, D5).
    row = next((r for r in rows if r.get("watch_id")), None)
    if row is None:
        return None
    metadata = row.get("metadata") or {}
    server_url = metadata.get("server_url")
    if not server_url:
        logger.warning("[TRACK_FOREIGN] binding for %s has no metadata.server_url", server_key)
        return None
    try:
        token = get_token_manager().decrypt(row["credentials_encrypted"])
    except Exception as exc:
        logger.warning("[TRACK_FOREIGN] token decrypt failed for %s: %s", server_key, exc)
        return None
    if not token:
        return None
    return server_url, token


# ---------------------------------------------------------------------------
# Distillation (bounded — ADR-153)
# ---------------------------------------------------------------------------

def _distill_file(result: Any) -> str:
    """Extract bounded file content from an MCP get_file_contents result.

    GitHub MCP returns the file body in structured content or text blocks; we
    take whatever text is present, bound it, and record an excerpt. The judgment
    reads the excerpt + the source_ref so it can cite the exact repo path.
    """
    text = getattr(result, "text", "") or ""
    if not text and getattr(result, "structured", None) is not None:
        structured = result.structured
        # GitHub MCP commonly returns {content: "...", ...} or a list of blocks.
        if isinstance(structured, dict):
            text = str(structured.get("content") or structured.get("text") or structured)
        else:
            text = str(structured)
    text = text.strip()
    if len(text) > _MAX_FILE_CHARS:
        text = text[:_MAX_FILE_CHARS] + f"\n\n_(truncated from {len(text)} chars — read the full file at source_ref)_"
    return text


# ---------------------------------------------------------------------------
# Signal write (the observation contract, ADR-335 D3)
# ---------------------------------------------------------------------------

def _write_signal(
    client: Any,
    user_id: str,
    distills_to: str,
    *,
    watch_declaration: str,
    repo: str,
    observed_at: str,
    blocks: list[dict],
) -> str:
    from services.authored_substrate import write_revision

    path = distills_to if distills_to.startswith("/workspace/") else f"/workspace/{distills_to.lstrip('/')}"
    payload = {
        "watch": watch_declaration,
        "repo": repo,
        "observed_at": observed_at,
        "sources": blocks,
    }
    header = (
        "# _watch_signal.yaml — distilled foreign-source observations (ADR-335 Crawl-B)\n"
        "# Written by TrackForeign (mechanical, deterministic, zero-LLM) via an MCP\n"
        "# transport binding. Judgment reads this file + each source_ref to cite the\n"
        "# exact repo path; it never calls the foreign server for perception.\n"
        "# Observation contract per ADR-335 D3: source_ref + attestation +\n"
        "# observed_at + bounded excerpt. Distilled, never raw (ADR-153).\n"
    )
    content = header + _yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    write_revision(
        client,
        user_id=user_id,
        path=path,
        content=content,
        authored_by="system:track-foreign",
        message=f"foreign-watch observation: {sum(1 for b in blocks if b.get('status') == 'ok')}/{len(blocks)} sources read from {repo}",
    )
    return path


__all__ = ["handle_track_foreign"]
