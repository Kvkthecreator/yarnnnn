"""
ADR-230 — Persona-Program activation harness.

Single entry point that activates a persona's program against their
workspace. Replaces the deleted scaffold_trader.py (per ADR-230 D5).

Program-agnostic: works for alpha-trader (program=alpha-trader) and
alpha-commerce (program=alpha-commerce) the same way; persona registry
declares which program each persona runs (ADR-230 D1), and the bundle
at docs/programs/{program}/ is the single source of truth for substrate
templates + program-default tasks.

Sequence (per ADR-230 D5, post-ADR-231 cutover, post-2026-05-18 dogfood-gap fix):
  1. Load persona from personas.yaml; resolve persona.program.
  2. Validate bundle exists at docs/programs/{persona.program}/.
  3. Run initialize_workspace(client, user_id, program_slug=None) —
     kernel-universal skeleton (Phases 1-4 of workspace_init): YARNNN
     agent row + kernel skeleton files + workspace narrative session +
     balance audit. **NEW per dogfood gap surfaced 2026-05-18.** This
     bridges the gap where service-key-provisioned users (via
     auth.admin.create_user) bypass the canonical initialize_workspace
     that web-UI signup triggers via /api/workspace/state lazy scaffold.
     Idempotent — re-running is a clean no-op (gate on existing IDENTITY.md
     skeleton + agents-table row).
  4. Run fork_reference_workspace(persona.user_id, persona.program) —
     same primitive as POST /api/programs/activate (ADR-226). Forks both
     .md files (operator substrate) AND .yaml files (recurrence
     declarations per ADR-231 D3). After this step, the operator's
     workspace has the program's recurrence declarations at natural-home
     locations. (Equivalent to Phase 5 of initialize_workspace, which we
     bypass by passing program_slug=None above and calling the fork
     primitive directly here.)
  5. Apply persona-specific overrides per ADR-230 D6 (if any) from
     docs/alpha/personas/{persona.slug}/overrides/.
  6. Pre-create specialist agent rows that the bundle's recurrence
     declarations reference (ADR-205 lazy-create gap).
  7. (DELETED — ADR-231) Recurrences are now scaffolded via the Step 4
     fork. The previous "POST /api/tasks per tasks.yaml entry" path is
     gone. Operator's workspace has the YAML declarations the moment
     fork completes; the scheduler walks them on next tick.
  8. Optional: run platform connect via existing connect.py for the
     persona's declared platform.kind.

Note: display labels in the script use [N/6] (kernel-init + fork + overrides
+ specialists + DELETED step + platform connect). The deleted ADR-231 slot
frees one display slot, so [N/6] remains accurate even after adding the
kernel-init step. Canonical sequence above uses 8 items for completeness.

Usage:
    .venv/bin/python api/scripts/alpha_ops/activate_persona.py \
        --persona alpha-trader-2 [--dry-run] [--skip-connect]

Idempotent: re-running is safe. ADR-226 fork honors three-tier rules
(canon re-applies, authored re-applies only when skeleton, placeholder
never overwrites). Tasks return 409 SKIP if already exist.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

import yaml

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

# Make api/ importable so services.workspace_init resolves.
_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from _shared import ProdClient, Persona, load_registry  # noqa: E402

REPO_ROOT = _THIS_DIR.parents[2]
PROGRAMS_ROOT = REPO_ROOT / "docs" / "programs"
PERSONAS_ROOT = REPO_ROOT / "docs" / "alpha" / "personas"


# =============================================================================
# Step 3 + 4 — Fork bundle reference-workspace + apply persona overrides
# =============================================================================

def _service_client() -> Any:
    """Build a service-key Supabase client for fork + override writes.
    The fork primitive expects a privileged client (writes via UserMemory
    bypass operator JWT scoping)."""
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL") or "https://noxgqcwynkzqabljjyon.supabase.co"
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not key:
        raise SystemExit("SUPABASE_SERVICE_KEY required for activation harness")
    return create_client(url, key)


async def _run_kernel_init(persona: Persona) -> dict[str, Any]:
    """Step 2: kernel-universal workspace skeleton via the canonical
    initialize_workspace function. Pass program_slug=None to run
    Phases 1-4 only — YARNNN agent row + kernel skeleton files +
    workspace narrative session + balance audit. Phase 5 (bundle fork)
    is handled by Step 3 directly.

    Bridges the service-key signup gap: auth.admin.create_user bypasses
    the lazy-scaffold path that normal web-UI signup goes through. Without
    this, the YARNNN agent row never gets seeded for harness-provisioned
    personas (surfaced as verify.py FAIL on agent_count=0 + role=None for
    thinking_partner, 2026-05-18).
    """
    from services.workspace_init import initialize_workspace
    return await initialize_workspace(
        client=_service_client(),
        user_id=persona.user_id,
        program_slug=None,  # kernel-universal only; fork handled by Step 3
    )


async def _run_fork(persona: Persona) -> dict[str, Any]:
    """Step 3: ADR-226 reference-workspace fork via the canonical primitive."""
    from services.programs import fork_reference_workspace as _fork_reference_workspace
    return await _fork_reference_workspace(
        client=_service_client(),
        user_id=persona.user_id,
        program_slug=persona.program,
    )


async def _run_clean_slate(persona: Persona) -> dict[str, Any]:
    """Step 1 (--clean-slate only): wipe the persona's workspace via the SAME
    L2 clear-workspace body the HTTP route uses (services.workspace_purge.
    clear_workspace_for_user) — capture active program → purge → reinit +
    re-fork. No second purge implementation.

    This is the longitudinal-track clean-slate (LONGITUDINAL-TRACKING): a
    soak/eval needs a true revision-1 ledger, and the route alone is JWT-scoped
    so it cannot reach another persona's workspace. clear_workspace_for_user
    is the singular body callable with the service key by user_id.

    Returns the purge summary {deleted, prior_program_slug, reinit_summary}.
    Note: clear_workspace_for_user already runs initialize_workspace with the
    captured program_slug, so Steps 2-3 below are idempotent re-runs that
    short-circuit; the value-add of the later steps is overrides + specialists
    + connect.
    """
    from services.workspace_purge import clear_workspace_for_user
    return await clear_workspace_for_user(_service_client(), persona.user_id)


async def _apply_overrides(persona: Persona) -> list[str]:
    """Step 4 (ADR-230 D6): walk docs/alpha/personas/{slug}/overrides/ and
    write each .md file to the operator's workspace via write_revision
    with authored_by=operator:alpha-{slug}.

    Returns the list of paths written. Empty list when no overrides
    directory exists for this persona — overrides are opt-in per ADR-230 D6.
    """
    overrides_dir = PERSONAS_ROOT / persona.slug / "overrides"
    if not overrides_dir.is_dir():
        return []

    from services.workspace import UserMemory
    um = UserMemory(_service_client(), persona.user_id)

    written: list[str] = []
    for src in sorted(overrides_dir.rglob("*.md")):
        relative = src.relative_to(overrides_dir).as_posix()
        # Skip the overrides directory's own README — it's documentation
        # about which files differ + why, not an operator workspace
        # substrate file. Same convention as _fork_reference_workspace
        # which skips the bundle's reference-workspace/README.md.
        if relative == "README.md":
            continue
        # Per ADR-230 D6, operator overrides land in the same paths as
        # bundle templates — overrides replace template content. Path
        # is relative to /workspace/ (UserMemory convention).
        target_path = relative
        try:
            content = src.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"  [WARN] Failed to read override {src}: {exc}")
            continue

        await um.write(
            target_path,
            content,
            summary=f"Persona override for {persona.slug}",
            authored_by=f"operator:alpha-{persona.slug}",
            message=(
                f"ADR-230 D6: applied persona override from "
                f"docs/alpha/personas/{persona.slug}/overrides/{relative}"
            ),
        )
        written.append(target_path)
        print(f"  [OK] override: {target_path}")
    return written


# =============================================================================
# Step 5 — Pre-create specialist agent rows
# =============================================================================

def _ensure_specialists(user_id: str, roles: list[str]) -> dict[str, str]:
    """Pre-create the specialist agent rows the program's tasks.yaml
    references. ADR-205 lazy-creates specialists at dispatch time, but
    ManageTask(create) validates the agent row exists up-front. Bridge
    by invoking ensure_infrastructure_agent for every unique role.
    Idempotent — existing rows short-circuit."""
    from services.agent_creation import ensure_infrastructure_agent

    client = _service_client()

    async def _run() -> dict[str, str]:
        created: dict[str, str] = {}
        for role in roles:
            agent = await ensure_infrastructure_agent(client, user_id, role)
            if agent:
                created[role] = agent.get("slug", "?")
        return created

    return asyncio.run(_run())


# =============================================================================
# Step 5 helpers — discover specialist roles from bundle YAML declarations
# =============================================================================
#
# ADR-231 cutover: tasks.yaml is gone. Specialist roles are discovered from
# the bundle's recurrence declaration YAMLs in reference-workspace/.
# Walks the same file set _fork_reference_workspace touches.

def _bundle_recurrence_roles(program_slug: str) -> list[str]:
    """Walk docs/programs/{program}/reference-workspace/ for recurrence
    YAMLs and return the unique set of agent_slug values referenced.

    Used by Step 5 to pre-create specialist rows the bundle's recurrences
    will dispatch against. Idempotent — duplicates dropped before return.
    """
    bundle_root = PROGRAMS_ROOT / program_slug / "reference-workspace"
    if not bundle_root.is_dir():
        return []

    roles: set[str] = set()
    for yaml_path in bundle_root.rglob("*.yaml"):
        try:
            raw = yaml.safe_load(yaml_path.read_text())
        except yaml.YAMLError:
            continue
        if not isinstance(raw, dict):
            continue
        # Single-decl shapes: {report:{...}} or {action:{...}} with agent_slug
        for wrapper_key in ("report", "action"):
            wrapped = raw.get(wrapper_key)
            if isinstance(wrapped, dict):
                slug = wrapped.get("agent_slug")
                if slug:
                    roles.add(str(slug))
                # also pick up entries in `agents:` list
                for ag in (wrapped.get("agents") or []):
                    if ag:
                        roles.add(str(ag))
        # Multi-decl shapes: {recurrences:[{...}]} or {back_office_jobs:[{...}]}
        for list_key in ("recurrences", "back_office_jobs"):
            entries = raw.get(list_key)
            if isinstance(entries, list):
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    slug = entry.get("agent") or entry.get("agent_slug")
                    if slug:
                        roles.add(str(slug))
                    for ag in (entry.get("agents") or []):
                        if ag:
                            roles.add(str(ag))
    return sorted(roles)


# =============================================================================
# Step 7 — Optional platform connect
# =============================================================================

def _platform_connect(persona: Persona, registry) -> int:
    """Optional Step 7: invoke the existing connect.py path for this
    persona's platform. Skipped when --skip-connect, when platform.kind
    is "none" (architecturally-agnostic persona per ADR-283 D7 — e.g.,
    alpha-author bundle requires no external writes), or when
    credentials_env vars aren't set.

    Reuses connect.py::_build_payload for credential resolution + endpoint
    routing; a thin POST through ProdClient executes the connect. Same
    primitive as `python connect.py {persona-slug}` — just inlined here
    so activation is one command end-to-end.
    """
    # ADR-283 D7 — architecturally-agnostic personas (substrate-continuity
    # archetype bundles like alpha-author) declare platform.kind="none"
    # because no external writes are structurally required. Skip cleanly
    # rather than treating this as an error.
    if persona.platform_kind == "none":
        print(f"  SKIP platform connect — persona.platform.kind=none (no external writes by design)")
        return 0
    cred_keys = list(persona.credentials_env.values())
    missing = [k for k in cred_keys if not os.environ.get(k)]
    if missing:
        print(f"  SKIP platform connect — missing env vars: {', '.join(missing)}")
        print(f"       (set them or pass --skip-connect to suppress this notice)")
        return 0
    try:
        from connect import _build_payload  # type: ignore[import-not-found]
        path, payload = _build_payload(persona)
        with ProdClient(persona, registry=registry) as client:
            r = client.post(path, json=payload)
        if r.status_code >= 300:
            print(f"  FAIL platform connect [{r.status_code}]: {r.text[:200]}")
            return 1
        print(f"  OK   {persona.platform_kind} platform connected")
        return 0
    except SystemExit as exc:
        # _build_payload raises SystemExit on missing creds (we already
        # filtered those above; this is defensive).
        print(f"  FAIL platform connect: {exc}")
        return 1
    except Exception as exc:
        print(f"  FAIL platform connect: {exc}")
        return 1


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    ap = argparse.ArgumentParser(description="Activate a persona's program (ADR-230)")
    ap.add_argument("--persona", required=True, help="Persona slug from personas.yaml")
    ap.add_argument("--dry-run", action="store_true", help="Show plan without writing")
    ap.add_argument("--skip-connect", action="store_true", help="Skip Step 7 platform connect")
    ap.add_argument(
        "--clean-slate",
        action="store_true",
        help=(
            "DESTRUCTIVE: wipe the persona's workspace first (L2 clear via "
            "services.workspace_purge.clear_workspace_for_user) before re-"
            "activating. Use for soak/eval clean-slate — gives a true revision-1 "
            "ledger. Preserves auth + platform_connections; purges substrate + "
            "tasks + agents + chat + proposals + wake_queue."
        ),
    )
    args = ap.parse_args()

    reg = load_registry()
    persona = reg.require(args.persona)

    if persona.program is None:
        # Bare-kernel persona (Stage-0 floor, eval-canon lifecycle journey).
        # There is no bundle to fork — Direction A holds (program-activation
        # is the OPERATING floor), and a bare persona deliberately never
        # operates. Kernel init (constitution/persona skeletons, YARNNN row)
        # happens via initialize_workspace(program_slug=None) on first
        # workspace touch (GET /api/workspace/state) after
        # provision_persona_auth — activation is structurally N/A.
        raise SystemExit(
            f"persona '{persona.slug}' is bare-kernel (program: null) — "
            f"nothing to activate. Stage-0 floor personas never fork a "
            f"bundle; provision auth + first workspace touch performs "
            f"kernel init. If this persona is meant to graduate (lifecycle "
            f"journey Stage 2), set its `program:` field first."
        )

    print(f"Persona:      {persona.slug}  ({persona.email})")
    print(f"  user_id:    {persona.user_id}")
    print(f"  workspace:  {persona.workspace_id}")
    print(f"  program:    {persona.program}")
    print(f"  platform:   {persona.platform_kind} ({persona.platform_provider})")
    print()

    unique_roles = _bundle_recurrence_roles(persona.program)
    overrides_dir = PERSONAS_ROOT / persona.slug / "overrides"
    has_overrides = overrides_dir.is_dir()

    if args.dry_run:
        print("DRY RUN. No writes.")
        if args.clean_slate:
            print(f"Step 1 CLEAN-SLATE: clear_workspace_for_user({persona.user_id}) "
                  f"[DESTRUCTIVE: purge substrate+tasks+agents+chat+proposals+wake_queue, "
                  f"reinit + re-fork program={persona.program}]")
        print(f"Step 2 init: initialize_workspace(program_slug=None) [idempotent, kernel skeleton + YARNNN agent row]")
        print(f"Step 3 fork: docs/programs/{persona.program}/reference-workspace/* → /workspace/* (.md + .yaml)")
        print(f"Step 4 overrides: {'apply' if has_overrides else 'skip'} (docs/alpha/personas/{persona.slug}/overrides/)")
        print(f"Step 5 specialists: ensure × {len(unique_roles)}: {', '.join(unique_roles)}")
        print(f"Step 6 (DELETED — ADR-231): recurrence YAMLs are scaffolded via Step 3 fork.")
        print(f"Step 7 connect: {'skip' if args.skip_connect else 'attempt platform connect'}")
        return 0

    errors: list[str] = []

    # ----- Step 1 (--clean-slate only): wipe the workspace first -----
    # Single L2 implementation (services.workspace_purge.clear_workspace_for_user):
    # capture active program → purge → reinit + re-fork. Gives the soak/eval a
    # true revision-1 ledger (LONGITUDINAL-TRACKING). Preserves auth +
    # platform_connections so the subsequent steps detect the live connection.
    if args.clean_slate:
        print(f"[1/6] CLEAN-SLATE wipe (DESTRUCTIVE) — clear_workspace_for_user({persona.user_id})")
        try:
            cs = asyncio.run(_run_clean_slate(persona))
            deleted = cs.get("deleted", {})
            reinit = cs.get("reinit_summary", {})
            print(f"  OK purged: workspace_files={deleted.get('workspace_files', 0)}, "
                  f"workspace_file_versions={deleted.get('workspace_file_versions', 0)}, "
                  f"agents={deleted.get('agents', 0)}, tasks={deleted.get('tasks', 0)}, "
                  f"wake_queue={deleted.get('wake_queue', 0)}")
            print(f"  OK captured prior_program={cs.get('prior_program_slug')!r}, "
                  f"reinit re-forked program={reinit.get('activated_program')!r}, "
                  f"agents_created={reinit.get('agents_created', [])}")
        except Exception as exc:
            errors.append(f"clean-slate: {exc}")
            print(f"  FAIL clean-slate: {exc}")
            return 1

    # ----- Step 2: Initialize kernel-universal workspace skeleton -----
    # Bridges the service-key signup gap. auth.admin.create_user (used by
    # the provisioning harness) bypasses GET /api/workspace/state's lazy
    # scaffold, so the YARNNN agent row + kernel skeleton files + workspace
    # narrative session + balance audit never get seeded. Without this step
    # verify.py reports agent_count=0 + role=None for thinking_partner.
    # Idempotent — re-runs return already_initialized=True and short-circuit.
    print(f"[2/6] Initialize kernel-universal workspace skeleton")
    try:
        init_summary = asyncio.run(_run_kernel_init(persona))
        print(f"  OK already_initialized={init_summary.get('already_initialized', False)}, "
              f"agents_created={init_summary.get('agents_created', [])}, "
              f"session_bootstrapped={init_summary.get('session_bootstrapped', False)}")
    except Exception as exc:
        errors.append(f"kernel-init: {exc}")
        print(f"  FAIL kernel-init: {exc}")
        return 1

    # ----- Step 3: Fork reference-workspace (.md + .yaml per ADR-231 cutover) -----
    print(f"[3/6] Fork reference-workspace from program={persona.program}")
    try:
        summary = asyncio.run(_run_fork(persona))
        print(f"  OK files_written={len(summary.get('files_written', []))}, "
              f"skipped={len(summary.get('files_skipped', []))}")
        for path in summary.get("files_written", []):
            print(f"    + {path}")
    except Exception as exc:
        errors.append(f"fork: {exc}")
        print(f"  FAIL fork: {exc}")
        return 1

    # ----- Step 4: Apply persona overrides -----
    print(f"[4/6] Apply persona overrides")
    try:
        overrides = asyncio.run(_apply_overrides(persona))
        if not overrides:
            print(f"  (no overrides directory at docs/alpha/personas/{persona.slug}/overrides/)")
    except Exception as exc:
        errors.append(f"overrides: {exc}")
        print(f"  FAIL overrides: {exc}")

    # ----- Step 5: Ensure specialist agent rows -----
    print(f"[5/6] Ensure specialist rows × {len(unique_roles)}")
    try:
        ensured = _ensure_specialists(persona.user_id, unique_roles)
        for role in unique_roles:
            status = "OK" if role in ensured else "MISS"
            slug = ensured.get(role, "?")
            print(f"  {status:<4} {role:<12} slug={slug}")
    except Exception as exc:
        errors.append(f"specialists: {exc}")
        print(f"  FAIL specialists: {exc}")

    # ----- Step 6 DELETED (ADR-231 cutover) -----
    # The previous step posted each tasks.yaml entry to /api/tasks.
    # Post-cutover, recurrence declarations are scaffolded as YAML files
    # via the Step 3 fork. Per ADR-261 D3 the fork itself calls
    # materialize_scheduling_index after writing /workspace/_recurrences.yaml,
    # so the thin `tasks` index is populated immediately — verify.py and
    # the scheduler both see the recurrences on the next read with no
    # manual reconciliation step.

    # ----- Step 7: Platform connect (now Step 6 of 6 in display) -----
    print(f"[6/6] Platform connect")
    if args.skip_connect:
        print(f"  SKIP --skip-connect")
    else:
        rc = _platform_connect(persona, reg)
        if rc != 0:
            errors.append(f"platform connect rc={rc}")

    # ----- Re-materialize scheduling index after platform connect -----
    # Activation flow ordering: Step 3 fork → materialize_scheduling_index runs
    # before Step 6 platform connect. Bundle market_context (ADR-268) is gated
    # on `platform_connections.status='active'` per
    # `services.bundle_reader.bundles_active_for_workspace`, so at fork-time
    # the workspace has no active connection → market_context resolves to
    # None → semantic schedules (`@market_open + 15min`,
    # `@every 1min during regular_hours`) fail to resolve →
    # tasks.next_run_at NULL → scheduler never fires market-anchored
    # recurrences autonomously. Re-materialize here AFTER connect so the
    # bundle's market_context becomes resolvable and semantic schedules
    # populate next_run_at on the thin scheduling index. Idempotent —
    # safe to run regardless of whether the connect succeeded (skipped
    # personas just re-run the same NULL-result materialize).
    if not args.skip_connect:
        print(f"[6.5/6] Re-materialize scheduling index (semantic schedules need active connection)")
        try:
            from services.scheduling import materialize_scheduling_index
            from services.supabase import get_service_client
            client = get_service_client()
            rows = asyncio.run(materialize_scheduling_index(client, persona.user_id))
            print(f"  OK   materialized {rows} scheduling-index rows")
        except Exception as exc:
            errors.append(f"re-materialize: {exc}")
            print(f"  FAIL re-materialize: {exc}")

    print()
    if errors:
        print(f"FINISHED WITH {len(errors)} ERRORS:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("ACTIVATION COMPLETE.")
    print(f"  verify: .venv/bin/python api/scripts/alpha_ops/verify.py {persona.slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
