"""
Publish — the OUTBOUND seam (ADR-628 phase (a)).

The third disposition of platform reach: content leaving the workspace for an
external platform. Everything outbound crosses HERE — the gate
(`test_adr628_outbound_publish.py`) pins that no other module under `api/`
performs an outbound platform write. Its predecessor, the ADR-028
`integrations/exporters/` DestinationExporter stack, is DELETED (a fossil:
its one `.deliver()` caller was removed 2026-08-26; the connectors copy cited
it to promise an export capability no route could perform).

Phase (a) shape, held strictly:

  - MEMBER-CLICKED. The caller is a human principal on their own turn; the
    credential resolves through `platform_credentials.resolve_platform_credential`,
    which REFUSES an agent caller (ADR-577 D1) — so "no agent decides to
    publish" is structural, not convention.
  - ONE POST PER ACT. No fan-out, no batch.
  - RECEIPTED. Every publish appends to a `_publish.yaml` sidecar beside the
    artifact (machine format, ADR-254), written through `write_revision` as
    the member's own act — attributed, versioned, revertible like everything
    else.
  - The destination is chosen AT THE ACT, never stored on the connection
    (ADR-594 D1: a connection is consent + credential + aperture — no
    per-connection settings).

Two tenants (ADR-628 amendments 1 and 3): WordPress (a `post` artifact →
a blog post) and Slack (a prose file → a channel message). Each carries its
own composition CONTRACT (D6) and its own receipt; Slack also mechanizes the
D8 read-back (post, read the stored message back, diff).

Phase (b) (a standing declaration publishing without a click) is NOT here —
it begins only on phase (a)'s receipts AND a demonstrated round-trip, via ADR
amendment, with its own narrow non-agent identity (`system:publish-{platform}`).

The ONE exception to "every outbound write crosses here" is recorded, not
hidden: `platform_slack_send_to_channel` (services/platform_tools.py) is the
AGENT's audience send — a free-text message, gated by ADR-307 into the
proposal queue and executed by the member from there. It predates this seam
(ADR-304) and is receipted as a proposal, not a sidecar. The gate pins
`post_message`'s caller set to exactly those two modules.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

#: The platforms with a live MEMBER-CLICKED outbound write path. The ONE
#: reach structure (`services/reach_status.py`, ADR-644) derives the member's
#: door from this roster + `PUBLISH_DOORS` below, so the connectors page, Reach,
#: the lane frame and the `list_integrations` result cannot promise a write the
#: seam does not perform (the exporter-fossil defect).
PUBLISH_TARGETS: frozenset[str] = frozenset({"wordpress", "slack"})

#: The member's DOOR at each tenant (ADR-644 D1): the verb, the door's own
#: name, the pane it is mounted on, and what it takes — so the connectors
#: page, Reach, the lane frame and the tool result name the same thing
#: (ADR-638: name the THING). Every target has one, and the ADR-644 gate
#: asserts each door is mounted where it says (pane ↔ `app.slug`).
PUBLISH_DOORS: dict[str, dict[str, str]] = {
    "wordpress": {"verb": "publish", "door": "Publish", "pane": "Blogger", "takes": "a post"},
    "slack": {"verb": "send a file", "door": "Send to Slack", "pane": "Text", "takes": "a prose file (.md or .txt)"},
}


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
# Slack — the composition contract (ADR-628 amendment 3, 2026-09-07). Pure.
# ---------------------------------------------------------------------------
#
# A channel post IS prose. The composer takes markdown / plain text and emits
# Slack mrkdwn. What it will not take is refused at the ACT, by extension,
# before composition: a `post` is WordPress's shape (HTML with a content
# root), a deck / a stage / a binary have no channel form. Inside the
# contract every rule is one of: escape what the platform requires escaped,
# translate a markdown form to its mrkdwn form, or DROP a form Slack cannot
# render (tables become a code block so their alignment survives; a rule
# vanishes; an image the platform cannot fetch keeps its alt text). Fenced
# and inline code cross VERBATIM — the member's material is not rewritten by
# transport (ADR-621 D2, outbound edition).

#: The file types the Slack door takes — prose only.
SLACK_PROSE_EXTENSIONS: tuple[str, ...] = (".md", ".txt")
#: chat.postMessage's documented ceiling for `text`. Above it the platform
#: refuses (`msg_too_long`); the contract refuses FIRST, with the count, so
#: the member can cut rather than guess.
SLACK_TEXT_CEILING = 40_000
#: Above this many characters Slack folds the message behind "Show more".
#: Not a refusal — recorded on the receipt as `folded`, so "sent" and "read
#: at a glance" stay two different facts (the D7 shape).
SLACK_FOLD_THRESHOLD = 4_000
#: Bumped whenever the composition contract changes. A receipt names the
#: composer that produced it, so a later read-back diff is attributable.
SLACK_COMPOSER_VERSION = 1

_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\n.*?\n---[ \t]*\n", re.DOTALL)
_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")
_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_MD_H1_RE = re.compile(r"^#[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
_MD_HEADING_RE = re.compile(r"^#{2,6}[ \t]+(.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
_MD_BOLD_RE = re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1")
_MD_ITALIC_STAR_RE = re.compile(r"(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])")
_MD_STRIKE_RE = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~")
_MD_BULLET_RE = re.compile(r"^([ \t]*)[-*+][ \t]+", re.MULTILINE)
_MD_HR_RE = re.compile(r"^[ \t]*(?:-{3,}|\*{3,}|_{3,})[ \t]*$\n?", re.MULTILINE)
_BLANK_RUN_RE = re.compile(r"\n{3,}")
_BOLD_MARK = "\x00B\x00"


def _protect(text: str, pattern: re.Pattern, store: list[str], tag: str) -> str:
    def _keep(m: re.Match) -> str:
        store.append(m.group(0))
        return f"\x00{tag}{len(store) - 1}\x00"

    return pattern.sub(_keep, text)


def _restore(text: str, store: list[str], tag: str) -> str:
    return re.sub(
        rf"\x00{tag}(\d+)\x00", lambda m: store[int(m.group(1))], text
    )


def _tables_to_code(text: str) -> str:
    """Consecutive pipe-table lines → one fenced block. Slack renders no
    tables; a code block keeps the columns readable instead of collapsing
    them into a paragraph of pipes."""
    out: list[str] = []
    block: list[str] = []

    def flush() -> None:
        if block:
            out.append("```\n" + "\n".join(block) + "\n```")
            block.clear()

    for line in text.split("\n"):
        if line.lstrip().startswith("|"):
            block.append(line.strip())
        else:
            flush()
            out.append(line)
    flush()
    return "\n".join(out)


def compose_slack_message(source: str) -> dict[str, Any]:
    """A prose file's bytes → the Slack message. Pure.

    Returns {title, text, chars, folded}. `text` is what crosses; `title`
    (the first H1, if any) leads it as a bold line. Raises PublishError for an
    empty result and for a result over the platform ceiling (ADR-628 D6).
    """
    text = (source or "").replace("\r\n", "\n").replace("\r", "\n")
    text = _FRONTMATTER_RE.sub("", text, count=1)

    # 1. Code crosses verbatim — lift it out before any rule can touch it.
    fences: list[str] = []
    inline: list[str] = []
    text = _protect(text, _FENCE_RE, fences, "F")
    text = _protect(text, _INLINE_CODE_RE, inline, "I")

    # 2. HTML has no channel form; Slack requires these three escaped.
    text = _HTML_TAG_RE.sub("", text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # 3. Images: a fetchable one becomes a link; a workspace path keeps only
    #    its alt text — Slack cannot reach the substrate.
    def _image(m: re.Match) -> str:
        alt, src = m.group(1).strip(), m.group(2).strip()
        if src.startswith(("http://", "https://")):
            return f"<{src}|{alt or src}>"
        return f"_{alt}_" if alt else ""

    text = _MD_IMAGE_RE.sub(_image, text)
    text = _MD_LINK_RE.sub(lambda m: f"<{m.group(2).strip()}|{m.group(1).strip()}>", text)

    # 4. The first H1 is the title; it leaves the body and leads the message.
    title = ""
    h1 = _MD_H1_RE.search(text)
    if h1:
        title = h1.group(1).strip()
        text = text[: h1.start()] + text[h1.end():]
    # A heading's bold is MARKED, like bold below — emitted as `*x*` here it
    # would be read by the italic pass one step later and cross as `_x_`
    # (the gate's fixture caught exactly that).
    text = _MD_HEADING_RE.sub(lambda m: f"{_BOLD_MARK}{m.group(1).strip()}{_BOLD_MARK}", text)

    # 5. Emphasis: markdown bold → mrkdwn bold (marked first so the italic
    #    pass cannot read its stars), then single-star italic → underscore.
    text = _MD_BOLD_RE.sub(lambda m: f"{_BOLD_MARK}{m.group(2)}{_BOLD_MARK}", text)
    text = _MD_ITALIC_STAR_RE.sub(lambda m: f"_{m.group(1)}_", text)
    text = text.replace(_BOLD_MARK, "*")
    text = _MD_STRIKE_RE.sub(lambda m: f"~{m.group(1)}~", text)

    # 6. Structure Slack lacks: bullets get the glyph, rules vanish, tables
    #    become a code block.
    text = _MD_BULLET_RE.sub(lambda m: f"{m.group(1)}• ", text)
    text = _MD_HR_RE.sub("", text)
    text = _tables_to_code(text)

    text = _restore(text, inline, "I")
    text = _restore(text, fences, "F")
    text = _BLANK_RUN_RE.sub("\n\n", text).strip()

    if title:
        text = f"*{title}*\n\n{text}" if text else f"*{title}*"
    if not text.strip():
        raise PublishError("This file has no text to send yet.")
    chars = len(text)
    if chars > SLACK_TEXT_CEILING:
        raise PublishError(
            f"Too long for one Slack message — this file composes to {chars:,} "
            f"characters and Slack takes {SLACK_TEXT_CEILING:,}. Send a section, "
            "or share a link instead."
        )
    return {
        "title": title,
        "text": text,
        "chars": chars,
        "folded": chars > SLACK_FOLD_THRESHOLD,
    }


# ---------------------------------------------------------------------------
# Shared act machinery
# ---------------------------------------------------------------------------

def _normalize_workspace_path(path: str) -> str:
    p = (path or "").strip()
    if not p.startswith("/workspace/"):
        p = "/workspace/" + p.lstrip("/")
    return p


def _decrypted_token(auth: Any, platform: str) -> Optional[str]:
    """The member's own token for `platform`, or None. ADR-577: the ONE
    credential path — an agent caller gets None there, never a fallthrough
    here."""
    from integrations.core.tokens import get_token_manager
    from services.platform_credentials import resolve_platform_credential

    row = resolve_platform_credential(auth, platform)
    if not row or not row.get("credentials_encrypted"):
        return None
    try:
        return get_token_manager().decrypt(row["credentials_encrypted"])
    except Exception:  # noqa: BLE001 — a bad ciphertext degrades to "not connected"
        logger.error("[PUBLISH] %s credential decrypt failed", platform)
        return None


def _read_artifact(auth: Any, wpath: str) -> str:
    """The artifact's bytes through the member's OWN reach (RLS-scoped)."""
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
    return rows[0]["content"]


def _append_receipt(
    auth: Any, user_id: str, wpath: str, entry: dict[str, Any], *, message: str
) -> None:
    """Append one receipt to the `_publish.yaml` sidecar beside the artifact,
    as the member's own attributed write (`derived_from=[artifact]`, ADR-628
    D8). `_publish.yaml` is machine-read (ADR-254 underscore rule); the FE
    renders it back as history.

    A receipt failure must never read as a publish failure — the content IS
    live. Logged loudly instead; the member still gets the URL.
    """
    from services.authored_substrate import write_revision

    folder = wpath.rsplit("/", 1)[0]
    sidecar = f"{folder}/_publish.yaml"
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
            message=message,
            # The receipt is MADE FROM the artifact (ADR-628 D8). Without this
            # edge "what was published here?" is unanswerable at exactly the
            # moment the act becomes irrevocable — and a standing declaration
            # producing posts from sources will need the same edge to trace
            # a published piece back to what it was built from.
            derived_from=[wpath],
        )
    except Exception:  # noqa: BLE001
        logger.exception("[PUBLISH] receipt sidecar write failed for %s", wpath)


# ---------------------------------------------------------------------------
# WordPress — the first tenant
# ---------------------------------------------------------------------------

async def list_wordpress_sites(auth: Any) -> Optional[list[dict]]:
    """The member's publishable sites, or None when not connected.

    None ≠ [] deliberately: None is "connect WordPress first"; [] is the
    three-state story's state 2 ("your login has no site yet — a free one is
    two clicks away"). The surface renders each differently.
    """
    from integrations.core import wordpress_client

    token = _decrypted_token(auth, "wordpress")
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
    from services.authoring import app_for_layout

    wpath = _normalize_workspace_path(path)
    user_id = (getattr(auth, "user_id", None) or "").strip()
    if not user_id:
        raise PublishError("No acting principal.")

    # 1. The artifact — the member's own reach (RLS-scoped client).
    html = _read_artifact(auth, wpath)

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
    token = _decrypted_token(auth, "wordpress")
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

    # 6. The receipt.
    entry: dict[str, Any] = {
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
    _append_receipt(
        auth, user_id, wpath, entry,
        message=f"published to WordPress ({result['status']}): {result['url']}",
    )
    return entry


# ---------------------------------------------------------------------------
# Slack — the second tenant (ADR-628 amendment 3)
# ---------------------------------------------------------------------------

#: Slack's refusal codes → the member's words. The raw code never surfaces:
#: a refusal is a correct outcome and it must say what to do next.
_SLACK_REFUSALS: dict[str, str] = {
    "not_in_channel": "The yarnnn app isn't in #{name} yet — invite it there (/invite @yarnnn) and try again.",
    "channel_not_found": "That channel is not reachable from your Slack connection — pick one from the list.",
    "is_archived": "#{name} is archived — Slack does not take new messages there.",
    "msg_too_long": "Slack refused the message as too long — send a section instead.",
    "restricted_action": "Your Slack workspace's policy does not let the app post in #{name}.",
    "missing_scope": "Your Slack connection predates message sending — reconnect Slack under Settings → Connectors.",
    "invalid_auth": "Your Slack connection has expired — reconnect it under Settings → Connectors.",
    "token_revoked": "Your Slack connection was revoked — reconnect it under Settings → Connectors.",
}


def _slack_refusal(error: Optional[str], name: str) -> str:
    tmpl = _SLACK_REFUSALS.get(error or "")
    if tmpl:
        return tmpl.replace("{name}", name)
    return f"Slack refused the message ({error or 'unknown error'})."


def _norm_for_diff(text: str) -> str:
    return " ".join((text or "").split())


async def list_slack_channels(auth: Any) -> Optional[list[dict]]:
    """The member's channels, or None when not connected. Archived channels
    are dropped; `is_member` rides so the picker can say which private
    channels need the invite first."""
    from integrations.core.slack_client import get_slack_client

    token = _decrypted_token(auth, "slack")
    if not token:
        return None
    chans = await get_slack_client().list_channels(token, limit=200)
    return [
        {
            "id": c["id"],
            "name": c.get("name") or c["id"],
            "is_private": bool(c.get("is_private")),
            "is_member": bool(c.get("is_member")),
        }
        for c in chans
        if c.get("id") and not c.get("is_archived")
    ]


async def _slack_read_back(
    client: Any, token: str, channel_id: str, ts: str, sent: str
) -> tuple[str, Optional[str]]:
    """ADR-628 D8 — read the stored message back and diff it against what was
    sent. Three verdicts, never a silent absence: `matched`, `differs` (with
    the sizes), `unreadable` (with why)."""
    try:
        msg = await client.get_message(token, channel_id, ts)
    except Exception as exc:  # noqa: BLE001
        return "unreadable", f"read failed: {exc}"
    if not msg:
        return "unreadable", "no message stored at that timestamp"
    stored = str(msg.get("text") or "")
    if _norm_for_diff(stored) == _norm_for_diff(sent):
        return "matched", None
    return "differs", f"sent {len(sent)} chars, stored {len(stored)}"


async def publish_file_to_slack(
    auth: Any,
    *,
    path: str,
    channel_id: str,
) -> dict[str, Any]:
    """The member-clicked send act (ADR-628 D2, Slack edition). Returns the
    receipt row. Raises PublishError with a member-readable reason on every
    refusal — honest refusals, never incorrect success."""
    from integrations.core.slack_client import get_slack_client

    wpath = _normalize_workspace_path(path)
    user_id = (getattr(auth, "user_id", None) or "").strip()
    if not user_id:
        raise PublishError("No acting principal.")
    channel_id = (channel_id or "").strip()
    if not channel_id:
        raise PublishError("Pick a channel first.")

    # 1. Only prose crosses — decided by the file's type, before the read.
    leaf = wpath.rsplit("/", 1)[-1].lower()
    if not leaf.endswith(SLACK_PROSE_EXTENSIONS):
        raise PublishError(
            "Only a prose file (.md or .txt) can be sent to Slack — this file is not one."
        )

    # 2. The artifact — the member's own reach.
    source = _read_artifact(auth, wpath)

    # 3. The member's own credential (agent callers already refused upstream).
    token = _decrypted_token(auth, "slack")
    if not token:
        raise PublishError("Slack is not connected. Connect it under Settings → Connectors.")

    # 4. Composition REFUSES before anything leaves (D6).
    payload = compose_slack_message(source)

    # 5. The channel, resolved at the act. The install lacks
    # `chat:write.public`, so the app must be IN the channel: a public one is
    # joined here (join_channel's first caller); a private one it is not in
    # is refused with the remedy named.
    client = get_slack_client()
    info = await client.get_channel_info(token, channel_id)
    if not info.get("ok"):
        raise PublishError(_slack_refusal(info.get("error") or "channel_not_found", channel_id))
    ch = info.get("channel") or {}
    name = str(ch.get("name") or channel_id)
    if ch.get("is_archived"):
        raise PublishError(_slack_refusal("is_archived", name))
    if not ch.get("is_member"):
        joined = (not ch.get("is_private")) and await client.join_channel(token, channel_id)
        if not joined:
            raise PublishError(_slack_refusal("not_in_channel", name))

    # 6. One message, one act.
    result = await client.post_message(
        bot_token=token, channel_id=channel_id, text=payload["text"]
    )
    if not result.get("ok"):
        raise PublishError(_slack_refusal(result.get("error"), name))
    ts = str(result.get("ts") or "")

    # 7. Read it back (D8) and find its link (best-effort). The message IS
    # live either way; neither failure may read as a send failure.
    read_back, detail = await _slack_read_back(client, token, channel_id, ts, payload["text"])
    permalink: Optional[str] = None
    try:
        permalink = await client.get_permalink(token, channel_id, ts)
    except Exception:  # noqa: BLE001
        logger.warning("[PUBLISH] slack permalink unresolved for %s", ts)

    # 8. The receipt.
    entry: dict[str, Any] = {
        "platform": "slack",
        "channel_id": channel_id,
        "channel": f"#{name}",
        "ts": ts,
        "url": permalink,
        "status": "posted",
        "at": datetime.now(timezone.utc).isoformat(),
        "path": wpath,
        "chars": payload["chars"],
        "folded": payload["folded"],
        "read_back": read_back,
        "composer_version": SLACK_COMPOSER_VERSION,
    }
    if detail:
        entry["read_back_detail"] = detail
    _append_receipt(auth, user_id, wpath, entry, message=f"sent to Slack #{name}")
    return entry
