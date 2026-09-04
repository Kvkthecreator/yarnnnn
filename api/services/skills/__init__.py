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

SCOPED BY APP: `metadata.apps` names the panes a skill is FOR. Silence means
EVERY app, so a skill that does not narrow itself is offered everywhere and no
undeclared skill changes meaning. A bound pane is not advertised craft that
belongs to another pane; an unbound lane (open chat) is offered everything,
because that is where a member goes for any kind of work. What is withheld is
NAMED with its count and the ListFiles that reaches it — hidden at
PRESENTATION only, never at authorization (the ADR-395 precedent): the mirror
still lands every skill in every workspace, and any of them reads fine.

SCOPED BY REACH (ADR-635 D7): `metadata.needs` names the connector
CATEGORIES a skill is for — the ecosystem's `~~category` placeholder
convention, declared. Offered when the member holds an attached connector of
one of them, withheld-and-counted otherwise; silence means no need. A public
skill written for "a project tracker" drops into `skills/` unchanged and
lights up when one is attached. Host-specific frontmatter (`allowed-tools`,
`model`, `tools`, `argument-hint`…) is STRIPPED and the strip is NAMED
(`stripped`): prose was never permission, and now an import says so.

MANAGEMENT DISCIPLINE: every `SKILL.md` here is LLM-facing content — an edit
gets an api/prompts/CHANGELOG.md entry (prompt change protocol), and a skill
earns a Hat-B eval probe as it matures. The index is bounded by TWO budgets,
both in bytes and BOTH enforced at composition: `INDEX_CEILING` ratchets the
kernel lines a BOUND pane carries (`UNBOUND_INDEX_CEILING` for open chat, which
filters nothing and must still keep its every-kind-of-work promise), and
`MEMBER_INDEX_ALLOWANCE` bounds the member lines — so neither the prose we
write nor the prose members write can grow the frame silently. The kernel half
was declarative until ADR-633 added a ninth skill and the unbound lane composed
3,239/3,000 unchecked: a ratchet a gate asserts but composition ignores is a
ratchet the frame can walk straight past.
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
#: The KERNEL index's ceiling for a BOUND pane — the lines that apply to that
#: pane plus the head, and nothing else. It sits ~70 bytes under the widest
#: pane's cost on purpose: this is the ratchet on OUR prose, so a longer
#: description has to displace another one. Raising it needs the same
#: evidence as adding a prompt instruction (DP22 / ADR-306).
#:
#: RAISED 3,000 → 3,400 by ADR-639 (2026-09-04), with the receipt: a Text
#: pane now applies NINE skills (the two standing-work skills join it), at
#: 3,327 bytes — at 3,000 it withheld `writing-a-spec` and `writing-updates`
#: by alphabetical accident, the exact outcome ADR-633's amendment named. The
#: trade is the one the index exists to make: ~4,600 bytes of Python posture
#: that composed into every strings-pane turn and every prose run left the
#: frames; two ~340-byte discovery lines arrived. Measured at ship: text
#: 3,327 · slides 2,659 · blogger 2,659 · images 1,647.
INDEX_CEILING = 3_400
#: The UNBOUND lane's ceiling — the open chat surface, which by construction
#: filters nothing and therefore carries every kernel skill.
#:
#: A SECOND number, not a raised first one, because the two answer different
#: questions. `INDEX_CEILING` ratchets a BOUND pane, where scoping already does
#: the work and the tight bound is what keeps us honest about per-turn cost.
#: This one bounds a surface whose whole job is that a member can ask for any
#: kind of work — ADR-630 §3b states it directly: "the open surface is where a
#: member goes for any kind of work: narrowing it would hide work that has no
#: other door." Truncating it drops real skills by ALPHABETICAL ACCIDENT
#: (at 9 skills: `writing-a-spec` and `writing-updates`), which is a worse
#: outcome than the bytes it saves.
#:
#: Sized to hold today's ELEVEN with ~50 bytes to spare, so it is a real
#: ratchet and not a blank cheque: a twelfth kernel skill tightens a
#: description or brings its own receipt. Raising EITHER number needs the
#: same evidence as adding a prompt instruction (DP22 / ADR-306).
#:
#: RAISED 3,400 → 4,000 by ADR-639 (2026-09-04), with the receipt the rule
#: asks for: the tenth and eleventh skills (`keeping-a-file-current`,
#: `declaring-standing-work`) arrive by moving ~4,600 bytes of Python posture
#: OUT of the frames that composed it every turn (the strings pane posture,
#: ~3,000 bytes on every strings-pane turn; the standing run posture, ~1,600
#: on every prose run) into two discovery-grade lines the open lane now
#: carries (~690 bytes). Net prose per turn falls; the open lane pays +690,
#: and at 3,400 it withheld the eleventh skill by alphabetical accident — the
#: exact outcome ADR-633's amendment raised this number to prevent. Measured
#: at ship: 3,947 of 4,000 with all eleven listed. (The same audit found the
#: budget loop reserving an overflow line for the LAST admission, which can
#: never need one — fixed beside the raise, so the numbers are honest.)
UNBOUND_INDEX_CEILING = 4_000
#: The MEMBER index's allowance, enforced at composition. A separate number
#: because it answers a different question: the kernel ceiling ratchets prose
#: we write, this bounds prose members write. Sized for ~8 discovery-grade
#: descriptions (~330 bytes each) — enough that a workspace's real working set
#: is visible, bounded so the frame cannot grow without limit on the one axis
#: we do not control. Beyond it the frame names the count and the agent runs
#: ListFiles — the same progressive disclosure the index gives skill BODIES.
MEMBER_INDEX_ALLOWANCE = 2_700
#: Member skills READ for the index, at most — a bound on the query so a
#: workspace with hundreds cannot make the read unbounded. The allowance above
#: decides how many of them survive into the frame.
MEMBER_INDEX_CAP = 24

