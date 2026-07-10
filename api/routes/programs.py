"""Programs routes — composition surface resolution + activation.

ADR-225: GET /api/programs/surfaces returns the resolved composition tree
for the operator's workspace. The FE compositor consumes the response and
renders via universal components from web/components/library/.

ADR-226: GET /api/programs/activatable returns the list of bundles the
operator may select at signup or activation time. POST /api/programs/activate
runs the reference-workspace fork against an existing workspace.

Routes are operator-scoped + stateless. Read paths consult bundle YAML
(cached via bundle_reader.lru_cache) and platform_connections. The
activation route writes substrate via the standard authored-substrate path
(ADR-209).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


class ActivateRequest(BaseModel):
    program_slug: str


@router.get("/surfaces")
async def get_workspace_surfaces(auth: UserClient) -> dict:
    """Resolve composition surfaces for the operator's workspace.

    Per ADR-225 §2: returns active_bundles[] metadata + composition tree
    (tabs + chat_chips) + schema_version.

    Response shape (illustrative — empty workspace):
        {
            "schema_version": 1,
            "active_bundles": [],
            "composition": {"tabs": {}, "chat_chips": []}
        }

    Response shape (alpha-trader active):
        {
            "schema_version": 1,
            "active_bundles": [{
                "slug": "alpha-trader",
                "title": "alpha-trader",
                "tagline": "...",
                "current_phase": "observation",
                "current_phase_label": "Phase 0 — Observation",
                "phases": [...]
            }],
            "composition": {
                "tabs": {
                    "chat": {"bands": [...]},
                    "work": {"list": {...}, "detail": {"middles": [...]}},
                    "agents": {"list": {...}, "detail": {"middles": [...]}},
                    "files": {"list": {...}}
                },
                "chat_chips": [...]
            }
        }
    """
    from services.composition_resolver import resolve_workspace_composition

    return resolve_workspace_composition(auth.user_id, auth.client)


@router.get("/activatable")
async def list_activatable_programs(auth: UserClient) -> dict:
    """ADR-226: list bundles the operator may activate.

    Returns bundles with `status` in {`active`, `deferred`} from the
    program registry. The UI renders these as a selection card list at
    signup or in a later "activate a program" flow.

    Deferred bundles are listed but with a `deferred: true` flag so the
    UI can disable selection (their activation_preconditions in MANIFEST
    aren't met). Today: alpha-trader is `active` (selectable),
    alpha-commerce is `deferred` (visible but not selectable),
    alpha-prediction + alpha-defi are `reference` (not listed).

    Auth-scoped only as a permission boundary — bundle availability is
    not user-specific (every authenticated operator sees the same list).
    """
    from services.bundle_reader import _all_slugs, _load_manifest, four_flow_preview

    items = []
    for slug in _all_slugs():
        manifest = _load_manifest(slug)
        if not manifest:
            continue
        status = manifest.get("status")
        if status not in ("active", "deferred"):
            continue
        # ADR-266 D5/D6: surface current_phase_label so the FE never renders
        # the bare enum slug (e.g. "OBSERVATION"). Bundle MANIFEST is the
        # source of truth — no FE-side phase registry. Derivation mirrors
        # services.composition_resolver._bundle_metadata.
        current_phase = manifest.get("current_phase")
        phases = manifest.get("phases") or []
        current_phase_label = next(
            (p.get("label") for p in phases if p.get("key") == current_phase),
            None,
        )
        items.append({
            "slug": manifest.get("slug"),
            "title": manifest.get("title"),
            "tagline": manifest.get("tagline"),
            "status": status,
            "deferred": status == "deferred",
            "oracle": manifest.get("oracle") or {},
            "current_phase": current_phase,
            "current_phase_label": current_phase_label,
            # ADR-338 D4.5 — the installer "what this program will do" panel:
            # the program's four-flow declaration (DP26) surfaced BEFORE the
            # operator activates. Same canonical slots the D9 conformance gate
            # reads (perception / work-out / outcomes / loop) + capabilities +
            # ground truth. None for a manifest the helper can't read.
            "flow_preview": four_flow_preview(slug),
        })
    return {"schema_version": 1, "programs": items}


@router.post("/activate")
async def activate_program(req: ActivateRequest, auth: UserClient) -> dict:
    """Hire a program agent (ADR-414 D5).

    "Hire a trader," not "become a trading workspace." Activation is a
    post-genesis Altitude-3 HIRE recorded as a `principal_grants` row; the
    bundle's persona / mandate / principles / governance content installs into
    the hired agent's home `agents/{slug}/` (ADR-414 §9a), NEVER into the
    workspace root — the workspace is never typed by a program (ADR-222).
    `fork_reference_workspace` mints the hire grant and writes the agent home.

    Idempotent — re-running re-applies canon, preserves operator-authored.

    Note (ADR-437 / ADR-432 D2): there is no operator-facing "hire" SURFACE
    yet — the hired-agent roster on /agents is deferred to ADR-382
    (build-when-demanded, ADR-380 §5). This route is the hire machinery; its
    operator entry point re-surfaces with the ADR-382 roster.

    Returns:
      {
        "schema_version": 1,
        "activated_program": "alpha-trader",
        "files_written": ["agents/{slug}/MANDATE.md", ...],
        "files_skipped": ["..."]
      }
    """
    from services.programs import fork_reference_workspace as _fork_reference_workspace

    try:
        summary = await _fork_reference_workspace(
            auth.client, auth.user_id, req.program_slug
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception(f"[ACTIVATE] Fork failed for {auth.user_id[:8]}, program={req.program_slug}")
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "schema_version": 1,
        "activated_program": req.program_slug,
        "files_written": summary.get("files_written", []),
        "files_skipped": summary.get("files_skipped", []),
    }


@router.post("/deactivate")
async def deactivate_program(auth: UserClient) -> dict:
    """ADR-244 D3: deactivate the workspace's active program.

    Soft deactivation: rewrites MANDATE.md's first heading line from
    `# Mandate — alpha-trader (template)` to plain `# Mandate`. Body
    untouched — operator-authored content stays. Severs the bundle's
    idempotent re-fork relationship without wiping authored content per
    ADR-209 (operator's authored substrate is theirs).

    Idempotent — if no program is active, returns deactivated=false with
    reason=no_active_program.

    Out of scope (deferred to follow-on ADR if pressure surfaces):
      - auto-archive recurrences scaffolded by the bundle
      - auto-disconnect bundle-required platforms

    Response:
      { schema_version: 1, deactivated: bool, prior_program_slug: str | null }
    """
    # ADR-414 D5: deactivation is a FIRE — revoke the hire grant. The
    # MANDATE.md content is untouched (the old heading marker is inert
    # prose the operator owns; the prose-strip write is deleted).
    from services.programs import resolve_hired_program_slug, revoke_hire_grant

    prior_slug = resolve_hired_program_slug(auth.user_id)
    if not prior_slug:
        return {
            "schema_version": 1,
            "deactivated": False,
            "prior_program_slug": None,
            "reason": "no_active_program",
        }

    if not revoke_hire_grant(auth.user_id, prior_slug):
        logger.exception(
            f"[DEACTIVATE] hire-grant revoke failed for {auth.user_id[:8]}"
        )
        raise HTTPException(status_code=500, detail="hire grant revoke failed")

    logger.info(
        f"[DEACTIVATE] User {auth.user_id[:8]} deactivated program={prior_slug}"
    )
    return {
        "schema_version": 1,
        "deactivated": True,
        "prior_program_slug": prior_slug,
    }
