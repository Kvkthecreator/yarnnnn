"""ADR-624 — the being has a home, and what it knows lives there.

Script-style (py3.9-safe, no pytest import): `python3 test_adr624_the_being_has_a_home.py`.

WHAT THIS GATE HOLDS
  1. The home's SHAPE — memory/ is the free half, the sidecars are the locked
     half, and the ten ADR-414 files stay deleted from the spec.
  2. The CONFINEMENT rule, driven in BOTH directions through the real gate
     (`_is_path_locked_for_principal`), not grepped — a rule asserted by
     substring passes for the wrong reason the day the function is rewritten.
  3. The sidecar rule PRESERVED (this ADR re-cut the home; it must not have
     loosened ADR-414 D6's lock).
  4. The four dormant surface rows stay DELETED (ADR-624 D5).
  5. The pane's coverage of the register — the fact that produced this ADR.

FALSIFICATION: every check below was run against the pre-change tree and the
ADR-624 ones went red for the stated reason (recorded per-section).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

failures = []


def check(label, cond, detail=""):
    if cond:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}" + (f" — {detail}" if detail else ""))
        failures.append(label)


class _Auth:
    """Minimal auth stand-in — the gate reads `caller_identity` only."""

    def __init__(self, caller_identity):
        self.caller_identity = caller_identity
        self.user_id = "u-test"
        self.freddie_caller = False


# ---------------------------------------------------------------------------
print("\n§1 — the home's shape (ADR-624 D1)")
# ---------------------------------------------------------------------------
from services.workspace_paths import (  # noqa: E402
    AGENT_GRANT_SIDECAR_LEAVES,
    AGENT_MEMORY_DIRNAME,
    agent_home,
    agent_home_owner,
    agent_memory_root,
    is_agent_grant_sidecar,
)

check("agent_home is the slug's prefix", agent_home("editor") == "agents/editor/")
check(
    "agent_memory_root is the free half",
    agent_memory_root("editor") == "agents/editor/memory/",
)
check("memory dirname is flat, not desk-scoped", AGENT_MEMORY_DIRNAME == "memory/")
check(
    "both grant sidecars are declared",
    set(AGENT_GRANT_SIDECAR_LEAVES) == {"_autonomy.yaml", "_budget.yaml"},
)

# The ten deleted files must not reappear as constants or spec lines. Read the
# SPEC BLOCK only — the ADR's own prose names them to say they are gone, and a
# whole-file grep would fire on the very comment that records the deletion.
_wp_src = open(os.path.join(os.path.dirname(__file__), "services/workspace_paths.py")).read()
_spec_start = _wp_src.index("# Per-agent homes (ADR-624")
_spec_end = _wp_src.index("AGENT_GRANT_SIDECAR_LEAVES")
_spec = _wp_src[_spec_start:_spec_end]
for banned in ("MANDATE.md", "principles.md", "_expected_output.yaml", "standing_intent.md"):
    check(
        f"the spec no longer LAYS OUT {banned}",
        f"     {banned}" not in _spec and f"#     {banned}" not in _spec,
        "a re-added layout line would re-create the ADR-414 model",
    )
# Matched on the two halves rather than the whole sentence: the rule is a
# comment and comments wrap, so pinning the exact one-line spelling would go red
# on a reflow that changed nothing. (First cut did exactly that.)
check(
    "the spec states the whole rule",
    "what it KNOWS (free)" in _spec and "runs under (locked)" in _spec,
)

# ---------------------------------------------------------------------------
print("\n§2 — agent_home_owner reads the home, and fails closed on malformed input")
# ---------------------------------------------------------------------------
check("owner of a memory file", agent_home_owner("agents/editor/memory/notes.md") == "editor")
check(
    "owner survives the /workspace/ prefix",
    agent_home_owner("/workspace/agents/blogger/_autonomy.yaml") == "blogger",
)
check("a bare agents/ names nobody", agent_home_owner("agents/") is None)
check("a leaf directly in agents/ names nobody", agent_home_owner("agents/editor") is None)
check("a double slash names nobody", agent_home_owner("agents//notes.md") is None)
check("a non-agents path names nobody", agent_home_owner("operation/report.md") is None)

# ---------------------------------------------------------------------------
print("\n§3 — CONFINEMENT, driven through the real gate (ADR-624 D3)")
# ---------------------------------------------------------------------------
# DRIVEN, not grepped: `_is_path_locked_for_principal` is the single gate entry
# point, so calling it proves the wiring as well as the rule. A grep for the
# helper's NAME would pass even if nothing called it — the exact defect class
# this repo has hit before.
from services.primitives.workspace import (  # noqa: E402
    _caller_agent_slug,
    _is_path_locked,
    _is_path_locked_for_principal,
)

editor = _Auth("agent:editor")
blogger = _Auth("specialist:blogger")
sluggless = _Auth("agent:")
member = _Auth("member:u-123 via anthropic/claude-sonnet-5")

check("slug resolves from agent:", _caller_agent_slug(editor) == "editor")
check("slug resolves from specialist:", _caller_agent_slug(blogger) == "blogger")
check("a sluggless agent identity resolves None", _caller_agent_slug(sluggless) is None)
check("a member identity carries no agent slug", _caller_agent_slug(member) is None)

# The rule, both directions.
check(
    "a being may write its OWN memory",
    not _is_path_locked_for_principal(editor, "agents/editor/memory/notes.md"),
    "the free half of the home must stay free",
)
check(
    "a being may NOT write ANOTHER being's memory",
    _is_path_locked_for_principal(editor, "agents/blogger/memory/notes.md"),
    "this is the gap ADR-624 D3 closes — agents/ was in no locked prefix set",
)
check(
    "a being may NOT write its own grant sidecar",
    _is_path_locked_for_principal(editor, "agents/editor/_autonomy.yaml"),
    "ADR-414 D6's lock must survive the re-cut",
)
check(
    "a being may NOT write another's grant sidecar",
    _is_path_locked_for_principal(editor, "agents/blogger/_budget.yaml"),
)
check(
    "a sluggless agent-class caller is locked out of EVERY home (fail closed)",
    _is_path_locked_for_principal(sluggless, "agents/editor/memory/notes.md"),
    "an unresolvable identity is misconfigured, not privileged",
)
check(
    "confinement does not leak outside agents/",
    not _is_path_locked_for_principal(editor, "operation/report.md"),
    "an agent-class caller keeps its ordinary operation/ reach",
)
check(
    "the root table still binds an agent-class caller",
    _is_path_locked_for_principal(editor, "governance/_budget.yaml"),
    "confinement is ADDITIVE to the five-root topology, never a replacement",
)

# The member/operator path is the one that actually runs today (ADR-624 D3's
# recorded seam). It must NOT be confined — a lane writes under the member's
# grant, so a being writing its memory today is a write the member makes.
check(
    "a member's lane is not confined by the agent rule",
    not _is_path_locked_for_principal(member, "agents/editor/memory/notes.md"),
    "ADR-411 D4 — the lane is the member's embodiment",
)

# ---------------------------------------------------------------------------
print("\n§4 — the class-level lock is unchanged for non-agent callers")
# ---------------------------------------------------------------------------
check("mcp still locked from a sidecar", _is_path_locked("mcp", "agents/editor/_autonomy.yaml"))
check("freddie still locked from a sidecar", _is_path_locked("freddie", "agents/x/_budget.yaml"))
check(
    "operator is NOT locked from a sidecar",
    not _is_path_locked("operator", "agents/editor/_autonomy.yaml"),
    "the operator sets the grant — ADR-414 D6",
)
check(
    "operator is NOT locked from a being's memory",
    not _is_path_locked("operator", "agents/editor/memory/notes.md"),
)

# ---------------------------------------------------------------------------
print("\n§5 — the four dormant surface rows stay DELETED (ADR-624 D5)")
# ---------------------------------------------------------------------------
from services.kernel_surfaces import KERNEL_SURFACES  # noqa: E402

_rows = KERNEL_SURFACES if isinstance(KERNEL_SURFACES, list) else list(KERNEL_SURFACES.values())
_slugs = {r.get("slug") for r in _rows}
for gone in ("identity", "mandate", "principles", "expected-output"):
    check(
        f"the `{gone}` surface row is gone",
        gone not in _slugs,
        "a row reserved for a surface ADR-624 declined to build is the ADR-592 inert-field shape",
    )

# Narrowed deliberately. My first cut asserted NO routeless row survives and was
# WRONG in a way worth recording: `top-bar`/`launcher`/`chat-drawer` are chrome
# and `setup` is a sequence — none of them is navigable BY DESIGN, so a blanket
# rule would have demanded deleting correct rows. The defect D5 names is
# narrower: a routeless DOCUMENT row, i.e. a reader-facing page reserved for a
# surface nobody is building. That is the shape to keep out.
#
# Scoped to the PER-AGENT four, not to every routeless document row: `program`
# is also routeless (ADR-432 D2d) but is a different concern with live hire
# machinery behind it, and this ADR has no standing to decide it. A gate that
# reached it would be legislating outside its own ADR.
_PER_AGENT_RESERVATIONS = {"identity", "mandate", "principles", "expected-output"}
_routeless_docs = {
    r.get("slug")
    for r in _rows
    if not (r.get("route") or "").strip() and r.get("archetype") == "document"
}
check(
    "no per-agent reservation survives as a routeless document row",
    not (_routeless_docs & _PER_AGENT_RESERVATIONS),
    f"still reserved: {sorted(_routeless_docs & _PER_AGENT_RESERVATIONS)} — "
    "a reader-facing page with no route is a reservation, not a surface",
)

# (the STEWARD_SURFACE_SLUGS filter retired with the steward — ADR-632)

# ---------------------------------------------------------------------------
print("\n§6 — the pane's coverage of the register (the fact behind this ADR)")
# ---------------------------------------------------------------------------
from services.agents_registry import AGENTS, AGENT_ROW_KEYS  # noqa: E402
from routes.lanes import _agents_payload  # noqa: E402

_payload = _agents_payload()
check("the register is non-empty", bool(AGENTS))
check("some being is served to the pane", bool(_payload))

# The row keys the pane does NOT render are exactly the two internal ones. If a
# NEW row key ever lands, this goes red — which is the point: a fact added to a
# being should be a deliberate decision about whether a member sees it.
_served_keys = set(_payload[0].keys()) if _payload else set()
_unrendered = {k for k in AGENT_ROW_KEYS if k not in _served_keys}
check(
    "only `posture` and `token_profile` are withheld from the pane",
    _unrendered == {"posture", "token_profile"},
    f"unrendered row keys: {sorted(_unrendered)} — a new key needs a surface decision",
)

# ---------------------------------------------------------------------------
print("\n" + "=" * 68)
if failures:
    print(f"RED — {len(failures)} failing assertion(s):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("GREEN — ADR-624 holds.")
