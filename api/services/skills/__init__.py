"""
Skills — how-to files for kinds of work (ADR-630).

A skill is CRAFT: the steps, quality bar and anti-patterns for one kind of
work, written for any agent that does that work. It is never grammar (the
pane posture derives that from the app's registries — DP29, ADR-601), never
contract (the kernel participant constants — ADR-533), never reach (the
gates decide what a caller may do — ADR-464 §3: prose is not permission).

Two homes, one file shape (the Agent Skills convention: a folder holding
`SKILL.md` with `name` + `description` frontmatter; ADR-254 names it as an
exception):

  api/services/skills/{slug}/SKILL.md   yarnnn's skills — CODE, shipped with
                                        the deploy, ratcheted and eval-probed
                                        like every other LLM-facing text
  /workspace/system/skills/{slug}/      the same files MIRRORED into every
                                        workspace as `system:kernel-skills`
                                        revisions (locked for every caller —
                                        `system/` is the kernel's root), so a
                                        lane, a connected principal (`open`),
                                        the Files pane and `trace` all reach
                                        them as ordinary files
  /workspace/skills/{name}/SKILL.md     the workspace's OWN skills — ordinary
                                        substrate any member may author, fork
                                        (DuplicateFile records the origin), or
                                        revert

Discovery is the DESCRIPTION: every lane's frame carries one index line per
skill (kernel from code, member from a bounded query); the body loads on
demand through ReadFile. Progressive disclosure — the ADR-464 D4 cost lesson
("a skill composes into every turn") answered by not composing it.

MANAGEMENT DISCIPLINE: every `SKILL.md` here is LLM-facing content — an edit
gets an api/prompts/CHANGELOG.md entry (prompt change protocol), and a skill
earns a Hat-B eval probe as it matures. The kernel index has a byte ceiling
(`INDEX_CEILING`, gated) so the set cannot grow the frame silently.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

KERNEL_SKILLS_DIR = Path(__file__).resolve().parent
SKILL_FILE = "SKILL.md"
#: Where the kernel mirror lands (workspace-relative). `system/` is locked for
#: every caller class (CALLER_WRITE_POLICY) and hidden from the operator's
#: organize reach — the kernel's root, by ADR-320.
KERNEL_SKILLS_PREFIX = "system/skills/"
#: Where a workspace's own skills live. A meaning-folder like any other.
MEMBER_SKILLS_PREFIX = "skills/"
#: One tiny machine file per workspace records WHICH kernel version is
#: mirrored, so the per-load check is one small row, never eight reads.
KERNEL_MANIFEST_PATH = f"{KERNEL_SKILLS_PREFIX}_manifest.yaml"
KERNEL_SKILLS_AUTHOR = "system:kernel-skills"
#: The frame index's ceiling — kernel lines only. Raising it needs the same
#: evidence as adding a prompt instruction (DP22 / ADR-306).
INDEX_CEILING = 3_000
#: Member skills listed in the frame, at most. Beyond it the frame says so and
#: the agent searches — progressive disclosure one level up.
MEMBER_INDEX_CAP = 24

_FM_RX = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_skill(text: str) -> dict:
    """Parse one SKILL.md: frontmatter (`name`, `description`, optional
    `metadata` map) + body. The ONE parser (CLAUDE.md §9: the sanctioned
    regex + `yaml.safe_load`, no hand-rolled splitting). Raises ValueError
    on a file that is not a skill, so a malformed kernel file fails at import
    and a malformed member file is skipped with a log line."""
    m = _FM_RX.match(text or "")
    if not m:
        raise ValueError("no frontmatter")
    fm = yaml.safe_load(m.group(1)) or {}
    if not isinstance(fm, dict):
        raise ValueError("frontmatter is not a map")
    name = str(fm.get("name") or "").strip()
    description = str(fm.get("description") or "").strip()
    if not name or not description:
        raise ValueError("name and description are required")
    body = text[m.end():]
    title = name
    for line in body.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    metadata = fm.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "name": name,
        "description": description,
        "metadata": {str(k): str(v) for k, v in metadata.items()},
        "title": title,
        "body": body,
        "raw": text,
    }


_kernel_cache: Optional[dict[str, dict]] = None


def _load_kernel() -> dict[str, dict]:
    global _kernel_cache
    if _kernel_cache is not None:
        return _kernel_cache
    skills: dict[str, dict] = {}
    for d in sorted(p for p in KERNEL_SKILLS_DIR.iterdir() if p.is_dir()):
        f = d / SKILL_FILE
        if not f.exists():
            continue
        s = parse_skill(f.read_text(encoding="utf-8"))
        if s["name"] != d.name:
            raise ValueError(f"skill name {s['name']!r} must equal its folder {d.name!r}")
        s["sha"] = hashlib.sha256(s["raw"].encode("utf-8")).hexdigest()
        s["path"] = kernel_skill_path(d.name)
        skills[d.name] = s
    _kernel_cache = skills
    return skills


def kernel_skill_path(slug: str) -> str:
    """Workspace-relative path of a mirrored kernel skill."""
    return f"{KERNEL_SKILLS_PREFIX}{slug}/{SKILL_FILE}"


def list_skills() -> list[dict]:
    """The chooser payload (served on the lane capability envelope)."""
    return [
        {"slug": slug, "title": s["title"], "description": s["description"], "path": s["path"]}
        for slug, s in _load_kernel().items()
    ]


def get_skill(slug: str) -> Optional[dict]:
    return _load_kernel().get((slug or "").strip())


def kernel_manifest() -> dict:
    """`version` = sha of every kernel skill's sha, in slug order; `skills` =
    slug → sha. What the mirror compares against a workspace's stored copy."""
    skills = _load_kernel()
    joined = "\n".join(f"{slug}:{s['sha']}" for slug, s in skills.items())
    return {
        "version": hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16],
        "skills": {slug: s["sha"] for slug, s in skills.items()},
    }


