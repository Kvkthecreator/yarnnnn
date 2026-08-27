"""
Workspace API — File Explorer + Navigation Endpoints

  GET  /api/workspace/nav            — structured nav for Agent OS (ADR-154)
  GET  /api/workspace/domain/:key    — entity listing for a context domain
  GET  /api/workspace/tree           — raw file/folder tree (legacy, still used by file viewer)
  GET  /api/workspace/file           — read file content by path
  PATCH /api/workspace/file          — edit file content by path

All paths are relative to the user's workspace scope in workspace_files table.
"""

import logging
import re
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from services.supabase import UserClient

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Models
# =============================================================================

class TreeNode(BaseModel):
    path: str
    name: str
    type: str  # "file" | "folder"
    updated_at: Optional[str] = None
    children: Optional[list["TreeNode"]] = None


class FileResponse(BaseModel):
    path: str
    content: Optional[str] = None
    summary: Optional[str] = None
    updated_at: Optional[str] = None
    content_type: Optional[str] = None
    content_url: Optional[str] = None
    metadata: Optional[dict] = None
    # ADR-406 D2: the head revision this content reflects — the editor holds
    # it as the base and sends it back on save (optimistic concurrency).
    head_version_id: Optional[str] = None


class FileEditRequest(BaseModel):
    path: str
    content: str
    summary: Optional[str] = None
    # ADR-209 Phase 4: optional message for the revision's authorship trailer.
    # Default is "edit file {path}"; UI revert sends "revert to r{N}"; bulk
    # edits can send any short description. Always attributed to "operator"
    # via this route.
    message: Optional[str] = None
    # ADR-406 D2: the head_version_id the editor loaded. When present, the
    # write is conditional — a moved head returns 409 with the intervening
    # revision's attribution instead of silently clobbering. Absent →
    # unconditional (legacy callers, bulk tools).
    expected_head_version_id: Optional[str] = None


def _substrate_scope_filter(auth) -> tuple:
    """ADR-373 route sweep: substrate scope for this auth — delegates to the
    ONE shared helper (services.workspace_context.substrate_scope_filter)."""
    from services.workspace_context import substrate_scope_filter
    return substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None))


#: Machine prefixes the substrate stamps onto `workspace_files.summary`
#: (services/primitives/workspace.py writes "Workspace write: {path}" /
#: "Workspace edit: {path}"). ONE list, read by both readers below — the
#: shapes are the same, so a new prefix must not have to be remembered twice.
_MACHINE_SUMMARY_PREFIXES = ("Workspace write:", "Workspace edit:", "Write:", "Output:")


def _strip_machine_prefix(summary: Optional[str]) -> str:
    """Drop a leading machine prefix from a stored summary. Returns the rest."""
    s = (summary or "").strip()
    for prefix in _MACHINE_SUMMARY_PREFIXES:
        if s.lower().startswith(prefix.lower()):
            return s[len(prefix):].strip()
    return s


def _plain_summary(summary: Optional[str]) -> Optional[str]:
    """The summary as an OPERATOR should read it, or None (ADR-587).

    A machine write-log line ("Workspace write: marketing/gtm.md") is not a
    description of the file; it is a record of the act that made it. Returning
    None lets the surface fall back to what it actually knows — the file's name
    and its path — instead of showing the operator a fragment of the writer.

    A real summary (operator- or agent-authored prose) passes through.
    """
    s = _strip_machine_prefix(summary)
    # Nothing left, or what remains is just a path: there was no prose here.
    if not s or "/" in s or s.endswith((".md", ".html", ".yaml", ".json")):
        return None
    return s


class RecentArtifact(BaseModel):
    """One delivered output across the workspace (ADR-312 kernel slot #5)."""
    slug: str            # recurrence slug the output belongs to
    date: str            # dated output folder (e.g. "2026-06-04")
    path: str            # full workspace_files path
    summary: Optional[str] = None
    updated_at: Optional[str] = None


class RecentArtifactsResponse(BaseModel):
    artifacts: list[RecentArtifact]


class WorkspaceMember(BaseModel):
    """One principal with an active grant to this workspace (ADR-373 D2).

    Read-only legibility: WHO can write here, and WHAT write-regions they hold.
    In this model an MCP connector from an external LLM is a *member* (a
    foreign-llm principal), so this lists humans AND foreign-LLM/3rd-party
    principals alike. Provisioning (invite / scope) is deferred to a separate
    ADR; this is the "who can touch this workspace" view (ADR-338 management
    plane idiom).
    """
    principal_id: str                      # the stable grant key (user id / provider host-id / slug)
    role: str                              # owner | member | own-agent | foreign-llm | platform | a2a
    label: Optional[str] = None            # humanized name (email / LLM provider / slug)
    write_regions: list[str]               # the raw write-scope prefixes (the wire truth)
    write_zones: list[str]                 # ADR-424 operator zones (Documents/Downloads/System files) — what the roster SHOWS
    scopes_explicit: bool                  # True if narrowed on the WRITE axis; False if class-default
    # Powerbox (2026-07-10) — TWO INDEPENDENT AXES, path prefixes at arbitrary
    # depth. Each axis has a three-way state (the polarity fix made 'none' real):
    #   'all'    → NULL → class default (unconfigured)
    #   'scoped' → [..] → narrowed to the named prefixes
    #   'none'   → []   → explicit deny-all (touches nothing)
    read_scopes: list[str]                 # the raw read-scope prefixes
    read_state: str                        # all | scoped | none
    write_state: str                       # all | scoped | none
    # `access_state` = the combined operator glance (the wider of the two axes,
    # since read ⊇ write is the norm): the reach the row's chip communicates.
    access_state: str
    status: str                            # active | revoked
    granted_by: Optional[str] = None
    created_at: Optional[str] = None
    # ADR-431 — the connecting member (for foreign-LLM/a2a/platform rows): WHO
    # authorized this AI connection. `connected_by` is the raw member id;
    # `connected_by_label` is that human's email; `connected_by_is_you` is True
    # when the viewer authorized it (the FE renders "You" then).
    connected_by: Optional[str] = None
    connected_by_label: Optional[str] = None
    connected_by_is_you: bool = False
    # ADR-445 §7 Phase 4 — the per-member spend cap on the shared pool (owner-set).
    # None = uncapped (the default). The owner is never capped.
    spend_cap_usd: Optional[float] = None
    # ADR-512 D6 Get-Info ("who can reach this file"): populated ONLY when the
    # request carries ?path= — per-principal reach over that path, computed
    # with the one powerbox matcher (never re-derived FE-side).
    can_read: Optional[bool] = None
    can_write: Optional[bool] = None
    # ADR-563 — the CONNECTION's scope tier, a DIFFERENT AXIS from the path
    # regions above. `read_scopes`/`write_scopes` say WHERE a principal may
    # reach; this says WHAT VERBS its OAuth token authorizes (files:read ⊂
    # files:write ⊂ files:share, or the legacy full-access `read`). A connector
    # narrowed to Documents can still hold a token that may delete and share
    # within it — the two axes compose and neither implies the other.
    #
    # foreign-llm rows only (nothing else authenticates by OAuth token). None
    # when the principal has no live token — i.e. the grant outlives the
    # session, which is exactly the state worth seeing.
    connection_scopes: Optional[list[str]] = None
    connection_legacy_full: bool = False


class WorkspaceMembersResponse(BaseModel):
    members: list[WorkspaceMember]
    # Whether the grant-consult is the active authorization path (always True
    # post-ADR-373; surfaced so the FE can render the legibility honestly).
    grant_consult_active: bool = True
    # ADR-437 D5 (Phase E) — proactive seat awareness AT the members surface,
    # not one surface away on the billing card. So a team sees the Free = owner
    # + 1 guest boundary (ADR-429 §12.3c) BEFORE hitting it as a surprise 400.
    # Derived, not stored: human_seats = active human grants; included_seats =
    # the tier ceiling; seats_available = whether another human may be invited.
    human_seats: int = 0
    included_seats: int = 0
    seats_available: bool = True


class TimelineEntry(BaseModel):
    """One attributed act in the workspace timeline (ADR-408 D5.1 / ADR-407
    Phase 4b). Derived from the ledgers at read time — never stored."""
    kind: str                              # revision | invocation | proposal | membership (ADR-608)
    # ADR-410 D6 — stable derived id ("kind:natural-key:at") for cursoring +
    # per-row keys. Derived, never stored (DP29).
    id: str = ""
    at: str                                # ISO timestamp (sort key)
    actor: Optional[str] = None            # authored_by | principal_id | source — FE attribution module maps the label
    # ADR-410/412 viewer pass — the ACTING PRINCIPAL's uuid where the ledger
    # records one (revisions: author_identity_uuid; invocations:
    # principal_id). Lets a viewer-aware surface resolve "You" vs a peer name
    # even for operator-class acts, which the authored_by string alone cannot
    # distinguish in a multi-member commons.
    actor_id: Optional[str] = None
    title: str                             # one-line human summary
    detail: Optional[str] = None           # message / status detail
    path: Optional[str] = None             # revision target (deep-link)
    slug: Optional[str] = None             # invocation slug
    proposal_id: Optional[str] = None
    status: Optional[str] = None           # invocation/proposal status
    decided_by: Optional[str] = None       # proposal approved_by (witness)
    # Proposal rows only — structured, so the FE labeler consumes them
    # directly instead of regex-unpacking the "primitive (family)" title.
    primitive: Optional[str] = None
    family: Optional[str] = None
    # ADR-489 — attention weight, derived at read time (never stored): the
    # Axiom 9 rendering-weight taxonomy. The bell mounts material only; the
    # workbench defaults to material + routine.
    weight: str = "material"           # material | routine | housekeeping


class WorkspaceTimelineResponse(BaseModel):
    entries: list[TimelineEntry]
    # True when any source query returned a full page — more history exists.
    has_more: bool = False


class WorkspaceMembership(BaseModel):
    """One workspace the CALLER can act in (ADR-407 Phase 5 — the switcher)."""
    workspace_id: str
    role: str                              # owner | member | viewer
    label: str                             # workspace name, else humanized fallback (owner email / 'My workspace')
    is_active: bool                        # True if this is the acting workspace
    # Workspace identity phase 1 (2026-08-14): the owner-chosen glyph (emoji).
    # None → the FE renders its default org glyph.
    icon: Optional[str] = None
    # ADR-596 D4: the workspace home timezone (IANA). None → undeclared → the
    # settings surface says "scheduling uses UTC" rather than implying a choice.
    timezone: Optional[str] = None


class WorkspaceIdentityUpdate(BaseModel):
    """PATCH /api/workspace — rename / re-glyph the acting workspace.

    All fields optional; only provided fields are written. `icon` accepts
    null/"" to clear. The gate is the RLS UPDATE policy (owner-only, mig 002):
    the write goes through the CALLER's client, so a non-owner's PATCH matches
    zero rows and 403s — never a service-role bypass.

    `timezone` (ADR-596 D4, mig 247): the workspace HOME timezone — an IANA
    name ("Asia/Seoul"), validated at this door; null/"" clears back to
    undeclared (scheduling then uses UTC). Shared clock declarations resolve
    against it (`schedule_utils.get_workspace_timezone`).
    """
    name: Optional[str] = None
    icon: Optional[str] = None
    timezone: Optional[str] = None


class WorkspaceIdentityResponse(BaseModel):
    workspace_id: str
    name: str
    icon: Optional[str] = None
    timezone: Optional[str] = None


class WorkspaceCreateRequest(BaseModel):
    """POST /api/workspace — mint a NEW owned workspace, named by the caller.

    Name-only by deliberate scope: genesis is staged in
    `services/workspace_genesis.py`, and future steps (directory shape, starting
    structure) are added THERE rather than by widening this model at call sites.
    `extra="forbid"` so a client sending a field we have not built yet is
    REFUSED rather than silently dropped — the ADR-562 lesson (a pin that is
    real and invisible).
    """
    model_config = {"extra": "forbid"}

    name: str


class WorkspaceMembershipsResponse(BaseModel):
    memberships: list[WorkspaceMembership]
    # ADR-501: the caller's workspace-clear authority in the ACTING workspace,
    # server-derived from the grant (owner_id OR the `workspace:clear` scope —
    # services.principal_grants.has_workspace_clear_authority). The FE reads
    # this instead of predicting from the role label (ADR-405: the test is
    # "which grant", never "which role").
    can_clear: bool = True


class RecentRevision(BaseModel):
    """One authored substrate change across the workspace (ADR-329 D2).

    Distinct from RecentArtifact: a RecentArtifact is a delivered *output*
    (a report). A RecentRevision is an authored *substrate change* — any
    mutation to Layer 1 (workspace_file_versions per ADR-209), regardless
    of whether it produced a deliverable. This is the data behind the
    Files "Recently authored" feed: what the system authored in the
    workspace, and by whom.
    """
    path: str                              # full workspace_files path
    authored_by: Optional[str] = None      # ADR-209 attribution taxonomy
    message: Optional[str] = None          # authorship trailer
    created_at: Optional[str] = None       # revision timestamp
    # Explorer icon-view thumbnails (2026-07-02): per-format preview material so
    # the tile shows real content, not a generic glyph. content_url → real image
    # thumbnail (resolved to a signed URL FE-side); preview → a short text
    # snippet for md/text tiles; content_type → format hint the FE dispatches on.
    content_url: Optional[str] = None      # image blob reference (→ signed URL)
    content_type: Optional[str] = None     # MIME/type hint
    preview: Optional[str] = None          # short text snippet (md/text tiles)
    # Finder-parity (2026-07-09): an inline SVG's markup lives in the text
    # column (no blob), so content_url is null and the card fell back to a flat
    # glyph while the detail view showed the real vector. Ship the markup for
    # `.svg` files with no blob so the tile draws the same vector, card→detail.
    svg_text: Optional[str] = None


class RecentRevisionsResponse(BaseModel):
    revisions: list[RecentRevision]


# =============================================================================
# GET /workspace/nav — Structured navigation (ADR-154: Agent OS model)
# =============================================================================
# Returns four sections: tasks, domains, outputs, uploads.
# System files hidden. Entities counted from _tracker.md.

