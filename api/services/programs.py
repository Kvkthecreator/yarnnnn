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


def resolve_active_program_slug(mandate_content: Optional[str]) -> Optional[str]:
    """Parse the active program slug from MANDATE.md AND validate it against
    the bundle registry. Returns the slug only when it's a registered bundle.

    This is the validated wrapper around `parse_active_program_slug` — the
    parse-then-membership-check pairing both the workspace-state surface
    (`routes/workspace.py`) and working memory (`working_memory.py`) need.
    Singular implementation: the parse/validate dance lives here once, not
    re-inlined per caller (the divergence that let a stale call site silently
    null the slug on one surface while the other stayed correct).
    """
    try:
        from services.bundle_reader import _all_slugs

        candidate = parse_active_program_slug(mandate_content)
        if candidate and candidate in _all_slugs():
            return candidate
    except Exception:  # pragma: no cover — defensive; never block the read
        pass
    return None


def compute_capability_gaps(
    program_slug: Optional[str], connected_platforms: set[str]
) -> list[dict]:
    """Return the active bundle's required-platform capability gaps.

    For each capability in the program's manifest that declares
    `requires_connection: <platform>`, emit one gap row noting whether that
    platform is currently connected. Deduped on (capability-name, platform).

    Empty list when:
      - no active program (`program_slug` is None)
      - active program has no required-platform capabilities
      - (gaps with `connected: True` are still returned — the caller decides
        whether "connected" counts as a gap; the surface renders N/M connected)

    Format: [{"capability": str, "platform": str, "connected": bool}, ...].

    Single source of the manifest-walk logic — both `routes/workspace.py`
    (surface) and `working_memory.py` (prompt signal) consume this. Callers
    fetch `connected_platforms` themselves (the surface via the RLS client,
    working memory from its already-fetched platform list) and map the dict
    into their own response shape.
    """
    if not program_slug:
        return []
    try:
        from services.bundle_reader import _load_manifest

        manifest = _load_manifest(program_slug) or {}
        gaps: list[dict] = []
        seen: set[tuple] = set()
        for cap in manifest.get("capabilities") or []:
            req = cap.get("requires_connection")
            if not req:
                continue
            key = (cap.get("name") or "", req)
            if key in seen:
                continue
            seen.add(key)
            gaps.append({
                "capability": cap.get("name") or req,
                "platform": req,
                "connected": req in connected_platforms,
            })
        return gaps
    except Exception:  # pragma: no cover — defensive; never block the read
        return []


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


