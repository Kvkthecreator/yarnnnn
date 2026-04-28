"""
ADR-230 — Persona-Program activation harness.

Single entry point that activates a persona's program against their
workspace. Replaces the deleted scaffold_trader.py (per ADR-230 D5).

Program-agnostic: works for alpha-trader (program=alpha-trader) and
alpha-commerce (program=alpha-commerce) the same way; persona registry
declares which program each persona runs (ADR-230 D1), and the bundle
at docs/programs/{program}/ is the single source of truth for substrate
templates + program-default tasks.

Sequence (per ADR-230 D5):
  1. Load persona from personas.yaml; resolve persona.program.
  2. Validate bundle exists at docs/programs/{persona.program}/.
  3. Run _fork_reference_workspace(persona.user_id, persona.program) —
     same primitive as POST /api/programs/activate (ADR-226).
  4. Apply persona-specific overrides per ADR-230 D6 (if any) from
     docs/alpha/personas/{persona.slug}/overrides/.
  5. Pre-create specialist agent rows the bundle's program-default
     tasks reference (ADR-205 lazy-create gap).
  6. POST /api/tasks for each entry in the bundle's tasks.yaml
     (program-default task instances per ADR-230 D2).
  7. Optional: run platform connect via existing connect.py for the
     persona's declared platform.kind.

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


async def _run_fork(persona: Persona) -> dict[str, Any]:
    """Step 3: ADR-226 reference-workspace fork via the canonical primitive."""
    from services.workspace_init import _fork_reference_workspace
    return await _fork_reference_workspace(
        client=_service_client(),
        user_id=persona.user_id,
        program_slug=persona.program,
    )


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
# Step 6 — Read program-default tasks + POST /api/tasks
# =============================================================================

def _load_program_tasks(program_slug: str) -> list[dict[str, Any]]:
    """Read docs/programs/{program}/tasks.yaml — the program-default task
    instances per ADR-230 D2. Returns empty list when the file doesn't
    exist (some programs may not declare default tasks)."""
    tasks_path = PROGRAMS_ROOT / program_slug / "tasks.yaml"
    if not tasks_path.exists():
        return []
    raw = yaml.safe_load(tasks_path.read_text())
    return list(raw.get("tasks", []))


def _post_tasks(persona: Persona, registry, tasks: list[dict[str, Any]]) -> list[str]:
    """Step 6: POST /api/tasks for each program-default task.
    Returns the list of error strings (empty = clean). 409 SKIP on
    already-existing tasks is treated as success."""
    errors: list[str] = []
    with ProdClient(persona, registry=registry) as pc:
        for t in tasks:
            payload = {k: v for k, v in t.items() if v is not None}
            r = pc.post("/api/tasks", json=payload)
            title = t["title"]
            if r.status_code == 409:
                print(f"  SKIP {title}  (already exists)")
                continue
            if r.status_code >= 300:
                errors.append(f"task {title}: [{r.status_code}] {r.text[:200]}")
                print(f"  FAIL {title}  [{r.status_code}]: {r.text[:200]}")
                continue
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            print(
                f"  OK   {body.get('slug', title):<30} "
                f"mode={body.get('mode','?'):<10} "
                f"role={(body.get('agent_slugs') or ['?'])[0]:<12} "
                f"next={body.get('next_run_at', '—')}"
            )
    return errors


# =============================================================================
# Step 7 — Optional platform connect
# =============================================================================

def _platform_connect(persona: Persona, registry) -> int:
    """Optional Step 7: invoke the existing connect.py path for this
    persona's platform. Skipped when --skip-connect or when
    credentials_env vars aren't set.

    Reuses connect.py::_build_payload for credential resolution + endpoint
    routing; a thin POST through ProdClient executes the connect. Same
    primitive as `python connect.py {persona-slug}` — just inlined here
    so activation is one command end-to-end.
    """
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
    args = ap.parse_args()

    reg = load_registry()
    persona = reg.require(args.persona)

    print(f"Persona:      {persona.slug}  ({persona.email})")
    print(f"  user_id:    {persona.user_id}")
    print(f"  workspace:  {persona.workspace_id}")
    print(f"  program:    {persona.program}")
    print(f"  platform:   {persona.platform_kind} ({persona.platform_provider})")
    print()

    program_tasks = _load_program_tasks(persona.program)
    overrides_dir = PERSONAS_ROOT / persona.slug / "overrides"
    has_overrides = overrides_dir.is_dir()

    if args.dry_run:
        print("DRY RUN. No writes.")
        print(f"Step 3 fork: docs/programs/{persona.program}/reference-workspace/* → /workspace/*")
        print(f"Step 4 overrides: {'apply' if has_overrides else 'skip'} (docs/alpha/personas/{persona.slug}/overrides/)")
        unique_roles = sorted({t["agent_slug"] for t in program_tasks})
        print(f"Step 5 specialists: ensure × {len(unique_roles)}: {', '.join(unique_roles)}")
        print(f"Step 6 tasks: POST /api/tasks × {len(program_tasks)}")
        for t in program_tasks:
            sched = t.get("schedule") or "(reactive)"
            print(f"  - {t['title']:<30} role={t['agent_slug']:<10} mode={t['mode']:<10} schedule={sched}")
        print(f"Step 7 connect: {'skip' if args.skip_connect else 'attempt platform connect'}")
        return 0

    errors: list[str] = []

    # ----- Step 3: Fork reference-workspace -----
    print(f"[3/7] Fork reference-workspace from program={persona.program}")
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
    print(f"[4/7] Apply persona overrides")
    try:
        overrides = asyncio.run(_apply_overrides(persona))
        if not overrides:
            print(f"  (no overrides directory at docs/alpha/personas/{persona.slug}/overrides/)")
    except Exception as exc:
        errors.append(f"overrides: {exc}")
        print(f"  FAIL overrides: {exc}")

    # ----- Step 5: Ensure specialist agent rows -----
    unique_roles = sorted({t["agent_slug"] for t in program_tasks})
    print(f"[5/7] Ensure specialist rows × {len(unique_roles)}")
    try:
        ensured = _ensure_specialists(persona.user_id, unique_roles)
        for role in unique_roles:
            status = "OK" if role in ensured else "MISS"
            slug = ensured.get(role, "?")
            print(f"  {status:<4} {role:<12} slug={slug}")
    except Exception as exc:
        errors.append(f"specialists: {exc}")
        print(f"  FAIL specialists: {exc}")

    # ----- Step 6: POST /api/tasks -----
    print(f"[6/7] POST /api/tasks × {len(program_tasks)}")
    if program_tasks:
        errors.extend(_post_tasks(persona, reg, program_tasks))
    else:
        print(f"  (program {persona.program} declares no default tasks)")

    # ----- Step 7: Platform connect -----
    print(f"[7/7] Platform connect")
    if args.skip_connect:
        print(f"  SKIP --skip-connect")
    else:
        rc = _platform_connect(persona, reg)
        if rc != 0:
            errors.append(f"platform connect rc={rc}")

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
