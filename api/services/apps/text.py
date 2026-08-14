"""The Text app (ADR-571) — the dedicated surface for the prose currency.

Docs-shaped and deliberately small: the app owns no namespace, no layouts,
no templates — its artifact is any prose document (.md/.markdown/.txt) in
the workspace, and its canvas is a plain-text editor. What lives here:

- the app's REGISTRATION (ADR-562: residency declared where the app lives).
  ``name="Editor"`` is the app's own label for the designer resident — the
  exact Docs/"Writer" shape; no new agent row is minted.
- ``build_text_posture`` — the bound lane's JOB overlay (ADR-567 D4's
  mechanism, ADR-571 D4's branch). Without it the lane falls through to
  ``build_studio_posture``, which lifts ``data-template`` from the artifact
  — an .md has none, silently resolves to ``document``, and the colleague
  would be handed an HTML-block contract for a markdown file.
"""

from __future__ import annotations

from typing import Any

from services.authoring import register_app

_WORKSPACE_PREFIX = "/workspace/"


def _read_file(client: Any, user_id: str, path: str) -> str:
    from services.workspace_context import substrate_scope_filter

    try:
        res = (
            client.table("workspace_files")
            .select("content")
            .eq(*substrate_scope_filter(user_id))
            .eq("path", path)
            .limit(1)
            .execute()
        )
        return (res.data[0].get("content") or "") if res.data else ""
    except Exception:  # noqa: BLE001 — the posture degrades to "unread", never raises
        return ""


def build_text_posture(client: Any, user_id: str, artifact_path: str) -> str:
    """The job overlay for a text-bound lane (ADR-571 D4).

    The lane is bound to ONE prose document. The job is that document —
    read fresh, refined conversationally, written whole and honestly. No
    block grammar, no Studio machinery (ADR-456 D1's grade constraint).
    """
    leaf = artifact_path.rsplit("/", 1)[-1]
    rel = (
        artifact_path[len(_WORKSPACE_PREFIX):]
        if artifact_path.startswith(_WORKSPACE_PREFIX)
        else artifact_path
    )
    head = _read_file(client, user_id, artifact_path)

    lines: list[str] = [
        "## Your desk — the Text app (a prose document)",
        "",
        f"You are bound to ONE document: {rel}",
        "",
        "THE DOCUMENT'S CURRENT HEAD"
        + (":" if head.strip() else " — EMPTY (nothing written yet):"),
    ]
    if head.strip():
        lines.append(head)
    lines += [
        "",
        "THE JOB:",
        f"- This document ({leaf}) is the member's working prose — a"
        " transcript, a brief, notes, a draft. Refine it WITH them:"
        " tighten, restructure, extend, correct — always conversationally,"
        " stating what you changed and why.",
        "- Write the document as plain markdown, WHOLE and honest — no HTML,"
        " no block ids, no data-* attributes, no Studio machinery. Prose"
        " documents are .md (the format discipline).",
        "- Write ONLY this document unless the member asks otherwise. When"
        " you author content FROM another file, cite it (derived_from).",
        "- The member edits the same document directly in their editor, and"
        " external connectors may revise it too — read the head fresh"
        " before you write; never assume your last write is current.",
        "- Small asks get small edits. Never rewrite the whole document to"
        " change a sentence.",
    ]
    return "\n".join(lines)


# ── ADR-562 D3: the registration, beside the code it configures ───────────
# The resident is IDENTITY only — the engine follows the designer row in
# KERNEL_AGENTS, never a caller-supplied model. "Editor" is the app's name
# for that resident (the Docs/"Writer" shape): Writer lives in Docs; Editor
# lives in Text.
register_app("text", resident="designer", name="Editor")
