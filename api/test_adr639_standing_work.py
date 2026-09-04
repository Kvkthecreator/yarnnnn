"""ADR-639 gate — standing work is a kernel lane, not an app.

Run with:  cd api && python3 test_adr639_standing_work.py
(script-style — prints ✗ and exits 1 on failure; under pytest it reports a
false PASS like the other script gates.)

Every check is falsified by construction — remove the mechanism and it reds:

  D1  THE STANDING FRAME composes through the lane module: the commons
      contract, the citation rule, the mandate head and the executor's
      character (the same door every lane uses) — and carries NO tools line,
      reach section, cast, focus, register clause or skills index. The run
      calls it (AST) and never composes a system string of its own.
  D2  CRAFT IS A SKILL: the two kernel skills load with the declared scoping;
      the two Python postures are gone; every lane's index holds its ceiling.
  D3  ONE DECLARATION GRAMMAR, ONE DRAIN LOOP: `app` derives from the target's
      type and explicit wins; no key names an agent; the kind, slugs and
      attribution are `standing`; `drain_due` is the one loop and both lanes
      ride it — DRIVEN with fakes; migration 251 carries the value.
  D4  THE APP, PANE, ROUTES AND AGENT ARE DELETED: the register, the app
      registry, the surface roster, the FE (stub + middleware + registry +
      pin + params + namespace + component), the Notifications pane exists,
      the steward fossil StandingBand is gone, a retired slug still shows its
      name.
  D5  `system:strings` and `system:standing` display as Standing work at both
      sites.
"""

from __future__ import annotations

import ast
import asyncio
import re
import sys
from pathlib import Path
from types import SimpleNamespace

API = Path(__file__).resolve().parent
ROOT = API.parent
WEB = ROOT / "web"
sys.path.insert(0, str(API))

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name} {detail}")
        FAILURES.append(name)


