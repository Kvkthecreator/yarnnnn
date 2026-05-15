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
      4b. Bundle's bolded operator-author prompt (`**Operator**: author this`)
          PLUS file is under 1500 chars (no substantive operator content beyond
          the template prompt itself) → skeleton. This catches the
          alpha-trader bundle's IDENTITY.md (~884 chars) and BRAND.md (~352
          chars) while preserving "authored" status for MANDATE.md (~3000
          chars of pre-filled Primary Action + Success Criteria + Boundary
          Conditions even though it also carries the template prompt).
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

    # Kernel-default workspace guide signature (ADR-281).
    # The no-program workspace guide (DEFAULT_WORKSPACE_GUIDE_MD in
    # services/orchestration.py) is written by workspace_init Phase 2 for
    # every workspace; bundle activation should overwrite via Phase 5 fork.
    # Without this signature check, the kernel-default is non-skeleton-shaped
    # (5350 bytes of legitimate prose) so the fork's is_skeleton_content
    # check returns False and the bundle guide doesn't write. Stable
    # discriminator: the kernel-default "## What this workspace contains"
    # section says "This workspace runs no program" — bundle-shipped guides
    # say "This workspace runs the <slug> program".
    if "this workspace runs no program" in lower:
        return True

    # Bundle template markers
    first_line = stripped.split("\n", 1)[0].lower()
    if "(template)" in first_line:
        return True
    # `_<not yet` is a kernel-default placeholder, always means skeleton.
    if "_<not yet" in lower:
        return True
    # Author-prompt markers — `"author here:"` (kernel default) and
    # `"**operator**: author this"` (bundle template) — only count as
    # skeleton when the file is *short enough* that the prompt represents
    # essentially all the content. Long files carrying these prompts
    # alongside substantive pre-filled sections (the alpha-trader bundle's
    # MANDATE.md ships ~4500 chars with an "Edge hypothesis" sub-section
    # whose prompt reads "Author here: in 2-4 sentences...") are still
    # operationally usable — they classify as authored.
    is_short_template = len(stripped) < 1500
    if is_short_template and "author here:" in lower:
        return True
    if is_short_template and "**operator**:" in lower and "author this" in lower:
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
