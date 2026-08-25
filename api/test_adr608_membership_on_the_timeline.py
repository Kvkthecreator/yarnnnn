"""ADR-608 gate — membership joins the timeline (Layer-1 G2).

Run script-style from api/:  python3 test_adr608_membership_on_the_timeline.py

Defends: the fourth derivation source (principal_grants → kind="membership",
JOINS only, human member/viewer roles, owner-genesis excluded, service-client
read), the explicit material weight, and the FE grammar/mounts admitting the
new kind. Behavioral where pure; AST-anchored on the wired block otherwise.
"""

from __future__ import annotations

import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_pass = 0
_fail = 0


def _assert(cond: bool, label: str) -> None:
    global _pass, _fail
    if cond:
        _pass += 1
        print(f"  ✓ {label}")
    else:
        _fail += 1
        print(f"  ✗ {label}")


def _read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), "r", encoding="utf-8") as f:
        return f.read()


def test_weight_is_material() -> None:
    print("\n[weight] a colleague arriving is material (CALLED, not grepped)")
    from services.attention import classify_weight

    _assert(classify_weight("membership") == "material",
            "classify_weight('membership') == material, explicitly")


def _membership_segment() -> str:
    src = _read("api/routes/workspace.py")
    tree = ast.parse(src)
    fns = [n for n in ast.walk(tree)
           if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))
           and "timeline" in n.name.lower()]
    for fn in fns:
        seg = ast.get_source_segment(src, fn) or ""
        if "principal_grants" in seg:
            return seg
    return ""


def test_fourth_source_wired() -> None:
    print("\n[derivation] the fourth source, in the timeline function itself")
    seg = _membership_segment()
    _assert(bool(seg), "the timeline derivation reads principal_grants")
    _assert('kind="membership"' in seg or "kind='membership'" in seg,
            "grant rows become kind='membership' entries")
    _assert('"member", "viewer"' in seg.replace("'", '"'),
            "human member/viewer roles only")
    _assert('"owner"' not in seg.split("principal_grants", 1)[1].split("except", 1)[0].replace("'", '"'),
            "the owner's founding grant is NOT a join (genesis ≠ arrival)")
    _assert('.eq("status", "active")' in seg.replace("'", '"'),
            "JOINS only — no wrong-timed 'left' from a revoked row's created_at")
    _assert("get_service_client" in seg,
            "the block reads via the service client (grants are not member-JWT-readable)")
    _assert('f"member:{pid}"' in seg or "actor_id=pid" in seg,
            "actor rides the member:{uuid} form so the viewer layer resolves + self-suppresses")


def test_fe_admits_the_kind() -> None:
    print("\n[FE] grammar + mounts admit membership")
    rows = _read("web/lib/workspace/timeline-rows.tsx")
    glyph_and_line = rows.count("entry.kind === 'membership'")
    _assert(glyph_and_line >= 2,
            "KindGlyph AND actorLine both branch on the new kind (wired, not typed)")
    _assert("joined the workspace" in rows,
            "the sentence exists in the shared grammar")
    bell = _read("web/components/shell/AttentionCenter.tsx")
    _assert("e.kind !== 'membership'" in bell.replace('"', "'"),
            "the bell's Activity admits membership entries")
    _assert("'membership'" in _read("web/lib/api/client.ts"),
            "the client's TimelineEntry kind union carries it")


if __name__ == "__main__":
    for fn in [test_weight_is_material, test_fourth_source_wired, test_fe_admits_the_kind]:
        fn()
    print(f"\n{'ALL PASS' if _fail == 0 else 'FAIL'} — {_pass} passed, {_fail} failed")
    sys.exit(0 if _fail == 0 else 1)
