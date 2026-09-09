"""An agent's FACE — yarnnn's kernel faces, mirrored into every workspace.

ADR-641 amendment. The 2026-07-16 operator ruling is that an agent's face is
an uploaded PICTURE, not a colour swatch and not a generated system creature.
`AgentFace.tsx` was built for exactly that and shipped with the URL chain
wired — but NOTHING EVER SUPPLIED A PICTURE. `avatar_url` did not exist
anywhere in the backend, so every agent fell through to its initial forever,
and the ruling was true on paper and dead in practice.

This is the missing half: yarnnn's three kernel agents ship WITH faces.

⭐ WHY THE FACE IS A FILE IN THE COMMONS, not a bundled static asset.
A face served from `/static/designer.png` would be invisible to the substrate:
not readable by a lane, not listable in Files, not reachable by a connected
principal, not attributable, not replaceable by the member. Everything in this
system that a principal can SEE is a file (ADR-209), and a face a member cannot
open, export or overwrite would be the one identity-bearing thing outside the
commons. So the faces land as ordinary `write_revision` rows.

⭐ WHY IT MIRRORS RATHER THAN SEEDS.
Seeding at workspace-genesis would freeze the face a workspace was born with:
a re-drawn glyph would reach new workspaces and never old ones, which is the
drift ADR-630 already solved for skills. This copies that solution exactly —
manifest-cheap (one small read when nothing changed), sha-compared, idempotent,
and running on the same scheduler lane. A face changes in code, and every
workspace picks it up on the next tick.

⭐ WHY A MEMBER CAN OVERWRITE IT AND THAT IS THE POINT.
`system/` is locked, so a mirrored kernel face is not member-writable — but the
registry resolves an agent's face by looking for a MEMBER face FIRST
(`agents/{slug}/face.png`, in the agent's own home, ADR-624's freely-writable
half). A member who uploads their own picture for Editor gets it, permanently,
and the mirror never fights them: the two paths are different files and the
lookup order is the whole policy. "An agent you HIRED having a face you CHOSE"
is the ruling; this is what makes choosing possible.

The PNGs are committed beside this module and ship with the deploy;
`_generate.py` is how they are (re)made from Lucide's own geometry.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

FACES_DIR = Path(__file__).resolve().parent
FACE_FILE = "face.png"

#: Where the kernel mirror lands (workspace-relative). `system/` is locked for
#: every caller class and is the kernel's root (ADR-320) — a mirrored face is
#: yarnnn's, not the workspace's, and must not be silently editable.
KERNEL_FACES_PREFIX = "system/agents/"
#: A member's OWN face for an agent, in that agent's home (ADR-624: `memory/`
#: and the grant sidecars are the home's two halves; a face is neither, so it
#: sits at the home's root as ordinary, freely-writable substrate).
MEMBER_FACE_DIR = "agents/"
#: One tiny machine file records WHICH kernel version is mirrored, so the
#: per-tick check is one small row rather than N image reads.
KERNEL_MANIFEST_PATH = f"{KERNEL_FACES_PREFIX}_manifest.yaml"
KERNEL_FACES_AUTHOR = "system:kernel-faces"

_kernel_cache: Optional[dict[str, dict]] = None


def kernel_face_path(slug: str) -> str:
    """Workspace-relative path of a MIRRORED kernel face."""
    return f"{KERNEL_FACES_PREFIX}{slug}/{FACE_FILE}"


def member_face_path(slug: str) -> str:
    """Workspace-relative path of a MEMBER-supplied face — the one that wins."""
    return f"{MEMBER_FACE_DIR}{slug}/{FACE_FILE}"


def _load_kernel() -> dict[str, dict]:
    """Every shipped face, by agent slug, with its sha. Cached per process."""
    global _kernel_cache
    if _kernel_cache is not None:
        return _kernel_cache
    faces: dict[str, dict] = {}
    for f in sorted(FACES_DIR.glob("*.png")):
        raw = f.read_bytes()
        faces[f.stem] = {
            "slug": f.stem,
            "raw": raw,
            "sha": hashlib.sha256(raw).hexdigest(),
            "path": kernel_face_path(f.stem),
        }
    _kernel_cache = faces
    return faces


def kernel_manifest() -> dict:
    """`version` = sha over every face's sha in slug order; `faces` = slug → sha.
    What the mirror compares against a workspace's stored copy."""
    faces = _load_kernel()
    joined = "\n".join(f"{slug}:{f['sha']}" for slug, f in faces.items())
    return {
        "version": hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16],
        "faces": {slug: f["sha"] for slug, f in faces.items()},
    }


