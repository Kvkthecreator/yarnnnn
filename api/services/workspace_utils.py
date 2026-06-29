"""
Workspace utility helpers (workspace-init refactor 2026-05-03,
simplified 2026-05-17 per ADR-286).

Thin pure-Python helpers shared across workspace_init, workspace.py (routes),
and working_memory. No DB access; no async.

ADR-286 simplification (2026-05-17): kernel-default rescue patches deleted.
Pre-ADR-286 `is_skeleton_content` had to distinguish "kernel default that
should be overwritten by bundle-fork" from "operator-customized content
that should be preserved" — a heuristic that needed a new patch per kernel
default shape. Under ADR-286, the kernel writes ONLY kernel-universal paths
(no bundle ships them). Bundle-owned paths are bundle-fork-only. The
heuristic's kernel-default-detection axis is dissolved; only the bundle-
template-detection axis survives.
"""

from typing import Optional


def is_skeleton_content(content: Optional[str], bundle_body: Optional[str] = None) -> bool:
    """Return True if the file content is still a bundle template (operator hasn't authored).

    Used by three callers (semantics unchanged post-ADR-286):
      - workspace_init._fork_reference_workspace: bundle-body comparison
        (was operator-authored or still matches bundle template?)
      - routes/workspace._classify_file_state: surface display
        (skeleton / authored / missing)
      - working_memory._classify_activation_state: activation gate
        (MANDATE.md skeleton → post_fork_pre_author state)

    Detection layers (post-ADR-286 simplified set — bundle-template-detection only):
      1. Empty / whitespace-only → skeleton.
      2. Exact match to bundle_body (when provided) → skeleton.
      3. Bundle-template markers ("(template)" in first line, "_<not yet"
         placeholder) → skeleton.
      4. Bundle's bolded operator-author prompt (`**Operator**: author this`
         or kernel-default `Author here:` for legacy operator-edited files)
         PLUS file is under 1500 chars (no substantive operator content
         beyond the template prompt itself) → skeleton. This catches bundle
         template files where the operator has not yet replaced the prompt
         with their own content.

    Deleted post-ADR-286 (was kernel-default rescue, no longer needed):
      - `placeholder_phrases` ("not yet declared", "<!-- identity not yet")
      - Kernel-default Reviewer principles signature
      - Kernel-default workspace guide signature (`"this workspace runs no program"`)
      - Very-short-and-sparse rule (was browser-tz-injected About Me rescue)
    """
    if not content or not content.strip():
        return True

    stripped = content.strip()

    if bundle_body is not None and stripped == bundle_body.strip():
        return True

    # ADR-383: steward defaults (the kernel-default MANDATE/IDENTITY/principles
    # for the bare-Freddie workspace) carry a stable marker so a program-fork
    # REPLACES them with the bundle's content rather than skipping them as
    # "operator-authored prose". This re-introduces ONE deterministic kernel-
    # default discriminator (an exact-marker check, not the fuzzy rescue the
    # ADR-286 simplification removed). A steward default is overwrite-eligible.
    if "<!-- yarnnn:steward-default -->" in stripped.split("\n", 1)[0]:
        return True

    lower = stripped.lower()

    # Bundle template markers — `(template)` in first line + `_<not yet` placeholder.
    first_line = stripped.split("\n", 1)[0].lower()
    if "(template)" in first_line:
        return True
    if "_<not yet" in lower:
        return True

    # Author-prompt markers — bundle template files (`**Operator**: author this`)
    # and any legacy kernel-erased-by-operator files (`Author here:`) — only
    # count as skeleton when the file is short enough that the prompt
    # represents essentially all the content. Long files carrying these
    # prompts alongside substantive pre-filled sections (the alpha-trader
    # bundle's MANDATE.md ships ~4500 chars with an "Edge hypothesis"
    # sub-section whose prompt reads "Author here: in 2-4 sentences...")
    # are still operationally usable — they classify as authored.
    is_short_template = len(stripped) < 1500
    if is_short_template and "author here:" in lower:
        return True
    if is_short_template and "**operator**:" in lower and "author this" in lower:
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
