"""ADR-580 gate — the connector derive step: connector data reaches the commons.

The failure classes this arc paid for, held here:

  - "ratified but unbuilt" (ADR-394 D3's derive-by-reference produced ZERO
    derived files in 7 weeks) → the write path is DRIVEN, not grepped.
  - the D5 lesson (capture cadence must never multiply judgment spend) → the
    pace law is a PURE function, driven over its whole truth table.
  - green-gates-test-the-room → the scheduler CALL SITE is AST-checked inside
    the flag branch, and the shared-turn rule is checked as an absence
    (no lane calls route_completion directly).

Script-style (python3, from api/). Every check below was falsified against a
broken shape before being trusted (see the ADR's verification section).
"""

from __future__ import annotations

import ast
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = Path(__file__).resolve().parent
sys.path.insert(0, str(API))

PASS = 0
FAIL = 0


def check(label: str, ok, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))


def _code_only(path: Path) -> str:
    """Source with docstrings stripped — a gate must never match its own prose."""
    src = path.read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                body[0].value.value = ""
    return ast.unparse(tree)


# ═════════════════════════════════════════════════════════════════════════════
print("§1 placement — kernel-deterministic, grammar-conformant, reachable")
# ═════════════════════════════════════════════════════════════════════════════

from services.connector_derive import (  # noqa: E402
    DERIVE_AUTHOR_PREFIX,
    build_connector_derive_posture,
    digest_path,
    is_due,
    parse_stamp,
    strip_provenance_header,
)

p = digest_path("slack", "C0A6P2WS4HL")
check("1a digest path is /workspace-absolute under operation/_connectors/",
      p == "/workspace/operation/_connectors/slack/c0a6p2ws4hl.md", p)
p2 = digest_path("github", "Kvk/yarnnnn")
check("1b a slash-bearing selector stays ONE segment (no tree escape)",
      p2.count("/") == p.count("/"), p2)
check("1c the digest is prose, never machine-parsed (no underscore leaf)",
      not p.rsplit("/", 1)[-1].startswith("_"))

from services.primitives.embed import is_embed_eligible  # noqa: E402
eligible, reason = is_embed_eligible(p, "x" * 500)
check("1d the digest is embed-eligible — stage 4 reachability is REAL",
      eligible, reason)
raw_ok, raw_reason = is_embed_eligible("/workspace/inbound/slack/c1/2026-01-01T00:00:00Z.md", "x" * 500)
check("1e the raw it derives from stays quarantined (control)", not raw_ok)


# ═════════════════════════════════════════════════════════════════════════════
print("§2 the pace law — pure, driven over its truth table (the D5 lesson)")
# ═════════════════════════════════════════════════════════════════════════════

NOW = datetime(2026, 8, 18, 12, 0, tzinfo=timezone.utc)
h = lambda n: NOW - timedelta(hours=n)  # noqa: E731

check("2a no raw → never due", not is_due(None, h(48), NOW))
check("2b raw + no prior derive → due (first derive)", is_due(h(1), None, NOW))
check("2c raw OLDER than the last derive → not due (quiet world costs $0)",
      not is_due(h(10), h(8), NOW))
check("2d newer raw but inside the 6h floor → not due (capture chatter "
      "cannot multiply judgment spend)", not is_due(h(1), h(2), NOW))
check("2e newer raw + floor passed → due", is_due(h(1), h(7), NOW))

check("2f stamp parses the capture-lane spelling",
      parse_stamp("2026-07-03T06:40:31Z.md") == datetime(2026, 7, 3, 6, 40, 31, tzinfo=timezone.utc))
check("2g stamp parses the compact web-lane spelling",
      parse_stamp("2026-08-17T210044Z.xml") == datetime(2026, 8, 17, 21, 0, 44, tzinfo=timezone.utc))
check("2h a non-stamp filename is None, not a crash", parse_stamp("unknown.md") is None)


# ═════════════════════════════════════════════════════════════════════════════
print("§3 the write — DRIVEN: attribution, kind, citation (never grepped)")
# ═════════════════════════════════════════════════════════════════════════════


class _Q:
    """Chainable query fake: any filter chain executes to empty data."""

    def __init__(self, data=None):
        self._data = data or []

    def __getattr__(self, name):
        def _chain(*a, **k):
            return self
        return _chain

    def execute(self):
        from types import SimpleNamespace
        return SimpleNamespace(data=self._data)