def has_kernel_face(slug: str) -> bool:
    return (slug or "").strip() in _load_kernel()


def _read_manifest(client: Any, user_id: str, workspace_id: Optional[str]) -> dict:
    """The workspace's stored mirror manifest, or {}.

    ⚠️ The path is ABSOLUTE (`/workspace/...`) and the scope filter is the
    shared one — both matter. The first cut queried the workspace-RELATIVE
    path with a bare `workspace_id` filter and matched zero rows, so the
    version check never fired: every scheduler tick rewrote all three faces
    forever, minting a fresh revision each time. It looked correct because the
    faces WERE present and correct; only re-running the mirror and watching
    `written` stay at 3 exposed it.
    """
    import yaml
    from services.workspace_context import substrate_scope_filter

    try:
        res = (
            client.table("workspace_files")
            .select("content")
            .eq(*substrate_scope_filter(user_id, workspace_id))
            .eq("path", f"/workspace/{KERNEL_MANIFEST_PATH}")
            .limit(1)
            .execute()
        )
        raw = (res.data or [{}])[0].get("content") or ""
        # The stored body carries a leading comment line; yaml ignores it.
        data = yaml.safe_load(raw) if raw else {}
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("[FACES] manifest read failed: %s", exc)
        return {}


def resolve_face_urls(
    client: Any, slugs: list[str], workspace_id: Optional[str] = None
) -> dict[str, str]:
    """Agent slug → a servable face URL, for every slug that has one.

    ⭐ THE MEMBER'S FACE WINS. Two paths are checked, and the ORDER is the whole
    policy: `agents/{slug}/face.png` (the member's own upload, ordinary
    writable substrate in the agent's home) beats `system/agents/{slug}/face.png`
    (yarnnn's mirrored default). "An agent you HIRED having a face you CHOSE"
    is the 2026-07-16 ruling; a lookup that preferred the kernel copy would
    make the member's choice unreachable, and the mirror would overwrite it on
    the next tick.

    BATCHED, never per-agent: one query for the rows, then `mint_thumb_urls`,
    which is already the ONE place a CAS-backed image's serving capability is
    minted (ADR-427 D4 — minted at read, never stored, so `content_url` on the
    row is NULL and forwarding it would serve nothing). Reusing it rather than
    re-minting here keeps the sha-dedupe and the degrade-to-nothing contract.

    Best-effort by contract: a failure returns fewer entries and those agents
    fall back to the accented initial, which is a complete rendering. A face is
    an enrichment; it must never be able to fail the roster.
    """
    slugs = [s for s in (slugs or []) if s]
    if not slugs:
        return {}
    try:
        wanted = {}
        for slug in slugs:
            wanted[f"/workspace/{member_face_path(slug)}"] = (slug, 1)
            wanted[f"/workspace/{kernel_face_path(slug)}"] = (slug, 0)
        q = (
            client.table("workspace_files")
            .select("path, head_version_id, content_type, lifecycle")
            .in_("path", list(wanted.keys()))
        )
        if workspace_id:
            q = q.eq("workspace_id", workspace_id)
        rows = (q.execute().data) or []
        # A trashed face is not a face (the lifecycle predicate two index
        # readers forgot, 2026-09-07 — `delete` archives by design).
        rows = [r for r in rows if (r.get("lifecycle") or "active") == "active"]
        if not rows:
            return {}

        from routes.workspace import mint_thumb_urls
        by_path = mint_thumb_urls(client, rows)

        out: dict[str, str] = {}
        best: dict[str, int] = {}
        for path, url in by_path.items():
            entry = wanted.get(path)
            if not entry:
                continue
            slug, rank = entry
            if rank >= best.get(slug, -1):
                best[slug] = rank
                out[slug] = url
        return out
    except Exception as exc:  # noqa: BLE001 — a face never fails the roster
        logger.warning("[FACES] resolve failed: %s", exc)
        return {}


