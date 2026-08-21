"""ADR-580 → ADR-594 gate — the digest is SUPERSEDED; the shared turn survives.

ADR-580 built the connector digest as the intake pipeline's distil step.
ADR-582 demoted it to an opt-in consumer; ADR-591 deleted its walker; ADR-594
D3 deleted the module itself — the digest is a special case of an md string
with connector sources (the ADR-569 generalization applied a second time,
after radar). What ADR-580 permanently contributed is the SHARED bounded
derive turn (`services/derive_turn.py`, D6), whose live tenant is Strings.

This gate holds:
  §1 the supersession — the digest module and its system-call row stay
     deleted; radar stays deleted (ADR-592)
  §2 one turn implementation — Strings routes through the shared turn and
     never calls the transport directly; derive_turn is the ONE home
  §3 the stamp grammar — both live spellings parse (the shared reader's
     contract, previously asserted here via the digest's re-export)

Script-style (python3, from api/).
"""

from __future__ import annotations

import ast
import sys
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
    src = path.read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                body[0].value.value = ""
    return ast.unparse(tree)


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


# ═════════════════════════════════════════════════════════════════════════════
print("§1 the supersession — deleted machinery stays deleted (ADR-594 D3)")
# ═════════════════════════════════════════════════════════════════════════════

check("1a connector_derive.py stays DELETED (the digest = an md string with "
      "connector sources; a second prose-derive lane is a dual implementation)",
      not (API / "services" / "connector_derive.py").exists())

from services.system_calls import SYSTEM_CALLS  # noqa: E402

check("1b the connector_derive SYSTEM_CALLS row is gone (Strings' judgment "
      "routes through its RESIDENT per ADR-562, never a system call)",
      "connector_derive" not in SYSTEM_CALLS)

check("1c radar stays DELETED (ADR-592 — the first specialization folded)",
      not (API / "services" / "radar.py").exists())

# The digest's substrate survives as ordinary attributed files — code re-cuts
# never delete substrate. Nothing here asserts on production data.


# ═════════════════════════════════════════════════════════════════════════════
print("§2 one turn implementation — no lane calls the transport directly")
# ═════════════════════════════════════════════════════════════════════════════

strings_code = _code_only(API / "services" / "strings.py")
strings_calls = _calls_in(ast.parse(strings_code))
check("2a strings routes through the shared turn",
      "run_bounded_derive_turn" in strings_calls)
check("2b strings never calls the transport directly",
      "route_completion" not in strings_calls)

turn_code = _code_only(API / "services" / "derive_turn.py")
check("2c derive_turn itself IS the transport caller (the one home)",
      "route_completion" in _calls_in(ast.parse(turn_code)))


# ═════════════════════════════════════════════════════════════════════════════
print("§3 the stamp grammar — the shared reader's contract")
# ═════════════════════════════════════════════════════════════════════════════

from services.connectors import parse_stamp  # noqa: E402

check("3a stamp parses the capture-lane spelling",
      parse_stamp("2026-07-03T06:40:31Z.md") is not None)
check("3b stamp parses the compact web-lane spelling",
      parse_stamp("2026-08-17T210044Z.md") is not None)
check("3c a non-stamp filename is None, not a crash",
      parse_stamp("unknown.md") is None)

n = PASS + FAIL
print(f"\n{PASS}/{n} ADR-580/594 assertions pass")
sys.exit(0 if FAIL == 0 else 1)