async def _seed_recurrences_from_preferences(
    client: Any,
    user_id: str,
    program_slug: str,
    bundle_version: str,
) -> tuple[list[str], list[str]]:
    """Seed _recurrences.yaml with operator-active deliverable preferences.

    Per ADR-275 D9 (2026-05-21 amendment).

    The contract-shape gap ADR-275 D9 closes: `_preferences.yaml` is
    operator-declaration-shape (operator names what they want), but the
    original D5 framing put its honoring mechanism in Reviewer-judgment-
    shape (Reviewer reconciles every wake). Every other operator-
    declaration substrate file (MANDATE, IDENTITY, BRAND, _risk,
    _operator_profile, _universe) has its content honored at activation
    deterministically. This helper restores shape-symmetry for
    `_preferences.yaml`.

    For each `active: true` deliverable preference in
    `/workspace/contract/_preferences.yaml` whose `slug` is NOT
    yet a recurrence in `/workspace/_recurrences.yaml`, this helper
    appends a new recurrence entry with:
      - mode: judgment
      - schedule: <preference.cadence>
      - prompt: built from the spec at preference.spec (capability-library
        skills.md analog)
      - authored_by="system:bundle-fork-from-preferences" (new ADR-209
        actor sub-type, distinct from system:bundle-fork and reviewer:...)

    Idempotency: if a slug already exists as a recurrence (regardless of
    who authored it — operator, Reviewer, prior bundle-fork), this helper
    does NOT overwrite. Operator-edited or Reviewer-authored cadences for
    the same slug are preserved.

    Returns (slugs_seeded, slugs_skipped_already_present). Caller writes
    `_recurrences.yaml` once at the end with the appended content.

    Skips silently if `_preferences.yaml` is missing or malformed.
    Reviewer reconciliation of subsequent operator preference CHANGES
    (cadence edits, active flips) per ADR-275 D10 is unchanged and
    happens at runtime via Schedule(update|pause|archive).
    """
    import yaml

    from services.conventions import RECURRENCES_PATH
    from services.workspace import UserMemory
    from services.workspace_paths import CONTRACT_PREFERENCES_PATH

    um = UserMemory(client, user_id)

    # Read post-fork preferences + current recurrences.
    preferences_yaml = await um.read(CONTRACT_PREFERENCES_PATH)
    if not preferences_yaml:
        logger.info(
            f"[FORK:D9] no _preferences.yaml for {user_id[:8]}/{program_slug}; "
            f"skipping deliverable-cadence seeding"
        )
        return [], []

    # Strip ADR-261-style tier frontmatter from the .yaml body before yaml.safe_load.
    pref_body = preferences_yaml
    if pref_body.lstrip().startswith("---"):
        parts = pref_body.split("---", 2)
        if len(parts) >= 3:
            pref_body = parts[2]

    try:
        pref_doc = yaml.safe_load(pref_body) or {}
    except yaml.YAMLError as exc:
        logger.warning(
            f"[FORK:D9] _preferences.yaml parse failed for {user_id[:8]}: {exc}; "
            f"skipping deliverable-cadence seeding"
        )
        return [], []

    declared = pref_doc.get("deliverable_preferences") or []
    active_prefs = [
        p for p in declared
        if isinstance(p, dict) and p.get("active") is True and p.get("slug")
    ]
    if not active_prefs:
        return [], []

    recurrences_relative = RECURRENCES_PATH.lstrip("/").removeprefix("workspace/")
    recurrences_yaml = await um.read(recurrences_relative)
    if not recurrences_yaml:
        logger.warning(
            f"[FORK:D9] _recurrences.yaml missing for {user_id[:8]}/{program_slug}; "
            f"cannot seed deliverable cadences"
        )
        return [], []

    # Inventory existing slugs in recurrences (regardless of who authored).
    try:
        rec_doc = yaml.safe_load(recurrences_yaml) or {}
        existing_slugs = {
            r.get("slug") for r in (rec_doc.get("recurrences") or [])
            if isinstance(r, dict) and r.get("slug")
        }
    except yaml.YAMLError as exc:
        logger.warning(
            f"[FORK:D9] _recurrences.yaml parse failed for {user_id[:8]}: {exc}; "
            f"skipping seeding to avoid clobber"
        )
        return [], []

    seeded: list[str] = []
    skipped: list[str] = []
    for pref in active_prefs:
        slug = pref["slug"]
        if slug in existing_slugs:
            skipped.append(slug)
            continue

        # Read the spec the preference points at. The spec is the
        # capability-library entry (Claude Code skills.md analog). Path
        # is workspace-absolute in the preference; convert to relative
        # for um.read.
        spec_path_abs = pref.get("spec", "")
        spec_relative = spec_path_abs.lstrip("/").removeprefix("workspace/")
        spec_content = await um.read(spec_relative) if spec_relative else None

        cadence = pref.get("cadence")
        description = pref.get("description") or f"Deliverable: {slug}"

        # Build the recurrence prompt from the spec. The prompt instructs
        # the Reviewer to produce the deliverable per the spec's schema.
        # If the spec is missing, build a minimal prompt that references
        # the spec path for the Reviewer to read at fire time.
        if spec_content:
            prompt_body = (
                f"Produce the {slug} deliverable per the capability spec at "
                f"{spec_path_abs}. Read the spec for output schema, sections, "
                f"and quality criteria. Write the composed output to the "
                f"slug-templated path per CONVENTIONS.md. Update "
                f"/workspace/persona/standing_intent.md with what you're "
                f"watching for in the next cycle per ADR-284 + principles.md "
                f'"Default posture".\n\n'
                f"This recurrence was seeded at activation from operator "
                f"`_preferences.yaml` declaration per ADR-275 D9. Operator "
                f"can edit the cadence or active flag in `_preferences.yaml`; "
                f"on operator preference CHANGE, the Reviewer reconciles "
                f"via Schedule(update|pause|archive) per ADR-275 D10."
            )
        else:
            prompt_body = (
                f"Produce the {slug} deliverable. Read the capability spec at "
                f"{spec_path_abs} (referenced by operator preference but not yet "
                f"present in the workspace; if missing, surface a Clarify to "
                f"the operator). Update standing_intent.md per ADR-284.\n\n"
                f"Seeded at activation per ADR-275 D9."
            )

        # Append a new entry to recurrences_yaml. We write idiomatic YAML
        # rather than re-serializing the whole doc (preserves operator
        # comments + ordering for existing entries).
        new_entry_yaml = _format_recurrence_entry_yaml(
            slug=slug,
            schedule=cadence,
            mode="judgment",
            prompt=prompt_body,
            display_name=description,
        )
        recurrences_yaml = recurrences_yaml.rstrip() + "\n\n" + new_entry_yaml + "\n"

        await um.write(
            recurrences_relative,
            recurrences_yaml,
            summary=f"Seed deliverable-cadence recurrence {slug} from _preferences.yaml",
            authored_by="system:bundle-fork-from-preferences",
            message=(
                f"seeded recurrence '{slug}' at activation from operator "
                f"`_preferences.yaml` declaration (cadence={cadence}, "
                f"spec={spec_path_abs}, bundle={program_slug} v{bundle_version}) "
                f"per ADR-275 D9"
            ),
        )
        seeded.append(slug)
        existing_slugs.add(slug)  # next iteration sees it as present
        logger.info(
            f"[FORK:D9] seeded recurrence '{slug}' for {user_id[:8]}/{program_slug} "
            f"from _preferences.yaml (cadence={cadence})"
        )

    return seeded, skipped


