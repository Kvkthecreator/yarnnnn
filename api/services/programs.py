"""Programs service helpers — program lifecycle + bundle fork.

ADR-414 D5 (2026-07-07): **the activation record is a GRANT ROW** — a
`principal_grants` row (role='own-agent', principal_id='program:{slug}')
minted at fork, revoked at deactivation. The prose-marker pair
(`parse_active_program_slug` / `resolve_active_program_slug` /
`strip_program_marker_from_mandate` + the heading regex) is DELETED.
`resolve_hired_program_slug(user_id)` is the singular activation
read for every consumer (workspace state, working memory, bundle_reader,
substrate reapply, purge capture, deactivate).

ADR-226: _fork_reference_workspace + helpers relocated here 2026-05-03 from
workspace_init.py. The fork is program-bundle logic, not initialization
logic. Post-ADR-414 D4, workspace_init never forks — routes/programs.py
(activate) and the L2/L4 reinit callers invoke fork_reference_workspace()
directly. Single implementation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# The activation record is a GRANT ROW (ADR-414 D5 — program-as-hire)
# =============================================================================
# The prose marker (`# Mandate — {slug} (template)` parsed by a heading
# regex) is DELETED VOCABULARY. Activation mints a `principal_grants` row
# (role='own-agent', principal_id='program:{slug}'); deactivation revokes
# it. DP33: the agent count is data. A bundle MANDATE heading that still
# carries an em-dash is inert prose the operator may edit freely.
# Backfill for live workspaces: scripts/oneshot/adr414_backfill_program_hire_grants.py.

HIRE_GRANT_ROLE = "own-agent"
HIRE_GRANT_PREFIX = "program:"
HIRE_GRANTED_BY = "system:program-hire"


def hire_grant_principal_id(slug: str) -> str:
    """The hired agent's principal id — `program:{slug}` (ADR-414 D5)."""
    return f"{HIRE_GRANT_PREFIX}{slug}"


def resolve_hired_program_slug(user_id: str) -> Optional[str]:
    """Return the workspace's hired program slug from the grant row, or None.

    THE singular activation read (replaces the deleted
    `parse_active_program_slug` / `resolve_active_program_slug` prose-marker
    pair). Reads the active `principal_grants` row with role='own-agent'
    and principal_id prefixed `program:`; validates the slug against the
    bundle registry. Uses the service client — grants are RLS
    service-role-only (ADR-373), and the activation fact is workspace
    infrastructure, not caller-scoped data.

    Tolerant: returns None on any failure (no grant, unresolvable
    workspace, unregistered slug) — never raises, never blocks a read.
    """
    try:
        from services.bundle_reader import _all_slugs
        from services.supabase import get_service_client
        from services.workspace_context import effective_workspace_id

        ws = effective_workspace_id(user_id)
        if not ws:
            return None
        rows = (
            get_service_client()
            .table("principal_grants")
            .select("principal_id")
            .eq("workspace_id", ws)
            .eq("role", HIRE_GRANT_ROLE)
            .eq("status", "active")
            .like("principal_id", f"{HIRE_GRANT_PREFIX}%")
            .limit(1)
            .execute()
        )
        if rows.data:
            candidate = rows.data[0]["principal_id"][len(HIRE_GRANT_PREFIX):]
            if candidate in _all_slugs():
                return candidate
    except Exception:  # pragma: no cover — defensive; never block the read
        pass
    return None


def resolve_judgment_home(user_id: str) -> Optional[str]:
    """The hired agent's home prefix (`agents/{slug}/`), or None when the
    workspace is steward-only (ADR-414 §9a).

    THE branch point for every judgment-home read/write re-point (envelope,
    witness dial, judgment-log writer, activation surfaces). Keys on the HIRE
    GRANT — never on `program_active`, which a platform connection alone can
    raise (chrome/capabilities are a different signal than installed judgment).
    """
    from services.workspace_paths import agent_home

    slug = resolve_hired_program_slug(user_id)
    return agent_home(slug) if slug else None


def mint_hire_grant(user_id: str, slug: str) -> Optional[dict]:
    """Record the hire — idempotent grant mint (ADR-414 D5).

    Called by `fork_reference_workspace` after a successful fork. Best-effort:
    a grant failure never breaks the fork (the resolver simply reports no
    hire until the next fork/backfill re-mints).
    """
    try:
        from services.principal_grants import ensure_principal_grant
        from services.workspace_context import effective_workspace_id

        ws = effective_workspace_id(user_id)
        if not ws:
            logger.warning(
                "[PROGRAMS] hire grant skipped — workspace unresolvable for %s",
                user_id[:8],
            )
            return None
        return ensure_principal_grant(
            principal_id=hire_grant_principal_id(slug),
            workspace_id=ws,
            role=HIRE_GRANT_ROLE,
            granted_by=HIRE_GRANTED_BY,
        )
    except Exception as exc:  # pragma: no cover — best-effort
        logger.warning("[PROGRAMS] hire grant mint failed for %s: %s", slug, exc)
        return None


def revoke_hire_grant(user_id: str, slug: str) -> bool:
    """Record the fire — deactivation revokes the hire grant (ADR-414 D5)."""
    try:
        from services.supabase import get_service_client
        from services.workspace_context import effective_workspace_id

        ws = effective_workspace_id(user_id)
        if not ws:
            return False
        get_service_client().table("principal_grants").update(
            {"status": "revoked"}
        ).eq("workspace_id", ws).eq(
            "principal_id", hire_grant_principal_id(slug)
        ).eq("status", "active").execute()
        return True
    except Exception as exc:  # pragma: no cover — best-effort
        logger.warning("[PROGRAMS] hire grant revoke failed for %s: %s", slug, exc)
        return False


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
    from services.workspace_paths import agent_home

    um = UserMemory(client, user_id)

    # Read post-fork preferences + current recurrences. ADR-414 §9a: the
    # bundle ships its contract into the agent home (agents/{slug}/), so the
    # fork-time seed reads the just-installed per-agent _preferences.yaml.
    preferences_yaml = await um.read(f"{agent_home(program_slug)}_preferences.yaml")
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
                f"/workspace/agents/{program_slug}/standing_intent.md with what "
                f"you're watching for in the next cycle per ADR-284 + "
                f'principles.md "Default posture".\n\n'
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

    # ADR-414 D5/§9a: the ADR-284 occupant-fork (`_populate_occupant_for_runtime`)
    # is DELETED per the deletion ledger — the occupant fact is kernel data
    # (FREDDIE_MODEL_IDENTITY, ADR-414 D2); a hired agent has no OCCUPANT.md.
    # The fork installs the bundle's agent home (agents/{slug}/…) verbatim.

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

    # ADR-414 D5: record the HIRE — the activation record is a grant row,
    # not a prose marker. Idempotent (re-fork re-ensures the same grant).
    hire_grant = mint_hire_grant(user_id, program_slug)

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
        "hire_grant_minted": bool(hire_grant),  # ADR-414 D5
    }
