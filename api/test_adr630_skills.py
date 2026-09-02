"""ADR-630 — skills are files: craft lives in SKILL.md, discovered by
description, read on demand. Script-style gate; falsified where it counts.

Run: cd api && python3 test_adr630_skills.py
"""
from __future__ import annotations

import os
import re
import sys

API = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(API)
sys.path.insert(0, API)

_p = _f = 0


def _check(label, ok, detail=""):
    global _p, _f
    if ok:
        _p += 1; print(f"  ok   {label}")
    else:
        _f += 1; print(f"  FAIL {label}{(' — ' + detail) if detail else ''}")


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


from services import skills as sk  # noqa: E402

print("§1 the kernel set — the Agent Skills shape, name == folder, discovery-grade descriptions")
K = sk._load_kernel()
_check("eight kernel skills", len(K) == 8, str(sorted(K)))
_check("the migrated three are present under verb names",
       {"deriving-a-design-system", "writing-a-spec", "presenting-from-sources"} <= set(K))
_check("the brief returned with its door (ADR-579 D9 reversal condition)", "summarizing-sources" in K)
_check("creating-skills teaches the member's half", "creating-skills" in K)
for slug, s in K.items():
    _check(f"{slug}: name == folder", s["name"] == slug)
    _check(f"{slug}: description is discovery-grade (what + when, ≤300 chars)",
           0 < len(s["description"]) <= 300 and "Use when" in s["description"], str(len(s["description"])))
    _check(f"{slug}: third person (no 'I ' / 'you can' in the description)",
           not re.search(r"\bI\b|\byou can\b", s["description"]))
    _check(f"{slug}: body under 500 lines", s["body"].count("\n") < 500)
    _check(f"{slug}: names no agent (craft, not identity)", "resident" not in s["raw"].split("---")[1])
    _check(f"{slug}: has a target contract", bool(s["metadata"].get("target")))

print("§2 the parser is the ONE sanctioned shape (regex + safe_load) and refuses non-skills")
_check("frontmatter regex is the CLAUDE.md §9 form", sk._FM_RX.pattern.startswith("^---"))
for bad in ("no frontmatter", "---\nname: x\n---\nbody", "---\ndescription: y\n---\n", "---\n- a\n- b\n---\n"):
    try:
        sk.parse_skill(bad); ok = False
    except ValueError:
        ok = True
    _check(f"refuses {bad[:22]!r}", ok)
good = sk.parse_skill("---\nname: a-b\ndescription: d\nmetadata:\n  target: t\n---\n\n# Title here\n\nbody\n")
_check("parses name/description/metadata/title/body", good["title"] == "Title here" and good["metadata"]["target"] == "t" and "body" in good["body"])

print("§3 the frame carries the INDEX, bounded, and the body only on demand")
idx = sk.skills_index_section()
_check("index under its ceiling", len(idx) <= sk.INDEX_CEILING, f"{len(idx)} > {sk.INDEX_CEILING}")
_check("index lists every kernel path", all(sk.kernel_skill_path(s) in idx for s in K))
_check("index carries descriptions, never bodies", "## Steps" not in idx and "Quality bar" not in idx)
many = [{"path": f"skills/s{i}/SKILL.md", "description": "d", "title": "t"} for i in range(sk.MEMBER_INDEX_CAP + 3)]
idx2 = sk.skills_index_section(many)
_check("member index caps and says so", idx2.count("\n- skills/s") == sk.MEMBER_INDEX_CAP and "more under skills/" in idx2)
lr = _read("api/services/lane_runner.py")
_check("the conventions frame has the skills slot", "{skills_section}" in lr and "skills_section=skills_section" in lr)
_check("lane_runner composes the index every turn", "skills_index_section(read_member_skills(client, user_id))" in lr)
_check("a skill-bound lane composes the body through build_skill_section", "build_skill_section(" in lr and "artifact_path=artifact_path" in lr)
_check("no recipe registry survives", not os.path.exists(os.path.join(API, "services/derive_recipes.py")) and "derive_recipes" not in lr)