def _format_recurrence_entry_yaml(
    *,
    slug: str,
    schedule: Any,
    mode: str,
    prompt: str,
    display_name: str,
) -> str:
    """Format a single recurrence entry as YAML text for append.

    Output matches the hand-authored bundle reference _recurrences.yaml
    style (2-space indent under `recurrences:` top key, schedule as
    quoted string or list, mode field, prompt as `|` block scalar).
    """
    # Schedule: quote if string, render as inline list if list.
    if isinstance(schedule, list):
        sched_yaml = "[" + ", ".join(f'"{s}"' for s in schedule) + "]"
    else:
        sched_yaml = f'"{schedule}"'

    # Indent prompt body by 6 spaces (4 for entry + 2 for prompt key block).
    prompt_lines = prompt.splitlines() or [""]
    prompt_indented = "\n".join(f"      {line}".rstrip() for line in prompt_lines)

    entry = (
        f"  # ── {slug} — operator-declared deliverable (ADR-275 D9 seeded) ──\n"
        f"  - slug: {slug}\n"
        f"    schedule: {sched_yaml}\n"
        f"    mode: {mode}\n"
        f"    display_name: \"{display_name}\"\n"
        f"    prompt: |\n"
        f"{prompt_indented}"
    )
    return entry


async def _populate_occupant_for_runtime(um: Any, program_slug: str) -> None:
    """ADR-284 D3: write OCCUPANT.md with runtime-truth-aligned occupant identity.

    Pre-ADR-284 the bundle template shipped `occupant_class: human` as a
    hardcoded default. This produced substrate-runtime drift in alpha
    workspaces where AI ran the seat — OCCUPANT.md said "human" but every
    judgment-mode fire was attributed `reviewer:ai:freddie-sonnet-v8`.

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

    # ADR-315: import the occupant identity from the published contract
    # (pure data, no circular risk) rather than the occupant implementation.
    from agents.occupant_contract import FREDDIE_MODEL_IDENTITY

    activated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # FREDDIE_MODEL_IDENTITY is "ai:freddie-sonnet-v8" (prefix included);
    # the occupant field uses the same string for symmetry with the
    # authored_by attribution surfaced in workspace_file_versions.
    occupant_body = f"""---
