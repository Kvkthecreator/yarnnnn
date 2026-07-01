"""ADR-392 regression gate — the connector lane (context-in capture→derive).

Connectors are the third context-in transport; ADR-392 makes SyncPlatformState
conform to the ledger-intake axiom (ADR-376/DP32): a platform sync is an
attributed RAW observation that lands in the capture lane
inbound/{platform}/{selector}/{observed_at}.{ext} (retain + attribute), and a
SEPARATE derive act distills understanding into operation/ (cite via
derived_from). Raw-lane mechanism = Option A (inbound/ namespace, ratified
2026-07-01), byte-parallel to the live inbound/mcp/ + inbound/web/ lanes.

Pure-Python structural gate (no DB, no platform APIs). Asserts:
  1. resolve_capture_path lands raw in inbound/{platform}/{selector}/... — never
     operation/, never a locked root.
  2. The capture prefix is `inbound/` (the shared raw lane, sibling to mcp/web).
  3. selector is slugified to one safe path segment (no slashes escape the lane);
     absent selector → the platform `inbox` sublane.
  4. The tool schema carries the `capture` block (the context-in mode signal).
  5. Legacy write_to-direct mode is preserved when `capture` is absent (the
     alpha-trader migration window) — write_to still required in that mode.
  6. Capture mode makes write_to OPTIONAL (the primitive derives the path).
  7. The connector caller is NOT locked from inbound/ (system: writes it) but the
     lane is OUTSIDE operation/ (quarantine — the anti-bloat property).
"""

import sys


def _check(label, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail and not ok else ""))
    return bool(ok)


def main():
    results = []

    from services.primitives.sync_platform_state import (
        resolve_capture_path,
        INBOUND_CAPTURE_PREFIX,
        SYNC_PLATFORM_STATE_TOOL,
    )

    # 1 — raw lands in inbound/{platform}/{selector}/... , never operation/ or a lock
    LOCKED = ("governance/", "constitution/", "persona/", "system/", "operation/")
    adversarial = [
        ("slack", "daily-work"),
        ("notion", "Meeting Notes"),
        ("gmail", "INBOX/Important"),
        ("github", "org/repo"),
        ("slack", "../../governance/_autonomy"),  # path-escape attempt
    ]
    all_safe = True
    detail = ""
    for plat, sel in adversarial:
        p = resolve_capture_path(plat, sel, "2026-07-01T10:00:00Z")
        if not p.startswith(f"inbound/{plat}/"):
            all_safe = False
            detail = f"{plat}/{sel} → {p} (not under inbound/{plat}/)"
            break
        if any(root in p for root in LOCKED):
            all_safe = False
            detail = f"{plat}/{sel} → {p} (leaked into a locked/operation root)"
            break
        # exactly 4 segments: inbound / platform / selector / stamp.ext
        if len(p.split("/")) != 4:
            all_safe = False
            detail = f"{plat}/{sel} → {p} (selector escaped its single segment)"
            break
    results.append(_check(
        "1 raw lands in inbound/{platform}/{selector}/... — never operation/ or a lock",
        all_safe, detail))

    # 2 — the capture prefix is the shared raw lane
    results.append(_check(
        "2 INBOUND_CAPTURE_PREFIX == 'inbound/' (sibling to inbound/mcp/ + inbound/web/)",
        INBOUND_CAPTURE_PREFIX == "inbound/", f"got {INBOUND_CAPTURE_PREFIX!r}"))

    # 3 — selector slugified to one segment; absent → inbox
    p_none = resolve_capture_path("slack", None, "2026-07-01T10:00:00Z")
    p_msgy = resolve_capture_path("slack", "Foo / Bar Baz!", "2026-07-01T10:00:00Z")
    ok3 = (
        p_none == "inbound/slack/inbox/2026-07-01T10:00:00Z.md"
        and p_msgy.split("/")[2] == "foo-bar-baz"
        and len(p_msgy.split("/")) == 4
    )
    results.append(_check(
        "3 selector slugified to one segment; absent selector → the `inbox` sublane",
        ok3, f"none→{p_none} messy→{p_msgy}"))

    # 4 — tool schema carries the capture block
    props = SYNC_PLATFORM_STATE_TOOL.get("input_schema", {}).get("properties", {})
    cap = props.get("capture", {})
    cap_props = cap.get("properties", {})
    ok4 = (
        cap.get("type") == "object"
        and {"platform", "selector", "observed_at", "ext"}.issubset(cap_props.keys())
    )
    results.append(_check(
        "4 tool schema carries the `capture` block (platform/selector/observed_at/ext)",
        ok4))

    # 5 + 6 — legacy write_to required without capture; optional with capture.
    #   Exercised via the handler's validation branch (no DB needed — auth fails
    #   fast AFTER validation would, so we test the validation ordering directly
    #   by asserting the schema still lists write_to required (legacy contract)
    #   AND the docstring/handler treat capture as the relaxation.
    required = set(SYNC_PLATFORM_STATE_TOOL.get("input_schema", {}).get("required", []))
    ok5 = {"tool", "write_to"}.issubset(required)  # legacy contract preserved
    results.append(_check(
        "5 legacy contract preserved: schema still requires {tool, write_to}",
        ok5, f"required={required}"))

    # 6 — capture makes write_to optional: assert the handler's own validation
    #     source treats `capture is None` as the write_to-required gate.
    import inspect
    from services.primitives import sync_platform_state as sps
    src = inspect.getsource(sps.handle_sync_platform_state)
    ok6 = (
        "capture is None and (not write_to" in src  # the relaxed gate
        and "resolve_capture_path(" in src           # capture routes to the lane
    )
    results.append(_check(
        "6 capture mode makes write_to optional + routes through resolve_capture_path",
        ok6))

    # 7 — the connector caller writes inbound/ (system:) and the lane is OUTSIDE
    #     operation/ (the quarantine / anti-bloat property).
    from services.workspace_paths import CALLER_WRITE_POLICY, INBOUND_ROOT
    system_locks = CALLER_WRITE_POLICY.get("system", ())
    ok7 = (
        INBOUND_ROOT == "inbound/"
        and not any(INBOUND_ROOT.startswith(lock) for lock in system_locks)
        and "operation/" not in INBOUND_CAPTURE_PREFIX
    )
    results.append(_check(
        "7 system: writes inbound/ (unlocked) + the lane is OUTSIDE operation/ (quarantine)",
        ok7, f"system_locks={system_locks}"))

    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} ADR-392 assertions pass")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    main()