@router.get("/workspace/nav")
async def get_workspace_nav(auth: UserClient) -> dict:
    """Structured navigation for the Agent OS workfloor.

    Returns sections the user should see, with system files hidden.
    Tasks come from the tasks table. Domains come from the directory
    registry + _tracker.md entity counts. Outputs and uploads from
    workspace_files.

    ADR-236 Item 6 (2026-04-29): the columns selected here were aligned
    with the post-ADR-231 thin scheduling index. `mode` and `essential`
    were dropped in migration 164.

    Post-ADR-231 cleanup (2026-05-11): the previous "enrich with title from
    TASK.md" loop read `/tasks/{slug}/TASK.md` which no longer exists in
    substrate (ADR-231 D2 deleted the entire `/tasks/` filesystem tree).
    Every iteration silently fell through the exception path to `title=slug`,
    making the read loop a dead RPC. Replaced with deterministic slug → title
    derivation that produces operator-readable strings without a DB hit.
    """
    try:
        # ── Recurrences (from `tasks` thin scheduling index per ADR-231 D4) ──
        # Columns match the post-migration-164 shape. The operator-facing
        # label (Recurring vs One-time) is derived from `schedule` per ADR-163.
        tasks_result = (
            auth.client.table("tasks")
            .select("id, slug, status, schedule, next_run_at, last_run_at")
            # ADR-501: workspace-scoped like every other query in this handler
            # (and like GET /api/recurrences) — the index rows are trigger-
            # stamped with workspace_id, and a member must see the workspace's
            # recurrences, not an empty section contradicting /api/recurrences.
            .eq(*_substrate_scope_filter(auth))
            .order("created_at", desc=True)
            .execute()
        )
        tasks_rows = tasks_result.data or []

        # Derive operator-readable title from slug. Post-ADR-231 recurrences
        # have no `title` field — the slug IS the operator-facing handle —
        # so we humanize it (hyphens → spaces, title-case) for nav display.
        tasks = []
        for row in tasks_rows:
            slug = row["slug"]
            title = slug.replace("-", " ").replace("_", " ").title()
            tasks.append({
                "slug": slug,
                "title": title,
                "status": row.get("status", "active"),
                "schedule": row.get("schedule"),
                "next_run_at": row.get("next_run_at"),
                "last_run_at": row.get("last_run_at"),
            })

        # ── Domains (from directory registry + tracker entity counts) ──
        from services.directory_registry import WORKSPACE_DIRECTORIES, get_tracker_path

        domains = []
        for key, d in WORKSPACE_DIRECTORIES.items():
            if d.get("type") != "context":
                continue
            if key == "signals":
                continue  # Temporal log, not browseable

            entity_count = 0
            tracker_path = get_tracker_path(key)
            if tracker_path:
                try:
                    tracker_result = (
                        auth.client.table("workspace_files")
                        .select("content")
                        .eq(*_substrate_scope_filter(auth))
                        .eq("path", f"/workspace/{tracker_path}")
                        .limit(1)
                        .execute()
                    )
                    if tracker_result.data:
                        tracker_content = tracker_result.data[0].get("content", "")
                        # Count table rows (lines with | that aren't header/separator)
                        for line in tracker_content.split("\n"):
                            if line.startswith("|") and "Slug" not in line and "---" not in line and line.strip() != "|":
                                entity_count += 1
                except Exception:
                    pass

            domains.append({
                "key": key,
                "display_name": d.get("display_name", key.title()),
                "entity_count": entity_count,
                "entity_type": d.get("entity_type"),
                "path": f"/workspace/{d['path']}",
            })

        # ADR-154: Outputs section removed — tasks own their outputs directly.
        # Users see outputs by clicking tasks in the Tasks section.

        # ── Uploads (user-contributed files) ──
        uploads = []
        try:
            uploads_result = (
                auth.client.table("workspace_files")
                .select("path, updated_at, summary")
                .eq(*_substrate_scope_filter(auth))
                .like("path", "/workspace/uploads/%")
                .order("updated_at", desc=True)
                .limit(20)
                .execute()
            )
            for row in (uploads_result.data or []):
                name = row["path"].split("/")[-1]
                uploads.append({
                    "name": name,
                    "path": row["path"],
                    "updated_at": row.get("updated_at"),
                })
        except Exception:
            pass

        # ── Settings (user-visible and editable) ──
        # ADR-206: authored shared context under constitution/ + governance/ + operation/ (ADR-320 split of legacy _shared/),
        # YARNNN working-memory files under /workspace/system/.
        from services.workspace_paths import (
            PERSONA_IDENTITY_PATH,
            SYSTEM_AWARENESS_PATH, SYSTEM_NOTES_PATH, SYSTEM_STYLE_PATH,
        )
        # ADR-432 D1c: BRAND.md removed from the settings file set (Brand retired).
        SETTINGS_FILES = [
            (PERSONA_IDENTITY_PATH, "IDENTITY.md", "Identity"),
            (SYSTEM_AWARENESS_PATH, "awareness.md", "Awareness"),
            (SYSTEM_NOTES_PATH, "notes.md", "Notes"),
            (SYSTEM_STYLE_PATH, "style.md", "Style"),
        ]
        settings = []
        for relative_path, filename, label in SETTINGS_FILES:
            path = f"/workspace/{relative_path}"
            try:
                check = (
                    auth.client.table("workspace_files")
                    .select("path, updated_at")
                    .eq(*_substrate_scope_filter(auth))
                    .eq("path", path)
                    .limit(1)
                    .execute()
                )
                if check.data:
                    settings.append({
                        "name": label,
                        "filename": filename,
                        "path": path,
                        "updated_at": check.data[0].get("updated_at"),
                    })
            except Exception:
                pass

        # ── Readiness (ADR-155: workspace maturity signal for routing) ──
        # Computed from data we already have — no extra DB queries.
        identity_setting = next((s for s in settings if s["filename"] == "IDENTITY.md"), None)
        identity_richness = "empty"
        if identity_setting:
            try:
                id_content = (
                    auth.client.table("workspace_files")
                    .select("content")
                    .eq(*_substrate_scope_filter(auth))
                    .eq("path", f"/workspace/{PERSONA_IDENTITY_PATH}")
                    .limit(1)
                    .execute()
                )
                if id_content.data:
                    text = id_content.data[0].get("content", "")
                    if text and len(text.strip()) >= 100 and text.strip().count("\n") >= 3:
                        identity_richness = "rich"
                    elif text and text.strip():
                        identity_richness = "sparse"
            except Exception:
                pass

        # ADR-156: Phase computed from raw signals — no inference_state needed
        has_domains = any(d["entity_count"] > 0 for d in domains)
        has_tasks = len(tasks) > 0

        return {
            "tasks": tasks,
            "domains": domains,
            "uploads": uploads,
            "settings": settings,
            "readiness": {
                "identity": identity_richness,
                "has_domains": has_domains,
                "has_tasks": has_tasks,
                "phase": (
                    "active" if has_tasks else
                    "ready" if (identity_richness == "rich" and has_domains) else
                    "setup"
                ),
            },
        }

    except Exception as e:
        logger.error(f"[WORKSPACE_API] Nav query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GET /workspace/domain/:key — Entity listing for a context domain
# =============================================================================

@router.get("/workspace/domain/{domain_key}")
async def get_domain_entities(
    auth: UserClient,
    domain_key: str,
) -> dict:
    """List entities in a context domain with their file details.

    Returns entity cards for the domain browser view — each entity
    with its files, last updated, and content preview.
    """
    from services.directory_registry import get_directory, get_directory_path

    directory = get_directory(domain_key)
    if not directory or directory.get("type") != "context":
        raise HTTPException(status_code=404, detail=f"Domain not found: {domain_key}")

    dir_path = get_directory_path(domain_key)
    prefix = f"/workspace/{dir_path}/"

    try:
        result = (
            auth.client.table("workspace_files")
            .select("path, content, updated_at, summary")
            .eq(*_substrate_scope_filter(auth))
            .like("path", f"{prefix}%")
            .order("path")
            .limit(200)
            .execute()
        )
        rows = result.data or []

        # Separate synthesis files (domain-level) from entity files
        synthesis_files = []
        entities: dict[str, dict] = {}

        for row in rows:
            rel = row["path"].replace(prefix, "")
            parts = rel.split("/")

            # _tracker.md = hidden system file
            if parts[0] == "_tracker.md":
                continue

            # Other _prefixed files at domain root = synthesis files (user-visible)
            if len(parts) == 1 and parts[0].startswith("_"):
                name = parts[0].replace("_", "").replace(".md", "").replace("-", " ").title()
                synthesis_files.append({
                    "name": name,
                    "filename": parts[0],
                    "path": row["path"],
                    "updated_at": row.get("updated_at"),
                    "preview": (row.get("content") or "")[:200].strip() if row.get("content") else None,
                })
                continue

            if len(parts) < 2:
                continue  # Top-level domain files

            entity_slug = parts[0]
            filename = parts[1]

            if entity_slug not in entities:
                entities[entity_slug] = {
                    "slug": entity_slug,
                    "name": entity_slug.replace("-", " ").title(),
                    "files": [],
                    "last_updated": None,
                    "preview": None,
                }

            entities[entity_slug]["files"].append({
                "name": filename,
                "path": row["path"],
                "updated_at": row.get("updated_at"),
            })

            # Track most recent update
            updated = row.get("updated_at")
            if updated and (not entities[entity_slug]["last_updated"] or updated > entities[entity_slug]["last_updated"]):
                entities[entity_slug]["last_updated"] = updated

            # Use profile.md content as preview (first 200 chars)
            if filename == "profile.md" and row.get("content"):
                # Strip markdown headers for clean preview
                content = row["content"]
                preview_lines = []
                for line in content.split("\n"):
                    if line.startswith("#"):
                        continue
                    if line.strip():
                        preview_lines.append(line.strip())
                    if len(" ".join(preview_lines)) > 200:
                        break
                entities[entity_slug]["preview"] = " ".join(preview_lines)[:200]
                # Extract name from first H1
                for line in content.split("\n"):
                    if line.startswith("# "):
                        entities[entity_slug]["name"] = line[2:].strip()
                        break

        return {
            "domain_key": domain_key,
            "domain_path": f"/workspace/{dir_path}",  # actual workspace path (may differ from registry key)
            "display_name": directory.get("display_name", domain_key.title()),
            "entity_type": directory.get("entity_type"),
            "synthesis_files": synthesis_files,
            "entities": list(entities.values()),
            "entity_count": len(entities),
        }

    except Exception as e:
        logger.error(f"[WORKSPACE_API] Domain listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GET /workspace/tree — File/folder tree (legacy, used by file viewer)
# =============================================================================

@router.get("/workspace/tree")
async def get_workspace_tree(
    auth: UserClient,
    root: str = Query("/workspace", description="Root path to list (default: /workspace)"),
) -> list[dict]:
    """
    Returns the workspace file tree for the explorer panel.

    Queries workspace_files for all paths under the root, then builds
    a folder/file tree structure. Supports /workspace/ (the canonical
    substrate root; ADR-320 five-root topology — subfolders include
    constitution/, governance/, persona/, operation/ (domains + reports/ +
    specs/), system/, agents/, uploads/) and /agents/.

    ADR-209 authored substrate enrichment: includes head-revision
    authored_by via the head_version_id FK → workspace_file_versions.
    PostgREST embedded select resolves the FK automatically. When
    head_version_id is NULL (file predates ADR-209 Phase 2 or hasn't
    been attributed yet), authored_by falls back to None and the FE
    shows the updated_at timestamp without an author label.
    """
    try:
        # ADR-209: include head revision authored_by via FK embed.
        # workspace_file_versions!head_version_id resolves the FK named
        # head_version_id on workspace_files → workspace_file_versions.id.
        result = (
            auth.client.table("workspace_files")
            .select(
                # head_version_id rides along so an image child can have its
                # serving URL MINTED below (ADR-427 D4 — never stored).
                "path, updated_at, summary, content_type, head_version_id, "
                "workspace_file_versions!head_version_id(authored_by, created_at)"
            )
            .eq(*_substrate_scope_filter(auth))
            .like("path", f"{root}/%")
            # ADR-329: archived files (operator 'Delete' = trash-semantics
            # via lifecycle, ADR-209-retained) leave the active tree. NULL
            # lifecycle (the common case) still shows — .neq alone would
            # also exclude NULLs, so the OR keeps them.
            .or_("lifecycle.is.null,lifecycle.neq.archived")
            .order("path")
            .limit(500)
            .execute()
        )
        rows = result.data or []

        # ADR-395: hide the upload text PROJECTION from the tree — it's plumbing
        # (a searchable derivation read by recall, not a user file). The operator
        # sees ONE file (their PDF), not a confusing raw + `.extracted.md` pair.
        # Narrow + symmetric (is_upload_projection): only the co-located
        # inbound/uploads/**.extracted.md is hidden; a pure-text upload (no raw
        # container, no projection) and any user `.md` show normally.
        from services.documents import is_upload_projection
        # ADR-554 D2: the edge, not the lane. `rows` already holds the sibling
        # raws, so the pair is answerable without fetching a single body.
        _sibs = [r.get("path", "") for r in rows]
        rows = [
            r for r in rows
            if not is_upload_projection(r.get("path", ""), siblings=_sibs)
        ]

        # Normalize: lift authored_by + revision created_at from nested embed.
        # PostgREST returns the embed as a dict (single FK row) or None.
        for row in rows:
            # ADR-587: drop the machine summary. `summary` is written as
            # f"Workspace write: {path}" / f"Workspace edit: {path}"
            # (services/primitives/workspace.py) — a write-log line, not a
            # description. `_artifact_title` below already calls this shape a
            # leak ("leaks paths to the operator") and strips it, but only on
            # the Home slot; the tree served it raw, so it reached the Files
            # row subtitle and the surface identity header verbatim.
            #
            # DROPPED, not re-titled: the Home slot substitutes a titleized
            # slug because an artifact card needs SOME title. A tree node
            # already has its name and (since ADR-587) its path, so the honest
            # move is to serve nothing rather than invent prose. An operator- or
            # agent-authored summary still passes through untouched.
            row["summary"] = _plain_summary(row.get("summary"))
            embed = row.pop("workspace_file_versions", None) or {}
            row["authored_by"] = embed.get("authored_by")
            # Use revision created_at as the authoritative "last edited" time
            # when available; fall back to workspace_files.updated_at.
            if embed.get("created_at"):
                row["revision_at"] = embed["created_at"]
            else:
                row["revision_at"] = row.get("updated_at")

        # Thumbnails for the folder LISTING (2026-08-27). Until now a file tile
        # in the folder view could never draw a real preview — the tile's
        # thumbnail path was complete but the tree served no `content_url`, so
        # every photo fell to the format glyph even when its bytes were healthy.
        # (`content_url` on the row is NULL for CAS-backed binaries by contract:
        # ADR-427 D4 mints the capability at read and never stores it.)
        #
        # SCOPED TO THE IMMEDIATE CHILDREN, deliberately. This endpoint serves a
        # whole subtree (up to 500 rows) and the Files explorer fetches several
        # roots in parallel, so minting every image underneath would sign
        # hundreds of URLs the operator never looks at — a real cost on every
        # root load, paid for pixels nobody sees. The listing draws one folder's
        # direct children; those are what get a URL.
        depth = len(root.rstrip("/").split("/"))
        direct = [
            r for r in rows
            if len(r.get("path", "").rstrip("/").split("/")) == depth + 1
        ]
        by_path = {r.get("path"): r for r in rows}
        for path, url in mint_thumb_urls(auth.client, direct).items():
            if path in by_path:
                by_path[path]["content_url"] = url

        # INLINE SVG has no blob to mint — its markup lives in the text column,
        # and the tile draws the vector from that. So it needs the BODY, not a
        # URL, which is why it is a second fetch rather than part of the mint.
        #
        # Restricted to the direct children AND to .svg, deliberately: `content`
        # is deliberately absent from this endpoint's select, because hauling
        # every file body across a 500-row subtree (× several roots in parallel)
        # to draw one folder's tiles is the cost this endpoint is shaped to
        # avoid. A handful of vector bodies is not that.
        svg_paths = [
            r["path"] for r in direct if r.get("path", "").lower().endswith(".svg")
        ]
        if svg_paths:
            try:
                bodies = (
                    auth.client.table("workspace_files")
                    .select("path, content")
                    .eq(*_substrate_scope_filter(auth))
                    .in_("path", svg_paths)
                    .execute()
                ).data or []
                for b in bodies:
                    row = by_path.get(b.get("path"))
                    if row is not None and (b.get("content") or "").strip():
                        row["svg_text"] = b["content"]
            except Exception as exc:  # noqa: BLE001 — a preview never fails a listing
                logger.warning("[WORKSPACE_API] svg body fetch failed: %s", exc)

        # Build tree from flat paths
        tree = _build_tree(rows, root)
        return tree

    except Exception as e:
        logger.error(f"[WORKSPACE_API] Tree query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GET /workspace/roots — the Files explorer tree SPINE (ADR-388 D1)
# =============================================================================

@router.get("/workspace/roots")
async def get_workspace_roots(auth: UserClient) -> list[dict]:
    """The actual top-level directories under /workspace/, for the derived
    explorer tree (ADR-388 D1 — filesystem-literal, never a hardcoded list).

    Cheap: one path scan, distinct top-level segment, counted in Python (the
    PostgREST client has no GROUP BY). Merged with WORKSPACE_ROOTS so known
    roots get friendly labels/icons and unknown/new roots still appear (raw
    name) — so the ADR-320 governance/+constitution/ roots and the ADR-376
    inbound/ lane show, and any future root the re-founding adds shows too,
    with zero code change (ADR-388 §6).

    Canonical-but-empty roots (agents/, uploads/) are included so the operator
    sees them as creatable. The response is sorted by WORKSPACE_ROOTS.order
    (unknown roots last, alphabetically). Each entry:
      {name, path, display_name, semantic_class, description, icon,
       file_count, exists}
    """
    from services.workspace_paths import WORKSPACE_ROOTS, root_metadata

    try:
        # Scan distinct top-level segments. We only need `path` (cheap select),
        # excluding archived files (mirror the tree query's lifecycle filter).
        result = (
            auth.client.table("workspace_files")
            .select("path, content_type")
            .eq(*_substrate_scope_filter(auth))
            .like("path", "/workspace/%")
            .or_("lifecycle.is.null,lifecycle.neq.archived")
            .limit(5000)
            .execute()
        )
        rows = result.data or []

        # Count files per top-level segment. A depth-1 file (e.g.
        # /workspace/_workspace_guide.md) has no segment dir — skip it (it's a
        # file, not a root); it surfaces under the root listing, not as a root.
        #
        # ADR-588 D1: a FOLDER MARKER makes its root EXIST but is not counted as
        # a file — `file_count` is operator-facing ("3 files"), and a marker is a
        # directory, not a document. So markers are tracked in a separate set and
        # unioned into `names` below: an empty top-level folder appears in the
        # roots list with file_count 0, which is the honest reading of it.
        from services.workspace_paths import is_folder_marker
        counts: dict[str, int] = {}
        marker_segs: set[str] = set()
        for row in rows:
            path = row.get("path") or ""
            rel = path[len("/workspace/"):]
            if is_folder_marker(path, row.get("content_type")):
                seg = rel.strip("/").split("/", 1)[0]
                if seg:
                    marker_segs.add(seg)
                continue
            if "/" not in rel:
                continue  # depth-1 file, not a root directory
            seg = rel.split("/", 1)[0]
            if not seg:
                continue
            counts[seg] = counts.get(seg, 0) + 1

        # Union of: roots that actually have files + canonical roots we always
        # show (even empty) so the operator can create into them.
        # ADR-395: `uploads` REMOVED from always-show — new uploads land in the
        # inbound/uploads/ raw lane (shown under the `inbound/` root, "Intake"),
        # so the legacy uploads/ root would otherwise render EMPTY next to
        # Intake (the operator-observed duplicate-upload-root). It now shows only
        # when it actually holds pre-ADR-395 legacy files (count > 0).
        always_show = {"agents"}
        # ADR-588: a root that holds ONLY an empty marked folder still exists.
        names = set(counts) | marker_segs | (always_show & set(WORKSPACE_ROOTS))

        out: list[dict] = []
        for name in names:
            meta = root_metadata(name)
            count = counts.get(name, 0)
            out.append(
                {
                    "name": name,
                    "path": f"/workspace/{name}",
                    "display_name": meta["display_name"],
                    "semantic_class": meta["semantic_class"],
                    # ADR-423 follow-on (Files-model note): the operator zone —
                    # work (Documents) | arrival (Downloads) | system (collapsed).
                    "group": meta.get("group", "work"),
                    "description": meta["description"],
                    "icon": meta["icon"],
                    "file_count": count,
                    # ADR-588: a marker alone is enough to exist (an empty
                    # folder is a real folder), even at file_count 0.
                    "exists": count > 0 or name in marker_segs,
                    "_order": meta["order"],
                }
            )

        # Sort by known order, then alphabetically by display_name.
        out.sort(key=lambda r: (r.pop("_order"), r["display_name"].lower()))
        return out

    except Exception as e:
        logger.error(f"[WORKSPACE_API] Roots query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GET /workspace/file — Read file content
# =============================================================================

@router.get("/workspace/file")
async def get_workspace_file(
    auth: UserClient,
    path: str = Query(
        ...,
        description=(
            "File path. Accepts either workspace-relative "
            "(e.g., 'constitution/MANDATE.md') matching the "
            "WriteFile(scope='workspace') convention, OR absolute "
            "(e.g., '/workspace/constitution/MANDATE.md'). The two "
            "shapes resolve to the same row — the absolute form is "
            "what's stored, the relative form is what callers usually "
            "type."
        ),
    ),
) -> FileResponse:
    """
    Read a single workspace file by path. Path is normalized to match
    UserMemory._full_path convention (services.workspace.UserMemory:670):
    workspace-relative paths get the /workspace/ prefix prepended.
    """
    # ADR-209 + ADR-235 Option A: WriteFile(scope='workspace') passes
    # workspace-relative paths ('constitution/MANDATE.md'), but
    # workspace_files.path is stored absolute ('/workspace/...'). Match
    # the UserMemory convention by normalizing here so readback after
    # write doesn't 404. Singular implementation: one normalization rule
    # per the canonical UserMemory._full_path.
    if not path.startswith("/"):
        normalized_path = f"/workspace/{path}"
    else:
        normalized_path = path

    try:
        result = (
            auth.client.table("workspace_files")
            .select("path, content, summary, updated_at, content_type, content_url, metadata, head_version_id")
            .eq(*_substrate_scope_filter(auth))
            .eq("path", normalized_path)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            # Echo the original path the caller asked for in the error
            # so they can see what they sent — but mention the normalized
            # form for debugging.
            raise HTTPException(
                status_code=404,
                detail=(
                    f"File not found: {path} "
                    f"(looked up as {normalized_path})"
                ),
            )

        row = rows[0]

        # ADR-427 Phase 2 (D4): a binary head serves a MINTED, TTL'd URL in
        # the response — never a stored capability. Detected by the head
        # blob's storage_key; content goes None (the '' denorm is a
        # Category-2 text cache, meaningless for binary).
        content = row.get("content")
        content_url = row.get("content_url")
        if not (content or "").strip() and row.get("head_version_id"):
            try:
                blob = (
                    auth.client.table("workspace_file_versions")
                    .select("blob_sha, workspace_blobs(storage_key)")
                    .eq("id", row["head_version_id"])
                    .limit(1)
                    .execute()
                ).data
                meta = (blob or [{}])[0].get("workspace_blobs") or {}
                if isinstance(meta, dict) and meta.get("storage_key"):
                    from services.storage_backend import get_storage_backend
                    from services.supabase import get_service_client

                    minted = get_storage_backend(get_service_client()).mint_serving_url(
                        blob[0]["blob_sha"], expires_in=3600
                    )
                    if minted:
                        content = None
                        content_url = minted
            except Exception as exc:  # noqa: BLE001 — serving falls back to the row
                logger.warning("[WORKSPACE_API] binary mint failed for %s: %s", path, exc)

        return FileResponse(
            path=row["path"],
            content=content,
            summary=row.get("summary"),
            updated_at=row.get("updated_at"),
            content_type=row.get("content_type"),
            content_url=content_url,
            metadata=row.get("metadata"),
            head_version_id=row.get("head_version_id"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WORKSPACE_API] File read failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GET /workspace/file/dependents — the reference edge, read outward (ADR-448)
# =============================================================================
# The legibility register: which files' HEAD revision was made FROM this path
# (derived_from column-first, content-convention fallback — read-both). Serves
# the Files delete-confirm warning ("N other files were made from this one")
# and any "referenced by" badge. Best-effort and read-only — a dependents
# lookup never blocks an action; protection beyond a warning is the powerbox's
# job (ADR-434), not this endpoint's.

@router.get("/workspace/file/dependents")
async def get_workspace_file_dependents(
    auth: UserClient,
    path: str = Query(..., description="File path — workspace-relative or absolute."),
) -> dict:
    from services.authored_substrate import list_dependents

    try:
        deps = list_dependents(auth.client, user_id=auth.user_id, path=path)
        return {"path": path, "dependents": deps, "count": len(deps)}
    except Exception as e:  # noqa: BLE001 — legibility is best-effort
        logger.warning(f"[WORKSPACE_API] dependents lookup failed for {path}: {e}")
        return {"path": path, "dependents": [], "count": 0}


# =============================================================================
# GET /workspace/recent-artifacts — Recent delivered outputs (ADR-312 slot #5)
# =============================================================================
# Kernel-universal Home slot. Reads delivered task outputs across the WHOLE
# workspace (not per-recurrence) from workspace_files, where each
# produces_deliverable recurrence writes /workspace/operation/reports/{slug}/{date}/
# output.md (per routes/recurrences.py report_root convention). Ordered by
# recency. Self-hides on the frontend when empty (bare kernel before any
# deliverable has run). Browser-consumed only — no scheduler/MCP impact.

def _artifact_title(summary: Optional[str], slug: str) -> str:
    """Human title for a delivered artifact (plain-language pass).

    The stored `summary` is frequently a machine string — e.g.
    "Workspace write: reports/weekly-corpus-review/2026-05-26/output.md" —
    which leaks paths to the operator. Strip those shapes and fall back to
    the titleized slug so the Home reads like a Mac, not a workbench.
    """
    # ADR-587: the prefix list is shared with _plain_summary — one place to
    # add a prefix, two readers. (This one previously missed "Workspace edit:".)
    s = _strip_machine_prefix(summary)
    # If what's left looks like a path or is empty, titleize the slug.
    if not s or "/" in s or s.endswith(".md") or s.endswith(".html"):
        return slug.replace("-", " ").replace("_", " ").title() if slug else "Output"
    return s


@router.get("/workspace/recent-artifacts", response_model=RecentArtifactsResponse)
async def get_recent_artifacts(
    auth: UserClient,
    limit: int = Query(5, ge=1, le=25),
) -> RecentArtifactsResponse:
    """Recent delivered outputs across the workspace (ADR-312 Home slot #5)."""
    try:
        result = (
            auth.client.table("workspace_files")
            .select("path, summary, updated_at")
            .eq(*_substrate_scope_filter(auth))
            .like("path", "/workspace/operation/reports/%/output.md")
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )
        artifacts: list[RecentArtifact] = []
        for row in result.data or []:
            path = row["path"]
            # /workspace/operation/reports/{slug}/{date}/output.md → slug, date
            parts = path.split("/")
            try:
                reports_idx = parts.index("reports")
                slug = parts[reports_idx + 1]
                date = parts[reports_idx + 2]
            except (ValueError, IndexError):
                slug, date = "", ""
            artifacts.append(
                RecentArtifact(
                    slug=slug,
                    date=date,
                    path=path,
                    # Operator-facing title. The stored summary is often a
                    # machine string ("Workspace write: reports/.../output.md")
                    # — strip path-shaped / "Workspace write:" summaries so the
                    # Home shows a human title, falling back to the titleized
                    # slug. Plain-language pass (2026-06-04).
                    summary=_artifact_title(row.get("summary"), slug),
                    updated_at=row.get("updated_at"),
                )
            )
        return RecentArtifactsResponse(artifacts=artifacts)
    except Exception as e:
        logger.error(f"[WORKSPACE_API] Recent artifacts read failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GET /workspace/members — Workspace Members legibility (ADR-373 D2)
# =============================================================================
# Read-only "who can write here, and what regions" view over principal_grants.
# The grant-consult (the gate) authorizes per-principal; this surfaces the same
# facts the gate reads. Provisioning (invite / scope) is a separate ADR — this
# is legibility only.

# The class-default write-region logic now lives in services/principals.py (the
# shared principal-commons home) so the steward wake envelope reads the SAME
# roster logic this route does — Singular Implementation. Re-exported under the
# route's prior private name to keep call sites below unchanged.
from services.principals import class_default_write_regions as _class_default_write_regions

#: ADR-532 D3 — what a NULL read axis actually reaches. The read gate
#: (`primitives/workspace.py::_is_path_readable_for_principal`) returns True for
#: a NULL axis without consulting any prefix, so the honest display is the whole
#: substrate root, not the write class default. Kept as a named constant so the
#: FE's "not narrowed" test is a value comparison, never a role re-derivation.
READ_ALL_REGIONS: list[str] = ["/"]


def _axis_state(scopes) -> str:
    """The powerbox three-way state of a scope axis: 'all' (NULL → class default),
    'none' ([] → deny-all), 'scoped' ([..] → allow-list)."""
    if scopes is None:
        return "all"
    if len(scopes) == 0:
        return "none"
    return "scoped"


def _write_regions_to_zones(regions: list[str]) -> list[str]:
    """Collapse raw ADR-320 write-region roots → operator-facing ADR-424 zones.

    The roster is a legibility surface, and ADR-424 D4 is explicit: no
    operator-facing surface enumerates kernel roots — the filesystem is presented
    as Documents / Downloads / peer folders / System files, never as
    governance/constitution/persona/… The pre-424 roster recited the raw roots
    (the "fifth enumeration" ADR-424's four-collapse missed), showing an owner
    5 kernel chips (Governance·Constitution·Persona·Operation·Contract) and an
    AI connection "Operation" — legacy topology the operator doesn't hold.

    This maps each region to its `WORKSPACE_ROOTS.group` zone (the SINGULAR source
    the Files surface uses), dedupes, and orders Documents → Downloads → System
    files. So the owner reads "Documents · System files" and an AI connection
    reads "Documents" — the same vocabulary the Files tree uses. The gate is
    UNCHANGED (ADR-424: presentation only); write_regions stays the raw truth on
    the wire, write_zones is the operator projection.
    """
    from services.workspace_paths import WORKSPACE_ROOTS
    GROUP_LABEL = {"work": "Documents", "arrival": "Downloads", "system": "System files"}
    GROUP_ORDER = {"Documents": 0, "Downloads": 1, "System files": 2}
    zones: set[str] = set()
    for region in regions:
        root = region.rstrip("/")
        meta = WORKSPACE_ROOTS.get(root)
        if meta:
            zones.add(GROUP_LABEL.get(meta.get("group", "system"), "System files"))
        else:
            # An unknown/peer root (ADR-424 D2 peer folder) → its own name, title-cased.
            zones.add(root.replace("-", " ").replace("_", " ").title() or "Documents")
    return sorted(zones, key=lambda z: GROUP_ORDER.get(z, 99))


@router.get("/workspace/timeline", response_model=WorkspaceTimelineResponse)
async def get_workspace_timeline(
    auth: UserClient, limit: int = 40, before: Optional[str] = None
) -> WorkspaceTimelineResponse:
    """The workspace's shared timeline — what happened, by whom (ADR-408 D5.1,
    ADR-407 Phase 4b).

    DERIVED at read time from the three attributed ledgers (DP29 — never
    stored, never a chat table): substrate revisions
    (workspace_file_versions), invocations (execution_events, no dollar
    figures — ADR-396 display discipline), and proposal lifecycle
    (action_proposals, including who witnessed the decision). Workspace-scoped
    — every member reads the same timeline; each entry carries its actor for
    the FE attribution module. This is the member-visible home of autonomous
    and peer work that private chat threads can't show.
    """
    from services.attention import classify_weight
    from services.workspace_context import substrate_scope_filter

    limit = max(1, min(limit, 100))
    col, val = substrate_scope_filter(auth.user_id, getattr(auth, "workspace_id", None))
    entries: list[TimelineEntry] = []
    page_full = False

    # 1. Substrate revisions — who wrote what.
    try:
        q = (
            auth.client.table("workspace_file_versions")
            .select("path, authored_by, author_identity_uuid, message, revision_kind, created_at")
            .eq(col, val)
        )
        if before:
            q = q.lt("created_at", before)
        rows = q.order("created_at", desc=True).limit(limit).execute().data or []
        page_full = page_full or len(rows) >= limit
        for r in rows:
            at = r.get("created_at") or ""
            entries.append(TimelineEntry(
                kind="revision",
                id=f"revision:{r.get('path') or ''}:{at}",
                at=at,
                actor=r.get("authored_by"),
                actor_id=r.get("author_identity_uuid"),
                title=r.get("path") or "substrate change",
                detail=r.get("message"),
                path=r.get("path"),
                weight=classify_weight(
                    "revision",
                    path=r.get("path"),
                    revision_kind=r.get("revision_kind"),
                ),
            ))
    except Exception as e:
        logger.warning("[TIMELINE] revisions read failed: %s", e)

    # 2. Invocations — who ran what. No cost fields (dollars stay internal).
    try:
        q = (
            auth.client.table("execution_events")
            .select("slug, mode, status, trigger_type, principal_id, created_at")
            .eq(col, val)
        )
        if before:
            q = q.lt("created_at", before)
        rows = q.order("created_at", desc=True).limit(limit).execute().data or []
        page_full = page_full or len(rows) >= limit
        for r in rows:
            at = r.get("created_at") or ""
            entries.append(TimelineEntry(
                kind="invocation",
                id=f"invocation:{r.get('slug') or ''}:{at}",
                at=at,
                actor=r.get("principal_id"),
                # A human principal_id IS the acting uuid; non-uuid principals
                # (freddie, provider hosts) resolve via the string labeler.
                actor_id=r.get("principal_id"),
                title=r.get("slug") or "invocation",
                detail=f"{r.get('mode') or ''} · {r.get('trigger_type') or ''}".strip(" ·"),
                slug=r.get("slug"),
                status=r.get("status"),
                weight=classify_weight(
                    "invocation", mode=r.get("mode"), status=r.get("status"),
                ),
            ))
    except Exception as e:
        logger.warning("[TIMELINE] invocations read failed: %s", e)

    # 3. Proposal lifecycle — what awaited witness + who decided. Timeline
    # position = the decision when one exists, else the arrival.
    try:
        q = (
            auth.client.table("action_proposals")
            .select("id, primitive, family, status, source, approved_by, created_at, approved_at")
            .eq(col, val)
        )
        if before:
            q = q.lt("created_at", before)
        rows = q.order("created_at", desc=True).limit(limit).execute().data or []
        page_full = page_full or len(rows) >= limit
        for r in rows:
            at = r.get("approved_at") or r.get("created_at") or ""
            entries.append(TimelineEntry(
                kind="proposal",
                id=f"proposal:{r.get('id') or ''}:{at}",
                at=at,
                actor=r.get("source"),
                title=f"{r.get('primitive') or 'action'} ({r.get('family') or 'proposal'})",
                proposal_id=r.get("id"),
                status=r.get("status"),
                decided_by=r.get("approved_by"),
                primitive=r.get("primitive"),
                family=r.get("family"),
            ))
    except Exception as e:
        logger.warning("[TIMELINE] proposals read failed: %s", e)

    # 4. Membership — who joined the commons (ADR-608, Layer-1 G2). Derived
    # from the grant ledger itself (DP29 — no event table): human member/
    # viewer grants, JOINS only (a revoked row's created_at is the grant's
    # birth, not the revocation moment — a wrong-timed "left" is worse than
    # none). The owner's founding grant is genesis, not an arrival. Service
    # client: principal_grants is not member-JWT-readable; the workspace
    # filter is the already-resolved acting scope (activity_log precedent).
    try:
        from services.supabase import get_service_client

        from services.workspace_context import effective_workspace_id

        ws_for_grants = val if col == "workspace_id" else effective_workspace_id(auth.user_id)
        if ws_for_grants:
            q = (
                get_service_client().table("principal_grants")
                .select("principal_id, role, status, created_at")
                .eq("workspace_id", ws_for_grants)
                .in_("role", ["member", "viewer"])
                .eq("status", "active")
            )
            if before:
                q = q.lt("created_at", before)
            rows = q.order("created_at", desc=True).limit(limit).execute().data or []
            for r in rows:
                at = r.get("created_at") or ""
                pid = r.get("principal_id")
                entries.append(TimelineEntry(
                    kind="membership",
                    id=f"membership:{pid}:{at}",
                    at=at,
                    # member:{uuid} — the FE attribution module resolves the
                    # name; actor_id lets the viewer layer suppress self
                    # (ADR-405 D4: the joiner is not told they joined).
                    actor=f"member:{pid}",
                    actor_id=pid,
                    title="joined the workspace",
                    status=r.get("role"),
                    weight=classify_weight("membership"),
                ))
    except Exception as e:
        logger.warning("[TIMELINE] membership read failed: %s", e)

    entries.sort(key=lambda e: e.at or "", reverse=True)
    return WorkspaceTimelineResponse(entries=entries[:limit], has_more=page_full)


@router.patch("/workspace", response_model=WorkspaceIdentityResponse)
async def update_workspace_identity(
    body: WorkspaceIdentityUpdate, auth: UserClient
) -> WorkspaceIdentityResponse:
    """Rename / re-glyph the ACTING workspace (workspace identity phase 1).

    Owner-gated by construction: the update runs through the caller's own
    client, so the RLS UPDATE policy (owner_id = auth.uid(), mig 002) is the
    enforcement — a member's PATCH matches zero rows and 403s. The name is
    what invite emails, the invite/share landings, and the switcher show.
    """
    from services.supabase import resolve_owner_workspace_id

    workspace_id = auth.workspace_id or resolve_owner_workspace_id(auth.user_id)
    if not workspace_id:
        raise HTTPException(status_code=404, detail="No workspace to update")

    update: dict = {}
    if "name" in body.model_fields_set:
        name = (body.name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Workspace name cannot be empty")
        if len(name) > 80:
            raise HTTPException(status_code=400, detail="Workspace name is too long (80 max)")
        update["name"] = name
    if "icon" in body.model_fields_set:
        icon = (body.icon or "").strip()
        if len(icon) > 16:
            raise HTTPException(status_code=400, detail="Workspace icon is too long")
        update["icon"] = icon or None
    if "timezone" in body.model_fields_set:
        # ADR-596 D4 — IANA name or clear. Validated here, at the one door,
        # so the column never holds a name the scheduler cannot resolve
        # (store names, never offsets; DST math stays in kernel scheduling).
        tz = (body.timezone or "").strip()
        if tz:
            import pytz
            try:
                pytz.timezone(tz)
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="Unknown timezone — use an IANA name like Asia/Seoul or Europe/London",
                )
        update["timezone"] = tz or None
    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")

    rows = (
        auth.client.table("workspaces")
        .update(update)
        .eq("id", workspace_id)
        .execute()
    ).data or []
    if not rows:
        # RLS matched nothing — the caller is not this workspace's owner.
        raise HTTPException(
            status_code=403, detail="Only the workspace owner can change its name or icon"
        )
    row = rows[0]
    return WorkspaceIdentityResponse(
        workspace_id=workspace_id,
        name=row.get("name") or "",
        icon=row.get("icon"),
        timezone=row.get("timezone"),
    )


@router.post("/workspace", response_model=WorkspaceIdentityResponse, status_code=201)
async def create_owned_workspace(
    body: WorkspaceCreateRequest, auth: UserClient
) -> WorkspaceIdentityResponse:
    """Create a NEW workspace owned by the caller (ADR-465 D2, deliberate genesis).

    The counterpart to the cold-user door's `ensure_owner_workspace`: that one is
    implicit, idempotent and carries the $3 signup grant; this one is explicit,
    named, non-idempotent and mints at ZERO balance (the grant is per-person, not
    per-workspace — see services/workspace_genesis.py).

    Open to ANY authenticated principal, including a member-only one who owns
    nothing yet — that is ADR-465:129's ratified "explicitly start your own
    workspace", the case a share-first arrival has had no path to until now.

    Deliberately NOT owner-gated on the acting workspace: the caller is asking
    for a commons of their own, which says nothing about their role in the one
    they happen to be bound to. Genesis stamps `owner_id` from the authenticated
    user, so the caller can only ever create a workspace they own.

    The response is the new workspace's identity; the CLIENT then binds to it
    (X-Workspace-Id) and hard-navigates, the same rebind the invite/share accept
    paths take (ADR-407 D9 — a bind change requires a full reload).
    """
    from services.workspace_genesis import WorkspaceGenesisError, create_workspace

    try:
        row = create_workspace(auth.user_id, body.name)
    except WorkspaceGenesisError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    logger.info("[WORKSPACE] %s created workspace %s", auth.user_id, row["id"])
    return WorkspaceIdentityResponse(
        workspace_id=row["id"], name=row["name"], icon=row.get("icon")
    )


# ⚠️ The lifecycle verbs live under `/workspace/lifecycle/{id}`, NOT the
# prettier `/workspace/{id}`. A bare path-param segment at this level is a
# CATCH-ALL that shadows every literal `/workspace/*` sibling registered after
# it: with `DELETE /workspace/{workspace_id}` registered first, a real
# `DELETE /workspace/byok` matched `delete_workspace` and would have tried to
# delete a workspace named "byok". Verified by resolving the route against the
# live app, not by reading the decorators. Do not "simplify" this prefix away.
class WorkspaceDeletePreview(BaseModel):
    """What deleting THIS workspace costs — read before the confirm (ADR-578 D4)."""
    workspace_id: str
    name: str
    is_last_owned: bool
    other_principals: list
    deleted_at: Optional[str] = None


def _assert_delete_authority(user_id: str, workspace_id: str) -> None:
    """ADR-578 D2 — delete reuses the L1/L2 clear gate, no new capability.

    Deleting a workspace is strictly heavier than clearing one, and clearing is
    already owner-grade (ADR-476 D2), so a separate permission would add
    vocabulary without adding a decision.
    """
    from services.principal_grants import has_workspace_clear_authority

    if not has_workspace_clear_authority(user_id, workspace_id):
        raise HTTPException(
            status_code=403,
            detail=(
                "Deleting this workspace requires the workspace owner (or a "
                "principal granted `workspace:clear`). It removes every "
                "member's work, not only your own."
            ),
        )


@router.get("/workspace/lifecycle/{workspace_id}/preview", response_model=WorkspaceDeletePreview)
async def preview_workspace_delete(workspace_id: str, auth: UserClient) -> WorkspaceDeletePreview:
    """Who loses access if this workspace is deleted (ADR-578 D4).

    The witness dial (ADR-405): the operator may end a shared commons, but not
    without being shown who it lands on. The confirm surface reads this rather
    than printing a generic "cannot be undone".
    """
    from services.supabase import get_service_client, resolve_owned_workspace_ids
    from services.workspace_delete import other_principals

    _assert_delete_authority(auth.user_id, workspace_id)
    svc = get_service_client()
    rows = (
        svc.table("workspaces").select("id, name, owner_id, deleted_at")
        .eq("id", workspace_id).limit(1).execute()
    ).data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Workspace not found")
    ws = rows[0]
    owned = resolve_owned_workspace_ids(auth.user_id)
    return WorkspaceDeletePreview(
        workspace_id=workspace_id,
        name=ws.get("name") or "",
        is_last_owned=(owned == [workspace_id]),
        other_principals=other_principals(svc, workspace_id, ws.get("owner_id")),
        deleted_at=ws.get("deleted_at"),
    )


@router.delete("/workspace/lifecycle/{workspace_id}")
async def delete_workspace(workspace_id: str, auth: UserClient) -> dict:
    """Soft-delete a workspace (ADR-578 D1). Reversible; destroys nothing."""
    from services.supabase import get_service_client
    from services.workspace_delete import WorkspaceDeleteError, soft_delete_workspace

    _assert_delete_authority(auth.user_id, workspace_id)
    try:
        return soft_delete_workspace(get_service_client(), auth.user_id, workspace_id)
    except WorkspaceDeleteError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/workspace/lifecycle/{workspace_id}/restore")
async def restore_deleted_workspace(workspace_id: str, auth: UserClient) -> dict:
    """Undo a soft delete (ADR-578 D1)."""
    from services.supabase import get_service_client
    from services.workspace_delete import WorkspaceDeleteError, restore_workspace

    _assert_delete_authority(auth.user_id, workspace_id)
    try:
        return restore_workspace(get_service_client(), auth.user_id, workspace_id)
    except WorkspaceDeleteError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/workspace/lifecycle/{workspace_id}/purge")
async def purge_deleted_workspace(workspace_id: str, auth: UserClient) -> dict:
    """Terminal purge (ADR-578 D1 second act). Requires a prior soft-delete."""
    from services.supabase import get_service_client
    from services.workspace_delete import WorkspaceDeleteError, purge_workspace

    _assert_delete_authority(auth.user_id, workspace_id)
    try:
        return purge_workspace(get_service_client(), auth.user_id, workspace_id)
    except WorkspaceDeleteError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/workspace/memberships", response_model=WorkspaceMembershipsResponse)
async def get_workspace_memberships(auth: UserClient) -> WorkspaceMembershipsResponse:
    """The workspaces the CALLER can act in (ADR-407 Phase 5 — the switcher).

    Owner workspace + every workspace where the caller holds an active human
    grant. Labels: the caller's own workspace is 'My workspace'; a granted
    commons is labeled by its owner's email. `is_active` marks the workspace
    the current request resolved to (X-Workspace-Id → owner fallback), so the
    switcher can render the current binding without re-deriving it.
    """
    from services.supabase import (
        display_workspace_name,
        get_service_client,
        resolve_owned_workspace_ids,
        resolve_owner_workspace_id,
    )

    svc = get_service_client()
    acting = auth.workspace_id or resolve_owner_workspace_id(auth.user_id)
    memberships: list[WorkspaceMembership] = []
    seen: set[str] = set()

    try:
        # EVERY owned workspace, oldest-first — not just the home one. The
        # singular `resolve_owner_workspace_id` answers "where is home"; using it
        # here listed ONE owned workspace and silently hid the rest, so a
        # workspace the member had just created was unreachable from the
        # switcher that is supposed to reach it (2026-08-18).
        own_ids = resolve_owned_workspace_ids(auth.user_id)
        own_rows: dict = {}
        if own_ids:
            try:
                fetched = (
                    svc.table("workspaces").select("id, name, icon, timezone")
                    .in_("id", own_ids).execute()
                ).data or []
                own_rows = {r["id"]: r for r in fetched}
            except Exception:  # noqa: BLE001 — labels degrade, rows still render
                pass
        for own_ws in own_ids:
            # Workspace identity phase 1: the label is the CHOSEN name; a
            # workspace still wearing the mint default reads "My workspace"
            # (what this row always said before names were writable).
            row = own_rows.get(own_ws) or {}
            own_name = display_workspace_name(row.get("name"))
            memberships.append(WorkspaceMembership(
                workspace_id=own_ws, role="owner",
                label=own_name or "My workspace", icon=row.get("icon"),
                timezone=row.get("timezone"),
                is_active=(own_ws == acting),
            ))
            seen.add(own_ws)
    except Exception as e:
        logger.warning("[MEMBERSHIPS] owner resolution failed: %s", e)

    try:
        rows = (
            svc.table("principal_grants")
            .select("workspace_id, role")
            .eq("principal_id", auth.user_id)
            .eq("status", "active")
            # ADR-517 D6 — viewer included: a viewer must be able to enter
            # the workspace they can view. (Seats stay owner|member.)
            .in_("role", ["member", "viewer"])
            .execute()
        ).data or []
        # ADR-578 D1: a grant into a soft-deleted workspace shows nothing —
        # the owner branch already filters via resolve_owned_workspace_ids.
        try:
            live_ids = {
                w["id"] for w in (
                    svc.table("workspaces").select("id, deleted_at")
                    .in_("id", [r.get("workspace_id") for r in rows if r.get("workspace_id")])
                    .execute()
                ).data or [] if not w.get("deleted_at")
            } if rows else set()
        except Exception:  # noqa: BLE001 — degrade to showing them
            live_ids = {r.get("workspace_id") for r in rows}
        for r in rows:
            ws_id = r.get("workspace_id")
            if ws_id and ws_id not in live_ids:
                continue
            if not ws_id or ws_id in seen:
                continue
            seen.add(ws_id)
            # A NAMED workspace is labeled by its name (which also stops
            # leaking the owner's email to every member); one still wearing
            # the mint default keeps the owner-email fallback — "My Workspace"
            # would be a nonsense label on a workspace that isn't the
            # caller's.
            label = "Shared workspace"
            icon = None
            ws_tz = None
            try:
                owner_row = (
                    svc.table("workspaces").select("owner_id, name, icon, timezone")
                    .eq("id", ws_id).limit(1).execute()
                ).data or []
                if owner_row:
                    icon = owner_row[0].get("icon")
                    ws_tz = owner_row[0].get("timezone")
                    named = display_workspace_name(owner_row[0].get("name"))
                    if named:
                        label = named
                    else:
                        from jobs.unified_scheduler import get_user_email
                        email = await get_user_email(svc, owner_row[0]["owner_id"])
                        if email:
                            label = f"{email}'s workspace"
            except Exception:
                pass
            memberships.append(WorkspaceMembership(
                workspace_id=ws_id, role=r.get("role") or "member", label=label,
                icon=icon, timezone=ws_tz, is_active=(ws_id == acting),
            ))
    except Exception as e:
        logger.warning("[MEMBERSHIPS] grant lookup failed: %s", e)

    # ADR-501: the caller's clear-authority in the acting workspace — the same
    # verdict the purge gate enforces (routes/account.py), so the FE's Danger
    # Zone affordance and the server can never disagree. Best-effort open on
    # failure (the gate still enforces; a probe error must not hide the card).
    can_clear = True
    try:
        if acting:
            from services.principal_grants import has_workspace_clear_authority
            can_clear = has_workspace_clear_authority(auth.user_id, acting)
    except Exception as e:  # noqa: BLE001 — legibility only, gate enforces
        logger.debug("[MEMBERSHIPS] clear-authority probe failed: %s", e)

    return WorkspaceMembershipsResponse(memberships=memberships, can_clear=can_clear)


@router.get("/workspace/members", response_model=WorkspaceMembersResponse)
async def get_workspace_members(
    auth: UserClient, path: Optional[str] = None
) -> WorkspaceMembersResponse:
    """List the principals with an active grant to this workspace (ADR-373 D2).

    Read-only legibility surface for the Workspace Members panel. Humanizes each
    principal where possible (owner email; MCP/foreign-LLM room name) and shows
    its resolved write-region set (explicit grant scopes, else the class
    default). At N=1 this is just the owner; the surface is multi-principal-ready
    so a future member / foreign-LLM grant appears the moment it is written.

    ?path= (ADR-512 D6, the Get-Info panel): additionally computes each
    principal's reach OVER THAT PATH — can_read / can_write — using the same
    powerbox matcher the gate consults (`path_under_scopes`), so the panel and
    the gate can never disagree. Owner: always both. Axis semantics: NULL →
    class default (read-all; write per class regions); [] → deny-all; [..] →
    longest-prefix allow-list.
    """
    try:
        workspace_id = auth.workspace_id
        if not workspace_id:
            from services.supabase import resolve_owner_workspace_id
            workspace_id = resolve_owner_workspace_id(auth.user_id)
        if not workspace_id:
            # No workspace row yet (pre-substrate) → no members to show.
            return WorkspaceMembersResponse(members=[])

        # The grant table is the gate's authority — read it with the service
        # client (membership RLS is mid-transition; the route already scoped to
        # this workspace_id, resolved from the authenticated owner).
        from services.supabase import get_service_client
        svc = get_service_client()
        rows = (
            svc.table("principal_grants")
            .select("principal_id, role, scopes, read_scopes, write_scopes, status, granted_by, created_at, connected_by")
            .eq("workspace_id", workspace_id)
            .eq("status", "active")
            .order("created_at")
            .execute()
        ).data or []

        # Humanize: owner → email (this auth IS the owner). ADR-373 D2.a:
        # foreign-LLM/platform principal_id is now the PROVIDER host-id
        # (claude.ai / chatgpt), so humanize via the host registry's friendly
        # label. A legacy client_id-keyed row (pre-D2.a, not yet migrated) falls
        # back to the mcp_oauth_clients name lookup so it still shows a name.
        from services.principal_grants import provider_label
        legacy_client_names: dict[str, str] = {}
        legacy_ids = [
            r["principal_id"] for r in rows
            if r.get("role") in ("foreign-llm", "platform", "a2a")
            and provider_label(r["principal_id"]) is None  # not a known host-id
        ]
        if legacy_ids:
            try:
                name_rows = (
                    svc.table("mcp_oauth_clients")
                    .select("client_id, client_name")
                    .in_("client_id", legacy_ids)
                    .execute()
                ).data or []
                legacy_client_names = {r["client_id"]: r.get("client_name") for r in name_rows}
            except Exception as exc:  # best-effort humanization
                logger.debug("[WORKSPACE_API] legacy member client-name lookup failed: %s", exc)

        # ADR-563 — the CONNECTION scope tier per foreign-LLM principal.
        #
        # The join is not direct: a grant is keyed on the PROVIDER host-id
        # (ADR-373 D2.a — `claude.ai`, stable across re-registrations) while
        # tokens are keyed on the churning OAuth `client_id`. `client_ids_for_
        # provider` is the existing bridge (eviction already needs it), so this
        # reuses it rather than inventing a second mapping.
        #
        # Scoped to `connected_by` where present so one member's ChatGPT does
        # not report another member's tier — the ADR-431 distinction that makes
        # revoke work per-connection.
        from services.mcp_scopes import is_legacy_full

        connection_scopes: dict[str, list[str]] = {}
        llm_rows = [r for r in rows if r.get("role") == "foreign-llm"]
        if llm_rows:
            try:
                from services.principal_grants import client_ids_for_provider

                for r in llm_rows:
                    pid = r["principal_id"]
                    ids = client_ids_for_provider(workspace_id, pid) or [pid]
                    q = (
                        svc.table("mcp_oauth_access_tokens")
                        .select("scopes, expires_at, user_id")
                        .in_("client_id", ids)
                    )
                    if r.get("connected_by"):
                        q = q.eq("user_id", str(r["connected_by"]))
                    tok = (q.order("expires_at", desc=True).limit(1).execute()).data or []
                    if tok and tok[0].get("scopes"):
                        connection_scopes[pid] = list(tok[0]["scopes"])
            except Exception as exc:  # best-effort — never fail the roster
                logger.debug("[ADR-563] connection-scope lookup failed: %s", exc)

        # ADR-404 step 5 follow-on (operator-observed 2026-07-04): humanize
        # HUMAN principals for every viewer, not just the owner viewing
        # themself. A member's roster showed raw UUIDs for the owner row and
        # their own row. principal_id for owner/member IS auth.users.id —
        # resolve emails via the auth admin API (service key), best-effort.
        # The set of human ids to resolve to emails: owner/member principal_ids
        # PLUS every `connected_by` (ADR-431 — the member who authorized an AI
        # connection; may not appear as a roster row of their own).
        human_ids: set[str] = set()
        for r in rows:
            if r.get("role") in ("owner", "member", "viewer"):
                human_ids.add(r["principal_id"])
            if r.get("connected_by"):
                human_ids.add(str(r["connected_by"]))

        # THE ONE RESOLVER (`services/principal_display.py`), not a second
        # derivation. This loop used to call `get_user_by_id` itself, once per
        # member, with three differences that were all regressions: no cache (N
        # sequential admin round-trips per roster read), email-ADDRESS only
        # (the resolver prefers `user_metadata.full_name`, then the email's
        # local part — a handle, not an address), and a bare `except` that
        # logged at DEBUG and left the label None.
        #
        # That None is the reported defect: every other principal class ends in
        # `or principal_id`, humans ended in nothing, so one transient admin
        # failure rendered a member as "member-2abf3f96" in the transcript.
        from services.principal_display import UNRESOLVED_MEMBER, resolve_member_names

        human_emails: dict[str, str] = {}
        try:
            human_emails.update(
                {k: v for k, v in resolve_member_names(svc, list(human_ids)).items() if v}
            )
        except Exception as exc:  # noqa: BLE001 — humanization is best-effort
            logger.warning("[WORKSPACE_API] member name resolution failed: %s", exc)
        # The caller's own address is known without a lookup and is the more
        # useful self-label (they recognize their own email).
        if auth.email:
            human_emails[auth.user_id] = auth.email

        # ADR-445 §7 Phase 4 — the per-member cap map (owner-set), read once for the
        # roster. Absent = uncapped. Best-effort — a read failure leaves all None.
        member_caps: dict[str, float] = {}
        try:
            from services.member_caps import load_member_caps
            # Workspace-scoped (ADR-373): the roster's caps belong to the workspace
            # being listed, not to the calling user's own singleton.
            member_caps = load_member_caps(svc, auth.user_id, workspace_id)
        except Exception as exc:  # noqa: BLE001 — legibility, never blocks the roster
            logger.debug("[WORKSPACE_API] member-cap load failed: %s", exc)

        members: list[WorkspaceMember] = []
        for r in rows:
            role = r.get("role") or "member"
            principal_id = r["principal_id"]
            # Powerbox (2026-07-10) — TWO AXES. Prefer the new columns; if a row
            # predates migration 211 (both absent → None) fall back to the legacy
            # `scopes` mirror for BOTH axes (read ⊇ write), preserving behavior.
            raw_read = r.get("read_scopes")
            raw_write = r.get("write_scopes")
            if raw_read is None and raw_write is None and r.get("scopes") is not None:
                raw_read = raw_write = r.get("scopes")

            write_state = _axis_state(raw_write)
            read_state = _axis_state(raw_read)
            explicit = write_state != "all"

            # write_regions (the raw truth behind the operator-zone chips) follow
            # the WRITE axis: class default when unconfigured, [] when deny-all.
            if write_state == "all":
                write_regions = _class_default_write_regions(role)
            elif write_state == "none":
                write_regions = []
            else:
                write_regions = list(raw_write)
            # ADR-532 D3: the read display reads the READ gate. A NULL read axis
            # is read-all (`_is_path_readable_for_principal` returns True before
            # it ever consults a prefix) — NOT the write class default, which is
            # what this reported until 2026-08-07. The pane said a member read
            # `operation/` while the kernel let them read the whole commons: the
            # ADR-501 D1 display/gate divergence, recurring on the read axis.
            # `[]` on the read axis is the deny-all the operator explicitly set.
            read_regions = (
                list(raw_read) if read_state == "scoped"
                else [] if read_state == "none"
                else READ_ALL_REGIONS
            )
            # The combined operator-glance chip: the WIDER axis (read ⊇ write
            # norm). 'all' on either → 'all'; else 'scoped' unless both 'none'.
            access_state = (
                "all" if "all" in (read_state, write_state)
                else "none" if read_state == "none" and write_state == "none"
                else "scoped"
            )

            label: Optional[str] = None
            if role in ("owner", "member", "viewer"):
                # A TERMINAL fallback, like every other class below. Humans were
                # the only principals whose label could come back None, and the
                # surfaces that consume it each invented their own UUID-shaped
                # stand-in — which `principal_display.UNRESOLVED_MEMBER` exists
                # precisely to prevent ("NEVER a UUID or email").
                label = human_emails.get(principal_id) or UNRESOLVED_MEMBER
                if principal_id == auth.user_id:
                    label = f"{label} (you)"
            elif role in ("foreign-llm", "platform", "a2a"):
                # Provider host-id → friendly label; legacy client_id → name lookup.
                label = (
                    provider_label(principal_id)
                    or legacy_client_names.get(principal_id)
                    or principal_id
                )

            # ADR-431 — the connecting-member attribution ("whose ChatGPT").
            # The label is the authorizing member's email (or None for the viewer's
            # own — the FE renders "You" for that case, keyed on connected_by_is_you).
            # Only meaningful for the external-principal classes.
            connected_by = r.get("connected_by")
            connected_by_label: Optional[str] = None
            connected_by_is_you = False
            if connected_by and role in ("foreign-llm", "platform", "a2a"):
                cb = str(connected_by)
                if cb == auth.user_id:
                    connected_by_is_you = True
                    connected_by_label = auth.email  # the viewer's own email, if we have it
                else:
                    connected_by_label = human_emails.get(cb)

            # ADR-512 D6 Get-Info: per-path reach, via the ONE powerbox matcher
            # (the same call the gate makes — panel and gate cannot disagree).
            can_read: Optional[bool] = None
            can_write: Optional[bool] = None
            if path:
                from services.primitives.workspace import path_under_scopes
                rel = path[len("/workspace/"):] if path.startswith("/workspace/") else path.lstrip("/")
                if role == "owner":
                    can_read = can_write = True
                else:
                    # Read axis: NULL → class default read-all (matcher's None
                    # polarity is exactly that); [] → deny-all; [..] → allow-list.
                    can_read = path_under_scopes(rel, raw_read)
                    # Write axis: NULL → the class-default write regions.
                    can_write = path_under_scopes(
                        rel,
                        raw_write if raw_write is not None
                        else _class_default_write_regions(role),
                    )

            members.append(WorkspaceMember(
                principal_id=principal_id,
                role=role,
                label=label,
                write_regions=write_regions,
                write_zones=_write_regions_to_zones(write_regions),  # ADR-424 operator projection
                scopes_explicit=explicit,
                read_scopes=read_regions,
                read_state=read_state,
                write_state=write_state,
                access_state=access_state,
                status=r.get("status") or "active",
                granted_by=r.get("granted_by"),
                created_at=r.get("created_at"),
                connected_by=str(connected_by) if connected_by else None,
                connected_by_label=connected_by_label,
                connected_by_is_you=connected_by_is_you,
                spend_cap_usd=member_caps.get(principal_id),
                can_read=can_read,
                can_write=can_write,
                # ADR-563 — the verb tier the live token carries (foreign-llm
                # only; None when no live token backs the grant).
                connection_scopes=connection_scopes.get(principal_id),
                connection_legacy_full=is_legacy_full(
                    connection_scopes.get(principal_id) or []
                ),
            ))

        # ADR-445 §6 — proactive seat awareness. Human seats = active grants with a
        # human role. `included_seats` = the tier's billing baseline — TWO on every
        # tier post-ADR-490 §1① (the owner + one teammate free; the 3rd human is
        # the free→paid boundary). `seats_available` means "another human may be
        # invited without an upgrade" — which mirrors the invite gate EXACTLY: a
        # PAID (or exempt) workspace can always invite (the team grows freely, each
        # new human a billed seat); a FREE workspace can invite only until it fills
        # its two included seats. Computed from the rows in hand + one tier read.
        human_seats = 0
        included_seats = 0
        seats_available = True
        try:
            from services.billing_tiers import (
                DEFAULT_TIER,
                HUMAN_SEAT_ROLES,
                PAID_TIERS,
                normalize_tier,
                tier_included_seats,
            )
            human_seats = len({
                r["principal_id"] for r in rows
                if r.get("role") in HUMAN_SEAT_ROLES and r.get("principal_id")
            })
            ws_row = (
                svc.table("workspaces")
                .select("subscription_tier, billing_exempt")
                .eq("id", workspace_id)
                .limit(1)
                .execute()
            ).data or []
            ws = ws_row[0] if ws_row else {}
            tier = normalize_tier(ws.get("subscription_tier") or DEFAULT_TIER)
            included_seats = tier_included_seats(tier)
            is_paid_or_exempt = bool(ws.get("billing_exempt")) or tier in PAID_TIERS
            if is_paid_or_exempt:
                seats_available = True  # paid/exempt grows freely
            else:
                # Pending invites also hold seats (each is a seat about to fill).
                pending = (
                    svc.table("workspace_invites")
                    .select("id", count="exact")
                    .eq("workspace_id", workspace_id)
                    .eq("status", "pending")
                    .execute()
                ).count or 0
                seats_available = (human_seats + pending) < included_seats
        except Exception as exc:  # noqa: BLE001 — seat awareness is best-effort legibility
            logger.debug("[WORKSPACE_API] seat awareness compute failed: %s", exc)

        return WorkspaceMembersResponse(
            members=members,
            human_seats=human_seats,
            included_seats=included_seats,
            seats_available=seats_available,
        )
    except Exception as e:
        logger.error(f"[WORKSPACE_API] Workspace members read failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Member lifecycle verbs (ADR-386 D2) — NARROW + REVOKE
# =============================================================================
# Operate on grants that ALREADY exist (no invite flow). The owner grant is
# immutable from this surface (ADR-386 D4) — the helpers raise
# OwnerGrantImmutable, mapped to 403 here. Both resolve the caller's workspace
# from the authenticated owner.

class NarrowMemberRequest(BaseModel):
    # Powerbox (2026-07-10) — two independent axes, path prefixes at arbitrary
    # depth. Send `write_scopes` (the primary narrowing); `read_scopes` optional
    # → defaults to "read ⊇ write" (read mirrors write). Pass read_scopes
    # explicitly to move the read axis independently (a read-only auditor).
    # Polarity per axis: [] = deny-all, [..] = allow-list.
    # `scopes` is the legacy field (= write); accepted for old clients. Exactly
    # one of {write_scopes, scopes} must be present (resolved in the route).
    write_scopes: Optional[list[str]] = None
    read_scopes: Optional[list[str]] = None
    scopes: Optional[list[str]] = None
    # ADR-431 — disambiguate WHICH connection when a provider is connected by
    # several members (foreign-LLM). None targets the singleton grant.
    connected_by: Optional[str] = None


class MemberLifecycleResponse(BaseModel):
    success: bool
    principal_id: str
    action: str                      # "narrow" | "revoke" | "cap"
    scopes: Optional[list[str]] = None
    tokens_deleted: Optional[int] = None


def _resolve_caller_workspace(auth: UserClient) -> str:
    workspace_id = auth.workspace_id
    if not workspace_id:
        # ADR-465 D2: member-aware fallback — a member-only admin (owns no
        # workspace) resolves to their newest active grant instead of 404ing.
        from services.supabase import resolve_workspace_for_principal
        workspace_id = resolve_workspace_for_principal(auth.user_id)
    if not workspace_id:
        raise HTTPException(status_code=404, detail="no workspace for this caller")
    return workspace_id


@router.post("/workspace/members/{principal_id}/narrow", response_model=MemberLifecycleResponse)
async def narrow_member(principal_id: str, body: NarrowMemberRequest, auth: UserClient) -> MemberLifecycleResponse:
    """Tighten a member's scopes (ADR-386 D2 — NARROW; powerbox read⊇write 2026-07-10).

    Authz-only (the member stays connected): the gate's allow-list path then
    denies BOTH writes AND reads outside the narrowed set — the powerbox read
    gate made `narrow` honest on the read axis (before, narrowing restricted
    writes but not reads). `scopes: []` is a deliberate DENY-ALL (the member may
    touch nothing); `scopes: ['operation/', ...]` narrows to those roots. The
    owner grant is immutable (403)."""
    from services.principal_grants import (
        narrow_grant, OwnerGrantImmutable, ScopeEscalation, _UNSET,
    )
    # Owner-only: narrowing is a GOVERNANCE verb. `OwnerGrantImmutable` below
    # protects the TARGET from being the owner; it says nothing about the
    # CALLER, so without this gate any member could rewrite any grant —
    # including their own, widening it (2026-07-31 finding).
    workspace_id = _require_owner_workspace(auth, "change a member's access")
    # write axis: prefer the powerbox field, fall back to the legacy `scopes`.
    write_scopes = body.write_scopes if body.write_scopes is not None else body.scopes
    if write_scopes is None:
        raise HTTPException(status_code=422, detail="write_scopes (or legacy scopes) required")
    # read axis: None-in-body means "not specified" → read ⊇ write (_UNSET); an
    # explicit list (incl. []) moves the read axis independently.
    read_arg = _UNSET if body.read_scopes is None else body.read_scopes
    try:
        narrow_grant(principal_id, workspace_id, write_scopes, body.connected_by, read_scopes=read_arg)
    except OwnerGrantImmutable:
        raise HTTPException(status_code=403, detail="the owner grant cannot be narrowed")
    except ScopeEscalation as se:
        # 403, not 422: this is an authority refusal, not a malformed body.
        raise HTTPException(status_code=403, detail=str(se))
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"[WORKSPACE_API] member narrow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return MemberLifecycleResponse(
        success=True, principal_id=principal_id, action="narrow", scopes=write_scopes,
    )


@router.post("/workspace/members/{principal_id}/revoke", response_model=MemberLifecycleResponse)
async def revoke_member(
    principal_id: str,
    auth: UserClient,
    connected_by: Optional[str] = None,
) -> MemberLifecycleResponse:
    """REVOKE = full eviction (ADR-386 D2/D3): grant revoked + OAuth tokens
    deleted. The member can no longer authenticate, read, or write; it must
    re-authorize from scratch to return. The owner grant is immutable (403).

    ADR-431: `connected_by` (query param) targets a SPECIFIC member's AI
    connection when a provider is connected by several members — revoking
    "seulkim's ChatGPT" leaves the owner's ChatGPT connected. When a HUMAN
    member is revoked, D5 cascades to the AI connections THEY authorized
    (`connected_by = them`), so a departing member takes their AI with them."""
    from services.principal_grants import (
        evict_principal, cascade_member_ai_connections, OwnerGrantImmutable,
    )
    # Owner-only: eviction is a GOVERNANCE verb (see narrow above).
    workspace_id = _require_owner_workspace(auth, "revoke a member")
    try:
        result = evict_principal(principal_id, workspace_id, connected_by)
    except OwnerGrantImmutable:
        raise HTTPException(status_code=403, detail="the owner grant cannot be revoked")
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"[WORKSPACE_API] member revoke failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # ADR-431 D5 — a human member's eviction cascades to the AI connections they
    # authorized. principal_id for a member IS their user id, so it is the
    # `connected_by` of their AI grants. (No-op for AI/provider revokes: an AI
    # principal is never a `connected_by`.)
    try:
        cascade_member_ai_connections(principal_id, workspace_id)
    except Exception as exc:  # best-effort — the member is already evicted
        logger.warning("[ADR-431 D5] AI-connection cascade failed for %s: %s", principal_id[:8], exc)

    # ADR-445 §7 Phase 2 — a removed human shrinks the seat count; sync the LS
    # subscription quantity so the next invoice reflects the smaller team.
    # Best-effort + no-op for free/exempt/no-subscription workspaces.
    try:
        from routes.subscription import sync_seat_quantity
        await sync_seat_quantity(workspace_id)
    except Exception as exc:  # noqa: BLE001 — never block the revoke on a billing sync
        logger.warning("[ADR-445] seat-quantity sync after revoke failed: %s", exc)

    return MemberLifecycleResponse(
        success=True, principal_id=principal_id, action="revoke",
        tokens_deleted=result.get("tokens_deleted"),
    )


# =============================================================================
# Per-member spend caps — ADR-445 §7 Phase 4 (the owner's abuse lever)
# =============================================================================
# The owner bounds one principal's draw from the shared pool this cycle. Owner-only
# (the governance/ sidecar is owner-locked). Setting cap_usd = null clears the cap.

class MemberCapRequest(BaseModel):
    cap_usd: Optional[float] = None   # null / ≤0 clears the cap (uncapped)


@router.post("/workspace/members/{principal_id}/cap", response_model=MemberLifecycleResponse)
async def set_member_spend_cap(
    principal_id: str, body: MemberCapRequest, auth: UserClient,
) -> MemberLifecycleResponse:
    """Owner sets or clears a member's spend cap on the shared pool (ADR-445 §7
    Phase 4). Owner-only. The owner cannot cap themselves (400)."""
    workspace_id = _require_owner_workspace(auth)
    from services.member_caps import set_member_cap
    try:
        caps = set_member_cap(
            auth.client, auth.user_id, principal_id, body.cap_usd,
            workspace_id=workspace_id,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"[WORKSPACE_API] set member cap failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    logger.info(
        "[ADR-445] member cap set: ws=%s principal=%s → %s",
        workspace_id[:8], principal_id[:8], caps.get(principal_id, "cleared"),
    )
    return MemberLifecycleResponse(
        success=True, principal_id=principal_id, action="cap",
    )


# =============================================================================
# Workspace member invites — ADR-404 step 5 (ADR-373 D4 provisioning UX)
# =============================================================================
# The owner invites a human by email; accepting converts the invite into an
# active member grant (ADR-386 lifecycle). Owner-only on the manage verbs;
# the accept verb authenticates the acceptor and matches the invited email.

class InviteCreateRequest(BaseModel):
    email: str


class InviteSummary(BaseModel):
    id: str
    email: str
    role: str
    status: str
    created_at: Optional[str] = None
    expires_at: Optional[str] = None
    invite_link: Optional[str] = None


class InviteListResponse(BaseModel):
    invites: list[InviteSummary]


class InviteAcceptResponse(BaseModel):
    success: bool
    workspace_id: str
    workspace_name: Optional[str] = None
    role: str


def _require_owner_workspace(auth: UserClient, verb: str = "manage invites") -> str:
    """Owner-gate for every GOVERNANCE verb (members can't govern members).

    Governance = anything that mutates WHO may act or HOW FAR they may act:
    invite / revoke-invite / narrow / revoke / spend-cap. Membership alone is
    NOT authority — `_resolve_caller_workspace` answers "which workspace is this
    caller in", never "may this caller govern it".

    2026-07-31: `narrow` and `revoke` resolved the workspace with the bare
    `_resolve_caller_workspace` and so accepted ANY member as a governor. A
    member called `/narrow` against their OWN principal_id and added
    `governance/` to their own write_scopes; the server returned 200 and the
    grant row changed. Receipted on production against the rig workspace —
    see docs/evaluations/findings/2026-07-31-member-can-widen-own-grant.md.
    The `verb` arg exists so the refusal names the actual verb rather than
    always saying "manage invites".
    """
    from services.workspace_invites import workspace_owner_id
    workspace_id = _resolve_caller_workspace(auth)
    if not workspace_id:
        raise HTTPException(status_code=404, detail="No workspace")
    if workspace_owner_id(workspace_id) != auth.user_id:
        raise HTTPException(status_code=403, detail=f"Only the workspace owner can {verb}")
    return workspace_id


@router.post("/workspace/members/invite", response_model=InviteSummary)
async def invite_member(body: InviteCreateRequest, auth: UserClient) -> InviteSummary:
    """Invite a human by email as a member (class-default write regions,
    ADR-373 D3). Re-inviting the same address refreshes the token/expiry."""
    from services.deep_links import app_url
    from services.workspace_invites import InviteError, create_invite, send_invite_email

    # ADR-537 D3 — the TWO DOORS TO MEMBERSHIP AGREE ON WHO MAY OPEN THEM.
    #
    # This was owner-only while share-mint (the other door to exactly the same
    # outcome — a new member grant) allowed write-holders under the
    # `share_mint_policy` dial. A non-owner who could mint a full-access link
    # could not send an email invite: one outcome, two authorities. Under the
    # ADR-537 People tab the email field LEADS, so that mismatch would render a
    # control the server refuses — "a control that exists but cannot be entered",
    # the defect class ADR-532 §3a exists to remove.
    #
    # Deliberately NOT a loosened `_require_owner_workspace`: that helper carries
    # a receipted production incident (2026-07-31, a member widened their own
    # grant via /narrow), and narrow / revoke-member / spend-cap MUST keep it.
    # Those mutate an EXISTING principal's reach; inviting creates a NEW
    # principal — which is precisely what `assert_may_mint_share` governs.
    #
    # The seat gate is untouched: `create_invite`'s free-tier upgrade_required
    # check lives in the service, independent of the caller, so widening
    # authority cannot widen billing.
    from services.workspace_shares import ShareError as _MintError
    from services.workspace_shares import assert_may_mint_share

    workspace_id = _resolve_caller_workspace(auth)
    if not workspace_id:
        raise HTTPException(status_code=404, detail="No workspace")
    try:
        assert_may_mint_share(auth.user_id, workspace_id)
    except _MintError as e:
        raise HTTPException(status_code=403, detail=str(e))
    try:
        invite = create_invite(
            workspace_id=workspace_id, email=body.email, invited_by=auth.user_id,
        )
    except InviteError as e:
        # ADR-445 §6 — the free→paid boundary block is an upgrade-required signal
        # (402), so the FE branches cleanly to an upgrade CTA instead of parsing the
        # detail string. This fires only on the Free tier's 2nd-human invite; a paid
        # workspace never hits it (its team grows freely). Other invite errors
        # (invalid email/role) stay 400.
        status = 402 if e.code == "upgrade_required" else 400
        raise HTTPException(status_code=status, detail=str(e))

    # Best-effort email (never blocks — the returned link is the fallback).
    # An unnamed workspace (mint default) passes None so the mail keeps its
    # generic phrasing — "My Workspace" is nonsense addressed to an invitee.
    ws_name = None
    try:
        from services.supabase import display_workspace_name
        from services.workspace_invites import _svc
        rows = (_svc().table("workspaces").select("name")
                .eq("id", workspace_id).limit(1).execute()).data or []
        ws_name = display_workspace_name(rows[0].get("name")) if rows else None
    except Exception:  # noqa: BLE001
        pass
    await send_invite_email(
        email=invite["email"], token=invite["token"],
        workspace_name=ws_name, inviter_email=auth.email,
    )

    return InviteSummary(
        id=invite["id"], email=invite["email"], role=invite["role"],
        status=invite["status"], created_at=str(invite.get("created_at") or ""),
        expires_at=str(invite.get("expires_at") or ""),
        invite_link=f"{app_url()}/invite/{invite['token']}",
    )


@router.get("/workspace/invites", response_model=InviteListResponse)
async def get_workspace_invites(auth: UserClient) -> InviteListResponse:
    from services.workspace_invites import list_invites
    workspace_id = _require_owner_workspace(auth)
    return InviteListResponse(invites=[
        InviteSummary(
            id=r["id"], email=r["email"], role=r["role"], status=r["status"],
            created_at=str(r.get("created_at") or ""),
            expires_at=str(r.get("expires_at") or ""),
        )
        for r in list_invites(workspace_id)
    ])


@router.post("/workspace/invites/{invite_id}/revoke")
async def revoke_workspace_invite(invite_id: str, auth: UserClient) -> dict:
    from services.workspace_invites import revoke_invite
    workspace_id = _require_owner_workspace(auth)
    if not revoke_invite(workspace_id, invite_id):
        raise HTTPException(status_code=404, detail="No pending invite with that id")
    return {"success": True, "id": invite_id}


@router.get("/invites/{token}")
async def preview_invite(token: str, auth: UserClient) -> dict:
    """Accept-page preview: workspace name + invited address + state."""
    from services.workspace_invites import get_invite_by_token
    invite = get_invite_by_token(token)
    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found")
    return {
        "workspace_name": invite.get("workspace_name"),
        "email": invite["email"],
        "role": invite["role"],
        "status": invite["status"],
        "expires_at": invite.get("expires_at"),
    }


@router.post("/invites/{token}/accept", response_model=InviteAcceptResponse)
async def accept_workspace_invite(token: str, auth: UserClient) -> InviteAcceptResponse:
    """Convert a pending invite into an active member grant (ADR-386 D1).

    The acceptor's JWT email must match the invited address. On success the
    FE binds the commons via the X-Workspace-Id header (ADR-373 sweep spine).
    """
    from services.workspace_invites import InviteError, accept_invite
    try:
        result = accept_invite(token=token, user_id=auth.user_id, user_email=auth.email)
    except InviteError as e:
        status = {
            "not_found": 404, "expired": 410, "not_pending": 409,
            "email_mismatch": 403, "already_owner": 409,
        }.get(e.code, 400)
        raise HTTPException(status_code=status, detail=str(e))

    # ADR-445 §7 Phase 2 — a newly-accepted human grows the seat count; sync the LS
    # subscription quantity so the next invoice bills the added seat. Best-effort +
    # no-op for free/exempt/no-subscription workspaces.
    try:
        from routes.subscription import sync_seat_quantity
        await sync_seat_quantity(result["workspace_id"])
    except Exception as exc:  # noqa: BLE001 — never block the accept on a billing sync
        logger.warning("[ADR-445] seat-quantity sync after invite-accept failed: %s", exc)

    return InviteAcceptResponse(
        success=True,
        workspace_id=result["workspace_id"],
        workspace_name=result.get("workspace_name"),
        role=result["role"],
    )


# =============================================================================
# BYOK — the workspace's own LLM key for the member chat lanes (ADR-439)
# =============================================================================
# Owner-only, enterprise-tier-only. Storing/toggling a key is a consequential,
# workspace-scoped act; availability is gated on tier_byok_available (enterprise).
# The plaintext key never leaves services.byok + the router call site; these
# routes never RETURN the key (status returns only enabled/provider/configured).

class ByokKeyRequest(BaseModel):
    provider: str          # one of BYOK_PROVIDERS (anthropic|openai|gemini|deepseek)
    api_key: str           # the plaintext key — encrypted at rest, never returned


class ByokToggleRequest(BaseModel):
    enabled: bool


def _require_byok_owner_workspace(auth: UserClient) -> str:
    """Owner-gate + enterprise-tier gate for BYOK management. BYOK is an enterprise
    capability (ADR-439 §3) an owner manages; a non-enterprise workspace or a
    non-owner cannot touch it."""
    from services.workspace_invites import workspace_owner_id
    from services.billing_tiers import get_tier, tier_byok_available

    workspace_id = _resolve_caller_workspace(auth)
    if not workspace_id:
        raise HTTPException(status_code=404, detail="No workspace")
    if workspace_owner_id(workspace_id) != auth.user_id:
        raise HTTPException(status_code=403, detail="Only the workspace owner can manage BYOK")
    if not tier_byok_available(get_tier(auth.client, auth.user_id)):
        raise HTTPException(
            status_code=403,
            detail="BYOK is available on the Enterprise plan. Contact us to enable it.",
        )
    return workspace_id


@router.get("/workspace/byok")
async def get_workspace_byok(auth: UserClient) -> dict:
    """The BYOK legibility view (never the key). Available to read on any tier so
    the FE can show 'not available on your plan' vs the toggle; the write verbs
    below enforce the enterprise gate."""
    from services.byok import get_byok_status
    from services.billing_tiers import get_tier, tier_byok_available

    workspace_id = _resolve_caller_workspace(auth)
    available = tier_byok_available(get_tier(auth.client, auth.user_id))
    status = get_byok_status(auth.client, workspace_id)
    return {"available": available, **status}


@router.put("/workspace/byok")
async def set_workspace_byok(body: ByokKeyRequest, auth: UserClient) -> dict:
    """Store the workspace's BYOK key for a provider (encrypted) and enable it."""
    from services.byok import set_byok_key, get_byok_status

    workspace_id = _require_byok_owner_workspace(auth)
    try:
        set_byok_key(auth.client, workspace_id, body.provider, body.api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"success": True, **get_byok_status(auth.client, workspace_id)}


@router.patch("/workspace/byok")
async def toggle_workspace_byok(body: ByokToggleRequest, auth: UserClient) -> dict:
    """Turn BYOK on/off without changing the stored key (revert to managed keys
    while keeping the key on file)."""
    from services.byok import set_byok_enabled, get_byok_status

    workspace_id = _require_byok_owner_workspace(auth)
    set_byok_enabled(auth.client, workspace_id, body.enabled)
    return {"success": True, **get_byok_status(auth.client, workspace_id)}


@router.delete("/workspace/byok")
async def clear_workspace_byok(auth: UserClient) -> dict:
    """Remove the stored key and disable BYOK (full teardown)."""
    from services.byok import clear_byok_key, get_byok_status

    workspace_id = _require_byok_owner_workspace(auth)
    clear_byok_key(auth.client, workspace_id)
    return {"success": True, **get_byok_status(auth.client, workspace_id)}


# =============================================================================
# GET /workspace/recent-revisions — Recently authored substrate (ADR-329 D2)
# =============================================================================
# The Files "Recently authored" feed. Reads authored substrate changes across
# the WHOLE workspace from workspace_file_versions (ADR-209 revision chain),
# ordered by recency, with ADR-209 authored_by attribution. This answers
# "what did the system author in my workspace while I was away, and by whom?"
#
# Distinct from /recent-artifacts (delivered outputs / reports). This is the
# substrate-change feed — any Layer-1 mutation, deliverable or not.
#
# Layer-1-only (ADR-328 D6): surfaces ONLY authored substrate fields (path,
# authored_by, message, created_at). No Layer-2 leakage (no embeddings, no
# search internals). Read-only, workspace-scoped. Browser-consumed only —
# no scheduler/MCP impact.
#
# Hidden paths: `_`-prefixed machine-config files and signals/ temporal logs
# are excluded — same hide rule the Files explorer applies (files/page.tsx
# isHidden). They're system-accumulated state, not authored substrate the
# operator audits.

# System-strict path prefixes excluded from the authored-substrate feed.
_RECENT_REV_EXCLUDE_DIRS = ("/workspace/context/signals",)


def _is_authored_substrate_path(path: str) -> bool:
    """True if a revision path is operator-auditable authored substrate.

    Mirrors the Files explorer hide rule (files/page.tsx isHidden):
    drop `_`-prefixed machine-config files and temporal signal logs.

    ADR-588 D1: also drops a folder MARKER. Creating a folder writes a real
    attributed revision (it is a real act, correctly on the ledger), but Recents
    shows recently-authored DOCUMENTS — a directory has no content to preview,
    so a marker tile would render blank.
    """
    from services.workspace_paths import is_folder_marker
    if is_folder_marker(path):
        return False
    filename = path.rsplit("/", 1)[-1]
    if filename.startswith("_"):
        return False
    for prefix in _RECENT_REV_EXCLUDE_DIRS:
        if path.startswith(prefix):
            return False
    return True


def mint_thumb_urls(client, rows: list[dict]) -> dict[str, str]:
    """Mint serving URLs for the IMAGE rows in `rows`, keyed by path.

    ADR-427 D4: a binary's serving capability is MINTED AT READ, never stored —
    so `workspace_files.content_url` is NULL for every CAS-backed image and a
    listing that just forwards the column can never draw a thumbnail. The
    per-file door (`GET /workspace/file`) already mints; a LISTING has to do the
    same thing for many rows, which is what this is.

    Two round-trips regardless of how many files (never N+1): one to join the
    head revisions to their blobs, one mint per distinct sha. Restricted to
    IMAGES — the only kind a tile can actually draw, so a listing of 30 PDFs
    mints nothing.

    Best-effort by contract: a failure returns fewer entries and the tile falls
    to its format glyph. A preview is an enrichment; it must never be able to
    fail a listing.
    """
    want = {
        r["path"]: r["head_version_id"]
        for r in rows
        if r.get("head_version_id")
        and (r.get("content_type") or "").startswith("image/")
        # SVG markup lives in the text column and is drawn inline by the tile —
        # it has no blob to mint (and `svg_text` already carries it).
        and r.get("content_type") != "image/svg+xml"
    }
    if not want:
        return {}
    try:
        blobs = (
            client.table("workspace_file_versions")
            .select("id, blob_sha, workspace_blobs(storage_key)")
            .in_("id", list(want.values()))
            .execute()
        ).data or []
        sha_by_id = {
            b["id"]: b["blob_sha"]
            for b in blobs
            if isinstance(b.get("workspace_blobs") or {}, dict)
            and (b.get("workspace_blobs") or {}).get("storage_key")
        }
        if not sha_by_id:
            return {}
        from services.storage_backend import get_storage_backend
        from services.supabase import get_service_client

        backend = get_storage_backend(get_service_client())
        # One mint per DISTINCT sha — the CAS is content-addressed, so the same
        # image at two paths is one blob and must not be signed twice.
        minted: dict[str, Optional[str]] = {}
        out: dict[str, str] = {}
        for path, head_id in want.items():
            sha = sha_by_id.get(head_id)
            if not sha:
                continue
            if sha not in minted:
                minted[sha] = backend.mint_serving_url(sha, expires_in=3600)
            if minted[sha]:
                out[path] = minted[sha]
        return out
    except Exception as exc:  # noqa: BLE001 — a preview never fails a listing
        logger.warning("[WORKSPACE_API] thumbnail mint failed: %s", exc)
        return {}


def _thumb_preview(path: str, summary: Optional[str], content: Optional[str]) -> Optional[str]:
    """A short text snippet for an Explorer icon-view text tile (2026-07-02).

    Returns a clean ~140-char preview for markdown/text files (the common case
    in a substrate workspace), so a `.md` tile shows its first real line instead
    of a generic glyph — better than Explorer, which only shows a doc icon.
    Returns None for non-text files (images render a real thumbnail; binaries
    keep a branded glyph). Prefers the curated `summary`; else derives from
    `content`, stripping frontmatter, a `derived_from:` citation line, markdown
    heading/list markers, and blank lines.
    """
    lower = path.lower()
    if not (lower.endswith(".md") or lower.endswith(".txt")):
        return None
    if summary and summary.strip():
        return summary.strip()[:140]
    body = content or ""
    if not body.strip():
        return None
    # Strip a leading YAML frontmatter block if present.
    m = re.match(r"^---\s*\n.*?\n---\s*\n", body, re.DOTALL)
    if m:
        body = body[m.end():]
    lines = []
    for raw in body.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("derived_from:") or s.startswith("<!--"):
            continue
        # Drop leading markdown markers (#, -, *, >) for a cleaner snippet.
        s = re.sub(r"^[#>\-\*\s]+", "", s)
        if s:
            lines.append(s)
        if len(" ".join(lines)) >= 140:
            break
    snippet = " ".join(lines).strip()
    return snippet[:140] if snippet else None


@router.get("/workspace/recent-revisions", response_model=RecentRevisionsResponse)
async def get_recent_revisions(
    auth: UserClient,
    limit: int = Query(20, ge=1, le=50),
) -> RecentRevisionsResponse:
    """Recently authored substrate changes across the workspace (ADR-329 D2).

    Two honesty filters (2026-06-30) so a Recents row always opens a real file:
      1. DEDUP by path — keep only the latest revision per path. A file written
         16× was showing 16 identical rows; the feed is "recently-changed
         FILES", not "every revision event".
      2. LIVE-FILE filter — drop paths with no current `workspace_files` row.
         A revision can outlive its file (e.g. a `remember`-dump inbox path that
         was placed/removed by judgment, ADR-368): the revision survives in the
         chain but `GET /workspace/file` 404s. Listing it produced a Recents row
         that opened to "This file isn't here". A revision to a vanished file is
         not browsable substrate, so it leaves the feed.
    """
    try:
        # Over-fetch generously: dedup + the live-file filter both shrink the
        # set, and a hot path (16 revisions to one file) collapses to one row.
        result = (
            auth.client.table("workspace_file_versions")
            .select("path, authored_by, message, created_at")
            .eq(*_substrate_scope_filter(auth))
            .order("created_at", desc=True)
            .limit(limit * 10)
            .execute()
        )

        # Dedup by path (keep first = latest, since ordered created_at desc) +
        # apply the authored-substrate hide rule.
        # ADR-395: the upload text projection is plumbing (recall reads it, the
        # operator doesn't) — keep it out of Recents too, so a raw + `.extracted.md`
        # pair never shows as two recent changes.
        from services.documents import is_upload_projection
        # ADR-554 D2 — the sibling set for the edge test (see the tree listing).
        _recent_paths = [r.get("path") or "" for r in (result.data or [])]
        latest_by_path: dict[str, dict] = {}
        for row in result.data or []:
            path = row.get("path") or ""
            if not path or path in latest_by_path:
                continue
            if not _is_authored_substrate_path(path):
                continue
            if is_upload_projection(path, siblings=_recent_paths):
                continue
            latest_by_path[path] = row

        from services.workspace_context import live_files_filter

        # One round-trip to find live files AND pull per-format preview material
        # (content_url for image thumbnails, content/summary for text snippets) —
        # the Explorer icon view renders real content, not a generic glyph.
        candidate_paths = list(latest_by_path.keys())
        live: dict[str, dict] = {}
        # Initialized BESIDE `live`, not inside the branch that fills it: an
        # empty workspace skips that branch entirely, and a name defined only
        # under the `if` would NameError on the emit loop below.
        thumb_urls: dict[str, str] = {}
        if candidate_paths:
            # A file in Trash KEEPS its `workspace_files` row (delete is a
            # lifecycle transition, ADR-337 D2), so "the revision resolves a
            # row" is not the same question as "the file is live". Without this
            # the operator's Recents kept offering files they had deleted —
            # 20 briefs, still tiled in the Text app after a folder trash
            # (2026-08-21).
            existing = (
                live_files_filter(
                    auth.client.table("workspace_files")
                    .select(
                        "path, content_url, content_type, summary, content, "
                        # head_version_id rides along so the image rows can have
                        # a serving URL MINTED (ADR-427 D4 — never stored, so
                        # content_url is NULL for every CAS-backed image and
                        # forwarding it alone drew a glyph for every photo).
                        "head_version_id"
                    )
                )
                .eq(*_substrate_scope_filter(auth))
                .in_("path", candidate_paths)
                .execute()
            )
            live = {r["path"]: r for r in (existing.data or [])}
            # The image rows get a freshly-minted, TTL'd serving URL. Without
            # this every photo in Recents rendered as the generic format glyph
            # while its bytes sat in the CAS — the tile's thumbnail path was
            # complete and simply never fed (operator-observed, 2026-08-27).
            thumb_urls = mint_thumb_urls(auth.client, list(live.values()))

        # Emit in recency order (dict preserves insertion = created_at desc),
        # live files only, trimmed to limit.
        revisions: list[RecentRevision] = []
        for path, row in latest_by_path.items():
            f = live.get(path)
            if f is None:  # revision outlived its file → not browsable
                continue
            # Inline SVG (no blob) → ship the markup so the tile draws the vector.
            content_val = f.get("content")
            svg_text = (
                content_val
                if (path.lower().endswith(".svg") and not f.get("content_url") and content_val)
                else None
            )
            revisions.append(
                RecentRevision(
                    path=path,
                    authored_by=row.get("authored_by"),
                    message=row.get("message"),
                    created_at=row.get("created_at"),
                    content_url=thumb_urls.get(path) or f.get("content_url"),
                    content_type=f.get("content_type"),
                    preview=_thumb_preview(path, f.get("summary"), content_val),
                    svg_text=svg_text,
                )
            )
            if len(revisions) >= limit:
                break
        return RecentRevisionsResponse(revisions=revisions)
    except Exception as e:
        logger.error(f"[WORKSPACE_API] Recent revisions read failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PATCH /workspace/file — Edit file content
# =============================================================================

def _is_design_system_editable(client, user_id: str, path: str) -> bool:
    """Is `path` a design-system token/manifest file the var-editor may edit?

    DESIGN-SYSTEMS.md §5 Q4. True iff the file is a `.css` or `_design.yaml`
    AND its folder contains a `_design.yaml` (the ADR-449 manifest convention
    that makes a folder a design system). Best-effort: a lookup failure denies
    (falls through to the fixed-prefix check), never raises. The binary lane
    (fonts/images) is deliberately NOT editable this way — a var-editor writes
    text tokens, not bytes.
    """
    leaf = path.rsplit("/", 1)[-1]
    if not (leaf.endswith(".css") or leaf == "_design.yaml"):
        return False
    folder = path.rsplit("/", 1)[0]
    if not folder:
        return False
    try:
        from services.workspace_context import substrate_scope_filter

        res = (
            client.table("workspace_files")
            .select("path")
            .eq(*substrate_scope_filter(user_id))
            .eq("path", f"{folder}/_design.yaml")
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception as exc:  # noqa: BLE001 — deny on lookup failure
        logger.debug("[WORKSPACE_API] design-system editability check failed: %s", exc)
        return False


@router.patch("/workspace/file")
async def edit_workspace_file(
    auth: UserClient,
    body: FileEditRequest,
) -> dict:
    """
    Edit a workspace file. Upserts by path.

    Allowed for user-editable files: operator-authored substrate under
    `constitution/ + governance/ + operation/ (ADR-320 split of legacy _shared/)`, reviewer principles, memory files,
    task files, and uploads.

    Path normalization matches GET /workspace/file: workspace-relative
    paths (the WriteFile(scope='workspace') convention) get the
    /workspace/ prefix prepended before the editable-prefix check runs.
    """
    raw_path = body.path
    content = body.content

    # ADR-209 + ADR-235 Option A: align with GET handler — accept both
    # absolute and workspace-relative paths. Stored shape is absolute.
    if not raw_path.startswith("/"):
        path = f"/workspace/{raw_path}"
    else:
        path = raw_path

    # ADR-570 D4: the prose text class — .md/.markdown/.txt — is editable at
    # ANY path that survives the standing placement carves (system/, raw
    # inbound/, machine leaves — operator_can_organize, the ONE carve law);
    # which paths a given principal may actually write is the per-principal
    # gate below (class ceiling + grants), never this list. The old
    # file-specific .md entries (IDENTITY.md, MANDATE.md, …) are subsumed by
    # the class rule and deleted. The directory prefixes remain for their
    # NON-prose members (yaml state under context/, `_feedback.md`, etc.).
    from services.workspace_paths import is_prose_document, operator_can_organize

    editable_prose = is_prose_document(path) and operator_can_organize(path)
    editable_prefixes = [
        "/workspace/system/",     # awareness.md, notes.md, style.md
        "/workspace/uploads/",
        "/workspace/operation/reports/",    # per-recurrence outputs + _feedback.md + _run_log.md (ADR-231 D2)
        "/workspace/context/",    # accumulated context domains (entities, _tracker.md, _feedback.md)
    ]
    # DESIGN-SYSTEMS.md §5 Q4 — the permission decision the apply model forces.
    # A design system lives at an operator-chosen path (design-system/yarnnn/,
    # or inside a project), so it has no FIXED prefix. The manifest convention
    # is the identity: a .css or _design.yaml file is editable iff its folder
    # holds a _design.yaml. This is the same discovery contract find_design_
    # systems uses (ADR-449 D1) — the topology is "meaning-folder", not a root.
    # Scoped to the token/manifest text the mechanical var-editor writes; the
    # binary lane (fonts/images) is never edited this way.
    editable_ds = _is_design_system_editable(auth.client, auth.user_id, path)

    if (
        not editable_prose
        and not editable_ds
        and not any(path.startswith(p) or path == p for p in editable_prefixes)
    ):
        raise HTTPException(
            status_code=403,
            detail=f"File not editable via API: {path}. Prose documents (.md/.txt), workspace config and recurrence files are editable.",
        )

    # ADR-501 S1, COMPLETED (Hat-B probe 2026-07-29): the editable-prefix list
    # above answers "is this file editable by an operator at all" — it is NOT a
    # per-principal check. The ADR-373 grant consult lived only on the
    # primitive path (`permission.py`), so THIS door — the Files/settings
    # editor every browser uses — wrote straight through: a member with the
    # displayed `operation/`-only ceiling could PATCH constitution/MANDATE.md
    # and persona/principles.md (probe-verified live against prod; both
    # returned 200). Same gate, same one table, now on both doors.
    from services.primitives.workspace import _is_path_locked_for_principal

    if _is_path_locked_for_principal(auth, path):
        raise HTTPException(
            status_code=403,
            detail=(
                f"Your grant in this workspace does not permit writing {path}. "
                "The workspace owner can widen it from the Access pane."
            ),
        )

    try:
        from datetime import datetime, timezone
        from services.authored_substrate import StaleWriteError, write_revision

        now = datetime.now(timezone.utc).isoformat()

        # ADR-209: operator's direct file edit routes through the Authored
        # Substrate. authored_by="operator" because this is a user-initiated
        # edit via the Context surface. Phase 4: message accepts an explicit
        # short description from UI (revert action sends "revert to r{N}").
        # ADR-406 D2: when the editor states its base, the write is
        # conditional (StaleWriteError → 409 below).
        write_kwargs: dict = {}
        if body.expected_head_version_id is not None:
            write_kwargs["expected_parent_version_id"] = body.expected_head_version_id

        new_head_version_id = write_revision(
            auth.client,
            user_id=auth.user_id,
            path=path,
            content=content,
            authored_by="operator",
            # ADR-410/412 viewer pass — record WHICH human acted; the
            # authored_by string alone is ambiguous in a multi-member commons.
            author_identity_uuid=auth.user_id,
            message=body.message or f"edit file {path}",
            summary=body.summary,
            **write_kwargs,
        )

        logger.info(f"[WORKSPACE_API] File edited: {path}")

        return {
            "success": True,
            "path": path,
            "updated_at": now,
            # ADR-570 D5, the studio door's invisible-save shape: return the
            # new head so the caller can CAS-chain its next save off it
            # without a refetch.
            "head_version_id": new_head_version_id,
        }

    except StaleWriteError as e:
        # ADR-406 D2: the conflict is a witness moment (ADR-405) — return
        # WHO moved past the caller so the surface can say it. Resolution
        # is reload + reapply (revert-as-write), never a hidden merge.
        logger.info(f"[WORKSPACE_API] Stale write rejected: {path}")
        raise HTTPException(
            status_code=409,
            detail={
                "error": "stale_write",
                "path": path,
                "expected_head_version_id": e.expected_parent_version_id,
                "current_head": e.current_head,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WORKSPACE_API] File edit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ADR-209 Phase 4: Authored Substrate revision endpoints
#
# HTTP surface for the revision-aware primitives. Thin wrappers around the
# substrate helpers in services.authored_substrate — RLS via auth.user_id.
# =============================================================================

class RevisionSummary(BaseModel):
    id: str
    authored_by: str
    author_identity_uuid: Optional[str] = None
    # Principal display (2026-08-10 identity pass): the SAME resolution the MCP
    # surface uses (services/principal_display.py), so one revision never
    # renders two ways across surfaces. `authored_by` above stays the raw
    # ledger taxonomy (the FE tooltip / fallback); this is the resolved form
    # ("Kevin via Claude Sonnet", "Claude (via MCP)"). `author_is_you` lets the
    # FE substitute the viewer-relative "You".
    authored_by_display: Optional[str] = None
    author_is_you: bool = False
    message: str
    created_at: str
    parent_version_id: Optional[str] = None
    # Populated only in the subtree (folder Details) case — revisions there
    # span multiple files, so each row carries the file it changed. Omitted
    # (None) for the single-path (file Details) case where the path is the
    # query input and identical for every row.
    path: Optional[str] = None


class RevisionDetail(BaseModel):
    id: str
    path: str
    authored_by: str
    author_identity_uuid: Optional[str] = None
    message: str
    created_at: str
    parent_version_id: Optional[str] = None
    blob_sha: str
    content: Optional[str] = None


class RevisionListResponse(BaseModel):
    path: str
    count: int
    revisions: list[RevisionSummary]


class RevisionDiffResponse(BaseModel):
    path: str
    from_revision: RevisionSummary
    to_revision: RevisionSummary
    diff: str
    identical: bool


@router.get("/workspace/revisions", response_model=RevisionListResponse)
async def list_revisions_route(
    auth: UserClient,
    path: Optional[str] = Query(
        None,
        description="Absolute workspace path for FILE Details (e.g., /workspace/constitution/MANDATE.md). Exactly one of {path, path_prefix} is required.",
    ),
    path_prefix: Optional[str] = Query(
        None,
        description="Absolute workspace folder path for FOLDER Details — returns recent revisions across the subtree (e.g., /workspace/context/portfolio). Exactly one of {path, path_prefix} is required.",
    ),
    limit: int = Query(10, ge=1, le=100, description="Max revisions to return (newest first)"),
) -> RevisionListResponse:
    """ADR-209 Phase 4 + ADR-329 (amended): the revision chain for a node.

    Two scopes — node Details (ADR-329) renders both off this one route:
      - `path` (file Details): the revision chain for a single file, newest
        first. Drives RevisionHistoryPanel's revert/diff (RevisionSummary.path
        is None — the path is the query input).
      - `path_prefix` (folder Details): recent revisions across a folder's
        subtree, newest first, each row carrying the file it changed
        (RevisionSummary.path populated). Read-only aggregate — no revert
        (reverting an aggregate is meaningless; revert lives on file Details).

    Used by the Files surface NodeDetailsPanel.
    """
    if (path is None) == (path_prefix is None):
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of {path, path_prefix}.",
        )

    def _author_display_fields(rows: list[dict]) -> list[dict]:
        """Attach {authored_by_display, author_is_you} per row via the ONE
        resolver (services/principal_display.py — the same one the MCP surface
        renders through). Name resolution needs the admin API → service client.
        Best-effort: a resolution failure leaves the fields defaulted and the
        FE falls back to its local labeler."""
        try:
            from services.principal_display import display_for_rows, member_ids_of
            from services.supabase import get_service_client, resolve_workspace_for_principal

            try:
                ws_id = resolve_workspace_for_principal(auth.user_id)
            except Exception:  # noqa: BLE001
                ws_id = None
            displays = display_for_rows(get_service_client(), rows, workspace_id=ws_id)
            out = []
            for i, r in enumerate(rows):
                ids = member_ids_of(r.get("authored_by"), r.get("author_identity_uuid"))
                out.append({
                    "authored_by_display": displays.get(i),
                    "author_is_you": auth.user_id in ids,
                })
            return out
        except Exception as exc:  # noqa: BLE001 — display never breaks the read
            logger.debug("[WORKSPACE_API] author display attach failed: %s", exc)
            return [{} for _ in rows]

    try:
        if path is not None:
            # File Details — exact-path chain via the substrate helper.
            from services.authored_substrate import list_revisions

            rows = list_revisions(
                auth.client,
                user_id=auth.user_id,
                path=path,
                limit=limit,
            )
            display_fields = _author_display_fields(rows)
            revisions = [
                RevisionSummary(**r, **display_fields[i]) for i, r in enumerate(rows)
            ]
            return RevisionListResponse(path=path, count=len(revisions), revisions=revisions)

        # Folder Details — subtree scan over workspace_file_versions, newest
        # first. Carries per-row path. Same Layer-1-only field set (ADR-328 D6).
        result = (
            auth.client.table("workspace_file_versions")
            .select("id, path, authored_by, author_identity_uuid, message, created_at, parent_version_id")
            .eq(*_substrate_scope_filter(auth))
            .like("path", f"{path_prefix}%")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        subtree_rows = result.data or []
        display_fields = _author_display_fields(subtree_rows)
        revisions = [
            RevisionSummary(
                id=r["id"],
                authored_by=r.get("authored_by") or "system",
                author_identity_uuid=r.get("author_identity_uuid"),
                message=r.get("message") or "",
                created_at=str(r.get("created_at") or ""),
                parent_version_id=r.get("parent_version_id"),
                path=r.get("path"),
                **display_fields[i],
            )
            for i, r in enumerate(subtree_rows)
        ]
        return RevisionListResponse(path=path_prefix, count=len(revisions), revisions=revisions)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WORKSPACE_API] list_revisions failed for {path or path_prefix}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/revisions/{revision_id}", response_model=RevisionDetail)
async def read_revision_route(
    auth: UserClient,
    revision_id: str,
    path: str = Query(..., description="Absolute workspace path for ownership scope"),
) -> RevisionDetail:
    """ADR-209 Phase 4: read a specific historical revision's content + metadata.

    The client passes the path alongside the revision_id for clarity + RLS
    cross-check — the substrate helper enforces user scoping at the query
    layer. Used by RevisionHistoryPanel to fetch a selected revision's
    content for diff/revert preview.
    """
    try:
        from services.authored_substrate import read_revision

        rev = read_revision(
            auth.client,
            user_id=auth.user_id,
            path=path,
            revision_id=revision_id,
        )
        if rev is None:
            raise HTTPException(status_code=404, detail=f"Revision {revision_id} not found for {path}")
        return RevisionDetail(
            id=rev.id,
            path=rev.path,
            authored_by=rev.authored_by,
            author_identity_uuid=rev.author_identity_uuid,
            message=rev.message,
            created_at=str(rev.created_at) if rev.created_at else "",
            parent_version_id=rev.parent_version_id,
            blob_sha=rev.blob_sha,
            content=rev.content,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WORKSPACE_API] read_revision failed for {revision_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workspace/revisions/diff/two", response_model=RevisionDiffResponse)
async def diff_revisions_route(
    auth: UserClient,
    path: str = Query(..., description="Absolute workspace path"),
    from_rev: str = Query(..., description="Revision UUID (from) — typically older"),
    to_rev: str = Query(..., description="Revision UUID (to) — typically newer"),
) -> RevisionDiffResponse:
    """ADR-209 Phase 4: unified diff between two revisions of the same path.

    Pure-Python deterministic diff. Zero LLM cost. Used by RevisionHistoryPanel
    inline-diff view.

    Route segment is /diff/two (not /diff) to avoid colliding with the
    /revisions/{revision_id} pattern above — FastAPI would otherwise treat
    "diff" as a revision_id.
    """
    import difflib

    try:
        from services.authored_substrate import read_revision

        rev_from = read_revision(auth.client, user_id=auth.user_id, path=path, revision_id=from_rev)
        rev_to = read_revision(auth.client, user_id=auth.user_id, path=path, revision_id=to_rev)

        if rev_from is None or rev_to is None:
            raise HTTPException(status_code=404, detail="One or both revisions not found")

        from_content = rev_from.content or ""
        to_content = rev_to.content or ""

        diff_lines = list(
            difflib.unified_diff(
                from_content.splitlines(keepends=True),
                to_content.splitlines(keepends=True),
                fromfile=f"{path}@{rev_from.id[:8]}",
                tofile=f"{path}@{rev_to.id[:8]}",
                n=3,
            )
        )
        diff_text = "".join(diff_lines)

        def _summary(r) -> RevisionSummary:
            return RevisionSummary(
                id=r.id,
                authored_by=r.authored_by,
                author_identity_uuid=r.author_identity_uuid,
                message=r.message,
                created_at=str(r.created_at) if r.created_at else "",
                parent_version_id=r.parent_version_id,
            )

        return RevisionDiffResponse(
            path=path,
            from_revision=_summary(rev_from),
            to_revision=_summary(rev_to),
            diff=diff_text,
            identical=rev_from.blob_sha == rev_to.blob_sha,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WORKSPACE_API] diff_revisions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Helpers
# =============================================================================

def _build_tree(rows: list[dict], root: str) -> list[dict]:
    """Build a folder/file tree from flat workspace_files paths.

    Returns list of tree nodes: {name, path, type, updated_at, children}

    ADR-588 D1: two row kinds arrive here. A DOCUMENT row becomes a file node,
    and the folders above it are synthesized from its path segments (the
    pre-588 behaviour, unchanged — a folder holding files still exists through
    those files). A FOLDER MARKER row (trailing-slash path,
    content_type='inode/directory') becomes a FOLDER node with no children and
    is NEVER emitted as a file. That is what makes an EMPTY folder expressible:
    before ADR-588 the tree could not represent one, which is why create_folder
    seeded a README nobody wrote.
    """
    from services.workspace_paths import is_folder_marker

    # Collect all unique folder paths + file entries
    folders: dict[str, dict] = {}  # path → {name, children, updated_at}
    files: list[dict] = []

    root_prefix = root.rstrip("/") + "/"

    for row in rows:
        full_path = row["path"]
        if not full_path.startswith(root_prefix):
            continue

        # ADR-588: a folder marker registers its OWN folder node (so an empty
        # folder shows) and then falls through to the intermediate-folder
        # registration below for its ancestors — but never reaches the file
        # append. `parts` is computed off the slash-stripped path so the marker
        # and a document under it agree on every ancestor segment.
        marker = is_folder_marker(full_path, row.get("content_type"))
        relative = full_path[len(root_prefix):]
        if marker:
            relative = relative.rstrip("/")
            if not relative:
                continue  # a marker ON the root itself — no node to make
        parts = relative.split("/")

        if marker:
            folder_path = root_prefix + relative
            node = folders.get(folder_path)
            if node is None:
                folders[folder_path] = {
                    "name": parts[-1],
                    "path": folder_path,
                    "type": "folder",
                    "updated_at": row.get("updated_at"),
                    "children": [],
                }
            else:
                # A document already synthesized this folder — keep the node,
                # the marker adds nothing. (Both spellings of "this folder
                # exists" are legal and converge on one node.)
                existing_ts = node.get("updated_at") or ""
                new_ts = row.get("updated_at") or ""
                if new_ts > existing_ts:
                    node["updated_at"] = new_ts

        # Register all intermediate folders
        for i in range(len(parts) - 1):
            folder_path = root_prefix + "/".join(parts[:i + 1])
            if folder_path not in folders:
                folders[folder_path] = {
                    "name": parts[i],
                    "path": folder_path,
                    "type": "folder",
                    "updated_at": row.get("updated_at"),
                    "children": [],
                }
            else:
                # Update folder timestamp to most recent child
                existing_ts = folders[folder_path].get("updated_at") or ""
                new_ts = row.get("updated_at") or ""
                if new_ts > existing_ts:
                    folders[folder_path]["updated_at"] = new_ts

        # Register the file itself — a marker is NOT a file (ADR-588 D1).
        # authored_by + revision_at are set by the tree endpoint when it
        # reads the head_version_id FK embed (ADR-209). They may be None
        # for pre-ADR-209 files or files whose head_version_id is NULL.
        if marker:
            continue
        files.append({
            "name": parts[-1],
            "path": full_path,
            "type": "file",
            "updated_at": row.get("revision_at") or row.get("updated_at"),
            "summary": row.get("summary"),
            "authored_by": row.get("authored_by"),
            # Preview material for the icon-view tile (2026-08-27). Both fields
            # or neither: the tile picks its lane by `content_type` and draws
            # from `content_url`, so serving the URL without the type leaves the
            # thumbnail unreachable. `content_url` is None for everything the
            # tree did not mint (text, folders, an unminted binary) — the tile
            # falls to its format glyph exactly as before.
            "content_type": row.get("content_type"),
            "content_url": row.get("content_url"),
            # Inline SVG markup — the vector lane. Set only for the direct
            # children the listing draws (see the tree endpoint); None means
            # "no vector body here", and the tile falls to its glyph.
            "svg_text": row.get("svg_text"),
        })

    # Build parent→children relationships
    # Top-level items (direct children of root)
    top_level = []

    for file_node in files:
        parent_path = "/".join(file_node["path"].rsplit("/", 1)[:-1])
        if parent_path in folders:
            folders[parent_path]["children"].append(file_node)
        elif parent_path == root.rstrip("/"):
            top_level.append(file_node)

    for folder_path, folder_node in sorted(folders.items()):
        parent_path = "/".join(folder_path.rsplit("/", 1)[:-1])
        if parent_path in folders:
            folders[parent_path]["children"].append(folder_node)
        elif parent_path == root.rstrip("/"):
            top_level.append(folder_node)

    # Sort children by name (folders first, then files)
    def sort_children(nodes):
        for node in nodes:
            if node.get("children"):
                node["children"] = sorted(
                    node["children"],
                    key=lambda n: (0 if n["type"] == "folder" else 1, n["name"]),
                )
                sort_children(node["children"])

    top_level = sorted(top_level, key=lambda n: (0 if n["type"] == "folder" else 1, n["name"]))
    sort_children(top_level)

    return top_level


# =============================================================================
# GET /workspace/state — Workspace lifecycle status (ADR-244)
# =============================================================================
# Replaces the legacy GET /api/memory/user/onboarding-state endpoint. Single
# canonical workspace-state read for both auth/callback (lazy roster
# scaffolding gate) and the Settings → Workspace surface (program lifecycle).
#
# Side-effect preserved from the legacy endpoint: lazy roster scaffolding
# (calls initialize_workspace if no agents). Idempotent — only fires when
# zero agents exist for the user.
#
# Shape (ADR-244 D2):
#   - has_agents, activation_state, active_program_slug — preserved from
#     legacy OnboardingStateResponse for the auth/callback gate.
#   - available_programs — list of activatable bundles (mirrors the existing
#     /api/programs/activatable endpoint shape; co-located here so the
#     Workspace tab makes one round-trip).
#   - substrate_status — per-file skeleton/authored classification for the
#     core workspace files (mandate, identity, autonomy, principles).
#   - capability_gaps — required-but-not-connected platforms for the active
#     bundle; closes the visibility gap between the substrate marker
#     (active_program_slug) and the capability-implicit signal
#     (bundles_active_for_workspace per ADR-224 §3).

class ProgramItem(BaseModel):
    slug: str
    title: str
    tagline: Optional[str] = None
    status: str
    deferred: bool
    oracle: dict = {}
    current_phase: Optional[str] = None
    # ADR-266 D5/D6: human label for the current phase, derived from the
    # bundle MANIFEST's `phases[].label` field. The FE renders this instead
    # of the raw enum slug (no more bare "OBSERVATION" tokens).
    current_phase_label: Optional[str] = None
    # ADR-338 D4.5: the installer "what this program will do" preview — the
    # program's four-flow declaration (DP26) surfaced BEFORE activation. Shape:
    # {flows:[{key,label,present,summary|rationale}], capabilities, watch_count,
    #  ground_truth}. None when the helper can't read the bundle.
    flow_preview: Optional[dict] = None


class SubstrateFileStatus(BaseModel):
    """Per-file classification surfaced to the Workspace tab.

    `state` semantics:
      - "skeleton" — kernel-default placeholder OR bundle template not yet
        overwritten by operator (matches `_is_skeleton_content` heuristics).
      - "authored" — operator has written substantive content.
      - "missing" — file does not exist (rare; substrate seeding failed).
    """
    path: str
    state: str  # "skeleton" | "authored" | "missing"
    last_revised_at: Optional[str] = None


class SubstrateStatus(BaseModel):
    mandate: SubstrateFileStatus
    identity: SubstrateFileStatus
    # ADR-432 D1c: `brand` field removed (Brand retired).
    autonomy: SubstrateFileStatus
    principles: SubstrateFileStatus  # /workspace/persona/principles.md


class CapabilityGap(BaseModel):
    """A capability the active bundle declares but the workspace does not
    have a corresponding active platform_connection for. Surfaces in the
    Workspace tab so operators see why autonomous execution is paused.
    """
    capability: str
    requires_platform: str
    connected: bool


class WorkspaceStateResponse(BaseModel):
    """ADR-244: canonical workspace-state response.

    Replaces ADR-138/240 OnboardingStateResponse — same auth/callback gate
    fields preserved, plus surface-tab signals.
    """
    has_agents: bool = False
    activation_state: str = "none"
    active_program_slug: Optional[str] = None
    available_programs: list[ProgramItem] = []
    substrate_status: SubstrateStatus
    capability_gaps: list[CapabilityGap] = []
    # Account-level inventory of active platform_connections, independent of
    # the active program's declared requirements. The header connections chip
    # shows demand (capability_gaps) AND inventory (connected_platforms) so the
    # two surfaces stay consistent — e.g. a program that declares no required
    # platforms (alpha-author) no longer reads "No connections required" while
    # the Connectors pane shows Slack/Notion/GitHub Connected. The pane reads
    # the same platform_connections set via /api/integrations.
    connected_platforms: list[str] = []


def _classify_file_state(content: Optional[str]) -> str:
    """Classify a workspace file as 'missing', 'skeleton', or 'authored'.

    Delegates to services.workspace_utils.classify_file_state — single
    implementation shared with workspace_init and working_memory.
    """
    from services.workspace_utils import classify_file_state
    return classify_file_state(content)


@router.get("/workspace/state", response_model=WorkspaceStateResponse)
async def get_workspace_state(request: Request, auth: UserClient) -> WorkspaceStateResponse:
    """ADR-244: workspace lifecycle state — sole canonical read.

    Side effect: triggers lazy roster scaffolding when no agents exist.
    This is the load-bearing first-login behavior the auth/callback depends
    on — preserved verbatim from the legacy onboarding-state endpoint
    (browser timezone via X-Timezone header + workspace_init_complete
    system-card write on first init).
    """
    from services.workspace import UserMemory
    from services.workspace_paths import (
        CONSTITUTION_MANDATE_PATH,
        PERSONA_IDENTITY_PATH,
        GOVERNANCE_AUTONOMY_PATH,
        GOVERNANCE_BUDGET_PATH,
        PERSONA_PRINCIPLES_PATH,
    )
    from services.bundle_reader import (
        _all_slugs,
        _load_manifest,
        classify_activation_state,
    )
    from services.programs import (
        resolve_hired_program_slug,
        resolve_judgment_home,
        compute_capability_gaps,
    )

    # ─── Step 0: the cold-user door (ADR-465 D2 — lazy owner-genesis) ────
    # The migration-106 auto-mint trigger is retired (migration 233); the
    # workspaces row now mints HERE, and only for a principal who resolves NO
    # workspace at all (no owner row, no grants — the cold sign-up). A
    # share-first arrival holds a member grant, so auth.workspace_id is set
    # and this door never fires: join-only genesis is real (no phantom
    # owner-workspace). The contextvar is re-stamped so every downstream
    # substrate read in this request scopes to the fresh workspace.
    if not auth.workspace_id:
        from services.supabase import ensure_owner_workspace
        from services.workspace_context import set_request_workspace
        auth.workspace_id = ensure_owner_workspace(auth.user_id)
        set_request_workspace(auth.workspace_id)

    um = UserMemory(auth.client, auth.user_id)

    # ─── Step 1: lazy genesis ───────────────────────────────────────────
    # ADR-414 D4 follow-on: the trigger predicate re-keys to the budget dial
    # — the SAME key `initialize_workspace` uses for idempotency. The prior
    # probe ("zero non-archived agents rows") became permanently true on
    # every bare workspace after migration 205 retired the thinking_partner
    # row, re-entering init (4 redundant reads + a log line) on every state
    # call. `has_agents` stays in the response as a vestige (no FE reader —
    # the auth-callback gate keys on activation_state); it reports the
    # post-init value the legacy shape always carried.
    has_agents = True
    try:
        existing_budget = await um.read(GOVERNANCE_BUDGET_PATH)
        if not existing_budget:
            # ADR-286: `browser_tz` no longer threaded through workspace_init —
            # IDENTITY.md is bundle-owned, not kernel-scaffolded. Operator
            # declares timezone via chat or bundle authoring after activation.
            from services.workspace_init import initialize_workspace
            init_result = await initialize_workspace(auth.client, auth.user_id)

            # ADR-179: Write workspace_init_complete system card as persisted
            # session_messages row. Zero LLM cost. TP reads as conversation
            # history on every subsequent turn. Best-effort — workspace init
            # already succeeded; failure to write the card is non-fatal.
            if not init_result.get("already_initialized"):
                try:
                    from routes.feed import get_or_create_session, append_message
                    session = await get_or_create_session(auth.client, auth.user_id)
                    agents_created = init_result.get("agents_created", [])
                    tasks_created = init_result.get("tasks_created", [])
                    await append_message(
                        client=auth.client,
                        session_id=session["id"],
                        role="assistant",
                        content=(
                            "Your workspace is ready. Tell me what you work on "
                            "and I'll set up the rest."
                        ),
                        metadata={
                            "system_card": "workspace_init_complete",
                            "agents_created": len(agents_created),
                            "tasks_created": tasks_created,
                            "summary": "Workspace ready",
                            "pulse": "heartbeat",
                            "weight": "material",
                        },
                    )
                except Exception as card_err:
                    logger.warning(
                        f"[WORKSPACE_STATE] system_card write failed: {card_err}"
                    )
    except Exception as e:
        logger.error(f"[WORKSPACE_STATE] Lazy scaffold failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # ─── Step 2: activation state + active program slug ─────────────────
    # Active-program derivation and activation-state classification are
    # independent reads; keep them in separate try-blocks so a failure in
    # one never silently nulls the other. (Regression: 7e777bf dropped the
    # classifier's make_client_fn param while this call still passed it,
    # raising TypeError that swallowed the program slug for every workspace.)
    # Both the slug-resolve and the capability-gap walk now go through the
    # shared services.programs helpers — same derivation working_memory uses.
    # ADR-414 D5: the activation record is the hire grant row, not a prose marker.
    active_program_slug: Optional[str] = resolve_hired_program_slug(auth.user_id)
    # ADR-414 §9a: the judgment files live in the hired agent's home; the
    # workspace-root paths are the steward-era layout (no-hire workspaces).
    judgment_home = resolve_judgment_home(auth.user_id)
    mandate_path = f"{judgment_home}MANDATE.md" if judgment_home else CONSTITUTION_MANDATE_PATH
    identity_path = f"{judgment_home}IDENTITY.md" if judgment_home else PERSONA_IDENTITY_PATH
    principles_path = f"{judgment_home}principles.md" if judgment_home else PERSONA_PRINCIPLES_PATH
    autonomy_path = f"{judgment_home}AUTONOMY.md" if judgment_home else GOVERNANCE_AUTONOMY_PATH
    mandate_content = await um.read(mandate_path)
    activation_state = "none"
    try:
        activation_state = classify_activation_state(
            auth.user_id,
            mandate_content,
        )
    except Exception as exc:
        logger.warning(f"[WORKSPACE_STATE] activation-state classification failed: {exc}")

    # ─── Step 3: available programs (activatable list) ──────────────────
    available_programs: list[ProgramItem] = []
    try:
        for slug in _all_slugs():
            manifest = _load_manifest(slug)
            if not manifest:
                continue
            status = manifest.get("status")
            if status not in ("active", "deferred"):
                continue
            # ADR-266 D5/D6: derive current_phase_label from MANIFEST.phases.
            # Same shape as services.composition_resolver._bundle_metadata —
            # bundle MANIFEST is the singular source of truth for phase labels.
            current_phase = manifest.get("current_phase")
            phases = manifest.get("phases") or []
            current_phase_label = next(
                (p.get("label") for p in phases if p.get("key") == current_phase),
                None,
            )
            # ADR-338 D4.5: the installer four-flow preview (shared helper —
            # same canonical slots the activatable route + the D9 gate read).
            from services.bundle_reader import four_flow_preview
            available_programs.append(ProgramItem(
                slug=manifest.get("slug"),
                title=manifest.get("title"),
                tagline=manifest.get("tagline"),
                status=status,
                deferred=(status == "deferred"),
                oracle=manifest.get("oracle") or {},
                current_phase=current_phase,
                current_phase_label=current_phase_label,
                flow_preview=four_flow_preview(slug),
            ))
    except Exception as exc:
        logger.warning(f"[WORKSPACE_STATE] available_programs read failed: {exc}")

    # ─── Step 4: substrate status (per-file classification) ─────────────
    async def _read_file_status(path: str) -> SubstrateFileStatus:
        try:
            content = await um.read(path)
            return SubstrateFileStatus(
                path=path,
                state=_classify_file_state(content),
                last_revised_at=None,  # populated below via head_version_id lookup
            )
        except Exception:
            return SubstrateFileStatus(path=path, state="missing")

    substrate_status = SubstrateStatus(
        mandate=await _read_file_status(mandate_path),
        identity=await _read_file_status(identity_path),
        autonomy=await _read_file_status(autonomy_path),
        principles=await _read_file_status(principles_path),
    )

    # last_revised_at via batched workspace_files lookup (singular round-trip)
    try:
        paths = [
            mandate_path, identity_path,
            autonomy_path, principles_path,
        ]
        rows = (
            auth.client.table("workspace_files")
            .select("path, updated_at")
            .eq(*_substrate_scope_filter(auth))
            .in_("path", [f"/workspace/{p}" for p in paths])
            .execute()
        )
        timestamps = {
            (r["path"] or "").replace("/workspace/", "", 1): r.get("updated_at")
            for r in (rows.data or [])
        }
        substrate_status.mandate.last_revised_at = timestamps.get(mandate_path)
        substrate_status.identity.last_revised_at = timestamps.get(identity_path)
        substrate_status.autonomy.last_revised_at = timestamps.get(autonomy_path)
        substrate_status.principles.last_revised_at = timestamps.get(principles_path)
    except Exception as exc:
        logger.warning(f"[WORKSPACE_STATE] timestamp lookup failed: {exc}")

    # ─── Step 5: connected platforms + capability gaps ──────────────────
    # The active platform_connections set serves two surfaces: the inventory
    # (connected_platforms — always populated, program-independent) and the
    # demand check (capability_gaps — only when a program declares required
    # platforms). Manifest-walk logic lives in services.programs
    # .compute_capability_gaps (shared with working_memory); here we fetch the
    # connected set once via the RLS client and feed both.
    connected_platforms: list[str] = []
    capability_gaps: list[CapabilityGap] = []
    try:
        connections = (
            auth.client.table("platform_connections")
            .select("platform")
            .eq("user_id", auth.user_id)
            .eq("status", "active")
            .execute()
        )
        connected = {r["platform"] for r in (connections.data or [])}
        connected_platforms = sorted(connected)
        if active_program_slug:
            capability_gaps = [
                CapabilityGap(
                    capability=g["capability"],
                    requires_platform=g["platform"],
                    connected=g["connected"],
                )
                for g in compute_capability_gaps(active_program_slug, connected)
            ]
    except Exception as exc:
        logger.warning(f"[WORKSPACE_STATE] platform_connections lookup failed: {exc}")

    return WorkspaceStateResponse(
        has_agents=has_agents,
        activation_state=activation_state,
        active_program_slug=active_program_slug,
        available_programs=available_programs,
        substrate_status=substrate_status,
        capability_gaps=capability_gaps,
        connected_platforms=connected_platforms,
    )


# =============================================================================
# GET /workspace/setup-bundle — Single bundled read for /workspace page (ADR-266)
# =============================================================================
# Collapses 7 round-trips (state + 6 file reads) into 1. The /workspace surface
# (WorkspaceConfigSection) calls this once on mount and on activation refresh.
# Cards keep their self-fetch fallback path for the /agents reuse surface
# (singular implementation: one card, two data-source modes selected by prop
# presence per ADR-266 D8).
#
# Each FileWithRevision returns:
#   - content: workspace_files.content (None if missing)
#   - last_revision: most recent workspace_file_versions row (ADR-209 Phase 4)
#                    used by cards to render "Updated 3 days ago by you" line.
#
# All paths absolute (/workspace/...) for symmetry with workspace_files storage.

class FileWithRevision(BaseModel):
    """One file's content + most recent revision metadata.

    `content` is None when the file does not exist (rare — substrate seeding
    failed). `last_revision` is None when no revision rows exist yet (also
    rare — every write goes through write_revision per ADR-209 Phase 2).
    """
    path: str
    content: Optional[str] = None
    last_revision: Optional[RevisionSummary] = None


class WorkspaceSetupBundleResponse(BaseModel):
    """ADR-266 D8: bundled response for /workspace page mount.

    `state` mirrors the existing /workspace/state shape verbatim — no
    duplication of derivation logic, single source of truth.

    The 6 file fields cover every substrate file the four concept cards
    (Mandate, Autonomy, Principles, Identity/Brand) consume.
    """
    state: WorkspaceStateResponse
    mandate: FileWithRevision
    autonomy_yaml: FileWithRevision
    principles_prose: FileWithRevision
    principles_yaml: FileWithRevision
    identity: FileWithRevision
    # ADR-432 D1c: `brand` field removed (Brand retired).


@router.get("/workspace/setup-bundle", response_model=WorkspaceSetupBundleResponse)
async def get_workspace_setup_bundle(
    request: Request,
    auth: UserClient,
) -> WorkspaceSetupBundleResponse:
    """ADR-266: bundled read for the /workspace page.

    Single endpoint replaces the 7 fan-out reads (1 state + 6 file fetches)
    that WorkspaceConfigSection + 4 cards used to issue independently. The
    cards still accept self-fetch fallback when no data prop is supplied
    (preserves /agents reuse surface).

    All file reads issued in parallel via asyncio.gather. Revision lookups
    use existing list_revisions() with limit=1.
    """
    import asyncio
    from services.workspace import UserMemory
    from services.workspace_paths import (
        CONSTITUTION_MANDATE_PATH,
        PERSONA_IDENTITY_PATH,
        GOVERNANCE_AUTONOMY_YAML_PATH,
        PERSONA_PRINCIPLES_PATH,
        PERSONA_PRINCIPLES_YAML_PATH,
    )
    from services.authored_substrate import list_revisions

    # ─── Step 1: state derivation (delegate to existing endpoint logic) ──
    # Calling get_workspace_state directly would re-trigger the lazy
    # scaffolding side-effect; that's correct here too — first mount of
    # /workspace deserves the same scaffolding gate as auth/callback.
    state = await get_workspace_state(request, auth)

    # ─── Step 2: file reads (parallel, absolute paths) ──────────────────
    # UserMemory.read takes workspace-relative paths and prefixes
    # /workspace/ internally. The path constants are relative; the
    # absolute form is what we return to the caller (matches what cards
    # currently pass to api.workspace.getFile).
    um = UserMemory(auth.client, auth.user_id)

    async def _read(rel_path: str) -> Optional[str]:
        try:
            return await um.read(rel_path)
        except Exception:
            return None

    # ADR-432 D1c: brand read removed (Brand retired).
    (
        mandate_content,
        autonomy_yaml_content,
        principles_prose_content,
        principles_yaml_content,
        identity_content,
    ) = await asyncio.gather(
        _read(CONSTITUTION_MANDATE_PATH),
        _read(GOVERNANCE_AUTONOMY_YAML_PATH),
        _read(PERSONA_PRINCIPLES_PATH),
        _read(PERSONA_PRINCIPLES_YAML_PATH),
        _read(PERSONA_IDENTITY_PATH),
    )

    # ─── Step 3: revision metadata (parallel, absolute paths) ───────────
    # workspace_file_versions.path is stored absolute (matches workspace_files).
    abs_paths = {
        "mandate": f"/workspace/{CONSTITUTION_MANDATE_PATH}",
        "autonomy_yaml": f"/workspace/{GOVERNANCE_AUTONOMY_YAML_PATH}",
        "principles_prose": f"/workspace/{PERSONA_PRINCIPLES_PATH}",
        "principles_yaml": f"/workspace/{PERSONA_PRINCIPLES_YAML_PATH}",
        "identity": f"/workspace/{PERSONA_IDENTITY_PATH}",
    }

    def _last_rev_sync(abs_path: str) -> Optional[dict]:
        try:
            rows = list_revisions(
                auth.client,
                user_id=auth.user_id,
                path=abs_path,
                limit=1,
            )
            return rows[0] if rows else None
        except Exception as exc:
            logger.warning(f"[SETUP_BUNDLE] revision lookup failed for {abs_path}: {exc}")
            return None

    # list_revisions is sync (Supabase Python client); run in threadpool
    # to keep the gather parallel without blocking the event loop.
    rev_results = await asyncio.gather(
        *(asyncio.to_thread(_last_rev_sync, abs_paths[k]) for k in abs_paths)
    )
    rev_map = dict(zip(abs_paths.keys(), rev_results))

    def _build(key: str, content: Optional[str]) -> FileWithRevision:
        rev = rev_map.get(key)
        return FileWithRevision(
            path=abs_paths[key],
            content=content,
            last_revision=RevisionSummary(**rev) if rev else None,
        )

    return WorkspaceSetupBundleResponse(
        state=state,
        mandate=_build("mandate", mandate_content),
        autonomy_yaml=_build("autonomy_yaml", autonomy_yaml_content),
        principles_prose=_build("principles_prose", principles_prose_content),
        principles_yaml=_build("principles_yaml", principles_yaml_content),
        identity=_build("identity", identity_content),
    )


# =============================================================================
# GET /workspace/home-bundle — DELETED (ADR-435, 2026-07-10)
# =============================================================================
# The Home surface was deleted (the one composition in a registry of mirrors).
# This endpoint was its single bundled read (ADR-312 six-slot fan-out → one
# call). Each concern it aggregated is now read by its own mirror surface's
# existing handler: proposals → list_proposals (queue), recent_artifacts →
# get_recent_artifacts (files), judgment_log → the decisions read (activity),
# MANDATE/autonomy → the workspace-settings reads. No new consumer; no caller
# remains (HomeRenderer was the sole one).


# =============================================================================
# GET /workspace/export — the portability export (ADR-328 D4, via ADR-510)
# =============================================================================
# Category 1 leaves as a plain GIT REPOSITORY inside a zip: the authored
# filesystem as the working tree, the full attributed revision chain as commit
# history. Delivered as a ROUTE, not a primitive (ADR-328 Q2 — "download your
# workspace" is an operator-sovereignty affordance, not an LLM-surface tool).
# The manifest beside the repo DECLARES every omission (D8's binding
# discipline: silent omission would make "portable" a lie). RLS scopes the row
# walk to the caller's workspace; a powerbox-narrowed principal's export omits
# ungranted paths and the manifest declares the count.


@router.get("/workspace/export")
def export_workspace(auth: UserClient):
    """Download the workspace as a git repo in a zip (+ declared omissions)."""
    import shutil
    import tempfile
    import zipfile
    from datetime import datetime, timezone
    from pathlib import Path

    from fastapi.responses import StreamingResponse
    from starlette.background import BackgroundTask

    from services.export.git_export import build_workspace_export, manifest_markdown
    from services.primitives.workspace import grant_read_scopes, path_under_scopes
    from services.supabase import get_service_client
    from services.workspace_context import effective_workspace_id

    ws = effective_workspace_id(auth.user_id, None)
    scopes = grant_read_scopes(auth)
    readable = None if scopes is None else (lambda p: path_under_scopes(p, scopes))

    tmp = tempfile.mkdtemp(prefix="yarnnn-export-")
    try:
        manifest = build_workspace_export(
            auth.client,
            get_service_client(),
            user_id=auth.user_id,
            workspace_id=ws,
            out_dir=Path(tmp) / "workspace",
            readable=readable,
        )
        stamp = datetime.now(timezone.utc)
        (Path(tmp) / "EXPORT-MANIFEST.md").write_text(
            manifest_markdown(
                manifest, workspace_id=ws,
                generated_at=stamp.isoformat(timespec="seconds"),
            )
        )
        zip_path = Path(tmp) / "export.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(Path(tmp).rglob("*")):
                if p == zip_path or p.is_dir():
                    continue
                zf.write(p, p.relative_to(tmp))

        fh = open(zip_path, "rb")

        def _cleanup(handle=fh, root=tmp):
            handle.close()
            shutil.rmtree(root, ignore_errors=True)

        filename = f"yarnnn-export-{stamp:%Y%m%d}.zip"
        return StreamingResponse(
            fh,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(zip_path.stat().st_size),
            },
            background=BackgroundTask(_cleanup),
        )
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