def _read(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _code_only(src: str) -> str:
    """Source with every string constant blanked (docstrings + literals), so a
    check on a MECHANISM cannot pass on a comment or a docstring that names it."""
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            n.value = ""
    return ast.unparse(tree)


def _calls(tree) -> set[str]:
    return {
        n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", "")
        for n in ast.walk(tree) if isinstance(n, ast.Call)
    }


class FakeQuery:
    def __init__(self, table, files):
        self.table_name, self.files, self.path = table, files, None
    def select(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def order(self, *a, **k): return self
    def like(self, *a, **k): return self
    def in_(self, *a, **k): return self
    def lte(self, *a, **k): return self
    def eq(self, key, val):
        if key == "path": self.path = val
        return self
    def execute(self):
        if self.table_name == "workspace_files" and self.path in self.files:
            return SimpleNamespace(data=[{"content": self.files[self.path]}])
        return SimpleNamespace(data=[])


class FakeClient:
    def __init__(self, files=None): self.files = files or {}
    def table(self, name): return FakeQuery(name, self.files)


# ═══════════════════════════════════════════════════════════════════════════
print("D1. the standing run composes through the lane module")
# ═══════════════════════════════════════════════════════════════════════════
from services.lane_runner import (  # noqa: E402
    LANE_MODELS, _CONVENTIONS_FRAME, _STANDING_FRAME, build_standing_frame,
)
from services.workspace_paths import (  # noqa: E402
    PARTICIPANT_CITATION_RULE, PARTICIPANT_COMMONS_CONTRACT, PARTICIPANT_REGISTER,
)
from services.agents_registry import AGENTS  # noqa: E402
from services.standing_work import (  # noqa: E402
    KEEPING_SKILL, StandingDecl, build_standing_job,
)

STANDING_FRAME_CEILING = 600  # measured 430 at ship (2026-09-04)
_scaffold = re.sub(r"\{[a-z_]+\}", "", _STANDING_FRAME)
check(f"the standing scaffold is ratcheted ({len(_scaffold)} <= {STANDING_FRAME_CEILING})",
      len(_scaffold) <= STANDING_FRAME_CEILING,
      "raise only for a repeated observed failure, named in the raising commit (DP22)")

_model = AGENTS["editor"]["model"]
_decl = StandingDecl(topic="operation/notes", slug="standing:operation/notes",
                     target="notes.md", app="text")
_frame = build_standing_frame(
    FakeClient({"/workspace/constitution/MANDATE.md": "# Mandate\nKeep the copy bank current."}),
    "u1", model=_model, executor="editor", job=build_standing_job(_decl), skill=KEEPING_SKILL,
)
check("carries the commons contract verbatim (ADR-533 D1)", PARTICIPANT_COMMONS_CONTRACT in _frame)
check("carries the citation rule verbatim", PARTICIPANT_CITATION_RULE in _frame)
check("carries the mandate head (the run never had it before)", "Keep the copy bank current." in _frame)
check("carries the executor's character through the same door every lane uses",
      "WHO YOU ARE" in _frame and AGENTS["editor"]["posture"][:60] in _frame)
check("carries the kernel job (target + root + the output contract)",
      '"notes.md"' in _frame and "/workspace/operation/notes" in _frame and "NO_CHANGE" in _frame)
check("carries the craft skill's BODY, pushed (a toolless turn cannot pull it)",
      "Skill in use: Keeping a file current" in _frame and "fold" in _frame.lower()
      and "system/skills/keeping-a-file-current/SKILL.md" in _frame)
check("says affirmatively that it reaches nothing live", "reaches nothing live" in _frame)
for absent, why in [
    ("## Your tools", "no tools line"),
    ("list_integrations", "no reach section"),
    ("## Who else is here", "no cast"),
    ("The member is looking at", "no focus"),
    (PARTICIPANT_REGISTER.splitlines()[0], "no register clause (there is no reply — ADR-638 D2)"),
    ("## Skills\n", "no skills INDEX (a door is useless without ReadFile)"),
    ("SearchFiles", "no tool verbs"),
]:
    check(f"{why}", absent not in _frame, f"found {absent[:40]!r}")

# a missing skill fails OPEN — the job still carries the output contract
_bare = build_standing_frame(FakeClient(), "u1", model=_model, executor="editor",
                             job=build_standing_job(_decl), skill="no-such-skill")
check("a missing skill degrades craft, never correctness (job + contract still there)",
      "NO_CHANGE" in _bare and "Skill in use" not in _bare)

# the RUN uses it — read off the parsed CALLS, never the prose
_sw_src = _read("api/services/standing_work.py")
_sw_tree = ast.parse(_sw_src)
_run_fn = next(n for n in ast.walk(_sw_tree)
               if isinstance(n, ast.AsyncFunctionDef) and n.name == "run_standing_sweep")
_run_calls = _calls(_run_fn)
check("the run composes its system prompt with build_standing_frame",
      "build_standing_frame" in _run_calls)
check("…and rides the shared bounded derive turn", "run_bounded_derive_turn" in _run_calls)
check("the module never calls the transport directly", "route_completion" not in _calls(_sw_tree))
check("the module composes no system string of its own (no character + posture concat)",
      "resident_character" not in _code_only(_sw_src) and "build_standing_run_posture" not in _sw_src)
_lr_src = _read("api/services/lane_runner.py")
check("the standing frame lives BESIDE the lane frame, in the one module",
      "def build_standing_frame(" in _lr_src and "def build_lane_conventions(" in _lr_src)
check("the lane frame itself is byte-unchanged in shape (its scaffold ratchet still measures it)",
      "{skills_section}" in _CONVENTIONS_FRAME and "{tools_line}" in _CONVENTIONS_FRAME)

# ═══════════════════════════════════════════════════════════════════════════
print("D2. craft is a skill; the Python postures are gone")
# ═══════════════════════════════════════════════════════════════════════════
import services.skills as sk  # noqa: E402
import services.standing_work as sw  # noqa: E402

sk._kernel_cache = None
K = sk._load_kernel()
check("keeping-a-file-current is a kernel skill", "keeping-a-file-current" in K)
check("declaring-standing-work is a kernel skill", "declaring-standing-work" in K)
if "keeping-a-file-current" in K and "declaring-standing-work" in K:
    keep, decl = K["keeping-a-file-current"], K["declaring-standing-work"]
    check("keeping is scoped to text (the pane where a kept prose file is edited)", keep["apps"] == ("text",))
    check("declaring is universal (silence = everywhere — 'keep this current' said anywhere)", decl["apps"] == ())
    check("both descriptions are discovery-grade (<= 300 chars)",
          len(keep["description"]) <= 300 and len(decl["description"]) <= 300)
    check("keeping carries the output contract's honesty (NO_CHANGE) as craft", "NO_CHANGE" in keep["body"])
    check("declaring teaches the grammar (target · app · schedule · sources · shape)",
          all(w in decl["body"] for w in ("_standing.yaml", "target:", "app:", "schedule:", "sources:", "shape:")))
    check("declaring teaches the law (only the designated target)", "DESIGNATED target" in decl["body"])
    check("neither skill names an agent (ADR-630 D5)",
          not any(a in (keep["body"] + decl["body"]) for a in ("Supervisor", "Keeper", "Editor")))
for gone in ("_STANDING_RUN_POSTURE", "build_standing_run_posture", "_STANDING_PANE_FRAME",
             "build_strings_pane_posture", "resolve_strings_resident"):
    check(f"{gone} is deleted from the standing module", not hasattr(sw, gone))
for app in (None, "text", "slides", "images", "blogger"):
    b = len(sk.skills_index_section(app=app).encode())
    ceil = sk.UNBOUND_INDEX_CEILING if app is None else sk.INDEX_CEILING
    check(f"index[{app or 'open'}] holds its ceiling ({b} <= {ceil})", b <= ceil,
          "tighten a description, do not raise the ceiling (DP22)")
_text_idx = sk.skills_index_section(app="text")
_images_idx = sk.skills_index_section(app="images")
check("a Text pane is offered both skills", "keeping-a-file-current" in _text_idx and "declaring-standing-work" in _text_idx)
check("an Images pane is offered declaring but not keeping (scoped)",
      "declaring-standing-work" in _images_idx and "keeping-a-file-current" not in _images_idx)

# ═══════════════════════════════════════════════════════════════════════════
print("D3. one declaration grammar, one drain loop")
# ═══════════════════════════════════════════════════════════════════════════
import dataclasses  # noqa: E402
from services.standing_work import (  # noqa: E402
    DECLARATION_KEYS, DECLARATION_LEAF, STANDING_KIND, parse_standing_yaml, resolve_executor,
)

SRC = "sources:\n  - id: a\n    url: https://a.b/c\n"
d = parse_standing_yaml("target: notes.md\n" + SRC, topic="t", declaration_path="/workspace/t/_standing.yaml")
check("a prose target DERIVES app=text (the app follows the artifact, ADR-602 D7 one layer up)",
      d is not None and d.app == "text" and d.problem is None, f"{d and (d.app, d.problem)}")
d = parse_standing_yaml("target: notes.md\napp: blogger\n" + SRC, topic="t", declaration_path="p")
check("an explicit app WINS", d is not None and d.app == "blogger" and d.problem is None)
d = parse_standing_yaml("target: notes.md\napp: editor\n" + SRC, topic="t", declaration_path="p")
check("an AGENT slug in `app` is refused loudly (app_invalid) — never honoured, never parked",
      d is not None and d.problem == "app_invalid", f"{d and (d.app, d.problem)}")
d = parse_standing_yaml("target: a.csv\n" + SRC + "shape:\n  columns: [x]\n", topic="t", declaration_path="p")
check("a structured target needs no executor (app None, mechanical)",
      d is not None and d.app is None and d.problem is None, f"{d and (d.app, d.problem)}")
d = parse_standing_yaml("target: notes.md\nagent: editor\n" + SRC, topic="t", declaration_path="p")
check("an `agent:` key is inert residue in options, never a field",
      d is not None and d.options.get("agent") == "editor" and not hasattr(d, "agent"))
check("DECLARATION_KEYS is the parser's whitelist (options = everything else)",
      d is not None and set(d.options) == {"agent"} and "target" in DECLARATION_KEYS and "app" in DECLARATION_KEYS)
for banned in ("agent", "resident", "colleague", "assignee", "who", "executor"):
    check(f"no `{banned}` key", banned not in DECLARATION_KEYS)
check("no declaration key and no StandingDecl field is an agent's slug",
      not (DECLARATION_KEYS & set(AGENTS))
      and not ({f.name for f in dataclasses.fields(StandingDecl)} & set(AGENTS)))
check("the leaf is _standing.yaml and the kind is standing",
      DECLARATION_LEAF == "_standing.yaml" and STANDING_KIND == "standing")
check("the run stamps standing-sweep/standing-write with funnel_decision=standing",
      'slug=f"standing-sweep:{topic}"' in _sw_src and 'slug=f"standing-write:{topic}"' in _sw_src
      and 'funnel_decision="standing"' in _sw_src and 'funnel_decision="string"' not in _sw_src)
_consts = {n.value for n in ast.walk(_sw_tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
check("the run attributes system:standing and never writes system:strings",
      "system:standing" in _consts and "system:strings" not in _consts)
_mig251 = _read("supabase/migrations/251_adr639_funnel_decision_standing.sql")
check("migration 251 carries 'standing' in the funnel_decision CHECK (the value ships BEFORE the code)",
      "'standing'::text" in _mig251 and "'string'::text" in _mig251)
check("migration 252 renames the declaration, re-keys the index, re-stamps the lanes",
      all(w in _read("supabase/migrations/252_adr639_rename_the_declaration_and_restamp_lanes.sql")
          for w in ("_standing.yaml", "kind = 'standing'", "'{lane,app}'")))
check("the unwired rule module is gone (its rule lives beside the parser now)",
      not (API / "services" / "standing_declarations.py").exists())

# the executor derives — never named
_slug, _m, _post = resolve_executor(StandingDecl(topic="t", slug="standing:t", target="n.md", app="text"))
check("a text declaration resolves Editor's engine + character",
      _slug == "editor" and _post == AGENTS["editor"]["posture"] and _m in LANE_MODELS)
for bad in (None, "no-such-app"):
    try:
        resolve_executor(StandingDecl(topic="t", slug="standing:t", target="n.md", app=bad))
        check(f"an unresolvable app ({bad!r}) RAISES, never picks a plausible agent", False, "(no raise)")
    except KeyError:
        check(f"an unresolvable app ({bad!r}) RAISES, never picks a plausible agent", True)

# ONE loop — both lanes ride it, the twins are gone
from services.scheduling import claim_run, drain_due, record_run  # noqa: E402,F401

_cap_sched = _code_only(_read("api/services/capture/scheduling.py"))
_cap_drain = _code_only(_read("api/services/capture/drainer.py"))
_sw_code = _code_only(_sw_src)
check("the capture drainer rides drain_due", "drain_due(" in _cap_drain)
check("the standing drainer rides drain_due", "drain_due(" in _sw_code)
for twin in ("claim_capture_run", "record_capture_run", "claim_string_run", "record_string_run"):
    check(f"the twin `{twin}` is deleted", twin not in _cap_sched and twin not in _sw_code and twin not in _cap_drain)
_sched_src = _read("api/services/scheduling.py")
check("scheduling.py owns the loop (claim_run · record_run · drain_due)",
      all(f"def {f}(" in _sched_src for f in ("claim_run", "record_run", "drain_due")))

# DRIVE the loop with fakes: claim → run → record, in order; a raise still records
_log: list = []


class _Tasks:
    """A tasks table whose CAS claim succeeds once per baseline."""
    def __init__(self): self.rows = {("u1", "standing:a"): "T0"}; self._q = {}
    def table(self, n): return self
    def update(self, payload): self._q = {"update": payload}; return self
    def eq(self, k, v): self._q[k] = v; return self
    def execute(self):
        key = (self._q.get("user_id"), self._q.get("slug"))
        if "update" in self._q and "next_run_at" in self._q:
            if self.rows.get(key) == self._q["next_run_at"]:
                self.rows[key] = self._q["update"]["next_run_at"]; return SimpleNamespace(data=[{"id": 1}])
            return SimpleNamespace(data=[])
        return SimpleNamespace(data=[{"id": 1}])


_decl_a = SimpleNamespace(slug="standing:a", schedule=None, paused=False, paused_until=None, options={})


async def _due(client, now): return [("u1", _decl_a, "T0"), ("u1", _decl_a, "STALE")]
async def _run_ok(client, uid, decl): _log.append("run"); return {"success": True}
async def _run_boom(client, uid, decl): _log.append("run"); raise RuntimeError("x")
def _rec(client, uid, decl, at): _log.append("record")


_f, _s, _x = asyncio.new_event_loop().run_until_complete(
    drain_due(_Tasks(), "standing", due=_due, run=_run_ok, record=_rec))
check("the loop claims → runs → records, and a lost claim is a skipped row (not a run)",
      (_f, _s, _x) == (2, 1, 0) and _log == ["run", "record"], f"{(_f, _s, _x)} {_log}")
_log.clear()
import logging as _logging  # noqa: E402
_logging.disable(_logging.CRITICAL)  # the loop logs the raise it survives; that is the point
try:
    _f, _s, _x = asyncio.new_event_loop().run_until_complete(
        drain_due(_Tasks(), "standing", due=_due, run=_run_boom, record=_rec))
finally:
    _logging.disable(_logging.NOTSET)
check("a raising run is a FAILURE that still records (the row never strands on its sentinel)",
      (_f, _s, _x) == (2, 0, 1) and _log == ["run", "record"], f"{(_f, _s, _x)} {_log}")
check("claim_run refuses a None baseline (a never-indexed row is the CALLER's call, ADR-618 D2)",
      claim_run(_Tasks(), "u1", "standing:a", "standing", None) is False)
check("the tick drains standing work (and no strings lane)",
      "drain_due_standing_work(" in _read("api/jobs/unified_scheduler.py")
      and "drain_due_string_runs" not in _read("api/jobs/unified_scheduler.py"))

# ═══════════════════════════════════════════════════════════════════════════
print("D4. the app, its pane, its routes and the agent are DELETED")
# ═══════════════════════════════════════════════════════════════════════════
import services.apps  # noqa: F401,E402
from services.agents_registry import historical_agent_name, resolve_agent  # noqa: E402
from services.authoring import all_apps, resolve_app  # noqa: E402
from services.kernel_surfaces import KERNEL_SURFACES  # noqa: E402

check("the register is exactly {editor, designer, blogger}", set(AGENTS) == {"editor", "designer", "blogger"})
check("supervisor does not resolve (nothing routes a turn to it)", resolve_agent("supervisor") is None)
check("…but its name is still legible on the rows it signed (display only)",
      historical_agent_name("supervisor") == "Supervisor" and historical_agent_name("editor") is None)
check("lanes.py resolves transcript speakers through the historical table",
      "historical_agent_name(" in _code_only(_read("api/routes/lanes.py")))
check("the apps are exactly {slides, text, images, blogger}", set(all_apps()) == {"slides", "text", "images", "blogger"})
check("no strings registration", resolve_app("strings") is None)
check("no strings surface row", not [e for e in KERNEL_SURFACES if e.get("slug") == "strings"])
for gone in ("api/services/strings.py", "api/routes/strings.py",
             "web/components/strings/StringsSurface.tsx",
             "web/components/queue/StandingBand.tsx", "web/components/queue/standing-band.constants.ts"):
    check(f"{gone} is deleted", not (ROOT / gone).exists())
check("the standing routes are mounted", "standing_work.router" in _read("api/main.py"))
check("the routes are the roster + the two switches, and no composed view",
      all(w in _read("api/routes/standing_work.py") for w in ('"/standing"', '"/standing/{topic:path}"', '"/standing/{topic:path}/run"'))
      and "_consumers" not in _read("api/routes/standing_work.py"))

# the FE
_stub = _read("web/app/(authenticated)/strings/page.tsx")
check("/strings is an ADR-308 redirect stub (server transport, no client redirect)",
      "redirect(" in _stub and "'use client'" not in _stub and "useEffect(" not in _stub)
check("…hand-listed in middleware (the ADR-592 obligation)",
      '"/strings"' in _read("web/lib/supabase/middleware.ts"))
_slugs = _read("web/types/surface.ts")
_union = _slugs.split("KERNEL_SURFACE_SLUGS")[1].split(";")[0] if "KERNEL_SURFACE_SLUGS" in _slugs else ""
check("strings left KERNEL_SURFACE_SLUGS", "'strings'" not in _union)
check("no strings AppDescriptor (ADR-636 parity is bidirectional)",
      not re.search(r"^\s{2}strings:\s*\{", _code_only_ts := _read("web/lib/apps/registry.ts"), re.M))
_prefs = _read("web/lib/shell/surface-preferences.ts")
_kept_block = _prefs.split("DEFAULT_KEPT_SURFACES: string[] = [")[1].split("]")[0] if "DEFAULT_KEPT_SURFACES" in _prefs else ""
# Parse the ROWS (the ADR-592 gate's regex), never the block text: a comment
# that names the retired slug is documentation, not a pin.
_kept = set(re.findall(r"^\s*'([a-z0-9-]+)'", _kept_block, re.M))
check("the Dock pin is gone", "strings" not in _kept and len(_kept) >= 4)
check("a persisted pin renders no ghost (DOCK_RETIRED_SLUGS)",
      re.search(r"DOCK_RETIRED_SLUGS = new Set<string>\(\[[^\]]*'strings'", _prefs) is not None)
check("the surface params are gone", not re.search(r"^\s*strings:\s*\[", _prefs, re.M))
_client = _read("web/lib/api/client.ts")
check("the api client serves `standing` and no `strings` namespace",
      re.search(r"^\s*standing:\s*\{", _client, re.M) is not None
      and re.search(r"^\s*strings:\s*\{", _client, re.M) is None
      and "/api/standing" in _client)
check("no _string.yaml routing claim (the resolver claims nothing today)",
      not re.search(r"/_string\\?\.yaml\$/", _read("web/lib/file-types/index.ts"))
      and "surface: 'strings'" not in _read("web/lib/file-types/index.ts"))
check("the Files 'Keep this current…' door is gone (its act survives as a conversation)",
      "keep-current" not in _read("web/app/(authenticated)/files/page.tsx"))
_notif = _read("web/app/(authenticated)/notifications/page.tsx")
check("Notifications has a Standing work pane (ADR-603 D4's lens, finally housed)",
      'key: "standing"' in _notif and "<StandingWork" in _notif
      and "<StandingBand" not in _notif and "import { StandingBand" not in _notif)
check("the pane component exists and offers the two switches",
      all(w in _read("web/components/notifications/StandingWork.tsx") for w in ("api.standing.list", "api.standing.run", "api.standing.update")))
check("no SurfaceRegistry row mounts the deleted page", "StringsPage" not in _read("web/components/shell/SurfaceRegistry.tsx"))
check("the agent icon map no longer carries Supervisor's glyph (a map ROW, not a comment)",
      not re.search(r"^\s*'clipboard-list':\s*ClipboardList", _read("web/components/agents/AgentIcon.tsx"), re.M)
      and "ClipboardList }" not in _read("web/components/agents/AgentIcon.tsx").split("from 'lucide-react'")[0])
check("the landing page shows no Supervisor and no Strings",
      "Supervisor" not in _read("web/components/landing/product/AgentsReplica.tsx")
      and "supervisor" not in _read("web/components/landing/AppShowcase.tsx").lower())

# ═══════════════════════════════════════════════════════════════════════════
print("D5. attribution displays as the work, not a face")
# ═══════════════════════════════════════════════════════════════════════════
from services.principal_display import display_author  # noqa: E402

check("system:standing → Standing work", display_author("system:standing") == "Standing work")
check("system:strings (historical) → Standing work", display_author("system:strings") == "Standing work")
_attr = _read("web/lib/workspace/attribution.ts")
check("the FE attribution table maps both prefixes to Standing work",
      "system:standing" in _attr and "system:strings" in _attr and "Standing work" in _attr)

print()
if FAILURES:
    print(f"✗ {len(FAILURES)} check(s) failed: {FAILURES}")
    sys.exit(1)
print("✓ all ADR-639 checks passed")
