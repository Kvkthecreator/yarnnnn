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


async def _populate_occupant_for_runtime(um: Any, program_slug: str) -> None:
    """ADR-284 D3: write OCCUPANT.md with runtime-truth-aligned occupant identity.

    Pre-ADR-284 the bundle template shipped `occupant_class: human` as a
    hardcoded default. This produced substrate-runtime drift in alpha
    workspaces where AI ran the seat — OCCUPANT.md said "human" but every
    judgment-mode fire was attributed `reviewer:ai:reviewer-sonnet-v8`.

    Current alpha state: AI is the runtime occupant on every workspace. The
    fork populates OCCUPANT.md with the AI occupant identity, including a
    `delegation_charter` block that mirrors AUTONOMY.md's delegation level at
    the seat level (so the Reviewer can perceive at every wake what it's
    authorized to do without operator presence).

    Future shape (deferred per ADR-284 D10): when explicit human-occupant
    activation lands as an operator-UX option, this function branches on the
    activation-time signal. For now, AI is the structural default.

    Written through UserMemory.write with authored_by="system:occupant-fork"
    per ADR-209 attribution.
    """
    from datetime import datetime, timezone

    # Import locally to avoid circular dependency at module load.
    from agents.reviewer_agent import REVIEWER_MODEL_IDENTITY

    activated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # REVIEWER_MODEL_IDENTITY is "ai:reviewer-sonnet-v8" (prefix included);
    # the occupant field uses the same string for symmetry with the
    # authored_by attribution surfaced in workspace_file_versions.
    occupant_body = f"""---
occupant: {REVIEWER_MODEL_IDENTITY}
occupant_class: ai
activated_at: {activated_at}
activated_by: system:bundle-fork
delegation_charter:
  source: /workspace/context/_shared/AUTONOMY.md
  posture: read AUTONOMY.md at every wake; render verdicts within declared ceiling
config: {{}}
---

# Review Seat — Current Occupant (ADR-284 runtime-truth-aligned)

This file declares who currently fills the Reviewer seat. The seat is the
architectural role (see `IDENTITY.md`); the **occupant** is who fills it
right now. Per FOUNDATIONS Derived Principle 14, the seat persists and the
occupant rotates.

The current occupant is **AI** (`{REVIEWER_MODEL_IDENTITY}`), populated by
`services.programs.fork_reference_workspace` at bundle-activation time per
ADR-284 D3. This was the structural default for every alpha-{program_slug}
workspace at activation — the operator delegated the seat to the AI to run
in their absence per FOUNDATIONS Axiom 2 v8.4 ("operator-as-Reviewer is the
personified AI agent rendering the operator's judgment function in the
human's absence").

The `delegation_charter` block above names what this AI occupant is
authorized to do: read AUTONOMY.md at every wake, render verdicts within
the operator's declared ceiling. The operator can always override via the
Queue. Rotation is a substrate write (edit the `occupant:` field via chat
with YARNNN, or by direct edit through the cockpit); each rotation appends
to `handoffs.md`.

Occupant-class taxonomy:
- `human:<user_id>` — the operator via approval UX (future activation shape)
- `ai:<model>-<version>` — current alpha state
- `external:<service>-<identifier>` — an external AI service via adapter
- `impersonated:<admin>-as-<persona>` — admin alpha-stress-testing
"""
    await um.write(
        "review/OCCUPANT.md",
        occupant_body,
        summary=f"OCCUPANT runtime-population for {program_slug} (ADR-284)",
        authored_by="system:occupant-fork",
        message=(
            f"populated OCCUPANT.md with runtime occupant identity "
            f"({REVIEWER_MODEL_IDENTITY}) per ADR-284 D3"
        ),
    )