# ---------------------------------------------------------------------------
# Composition — what enters a lane's frame
# ---------------------------------------------------------------------------

_INDEX_HEAD = """## Skills
How-to files for kinds of work. Before doing work one names, read it
(ReadFile) and follow it while you work. yarnnn's live under system/skills/
(read-only — fork one into skills/ to change it); this workspace's own live
under skills/, and any member may add one (system/skills/creating-skills/SKILL.md)."""


def skills_index_section(member_skills: Optional[list[dict]] = None) -> str:
    """The frame's index: one line per skill, kernel first. Descriptions only —
    the body never enters the frame (DP22)."""
    lines = [_INDEX_HEAD]
    for slug, s in _load_kernel().items():
        lines.append(f"- {s['path']} — {s['description']}")
    members = list(member_skills or [])
    for m in members[:MEMBER_INDEX_CAP]:
        lines.append(f"- {m['path']} — {m['description']}")
    if len(members) > MEMBER_INDEX_CAP:
        lines.append(
            f"- …and {len(members) - MEMBER_INDEX_CAP} more under skills/ — "
            "ListFiles skills/ to see them."
        )
    return "\n".join(lines)


def read_member_skills(client: Any, user_id: str) -> list[dict]:
    """The workspace's own skills, parsed for the index. ONE bounded query;
    a malformed file is skipped with a log line, never a failed turn."""
    from services.workspace_context import substrate_scope_filter

    try:
        res = (
            client.table("workspace_files")
            .select("path, content")
            .eq(*substrate_scope_filter(user_id))
            .like("path", f"/workspace/{MEMBER_SKILLS_PREFIX}%/{SKILL_FILE}")
            .order("path")
            .limit(MEMBER_INDEX_CAP + 1)
            .execute()
        )
    except Exception as exc:
        logger.warning("[SKILLS] member skills read failed: %s", exc)
        return []
    out: list[dict] = []
    for row in res.data or []:
        try:
            s = parse_skill(row.get("content") or "")
        except ValueError as exc:
            logger.info("[SKILLS] skipping %s: %s", row.get("path"), exc)
            continue
        rel = (row.get("path") or "").removeprefix("/workspace/")
        out.append({"path": rel, "description": s["description"], "title": s["title"]})
    return out