class _FakeClient:
    def __init__(self, files=None):
        self.files = files or {}

    def table(self, name):
        if name == "workspace_files":
            return _FakeFilesQ(self.files)
        return _Q()


class _FakeFilesQ(_Q):
    def __init__(self, files):
        super().__init__()
        self.files = files
        self._path = None

    def eq(self, col, val):
        if col == "path":
            self._path = val
        return self

    def execute(self):
        from types import SimpleNamespace
        if self._path in self.files:
            return SimpleNamespace(data=[{"content": self.files[self._path]}])
        return SimpleNamespace(data=[])


class _FakeUM:
    def __init__(self, listing, bodies):
        self._listing = listing
        self._bodies = bodies

    async def list(self, sub):
        return self._listing

    async def read(self, rel):
        return self._bodies[rel]


captured = {}


def _fake_write_revision(client, **kw):
    captured.update(kw)
    return "rev-abc123def"


class _FakeTurn:
    status = "ok"
    text = "# Slack — daily-work\n\nThe team shipped the thing."
    ledger_model = "anthropic/claude-sonnet-5"
    usage: dict = {}
    error = None


async def _fake_turn(**kw):
    captured["turn_kwargs"] = kw
    return _FakeTurn()


def _run_drive():
    import services.authored_substrate as asub
    import services.derive_turn as dt
    import services.workspace as ws
    import services.telemetry as tel
    import services.connector_derive as cd

    orig = (asub.write_revision, dt.run_bounded_derive_turn, ws.UserMemory,
            tel.record_execution_event)
    asub.write_revision = _fake_write_revision
    dt.run_bounded_derive_turn = _fake_turn
    listing = ["2026-08-18T09:00:00Z.md", "2026-08-18T10:00:00Z.md"]
    bodies = {
        "inbound/slack/c0a6p2ws4hl/2026-08-18T09:00:00Z.md": "raw nine",
        "inbound/slack/c0a6p2ws4hl/2026-08-18T10:00:00Z.md": "raw ten",
    }
    ws.UserMemory = lambda client, uid: _FakeUM(listing, bodies)
    tel.record_execution_event = lambda *a, **k: None
    try:
        return asyncio.get_event_loop().run_until_complete(
            cd.run_connector_derive(
                _FakeClient(), "user-1", "slack", "C0A6P2WS4HL",
                connected_by="2abf3f96-118b-4987-9d95-40f2d9be9a18",
            )
        )
    finally:
        (asub.write_revision, dt.run_bounded_derive_turn, ws.UserMemory,
         tel.record_execution_event) = orig


result = _run_drive()
check("3a the derive succeeds and returns the revision id",
      result.get("success") and result.get("revision_id") == "rev-abc123def",
      str(result))
check("3b authored_by is the MECHANISM — system:derive-{platform}",
      captured.get("authored_by") == "system:derive-slack",
      str(captured.get("authored_by")))

from services.principal_display import _UUID_RE, display_author  # noqa: E402
check("3c no UUID rides the authored_by string (the _scrub law)",
      not _UUID_RE.search(captured.get("authored_by") or "uuid-missing"))
check("3d the OWNER rides author_identity_uuid (= connected_by)",
      captured.get("author_identity_uuid") == "2abf3f96-118b-4987-9d95-40f2d9be9a18")
check("3e the write is a derivation, never authored raw",
      captured.get("revision_kind") == "derivation")

expected_raws = [
    "/workspace/inbound/slack/c0a6p2ws4hl/2026-08-18T09:00:00Z.md",
    "/workspace/inbound/slack/c0a6p2ws4hl/2026-08-18T10:00:00Z.md",
]
check("3f the ledger derived_from edge cites the consumed raw (absolute)",
      captured.get("derived_from") == expected_raws, str(captured.get("derived_from")))

from services.authored_substrate import extract_derived_from_list  # noqa: E402
content = captured.get("content") or ""
check("3g the content's head-anchored citation parses back to the same raw "
      "(what gather_cited_raw_paths reads — the GC keeps cited raw)",
      extract_derived_from_list(content) == expected_raws,
      str(extract_derived_from_list(content)))