async def fork_reference_workspace(
    client: Any, user_id: str, program_slug: str
) -> dict[str, Any]:
    """Copy bundle's reference-workspace/ into operator's /workspace/.

    Per ADR-261 D6 + ADR-262 D6: the three-tier ``canon | authored |
    placeholder`` system from ADR-226/ADR-223 §5 is dissolved. Bundle
    files are markdown the operator owns; attribution captures the
    distinction between bundle-forked vs operator-edited content
    (per ADR-209: ``authored_by="system:bundle-fork"`` vs
    ``authored_by="operator"``).

    The fork rule is one decision per file:

      - File doesn't exist in operator's workspace → write the bundle copy.
      - File exists but is still skeleton (per workspace_utils.is_skeleton_content,
        which compares against the bundle copy) → write the bundle copy
        (operator hasn't customized yet — refresh from bundle).
      - File exists and operator has customized → skip (preserve operator
        content; the bundle update is available in the bundle's git
        history if the operator wants to merge manually).

    Bundle files are copied verbatim. They contain no tier frontmatter
    (stripped from bundle source files in Phase D.2). Operator's view
    of the file is exactly what's in the bundle.

    Written through UserMemory.write → authored_substrate.write_revision
    with authored_by="system:bundle-fork".

    Post-fork: if the bundle contained ``/workspace/_recurrences.yaml``,
    ``materialize_scheduling_index`` is called once to populate the thin
    `tasks` scheduling index. Without this, the scheduler can't see any
    of the just-forked recurrences until a manual materialize step
    (operator harness, scheduler tick, etc.). Per ADR-261 D3 the YAML is
    truth and the table is the index — the index has to be built before
    the scheduler can query it.

    Returns ``{"files_written": [...], "files_skipped": [...],
    "program_slug": slug, "scheduling_index_rows": N}``.
    """
    from services.bundle_reader import _load_manifest
    from services.conventions import RECURRENCES_PATH
    from services.scheduling import materialize_scheduling_index
    from services.workspace import UserMemory
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
            body = src_path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning(f"[FORK] Failed to read {src_path}: {exc}")
            continue

        existing = await um.read(target_path)
        if existing is None:
            should_write = True
        elif is_skeleton_content(existing, bundle_body=body):
            should_write = True
        else:
            should_write = False

        if should_write:
            await um.write(
                target_path,
                body,
                summary=f"Forked from {program_slug} bundle",
                authored_by="system:bundle-fork",
                message=(
                    f"forked {src_path.name} from "
                    f"docs/programs/{program_slug}/reference-workspace/ "
                    f"(per ADR-261 D6 + ADR-262 D6)"
                ),
            )
            files_written.append(target_path)
            logger.info(f"[FORK] {target_path} ← {program_slug}/reference-workspace/{relative}")
        else:
            files_skipped.append(target_path)
            logger.info(f"[FORK] {target_path} — skipped (operator-customized)")

    # ADR-284 (2026-05-17): Reviewer seat-occupant runtime-truth alignment.
    # Pre-ADR-284 the bundle always shipped OCCUPANT.md with
    # `occupant_class: human` — produced substrate-runtime drift in alpha
    # workspaces where AI ran the seat. Post-fork we overwrite the bundle's
    # template-shaped OCCUPANT.md with runtime occupant identity. Current
    # alpha state: AI is the runtime occupant on every workspace.
    # Future-shape (deferred): explicit human-occupant declaration honored
    # at activation time via operator UX; the kernel branches here.
    occupant_path = "review/OCCUPANT.md"
    if occupant_path in files_written or occupant_path in files_skipped:
        await _populate_occupant_for_runtime(um, program_slug)
        if occupant_path not in files_written:
            files_written.append(occupant_path)

    # Materialize the scheduling index when the fork touched the canonical
    # recurrences YAML. The YAML is truth (ADR-261 D3); the `tasks` table is
    # the index the scheduler queries. Without this, the freshly-forked
    # workspace has live recurrence declarations on disk but zero rows in
    # the index — the scheduler can't see them. Idempotent on no-op writes;
    # safe to call even if no recurrences were written this fork (returns 0).
    recurrences_relative = RECURRENCES_PATH.lstrip("/").removeprefix("workspace/")
    fork_touched_recurrences = (
        recurrences_relative in files_written
        or recurrences_relative in files_skipped
    )
    scheduling_index_rows = 0
    if fork_touched_recurrences:
        try:
            scheduling_index_rows = await materialize_scheduling_index(client, user_id)
            logger.info(
                f"[FORK] materialized scheduling index for {user_id[:8]}: "
                f"{scheduling_index_rows} rows"
            )
        except Exception as exc:
            # Materialization failure is not fatal — the scheduler's next
            # tick will recover. But log loudly so the gap is visible.
            logger.warning(
                f"[FORK] materialize_scheduling_index failed for {user_id[:8]}: {exc}"
            )

    return {
        "files_written": files_written,
        "files_skipped": files_skipped,
        "program_slug": program_slug,
        "scheduling_index_rows": scheduling_index_rows,
    }