def build_skill_section(
    skill_slug: str,
    source_path: str,
    artifact_path: Optional[str] = None,
) -> str:
    """The skill-bound lane's job section (ADR-450 D3 + ADR-452 D3, re-homed
    by ADR-630) — pure. The skill's body + the source + the two mechanics
    every derive shares: read the projection for binary raws, and cite via
    derived_from (the ADR-448 edge).

    ``artifact_path`` (ADR-452 D3 — the studio mode): when the lane is ALSO
    artifact-bound, a target-override block redirects the skill's
    file-creation mechanics to the bound artifact; the content constraints
    and citation discipline stand unchanged.
    """
    skill = get_skill(skill_slug)
    if not skill:
        return ""
    src = (
        source_path
        if source_path.startswith("/workspace/")
        else "/workspace/" + (source_path or "").lstrip("/")
    )
    target_line = skill["metadata"].get("target") or skill["description"]
    override = ""
    if artifact_path:
        target_line = f"the bound artifact at {artifact_path}"
        override = f"""
TARGET OVERRIDE (studio flow): your target is the bound artifact at
{artifact_path} — author the derived content THERE, in the artifact's format
(the pane posture above owns the grammar: blocks, slides, layout). Any
instruction below about creating a separate markdown file is superseded by
this; the content constraints, quality bar, and citation discipline stand.
"""
    return f"""## Skill in use: {skill['title']} (this lane's job)
This lane exists to derive from ONE source, following {skill['path']}:
  SOURCE: {src}
  TARGET: {target_line}

Mechanics (apply to every step below):
- If the source is a binary raw (its content is a one-line caption with an
  attachment), read its co-located text projection instead: the sibling file
  ending `.extracted.md`.
- Every file you author from the source MUST pass
  derived_from=["{src}", "{skill['path']}"] on the write — the edges are how
  the workspace shows what was made from what, and under which skill.
- The source is retained and immutable — never edit it; derive beside it.
{override}
{skill['body'].strip()}

When done, tell the member what you created (paths) and what you could NOT
evidence from the source."""


# ---------------------------------------------------------------------------
# The mirror — kernel skills as files in every workspace
# ---------------------------------------------------------------------------


def _read_manifest(client: Any, user_id: str, workspace_id: Optional[str]) -> dict:
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
        data = yaml.safe_load(raw) if raw else {}
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("[SKILLS] manifest read failed: %s", exc)
        return {}


def ensure_kernel_skills(
    client: Any, user_id: str, workspace_id: Optional[str] = None
) -> dict:
    """Mirror yarnnn's skills into this workspace. Manifest-cheap: ONE small
    read when nothing changed; on a kernel change only the changed skills are
    written (compared by sha, never by content reads). Idempotent. Every
    write is an attributed `system:kernel-skills` revision through the ONE
    write path (ADR-209)."""
    from services.authored_substrate import write_revision

    current = kernel_manifest()
    stored = _read_manifest(client, user_id, workspace_id)
    if stored.get("version") == current["version"]:
        return {"written": 0, "skipped": True}
    stored_skills = stored.get("skills") or {}
    written = 0
    for slug, s in _load_kernel().items():
        if stored_skills.get(slug) == s["sha"]:
            continue
        write_revision(
            client,
            user_id=user_id,
            path=f"/workspace/{s['path']}",
            content=s["raw"],
            authored_by=KERNEL_SKILLS_AUTHOR,
            message=f"kernel skill {slug} @ {s['sha'][:8]}",
            workspace_id=workspace_id,
        )
        written += 1
    manifest_text = yaml.safe_dump(
        {"version": current["version"], "skills": current["skills"]},
        sort_keys=True,
    )
    write_revision(
        client,
        user_id=user_id,
        path=f"/workspace/{KERNEL_MANIFEST_PATH}",
        content=f"# yarnnn's skills, mirrored (ADR-630). Machine-written; do not edit.\n{manifest_text}",
        authored_by=KERNEL_SKILLS_AUTHOR,
        message=f"kernel skills manifest @ {current['version']}",
        workspace_id=workspace_id,
    )
    return {"written": written, "skipped": False}


def mirror_kernel_skills_for_all_workspaces(client: Any) -> dict:
    """Per scheduler tick: every workspace, manifest-cheap. One workspace's
    failure is logged, never raised."""
    try:
        res = client.table("workspaces").select("id, owner_id").execute()
        rows = res.data or []
    except Exception as exc:
        logger.warning("[SKILLS] workspaces query failed: %s", exc)
        return {"workspaces": 0, "written": 0, "failed": 0}
    written = failed = 0
    for row in rows:
        wid, owner = row.get("id"), row.get("owner_id")
        if not (wid and owner):
            continue
        try:
            written += ensure_kernel_skills(client, owner, workspace_id=wid)["written"]
        except Exception as exc:
            failed += 1
            logger.warning("[SKILLS] mirror failed for workspace %s: %s", str(wid)[:8], exc)
    return {"workspaces": len(rows), "written": written, "failed": failed}


__all__ = [
    "KERNEL_SKILLS_PREFIX", "MEMBER_SKILLS_PREFIX", "KERNEL_MANIFEST_PATH",
    "KERNEL_SKILLS_AUTHOR", "INDEX_CEILING", "MEMBER_INDEX_CAP",
    "parse_skill", "list_skills", "get_skill", "kernel_skill_path", "kernel_manifest",
    "skills_index_section", "read_member_skills", "build_skill_section",
    "ensure_kernel_skills", "mirror_kernel_skills_for_all_workspaces",
]