check("3h the body survives after the provenance header",
      "The team shipped the thing." in strip_provenance_header(content))

# The ratified sentence composes at DISPLAY, never in storage.
shown = display_author(
    captured["authored_by"],
    author_identity_uuid=captured["author_identity_uuid"],
    member_names={"2abf3f96-118b-4987-9d95-40f2d9be9a18": "Kevin"},
)
check("3i display composes the ratified sentence — "
      "'system:derive-slack on behalf of Kevin'",
      shown == "system:derive-slack on behalf of Kevin", shown)
shown_unresolved = display_author(
    captured["authored_by"],
    author_identity_uuid=captured["author_identity_uuid"],
    member_names={},
)
check("3j an unresolvable owner degrades to the plain mechanism — never a UUID",
      shown_unresolved == "system:derive-slack" and not _UUID_RE.search(shown_unresolved),
      shown_unresolved)

posture = build_connector_derive_posture("slack", "daily-work")
check("3k the posture contracts the honest empty answer (NO_CHANGE)",
      "NO_CHANGE" in posture)


# ═════════════════════════════════════════════════════════════════════════════
print("§4 wiring — the scheduler calls the drain INSIDE the dormancy flag")
# ═════════════════════════════════════════════════════════════════════════════


def _calls_in(node) -> set:
    names = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                names.add(f.id)
            elif isinstance(f, ast.Attribute):
                names.add(f.attr)
    return names


sched_tree = ast.parse((API / "jobs" / "unified_scheduler.py").read_text())
wired = gated = False
for n in ast.walk(sched_tree):
    if isinstance(n, ast.If):
        test_names = {x.id for x in ast.walk(n.test) if isinstance(x, ast.Name)}
        if "capture_lane_on" in test_names and "drain_due_connector_derives" in _calls_in(n):
            wired = gated = True
if not wired:
    # wired anywhere at all? (distinguishes "missing" from "un-gated")
    wired = "drain_due_connector_derives" in _calls_in(sched_tree)
check("4a the scheduler CALLS drain_due_connector_derives", wired)
check("4b the call sits INSIDE the capture_lane_on branch "
      "(ADR-404 D2 — one lane, one flag)", gated)

drain_src = _code_only(API / "services" / "connector_derive.py")
drain_tree = ast.parse(drain_src)
drain_fn = next(n for n in ast.walk(drain_tree)
                if isinstance(n, ast.AsyncFunctionDef)
                and n.name == "drain_due_connector_derives")
check("4c the drain gates every turn on the pure pace law (is_due at the call site)",
      "is_due" in _calls_in(drain_fn))

lane_code = _code_only(API / "services" / "capture" / "lane.py")
check("4d the capture lane never invokes derive — cadence decoupling holds "
      "(the retired ADR-401 D5 wake stays retired)",
      "connector_derive" not in lane_code and "drain_due_connector_derives" not in lane_code)


# ═════════════════════════════════════════════════════════════════════════════
print("§5 one turn implementation — no lane calls the transport directly")
# ═════════════════════════════════════════════════════════════════════════════

for lane in ("services/radar.py", "services/strings.py", "services/connector_derive.py"):
    code = _code_only(API / lane)
    tree = ast.parse(code)
    check(f"5 {lane} routes through the shared turn (no direct route_completion call)",
          "route_completion" not in _calls_in(tree)
          and "run_bounded_derive_turn" in _calls_in(tree))

turn_code = _code_only(API / "services" / "derive_turn.py")
check("5d derive_turn itself IS the transport caller (the one home)",
      "route_completion" in _calls_in(ast.parse(turn_code)))


# ═════════════════════════════════════════════════════════════════════════════
print("§6 the engine row — machinery, declared, priced")
# ═════════════════════════════════════════════════════════════════════════════

from services.system_calls import SYSTEM_CALLS  # noqa: E402

check("6a connector_derive is a SYSTEM_CALLS row (machinery, not an app resident)",
      "connector_derive" in SYSTEM_CALLS)
# provider-prefix + pricing + tier + reason are held per-row by
# test_adr556_system_calls.py, which iterates every row — including this one.

n = PASS + FAIL
print(f"\n{PASS}/{n} ADR-580 assertions pass")
sys.exit(0 if FAIL == 0 else 1)