def ensure_kernel_faces(
    client: Any, user_id: str, workspace_id: Optional[str] = None
) -> dict:
    """Mirror yarnnn's agent faces into this workspace.

    Manifest-cheap: ONE small read when nothing changed; on a kernel change
    only the changed faces are written (compared by sha, never by reading the
    stored bytes back). Idempotent. Every write is an attributed
    `system:kernel-faces` revision through the ONE write path (ADR-209), on
    the BINARY lane (`content_bytes` → the ADR-427 CAS seam).
    """
    import yaml
    from services.authored_substrate import write_revision

    current = kernel_manifest()
    stored = _read_manifest(client, user_id, workspace_id)
    if stored.get("version") == current["version"]:
        return {"written": 0, "skipped": True}
    stored_faces = stored.get("faces") or {}
    written = 0
    for slug, f in _load_kernel().items():
        if stored_faces.get(slug) == f["sha"]:
            continue
        write_revision(
            client,
            user_id=user_id,
            path=f"/workspace/{f['path']}",
            content_bytes=f["raw"],
            authored_by=KERNEL_FACES_AUTHOR,
            message=f"kernel face {slug} @ {f['sha'][:8]}",
            workspace_id=workspace_id,
        )
        written += 1
    manifest_text = yaml.safe_dump(
        {"version": current["version"], "faces": current["faces"]}, sort_keys=True
    )
    write_revision(
        client,
        user_id=user_id,
        path=f"/workspace/{KERNEL_MANIFEST_PATH}",
        content=(
            "# yarnnn's agent faces, mirrored (ADR-641 amendment). "
            "Machine-written; do not edit.\n" + manifest_text
        ),
        authored_by=KERNEL_FACES_AUTHOR,
        message=f"kernel faces manifest @ {current['version']}",
        workspace_id=workspace_id,
    )
    return {"written": written, "skipped": False}


def mirror_kernel_faces_for_all_workspaces(client: Any) -> dict:
    """Per scheduler tick: every workspace, manifest-cheap. One workspace's
    failure is logged, never raised."""
    try:
        rows = (client.table("workspaces").select("id, owner_id").execute().data) or []
    except Exception as exc:
        logger.warning("[FACES] workspaces query failed: %s", exc)
        return {"workspaces": 0, "written": 0, "failed": 0}
    written = failed = 0
    for row in rows:
        wid, owner = row.get("id"), row.get("owner_id")
        if not (wid and owner):
            continue
        try:
            written += ensure_kernel_faces(client, owner, workspace_id=wid)["written"]
        except Exception as exc:
            failed += 1
            logger.warning("[FACES] mirror failed for workspace %s: %s", str(wid)[:8], exc)
    return {"workspaces": len(rows), "written": written, "failed": failed}


__all__ = [
    "KERNEL_FACES_PREFIX", "MEMBER_FACE_DIR", "KERNEL_MANIFEST_PATH",
    "KERNEL_FACES_AUTHOR", "FACE_FILE",
    "kernel_face_path", "member_face_path", "kernel_manifest",
    "has_kernel_face", "ensure_kernel_faces", "resolve_face_urls",
    "mirror_kernel_faces_for_all_workspaces",
]
