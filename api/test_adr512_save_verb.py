"""ADR-512 §8a regression gate — the save verb (the write half of exact-version).

Structural checks (no DB, no mcp package — same pattern as the open gate).

Run: python3 test_adr512_save_verb.py  (from api/)

Asserts:
  1. The WriteFile primitive threads the CAS rider (expected_parent_version_id
     → um.write) and maps StaleWriteError to a structured stale_write carrying
     the intervening head's attribution. The rider is optional (existing
     callers byte-identical).
  2. compose_save enforces read-before-write: existing file + no base →
     base_required (never a write); base + no file → not_found; the write
     dispatches through execute_primitive (all consequence at the gate — no
     second write door).
  3. server.py registers save with the base_revision contract taught in the
     docstring + instructions; six verbs taught; output schema present.
"""

import inspect
import sys

# ADR-533 D2: see the note in test_adr512_open_verb.py — the verb bullets are
# derived at import time, so this asserts the RENDERED instructions.
from test_adr533_participant_contract import rendered_instructions as _rendered_instructions


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def main():
    results = []

    # 1. the primitive's CAS rider
    from services.primitives import workspace as pw
    src = inspect.getsource(pw.handle_write_file)
    results.append(_check(
        "1a WriteFile threads expected_parent_version_id into um.write",
        'input.get("expected_parent_version_id")' in src
        and "expected_parent_version_id=expected_parent_version_id" in src))
    results.append(_check(
        "1b StaleWriteError → structured stale_write with the intervening head",
        "except StaleWriteError" in src and '"error": "stale_write"' in src
        and '"authored_by": head.get("authored_by")' in src))
    results.append(_check(
        "1c the rider is optional (None default — existing callers unchanged)",
        'or None' in src.split('expected_parent_version_id = ')[1].split("\n")[0]))

    # 2. compose_save contract
    from services import mcp_composition as m
    results.append(_check("2a compose_save EXISTS", hasattr(m, "compose_save")))
    csrc = inspect.getsource(m.compose_save)
    results.append(_check(
        "2b read-before-write: existing+no-base → base_required (no write)",
        '"error": "base_required"' in csrc
        and csrc.index('"base_required"') < csrc.index("execute_primitive(")))
    results.append(_check(
        "2c base+no-file → not_found",
        '"error": "not_found"' in csrc))
    results.append(_check(
        "2d the write goes through execute_primitive (no second write door)",
        'execute_primitive(' in csrc and '"WriteFile"' in csrc
        and "write_revision(" not in csrc and "um.write" not in csrc))
    results.append(_check(
        "2e stale_write re-shaped with merge guidance; success returns the new head",
        'stale_write' in csrc and '"revision_id": new_rev' in csrc))

    # 3. the tool surface
    with open("mcp_server/server.py", encoding="utf-8") as f:
        server_src = f.read()
    results.append(_check(
        "3a save registered with the base_revision contract taught",
        "async def save(" in server_src and "base_revision" in server_src
        and "stale_write" in server_src))
    results.append(_check(
        "3b all six verbs taught in instructions (rendered, ADR-533 D2)",
        all(f"• {v}" in _rendered_instructions()
            for v in ("open", "remember", "recall", "trace", "save", "share"))))
    results.append(_check(
        "3c save output schema present",
        '"save": {' in server_src and '"revision_id"' in server_src))

    ok = all(results)
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — {sum(results)}/{len(results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
