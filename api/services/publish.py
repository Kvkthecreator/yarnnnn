"""
Publish — the OUTBOUND seam (ADR-628 phase (a)).

The third disposition of platform reach: content leaving the workspace for an
external platform. Everything outbound crosses HERE — the gate
(`test_adr628_outbound_publish.py`) pins that no other module under `api/`
performs an outbound platform write. Its predecessor, the ADR-028
`integrations/exporters/` DestinationExporter stack, is DELETED (a fossil:
its one `.deliver()` caller was removed 2026-08-26; `connector_does` cited
it to promise an export capability no route could perform).

Phase (a) shape, held strictly:

  - MEMBER-CLICKED. The caller is a human principal on their own turn; the
    credential resolves through `platform_credentials.resolve_platform_credential`,
    which REFUSES an agent caller (ADR-577 D1) — so "no agent decides to
    publish" is structural, not convention.
  - ONE POST PER ACT. No fan-out, no batch.
  - RECEIPTED. Every publish appends to a `_publish.yaml` sidecar beside the
    post (machine format, ADR-254), written through `write_revision` as the
    member's own act — attributed, versioned, revertible like everything else.
  - The site is chosen AT THE ACT, never stored on the connection
    (ADR-594 D1: a connection is consent + credential + aperture — no
    per-connection settings).

Phase (b) (a standing declaration publishing without a click) is NOT here —
it begins only on phase (a)'s receipts, via ADR amendment, with its own
narrow non-agent identity (`system:publish-{platform}`).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: The platforms with a live outbound write path. `connector_does` derives
#: its "writes" copy from this — one home, so the connectors surface cannot
#: promise a write the seam does not perform (the exporter-fossil defect).
PUBLISH_TARGETS: frozenset[str] = frozenset({"wordpress"})


class PublishError(Exception):
    """A publish act failed, with a member-readable reason."""


# ---------------------------------------------------------------------------
# Payload composition — a CONTRACT, pure (gated directly)
# ---------------------------------------------------------------------------
#
# ADR-628 D6 (2026-09-03). The predecessor was three regexes with a fallback,
# and the first real artifact broke it three independent ways: no <main> →
# the fallback published the RAW DOCUMENT (doctype + <head> + <style>);
# WordPress then stripped the <style> TAGS but kept their TEXT, so a
# stylesheet published as prose with smart-quotes applied to the code; and
# the data-* strip missed CSS attribute selectors (`[data-block="x"]`), which
# carry no leading whitespace.
#
# The lesson is not "fix the pattern". It is that composition had no contract
# to violate, so it could not refuse — every other stage of this seam either
# receipts or refuses, and composition alone reported success on garbage.
#
# So: state what a publishable post IS, remove transport-hostile matter BY
# STRUCTURE (whole elements, not attribute patterns), and REFUSE what cannot
# be composed. A refusal is recoverable; a published post is not.

#: Elements whose CONTENT must never cross — dropped whole, open tag to close.
#: Removing the tags alone is not enough: the platform keeps the text (F2).
_DROP_WHOLE = ("style", "script", "template", "noscript")

#: The content root, in resolution order. `main` is the native `post`
#: scaffold (ADR-627 D1); `article`/`body` cover the pre-627 outward
#: artifacts, which ADR-627 D1 promised keep working. There is deliberately
#: NO "else the whole document" branch — its absence IS the F1 fix.
_CONTENT_ROOTS = ("main", "article", "body")

_H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
#: Any `data-…="…"` occurrence — no leading-whitespace requirement (F3).
_DATA_ATTR_RE = re.compile(r"\s*\bdata-[a-zA-Z0-9-]+=(\"[^\"]*\"|'[^']*')")


def _strip_dropped_elements(html: str) -> str:
    """Remove <style>/<script>/… **with their content**, and HTML comments."""
    out = html
    for tag in _DROP_WHOLE:
        out = re.sub(
            rf"<{tag}\b[^>]*>.*?</{tag}\s*>", "", out, flags=re.IGNORECASE | re.DOTALL
        )
        # A self-closed or unclosed instance still must not leak its open tag.
        out = re.sub(rf"<{tag}\b[^>]*/?>", "", out, flags=re.IGNORECASE)
    return _COMMENT_RE.sub("", out)


def _content_root(html: str) -> Optional[str]:
    """The publishable region's inner HTML, or None when none resolves.

    Resolved AFTER the drop pass — a `<style>` body mentioning `main` or
    `<article>` in a comment would otherwise match (it did: the first real
    artifact's stylesheet comment contains the literal text `<article>`).
    """
    for tag in _CONTENT_ROOTS:
        m = re.search(
            rf"<{tag}\b[^>]*>(.*?)</{tag}\s*>", html, re.IGNORECASE | re.DOTALL
        )
        if m and m.group(1).strip():
            return m.group(1)
    return None


def compose_wordpress_payload(html: str) -> dict[str, str]:
    """A post artifact's bytes → the WordPress {title, content} pair. Pure.

    - Transport-hostile matter is dropped WHOLE first (`<style>`, `<script>`,
      comments) — the platform keeps the text of tags it strips, so removing
      the element is the only removal that works.
    - `content` is the content root's inner HTML: `<main>`, else `<article>`,
      else `<body>`. **No document-wide fallback** — an artifact with no
      resolvable root is REFUSED, not degraded.
    - `title` is the first <h1>'s text, moved OUT of the body (WordPress
      renders the title itself, so it would otherwise print twice).
    - yarnnn's editing grammar (`data-*`: block ids, arrangements, citations)
      is stripped — meaningless, and noisy, on a published page. Classes stay:
      `.kicker`/`.standfirst` degrade to plain paragraphs, which reads fine.
    - Everything else passes through VERBATIM. The member's material is not
      rewritten by transport (the ADR-621 D2 lesson, outbound edition).

    Raises PublishError when no content root resolves (ADR-628 D6).
    """
    cleaned = _strip_dropped_elements(html or "")

    body = _content_root(cleaned)
    if body is None:
        raise PublishError(
            "This file has no publishable content — a post needs a <main>, "
            "<article> or <body> section with something in it."
        )

    title = ""
    h1 = _H1_RE.search(body)
    if h1:
        title = _TAG_STRIP_RE.sub("", h1.group(1)).strip()
        body = body[: h1.start()] + body[h1.end():]

    body = _DATA_ATTR_RE.sub("", body).strip()
    if not _TAG_STRIP_RE.sub("", body).strip():
        raise PublishError("This post has no text to publish yet.")

    return {"title": title or "Untitled post", "content": body}


# ---------------------------------------------------------------------------
# The act
# ---------------------------------------------------------------------------

def _normalize_workspace_path(path: str) -> str:
    p = (path or "").strip()
    if not p.startswith("/workspace/"):
        p = "/workspace/" + p.lstrip("/")
    return p


def _decrypted_wordpress_token(auth: Any) -> Optional[str]:
    """The member's own WordPress token, or None. ADR-577: the ONE credential
    path — an agent caller gets None there, never a fallthrough here."""
    from integrations.core.tokens import get_token_manager
    from services.platform_credentials import resolve_platform_credential

    row = resolve_platform_credential(auth, "wordpress")
    if not row or not row.get("credentials_encrypted"):
        return None
    try:
        return get_token_manager().decrypt(row["credentials_encrypted"])
    except Exception:  # noqa: BLE001 — a bad ciphertext degrades to "not connected"
        logger.error("[PUBLISH] wordpress credential decrypt failed")
        return None


async def list_wordpress_sites(auth: Any) -> Optional[list[dict]]:
    """The member's publishable sites, or None when not connected.

    None ≠ [] deliberately: None is "connect WordPress first"; [] is the
    three-state story's state 2 ("your login has no site yet — a free one is
    two clicks away"). The surface renders each differently.
    """
    from integrations.core import wordpress_client

    token = _decrypted_wordpress_token(auth)
    if not token:
        return None
    return await wordpress_client.list_sites(token)


async def publish_post_to_wordpress(
    auth: Any,
    *,
    path: str,
    site_id: str,
    status: str = "publish",
) -> dict[str, Any]:
    """The member-clicked publish act (ADR-628 D2). Returns the receipt row.

    Raises PublishError with a member-readable reason on every refusal —
    honest refusals, never incorrect success (ADR-373 D6).
    """
    from integrations.core import wordpress_client
    from services.authored_substrate import write_revision
    from services.authoring import app_for_layout

    wpath = _normalize_workspace_path(path)
    user_id = (getattr(auth, "user_id", None) or "").strip()
    if not user_id:
        raise PublishError("No acting principal.")

    # 1. The artifact — the member's own reach (RLS-scoped client).
    res = (
        auth.client.table("workspace_files")
        .select("content, workspace_id")
        .eq("path", wpath)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows or not (rows[0].get("content") or "").strip():
        raise PublishError(f"Nothing to publish at {wpath}.")
    html = rows[0]["content"]

    # 2. Only the publish medium crosses. The Blogger app owns `post`
    # (ADR-627 D1); a deck or a stage leaving through this door would be a
    # category error the member cannot see from the URL alone.
    tmpl = re.search(r'data-template="([^"]+)"', html)
    owner = app_for_layout(tmpl.group(1)) if tmpl else None
    if owner != "blogger":
        raise PublishError(
            "Only a Blogger post can be published — this file is not one."
        )

    # 3. The member's own credential (agent callers already refused upstream).
    token = _decrypted_wordpress_token(auth)
    if not token:
        raise PublishError(
            "WordPress is not connected. Connect it under Settings → Connectors."
        )

    # 4. One post, one act. Composition REFUSES a non-conforming artifact
    # (ADR-628 D6) — the PublishError surfaces before anything leaves.
    payload = compose_wordpress_payload(html)
    result = await wordpress_client.create_post(
        token, site_id, title=payload["title"], content=payload["content"],
        status=status,
    )

    # 5. Would a reader actually reach it? (ADR-628 D7.) Best-effort: the
    # post IS live either way, so a failure here must never read as a publish
    # failure — the fact is simply absent from the receipt when unknown.
    reachable: Optional[bool] = None
    try:
        for s in (await wordpress_client.list_sites(token)) or []:
            if str(s.get("id")) == str(site_id):
                reachable = bool(s.get("public", True))
                break
    except Exception:  # noqa: BLE001
        logger.warning("[PUBLISH] site visibility unresolved for %s", site_id)

    # 6. The receipt — appended to the sidecar beside the post, as the
    # member's own attributed write. `_publish.yaml` is machine-read
    # (ADR-254 underscore rule); the FE renders it back as history.
    folder = wpath.rsplit("/", 1)[0]
    sidecar = f"{folder}/_publish.yaml"
    entry = {
        "platform": "wordpress",
        "site_id": str(site_id),
        "post_id": result["post_id"],
        "url": result["url"],
        "status": result["status"],
        "at": datetime.now(timezone.utc).isoformat(),
        "path": wpath,
    }
    if reachable is not None:
        # Recorded only when KNOWN — an absent key is "unresolved", never a
        # silent "fine". `status: publish` alone is true and useless when no
        # reader can reach the post.
        entry["publicly_readable"] = reachable
    try:
        import yaml

        prev = (
            auth.client.table("workspace_files")
            .select("content")
            .eq("path", sidecar)
            .limit(1)
            .execute()
        )
        existing: list = []
        if prev.data and (prev.data[0].get("content") or "").strip():
            loaded = yaml.safe_load(prev.data[0]["content"])
            if isinstance(loaded, list):
                existing = loaded
        existing.append(entry)
        write_revision(
            auth.client,
            user_id=user_id,
            path=sidecar,
            content=yaml.safe_dump(existing, sort_keys=False, allow_unicode=True),
            authored_by="operator",
            author_identity_uuid=user_id,
            message=f"published to WordPress ({result['status']}): {result['url']}",
            # The receipt is MADE FROM the post (ADR-628 D8). Without this
            # edge "what was published here?" is unanswerable at exactly the
            # moment the act becomes irrevocable — and a standing declaration
            # producing posts from sources will need the same edge to trace
            # a published piece back to what it was built from.
            derived_from=[wpath],
        )
    except Exception:  # noqa: BLE001
        # The post IS live — a receipt failure must not read as a publish
        # failure. Logged loudly instead; the member still gets the URL.
        logger.exception("[PUBLISH] receipt sidecar write failed for %s", wpath)

    return entry
