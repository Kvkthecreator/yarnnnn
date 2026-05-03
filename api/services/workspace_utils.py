"""
Workspace utility helpers (workspace-init refactor 2026-05-03).

Thin pure-Python helpers shared across workspace_init, workspace.py (routes),
and working_memory. No DB access; no async.
"""

from typing import Optional


def is_skeleton_content(content: Optional[str], bundle_body: Optional[str] = None) -> bool:
    """Return True if the file content is still a kernel or bundle skeleton.

    Used by three callers with slightly different needs:
      - workspace_init._fork_reference_workspace: bundle-body comparison
        (was operator-authored or still matches bundle template?)
      - routes/workspace._classify_file_state: surface display
        (skeleton / authored / missing)
      - working_memory._classify_activation_state: activation gate
        (MANDATE.md skeleton → post_fork_pre_author state)

    Detection layers (applied in order):
      1. Empty / whitespace-only → skeleton.
      2. Exact match to bundle_body (when provided) → skeleton.
      3. Kernel-default placeholder phrases → skeleton.
      4. Bundle-template markers ("(template)" in first line,
         "Author here:", "_<not yet") → skeleton.
      5. Very-short-and-sparse rule (< 200 chars, no H2 section) → skeleton.
         Catches kernel-default files inflated by browser-tz injection
         (e.g. "# About Me\\n\\ntimezone: Asia/Seoul\\n").
    """
    if not content or not content.strip():
        return True

    stripped = content.strip()

    if bundle_body is not None and stripped == bundle_body.strip():
        return True

    lower = stripped.lower()

    placeholder_phrases = (
        "not yet declared",
        "not yet provided",
        "<!-- identity not yet",
        "<!-- brand not yet",
        "<!-- mandate not yet",
        "<!-- awareness",
    )
    if any(phrase in lower for phrase in placeholder_phrases) and len(stripped) < 800:
        return True

    # Kernel-default Reviewer principles signature
    if "this is the declared review framework for this workspace" in lower:
        return True

    # Bundle template markers
    first_line = stripped.split("\n", 1)[0].lower()
    if "(template)" in first_line:
        return True
    if "author here:" in lower or "_<not yet" in lower:
        return True

    # Very-short-and-sparse: no H2 sections and under 200 chars
    if len(stripped) < 200:
        h2_count = sum(1 for line in stripped.split("\n") if line.startswith("## "))
        if h2_count == 0:
            return True

    return False


def classify_file_state(content: Optional[str]) -> str:
    """Classify a workspace file as 'missing', 'skeleton', or 'authored'.

    Surface-facing wrapper over is_skeleton_content for the
    Settings → Workspace substrate status panel (ADR-244).
    """
    if content is None:
        return "missing"
    return "skeleton" if is_skeleton_content(content) else "authored"