print("§4 the skill section: body + source + citation mechanics; the studio override")
sec = sk.build_skill_section("presenting-from-sources", "operation/x.md")
_check("names the skill path and the source", "system/skills/presenting-from-sources/SKILL.md" in sec and "/workspace/operation/x.md" in sec)
_check("cites source AND skill on every write", 'derived_from=["/workspace/operation/x.md", "system/skills/presenting-from-sources/SKILL.md"]' in sec)
_check("carries the body", "titles as claims" in sec.lower() or "TITLE is the claim" in sec)
_check("plain mode: no override", "TARGET OVERRIDE" not in sec)
sec2 = sk.build_skill_section("presenting-from-sources", "operation/x.md", artifact_path="/workspace/operation/d/deck.html")
_check("studio mode: override names the artifact", "TARGET OVERRIDE" in sec2 and "/workspace/operation/d/deck.html" in sec2)
_check("unknown skill → empty section", sk.build_skill_section("nope", "x.md") == "")

print("§5 the mirror: manifest-cheap, diff-aware, attributed as system:kernel-skills")


class _Q:
    def __init__(self, store): self.store = store; self._path = None
    def select(self, *_): return self
    def eq(self, col, val):
        if col == "path": self._path = val
        return self
    def limit(self, *_): return self
    def execute(self):
        class R: pass
        r = R(); r.data = [{"content": self.store.get(self._path, "")}] if self._path in self.store else []; return r


class _Client:
    def __init__(self): self.store = {}; self.writes = []
    def table(self, name): return _Q(self.store)


import services.authored_substrate as _as  # noqa: E402
_real = _as.write_revision
_c = _Client()


def _fake_write(client, *, user_id, path, content, authored_by, message, workspace_id=None, **kw):
    _c.store[path] = content; _c.writes.append((path, authored_by)); return "rev"


_as.write_revision = _fake_write
try:
    r1 = sk.ensure_kernel_skills(_c, "u1", workspace_id="w1")
    r2 = sk.ensure_kernel_skills(_c, "u1", workspace_id="w1")
finally:
    _as.write_revision = _real
_check("first pass writes every skill + the manifest", r1["written"] == 8 and len(_c.writes) == 9)
_check("every write is the kernel's", all(a == sk.KERNEL_SKILLS_AUTHOR for _, a in _c.writes))
_check("lands under system/skills/ (the locked root)", all(p.startswith("/workspace/system/skills/") for p, _ in _c.writes))
_check("second pass is a no-op (manifest match)", r2["skipped"] is True and r2["written"] == 0)
_check("the hooks exist: workspace state + scheduler tick",
       "ensure_kernel_skills(" in _read("api/routes/workspace.py") and "mirror_kernel_skills_for_all_workspaces(" in _read("api/jobs/unified_scheduler.py"))
sched = _read("api/jobs/unified_scheduler.py")
_check("the tick has no steward gate to be inside of (ADR-632)", "is_agent_enabled" not in sched)

print("§6 the doors: the lane route binds `skill`, the FE names the same slugs")
lanes = _read("api/routes/lanes.py")
_check("create_lane validates `skill` against the kernel set", "Unknown skill:" in lanes and "get_skill(skill)" in lanes)
_check("no recipe resident survives (a skill never names an agent)", "resident_for_recipe" not in lanes)
_check("the envelope serves `skills`", '"skills": list_skills(),' in lanes and '"recipes"' not in lanes)
studio = _read("web/components/authoring/StudioSurface.tsx")
fe_slugs = set(re.findall(r"skill: '([a-z-]+)'", studio))
_check("FE learn targets name kernel skills", fe_slugs and fe_slugs <= set(K), str(fe_slugs))
_check("no `derive_recipe` on the wire", "derive_recipe" not in studio and "derive_recipe" not in _read("web/lib/api/client.ts"))

print("§7 the playbook vestige is gone (ADR-157 referential injection, 0 callers)")
orch = _read("api/services/orchestration.py")
_check("no playbook registry", "PLAYBOOK_METADATA" not in orch and "get_relevant_playbooks" not in orch and "get_type_playbook" not in orch)
_check("no playbook seeding in workspace.py", "get_type_playbook" not in _read("api/services/workspace.py"))

print("§8 canon")
gl = _read("docs/architecture/GLOSSARY.md")
_check("GLOSSARY defines Skill", "**Skill**" in gl and "ADR-630" in gl)
_check("ADR-254 records the SKILL.md exception", "SKILL.md" in _read("docs/adr/ADR-254-file-format-discipline.md") if os.path.exists(os.path.join(ROOT, "docs/adr/ADR-254-file-format-discipline.md")) else "SKILL.md" in "".join(_read(os.path.join("docs/adr", f)) for f in os.listdir(os.path.join(ROOT, "docs/adr")) if f.startswith("ADR-254")))

print(f"\n{_p} passed, {_f} failed")
sys.exit(1 if _f else 0)