_FM_RX = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _parse_apps(raw: Any) -> tuple[str, ...]:
    """`metadata.apps` — the apps whose panes this skill is FOR.

    Absent or empty means EVERY app (the open case, and the default: a skill
    that does not narrow itself is offered everywhere). A list of app slugs
    narrows it. Accepts a bare string for one app, because a member writing
    `apps: slides` means the obvious thing and refusing that is pedantry.
    """
    if raw is None:
        return ()
    if isinstance(raw, str):
        items = [raw]
    elif isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        return ()
    return tuple(sorted({str(i).strip() for i in items if str(i).strip()}))


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
    # ADR-635 D7 — a host-specific field is STRIPPED, and the strip is NAMED.
    # `allowed-tools`, `model`, `tools`, `argument-hint` and the rest describe
    # a host that is not this one; prose was never permission here (ADR-464
    # §3), so they were always dropped — silently. An import now says what it
    # lost. The portable spec's own fields (`license`, `compatibility`) are
    # kept in `metadata` as strings, since they describe the skill, not a host.
    stripped = sorted(
        str(k) for k in fm.keys()
        if k not in ("name", "description", "metadata", "license", "compatibility")
    )
    if stripped:
        logger.info("[SKILLS] %s: stripped host-specific frontmatter %s", name, stripped)
    kept_meta = {
        str(k): str(v) for k, v in metadata.items() if k not in ("apps", "needs")
    }
    for k in ("license", "compatibility"):
        if fm.get(k) is not None and k not in kept_meta:
            kept_meta[k] = str(fm[k])
    return {
        "name": name,
        "description": description,
        # Scalars only — `apps` and `needs` are the list-valued keys and are
        # lifted out below, so a stray list elsewhere still stringifies.
        "metadata": kept_meta,
        "apps": _parse_apps(metadata.get("apps")),
        # ADR-635 D7 — the connector CATEGORIES this skill needs (the
        # ecosystem's `~~category` placeholder, declared). Silence = none.
        "needs": _parse_apps(metadata.get("needs")),
        "stripped": stripped,
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


def _overflow_line(n: int) -> str:
    return (
        f"- …and {n} more under skills/ — ListFiles skills/ to see them."
    )


def _kernel_overflow_line(n: int) -> str:
    """The kernel half's escape hatch. Named (not inlined) because the budget
    loop must RESERVE its length before admitting a line — the same discipline
    the member loop already followed, and the reason its budget could never
    overflow while the kernel's could."""
    return (
        f"- …and {n} more under system/skills/ for other kinds of "
        "work — ListFiles system/skills/ to see them."
    )


def _applies_to(skill: dict, app: Optional[str], reach: Optional[set] = None) -> bool:
    """Does this skill belong in the index of a lane running `app`, whose
    member holds attached connectors of the categories in `reach`?

    A skill with no `apps` is universal — the default, so silence means
    "offered everywhere" and no existing skill changes meaning. A skill that
    NAMES apps appears only in those, and in an unbound lane (`app` None)
    every skill is offered: open chat is where a member goes for anything, and
    narrowing there would hide work the member cannot otherwise reach.

    ADR-635 D7 — a skill that NAMES needs (connector categories) is offered
    only when the member holds one of them; `reach` None means the caller
    did not look, and the skill is offered (presentation never fails closed
    — hiding is the ADR-395 posture, never authorization). Withheld skills
    are still counted and reachable by ListFiles, like app-scoped ones.
    """
    apps = skill.get("apps") or ()
    if apps and app and app not in apps:
        return False
    needs = skill.get("needs") or ()
    if needs and reach is not None and not (set(needs) & set(reach)):
        return False
    return True


def skills_index_section(
    member_skills: Optional[list[dict]] = None,
    app: Optional[str] = None,
    reach: Optional[set] = None,
) -> str:
    """The frame's index: one line per skill, kernel first. Descriptions only —
    the body never enters the frame (DP22).

Two budgets, enforced at composition.

    Kernel lines are the floor — ours, ratcheted by INDEX_CEILING in the gate.
    Member lines are admitted while they fit MEMBER_INDEX_ALLOWANCE, and the
    ones that do not are named as a count the agent can follow with ListFiles
    — progressive disclosure one level up, the same answer the index itself
    gives for skill BODIES.
    """
    lines = [_INDEX_HEAD]
    kernel = [m for m in _load_kernel().values() if _applies_to(m, app, reach)]
    # Two ways a kernel line can be withheld, ONE escape hatch.
    #
    # (1) SCOPE — the skill declares `apps` and this lane is not one of them.
    # (2) BUDGET — the lines that DO apply no longer fit INDEX_CEILING.
    #
    # (2) used to be unenforced: the ceiling was a gate-only ratchet, so a
    # BOUND lane stayed small (its filter did the work) while the UNBOUND lane
    # — which by definition filters nothing — composed every kernel line into
    # every turn, unchecked. Adding the ninth skill (ADR-633's `composing-an-
    # image`) put it at 3,239/3,000, and scoping could not fix it: `app=None`
    # means "no filter", so an open chat sees everything by construction.
    #
    # This is the same lesson as the member budget one commit earlier (a count
    # cap is not a byte cap), in the half that was left declarative. The
    # withheld ones are NAMED with a count and a ListFiles — presentation, never
    # authorization: the mirror still lands all nine and any of them reads fine.
    # The bound panes ratchet tight; the open surface gets its own, higher
    # ceiling so it can keep its promise (ADR-630 §3b).
    ceiling = INDEX_CEILING if app else UNBOUND_INDEX_CEILING
    kept: list[str] = []
    used = len(_INDEX_HEAD.encode())
    withheld_by_budget = 0
    for i, meta in enumerate(kernel):
        line = f"- {meta['path']} — {meta['description']}"
        # Reserve room for the overflow line this admission might force, so the
        # escape hatch can always be written (the member loop's discipline).
        # The LAST admission reserves nothing: no line follows it, so no
        # overflow line can be needed — reserving one anyway withheld an
        # eleventh skill that fit (found 2026-09-04, ADR-639).
        remaining = len(_load_kernel()) - len(kept) - 1
        reserve = 0 if remaining <= 0 else len(_kernel_overflow_line(remaining).encode()) + 1
        if used + len(line.encode()) + 1 + reserve > ceiling:
            withheld_by_budget = len(kernel) - i
            break
        kept.append(line)
        used += len(line.encode()) + 1
    lines.extend(kept)
    hidden = (len(_load_kernel()) - len(kernel)) + withheld_by_budget
    if hidden:
        lines.append(_kernel_overflow_line(hidden))

    members = [
        m for m in (member_skills or []) if _applies_to(m, app, reach)
    ][:MEMBER_INDEX_CAP]
    if not members:
        return "\n".join(lines)

    used = 0
    shown = 0
    for m in members:
        line = f"- {m['path']} — {m['description']}"
        # Reserve room for the overflow line this admission might force, so
        # the escape hatch can always be written. The last admission reserves
        # nothing (no line follows it).
        _left = len(members) - shown - 1
        reserve = 0 if _left <= 0 else len(_overflow_line(_left).encode()) + 1
        if used + len(line.encode()) + 1 + reserve > MEMBER_INDEX_ALLOWANCE:
            break
        lines.append(line)
        used += len(line.encode()) + 1
        shown += 1

    if shown < len(members):
        lines.append(_overflow_line(len(members) - shown))
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
        out.append({
            "path": rel,
            "description": s["description"],
            "title": s["title"],
            # carried so a member's skill can scope itself the same way
            "apps": s.get("apps") or (),
            "needs": s.get("needs") or (),
        })
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
    "KERNEL_SKILLS_AUTHOR", "INDEX_CEILING", "UNBOUND_INDEX_CEILING",
    "MEMBER_INDEX_ALLOWANCE",
    "MEMBER_INDEX_CAP",
    "parse_skill", "list_skills", "get_skill", "kernel_skill_path", "kernel_manifest",
    "skills_index_section", "read_member_skills", "build_skill_section",
    "ensure_kernel_skills", "mirror_kernel_skills_for_all_workspaces",
]