occupant: {FREDDIE_MODEL_IDENTITY}
occupant_class: ai
activated_at: {activated_at}
activated_by: system:bundle-fork
delegation_charter:
  source: /workspace/governance/AUTONOMY.md
  posture: read AUTONOMY.md at every wake; render verdicts within declared ceiling
config: {{}}
---

# Review Seat — Current Occupant (ADR-284 runtime-truth-aligned)

This file declares who currently fills the Reviewer seat. The seat is the
architectural role (see `IDENTITY.md`); the **occupant** is who fills it
right now. Per FOUNDATIONS Derived Principle 14, the seat persists and the
occupant rotates.

The current occupant is **AI** (`{FREDDIE_MODEL_IDENTITY}`), populated by
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
        "persona/OCCUPANT.md",
        occupant_body,
        summary=f"OCCUPANT runtime-population for {program_slug} (ADR-284)",
        authored_by="system:occupant-fork",
        message=(
            f"populated OCCUPANT.md with runtime occupant identity "
            f"({FREDDIE_MODEL_IDENTITY}) per ADR-284 D3"
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

    Per ADR-292 v3 D9–D10: bundle files divide into two architectural
    classes — config (operationally load-bearing; `_recurrences.yaml`,
    `_hooks.yaml`) and prose (operator-authored substrate). Per-file
    decision tree:

      - File doesn't exist in operator's workspace → write the bundle copy.
      - File exists but is still skeleton (per workspace_utils.is_skeleton_content,
        which compares against the bundle copy) → write the bundle copy
        (operator hasn't customized yet — refresh from bundle).
      - File exists, equals bundle body → already aligned, skip (no-op).
      - File exists, operator-edited, **and is a CONFIG_PATHS file**
        (`_recurrences.yaml` or `_hooks.yaml` per ADR-292 v3 D9) →
        auto-overwrite-with-backup: write operator's prior content to
        `system/conflict-backups/{ran_at}/{relative}` (ADR-320 relocation)
        attributed `system:substrate-update`, then write bundle's new content to the
        live path attributed `system:bundle-fork`. The conflict is recorded
        in the returned `config_conflicts` list. This preserves operator
        intent (backup) while letting the kernel's shape-constraints reach
        the live workspace.
      - File exists, operator-edited prose → skip (preserve operator content;
        bundle improvements are available in git history if the operator
        wants to merge manually).

    Bundle files are copied verbatim. Operator's view of a written file is
    exactly what's in the bundle.

    Written through UserMemory.write → authored_substrate.write_revision
    with appropriate attribution (`system:bundle-fork` for bundle writes;
    `system:substrate-update` for backup writes per D10).

    Post-fork: if the bundle contained ``/workspace/_recurrences.yaml``,
    ``materialize_scheduling_index`` is called once to populate the thin
    `tasks` scheduling index. Without this, the scheduler can't see any
    of the just-forked recurrences until a manual materialize step
    (operator harness, scheduler tick, etc.). Per ADR-261 D3 the YAML is
    truth and the table is the index — the index has to be built before
    the scheduler can query it.

    Returns ``{"files_written": [...], "files_skipped": [...],
    "config_conflicts": [...], "program_slug": slug,
    "scheduling_index_rows": N, "bundle_version": str | None}``.

    Each entry of ``config_conflicts`` is a dict ``{path, backup_path,
    bundle_version}`` matching the ``ConflictedFile`` dataclass shape in
    `services.substrate_reapply`.
    """
    from datetime import datetime, timezone

    from services.bundle_reader import (
        _load_manifest,
        get_bundle_version,
    )
    from services.conventions import CAPTURES_PATH, RECURRENCES_PATH
    from services.scheduling import materialize_scheduling_index
    from services.capture.scheduling import materialize_capture_index
    from services.substrate_reapply import (
        CONFIG_PATHS,
        CONFLICT_BACKUP_PREFIX,
        UPDATE_AUTHORED_BY,
    )
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

    # UserMemory must exist before the D8 default-pace seed below.
    um = UserMemory(client, user_id)

    # ADR-327: the bundle minimum-pace gate + default-pace seeding (ADR-298
    # D7/D8) are DELETED. Pace retires — a program no longer declares a
    # frequency floor because frequency is not a concept. Cost governance is
    # the dollar budget (_budget.yaml), seeded with a kernel default
    # ($50/monthly) at workspace init; the bundle ships its own _budget.yaml
    # via the normal reference-workspace fork. No activation-time pace gate.

    bundle_version = get_bundle_version(program_slug) or "unversioned"
    # Stable timestamp prefix shared by all conflict backups in this fork
    # call. Same ran_at value used by apply_substrate_update's UpdateReport;
    # they don't have to coincide perfectly, but using one timestamp per
    # fork keeps a single backup directory per event readable.
    ran_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    # um was initialized earlier (above the ADR-298 pace gate) so the
    # default-seed path could use it. No second init needed.
    files_written: list[str] = []
    files_skipped: list[str] = []
    config_conflicts: list[dict[str, str]] = []

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
        # Per ADR-292 v3 D10 decision tree. Compute exactly one branch.
        is_config_file = relative in CONFIG_PATHS

        if existing is None:
            branch = "write_new"
        elif existing == body:
            branch = "skip_aligned"
        elif is_skeleton_content(existing, bundle_body=body):
            branch = "write_refresh_skeleton"
        elif is_config_file:
            branch = "config_conflict_auto_resolve"
        else:
            branch = "skip_operator_authored_prose"

        if branch in ("write_new", "write_refresh_skeleton"):
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
        elif branch == "skip_aligned":
            files_skipped.append(target_path)
            logger.info(f"[FORK] {target_path} — skipped (already aligned with bundle)")
        elif branch == "config_conflict_auto_resolve":
            # ADR-292 v3 D9+D10: operator-edited CONFIG_PATHS file +
            # bundle has new content → back up operator content + overwrite
            # with bundle's. Backup path is operator-readable; the audit
            # log surfaces it so manual re-application of prior edits is
            # discoverable.
            backup_path = f"{CONFLICT_BACKUP_PREFIX}/{ran_at}/{relative}"
            await um.write(
                backup_path,
                existing,
                summary=f"Backup of operator-edited config before {program_slug} re-fork",
                authored_by=UPDATE_AUTHORED_BY,
                message=(
                    f"backed up operator-edited {relative} prior to bundle re-apply "
                    f"(bundle version {bundle_version}) per ADR-292 v3 D10"
                ),
            )
            await um.write(
                target_path,
                body,
                summary=f"Re-applied {program_slug} bundle config",
                authored_by="system:bundle-fork",
                message=(
                    f"re-applied {relative} from "
                    f"docs/programs/{program_slug}/reference-workspace/ "
                    f"(bundle version {bundle_version}, operator edits backed up at "
                    f"{backup_path}) per ADR-292 v3 D10"
                ),
            )
            files_written.append(target_path)
            config_conflicts.append({
                "path": target_path,
                "backup_path": backup_path,
                "bundle_version": bundle_version,
            })
            logger.info(
                f"[FORK] {target_path} — config conflict auto-resolved "
                f"(backup at {backup_path})"
            )
        else:  # skip_operator_authored_prose
            files_skipped.append(target_path)
            logger.info(f"[FORK] {target_path} — skipped (operator-authored prose)")

    # ADR-284 (2026-05-17): Reviewer seat-occupant runtime-truth alignment.
    # Pre-ADR-284 the kernel scaffold (workspace_init Phase 5) wrote OCCUPANT.md
    # with `occupant_class: human` as the default — produced substrate-runtime
    # drift in alpha workspaces where AI actually runs the seat. Post-ADR-284
    # bundle-fork unconditionally overwrites OCCUPANT.md with the runtime
    # occupant identity for the current alpha state (AI). The bundle does NOT
    # ship its own OCCUPANT.md template (the kernel owns the scaffold; the
    # bundle owns the runtime-occupant overwrite via this helper).
    # Future-shape (deferred): explicit human-occupant declaration honored
    # at activation time via operator UX; the kernel branches here.
    occupant_path = "persona/OCCUPANT.md"
    await _populate_occupant_for_runtime(um, program_slug)
    if occupant_path not in files_written:
        files_written.append(occupant_path)

    # ADR-275 D9 (2026-05-21 amendment): seed deliverable-cadence recurrences
    # from operator's _preferences.yaml at activation. Restores contract-
    # shape symmetry — every operator-declaration substrate file now has
    # its content honored at activation deterministically. The Reviewer's
    # authority survives at runtime for: (a) introspection cadence
    # (Reviewer-authored from first-principled judgment per D11),
    # (b) preference-CHANGE reconciliation (Reviewer-authored when operator
    # edits cadence or flips active flag per D10).
    #
    # Must run BEFORE materialize_scheduling_index so the seeded entries
    # land in the `tasks` index in the same fork transaction. Idempotent
    # — if a slug already exists in _recurrences.yaml regardless of
    # authorship, this helper does NOT overwrite (Reviewer-authored or
    # operator-edited cadences for the same slug are preserved).
    try:
        prefs_seeded, prefs_skipped = await _seed_recurrences_from_preferences(
            client, user_id, program_slug, bundle_version
        )
    except Exception as exc:
        # Non-fatal — preference seeding is operator-facing convenience, not
        # safety-critical. Log but continue; operator can manually Schedule()
        # the preferences via chat. Bundle's own recurrences are unaffected.
        logger.warning(
            f"[FORK:D9] _seed_recurrences_from_preferences failed for "
            f"{user_id[:8]}/{program_slug}: {exc}"
        )
        prefs_seeded, prefs_skipped = [], []

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
        or bool(prefs_seeded)  # ADR-275 D9: preference seeding mutates _recurrences.yaml
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

    # ADR-393: materialize the capture index when the fork touched _captures.yaml.
    # Same rationale as the recurrence index — without it a freshly-forked
    # workspace has capture declarations on disk but zero kind='capture' rows,
    # so the capture drainer can't see them. Idempotent; kind-scoped (never
    # touches recurrence rows). Independent of the recurrence branch above —
    # a bundle may ship captures without recurrences or vice versa.
    captures_relative = CAPTURES_PATH.lstrip("/").removeprefix("workspace/")
    fork_touched_captures = (
        captures_relative in files_written or captures_relative in files_skipped
    )
    capture_index_rows = 0
    if fork_touched_captures:
        try:
            capture_index_rows = await materialize_capture_index(client, user_id)
            logger.info(
                f"[FORK] materialized capture index for {user_id[:8]}: "
                f"{capture_index_rows} rows"
            )
        except Exception as exc:
            logger.warning(
                f"[FORK] materialize_capture_index failed for {user_id[:8]}: {exc}"
            )

    return {
        "files_written": files_written,
        "files_skipped": files_skipped,
        "config_conflicts": config_conflicts,  # ADR-292 v3 D10
        "program_slug": program_slug,
        "bundle_version": bundle_version,  # ADR-292 v3 D10: surface to caller
        "scheduling_index_rows": scheduling_index_rows,
        "capture_index_rows": capture_index_rows,  # ADR-393
        "preferences_seeded": prefs_seeded,  # ADR-275 D9 (2026-05-21)
        "preferences_skipped_already_present": prefs_skipped,  # ADR-275 D9
    }
