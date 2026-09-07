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


def build_text_posture(artifact_path: str, head: str) -> str:
    """The job overlay for a text-bound lane (ADR-571 D4).

    The lane is bound to ONE prose document. The job is that document —
    refined conversationally, written whole and honestly. No block grammar,
    no Studio machinery (ADR-456 D1's grade constraint).

    It DOES carry the three markdown reference forms (ADR-572 D17/D18 — image
    by path, mermaid fence, CSV snapshot under a provenance line). Measured
    2026-09-07: this posture named none of them and two bound runs retyped a
    CSV's figures with the source uncited — the toolbar's own snapshot shape
    minus the one line that makes it a citation. The `.html` citation grammar
    is a kernel constant every surface is handed; the `.md` grammar lived only
    in three FE insert functions, where no engine could read it. Here is where
    an app says how its artifact works (ADR-606 D3).

    Pure since ADR-606 D3: ``head`` is the artifact's current head, read ONCE
    by the lane kernel — this builder's private re-read (a second round-trip
    for the same bytes every turn) is deleted, the same fix the studio path
    made for itself in 2026-07.
    """
    leaf = artifact_path.rsplit("/", 1)[-1]
    rel = (
        artifact_path[len(_WORKSPACE_PREFIX):]
        if artifact_path.startswith(_WORKSPACE_PREFIX)
        else artifact_path
    )

    lines: list[str] = [
        "## Your pane — the Text app (a prose document)",
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
        "- Markdown refers to three things by keeping their content IN the"
        " file: an image by its workspace path — `![alt](marketing/assets/"
        "hero.png)`, never a URL or base64; a diagram as a ```mermaid fence,"
        " which renders as the diagram; figures from a CSV as a real markdown"
        " table under a provenance line — `_From `operation/q3.csv` ·"
        " snapshot 2026-09-07_`. That line IS the citation: it names the file"
        " and the day the rows were read, so no figure appears without its"
        " source and the next reader knows where to refresh it. An HTML"
        " citation (data-ref) is inert in a .md — never write one.",
        "- Write ONLY this document unless the member asks otherwise. When"
        " you author content FROM another file, cite it (derived_from).",
        "- The member edits the same document directly in their editor, and"
        " external connectors may revise it too — read the head fresh"
        " before you write; never assume your last write is current.",
        "- Small asks get small edits. Never rewrite the whole document to"
        " change a sentence: EditFile with the exact text you are changing"
        " is the ordinary act, and WriteFile is for a re-draft the member"
        " asked for.",
        "- When the frame says the member SELECTED something, it carries the"
        " span. Pass that anchor to EditFile and the edit is confined to"
        " their selection — the quoted excerpt is a clipped PREFIX and never"
        " tells you where the selection ends, so never infer its extent from"
        " the quote.",
    ]
    return "\n".join(lines)


def text_pane_posture(client: Any, user_id: str, artifact_path: str, artifact: str) -> str:
    """The ADR-606 D3 builder shape over the pure posture. ``client`` and
    ``user_id`` are part of the shared contract and deliberately unused —
    this app's whole job is the one document the kernel already read."""
    return build_text_posture(artifact_path, artifact)


# ── ADR-562 D3: the registration, beside the code it configures ───────────
# The resident is IDENTITY only — the engine follows Editor's own row in
# `agents_registry.AGENTS`, never a caller-supplied model.
# ADR-597 D2 — Text seats its OWN agent. Editor is a row of its own, not
# designer wearing a rename: one app, one voice. ADR-600 collapsed the
# register split, so Editor is simply an agent with `offered: False` — its
# home is this app.
# ADR-606 D3 — the job overlay is declared here, not branched in the kernel.
register_app("text", resident="editor", posture=text_pane_posture)
