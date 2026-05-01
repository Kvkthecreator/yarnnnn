"""Programs service helpers — shared utilities for program lifecycle.

ADR-244: this module hosts logic shared between `routes/workspace.py`
(workspace state endpoint), `routes/programs.py` (activate/deactivate),
and `routes/account.py` (purge program preservation).

Functions here are pure: they read existing substrate (MANDATE.md heading
marker) and parse it. Substrate writes happen at the call site through
`UserMemory.write` so revision attribution stays at the operator's seat
per ADR-209.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# Bundle template heading shape produced by `_fork_reference_workspace`:
#   "# Mandate — alpha-trader (template)"
# The em-dash separator is intentional — kernel-default MANDATE.md (no
# program) uses "# Mandate" with no em-dash, so the parser distinguishes
# program-active workspaces from kernel-default workspaces by looking
# for the em-dash on the first heading line.
_TEMPLATE_HEADING_RE = re.compile(
    r"^#\s+\S+\s+—\s+(?P<slug>[a-z0-9][a-z0-9\-]*)\b",
    re.IGNORECASE,
)


def parse_active_program_slug(mandate_content: Optional[str]) -> Optional[str]:
    """Return the active program slug parsed from MANDATE.md, or None.

    The active program slug lives as a marker in the MANDATE.md first heading:
    `# Mandate — {slug} (template)`. Bundle forks write this heading at fork
    time per `_fork_reference_workspace` (ADR-226). The kernel-default
    MANDATE.md heading is just `# Mandate` (no em-dash).

    The parser is intentionally tolerant — it returns None for any shape it
    doesn't recognise, including:
      - empty / whitespace-only content
      - kernel-default heading (`# Mandate` with no em-dash)
      - operator-rewritten heading that no longer carries the marker
      - heading with em-dash but slug not in the bundle registry
        (the caller is responsible for validation against `_all_slugs()`;
        this function only parses, doesn't validate)

    Used by:
      - `routes/workspace.py::get_workspace_state` — surface signal
      - `routes/programs.py::deactivate_program` — read prior slug for response
      - `routes/account.py::clear_workspace` / `reset_account` — preserve
        program activation across L2/L4 purges per ADR-244 D4
    """
    if not mandate_content:
        return None

    for raw_line in mandate_content.splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith("# "):
            continue
        # First H1 only; subsequent ones are section headers.
        match = _TEMPLATE_HEADING_RE.match(stripped)
        if match:
            return match.group("slug")
        # First heading found but no marker — return None (kernel default
        # or operator rewrote the heading).
        return None
    return None


def strip_program_marker_from_mandate(mandate_content: str) -> str:
    """Return MANDATE.md content with the program marker removed.

    Rewrites `# Mandate — alpha-trader (template)` → `# Mandate`. Body
    untouched. Used by `POST /api/programs/deactivate` per ADR-244 D3 to
    sever the bundle's idempotent re-fork relationship without touching
    operator-authored content.

    If no marker is present, returns content unchanged. Idempotent.
    """
    if not mandate_content:
        return mandate_content

    lines = mandate_content.splitlines(keepends=True)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("# "):
            continue
        if _TEMPLATE_HEADING_RE.match(stripped):
            # Preserve the line-ending of the original line.
            ending = ""
            if line.endswith("\r\n"):
                ending = "\r\n"
            elif line.endswith("\n"):
                ending = "\n"
            # Extract the heading word (typically "Mandate" — preserve case).
            word = stripped.split()[1] if len(stripped.split()) >= 2 else "Mandate"
            lines[i] = f"# {word}{ending}"
        # First heading processed; stop.
        break

    return "".join(lines)
