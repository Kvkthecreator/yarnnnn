"""Programs service helpers — program lifecycle + bundle fork.

ADR-244: parse_active_program_slug / strip_program_marker_from_mandate are shared
between routes/workspace.py (workspace state), routes/programs.py (activate/deactivate),
and routes/account.py (purge program preservation).

ADR-226: _fork_reference_workspace + helpers relocated here 2026-05-03 from
workspace_init.py. The fork is program-bundle logic, not initialization logic.
routes/programs.py and workspace_init.py both call fork_reference_workspace()
from here. Single implementation.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

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


# =============================================================================
# ADR-226: Reference-workspace fork (relocated from workspace_init.py 2026-05-03)
# =============================================================================


def _bundle_root_dir(program_slug: str) -> Path:
    """Resolve docs/programs/{slug}/reference-workspace/ from repo root."""
    return (
        Path(__file__).resolve().parent.parent.parent
        / "docs"
        / "programs"
        / program_slug
        / "reference-workspace"
    )


def _strip_tier_frontmatter(text: str) -> tuple[str, dict[str, Any]]:
    """Parse YAML frontmatter (if present) from a reference-workspace file.

    Per ADR-223 §5: tier metadata (tier:, prompt:, note:, optional:) is
    bundle-only — stripped before the file is written to operator's /workspace/.
    Returns (body_without_frontmatter, metadata_dict).
    """
    if not text.startswith("---\n"):
        return text, {}
    end_marker = text.find("\n---\n", 4)
    if end_marker < 0:
        return text, {}
    fm_text = text[4:end_marker]
    body = text[end_marker + 5:]
    metadata: dict[str, Any] = {}
    try:
        import yaml as _yaml
        parsed = _yaml.safe_load(fm_text)
        if isinstance(parsed, dict):
            metadata = parsed
    except Exception:
        pass
    if body.startswith("\n"):
        body = body[1:]
    return body, metadata


async def fork_reference_workspace(
    client: Any, user_id: str, program_slug: str
) -> dict[str, Any]:
    """Copy bundle's reference-workspace/ into operator's /workspace/.

    Per ADR-226: honors ADR-223 §5 three-tier file categorization:
      - canon: re-applied on every fork (operator edits preserved as prior
        revisions per ADR-209; no-op when content already matches).
      - authored: only applied if operator's file is still skeleton.
      - placeholder: only written on first fork; never overwritten.

    Written through UserMemory.write → authored_substrate.write_revision
    with authored_by="system:bundle-fork".

    Returns {"files_written": [...], "files_skipped": [...], "program_slug": slug}.
    """
    from services.workspace import UserMemory
    from services.bundle_reader import _load_manifest
    from services.workspace_utils import is_skeleton_content

    bundle_root = _bundle_root_dir(program_slug)
    if not bundle_root.is_dir():
        raise ValueError(
            f"Bundle reference-workspace not found: {bundle_root}. "
            f"Bundle '{program_slug}' may not exist or may not have a "
            f"reference-workspace/ directory."
        )

    manifest = _load_manifest(program_slug)
    if not manifest:
        raise ValueError(f"Bundle '{program_slug}' has no MANIFEST.yaml.")
    if manifest.get("status") not in ("active", "deferred"):
        raise ValueError(
            f"Bundle '{program_slug}' has status='{manifest.get('status')}'; "
            f"only active or deferred bundles can be forked."
        )

    um = UserMemory(client, user_id)
    files_written: list[str] = []
    files_skipped: list[str] = []

    bundle_files = sorted(
        list(bundle_root.rglob("*.md")) + list(bundle_root.rglob("*.yaml"))
    )
    for src_path in bundle_files:
        if src_path.name == "README.md" and src_path.parent == bundle_root:
            continue

        relative = src_path.relative_to(bundle_root).as_posix()
        target_path = relative

        try:
            raw = src_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning(f"[FORK] Failed to read {src_path}: {exc}")
            continue

        if src_path.suffix == ".yaml":
            body = raw
            tier = "canon"
        else:
            body, meta = _strip_tier_frontmatter(raw)
            tier = (meta.get("tier") or "placeholder").lower()
            if tier not in ("canon", "authored", "placeholder"):
                logger.warning(f"[FORK] Unknown tier '{tier}' for {src_path}; defaulting to placeholder")
                tier = "placeholder"

        existing = await um.read(target_path)
        should_write = False
        if existing is None:
            should_write = True
        elif tier == "canon":
            should_write = existing.strip() != body.strip()
        elif tier == "authored":
            should_write = (
                is_skeleton_content(existing, bundle_body=body)
                and existing.strip() != body.strip()
            )
        elif tier == "placeholder":
            should_write = False

        if should_write:
            await um.write(
                target_path,
                body,
                summary=f"Forked from {program_slug} bundle (tier={tier})",
                authored_by="system:bundle-fork",
                message=(
                    f"ADR-226: forked {src_path.name} from "
                    f"docs/programs/{program_slug}/reference-workspace/ "
                    f"(tier={tier})"
                ),
            )
            files_written.append(target_path)
            logger.info(f"[FORK] {target_path} (tier={tier}) ← {program_slug}/reference-workspace/{relative}")
        else:
            files_skipped.append(target_path)
            logger.info(f"[FORK] {target_path} (tier={tier}) — skipped (operator-authored or no-op)")

    return {
        "files_written": files_written,
        "files_skipped": files_skipped,
        "program_slug": program_slug,
    }
