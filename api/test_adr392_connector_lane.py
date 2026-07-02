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

    # --- ADR-392 D7 (Phase 2 Select) — the connector-watch declaration ---
    results += _test_connector_watch()

    # --- ADR-392 D8 — the retention-window dial + derive-then-prune GC ---
    results += _test_retention()

    # --- ADR-392 D9 — OAuth write-scope pre-provisioning (write-ready guard) ---
    results += _test_write_ready()

    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} ADR-392 assertions pass")
    if passed != total:
        sys.exit(1)


def _test_connector_watch():
    """D7 — the connector-watch declaration substrate + selected-id consumer.

    Exercises the store→read round-trip against an in-memory UserMemory fake, so
    the declaration path, serialization, and the `selected: true` filter (the
    Phase-3 capture consumer) are all proven without a DB.
    """
    import asyncio
    import services.workspace as ws
    from services import connector_watch as cw

    out = []

    # 8 — declaration path is the kernel-universal machine-parsed convention
    path = cw.watch_declaration_path("Slack")
    out.append(_check(
        "8 watch declaration path = operation/_connectors/{platform}/_watch.yaml",
        path == "operation/_connectors/slack/_watch.yaml", f"got {path}"))

    # In-memory UserMemory fake (files keyed by relative path).
    store = {}

    class _FakeUM:
        def __init__(self, db, user_id):
            pass

        async def write(self, filename, content, **kw):
            store[filename] = content
            return True

        async def read(self, filename):
            return store.get(filename)

    original = ws.UserMemory
    ws.UserMemory = _FakeUM
    try:
        selections = [
            {"id": "C001", "name": "#daily-work", "selected": True},
            {"id": "C002", "name": "#random", "selected": False},
            {"id": "C003", "name": "#eng", "selected": True},
            {"id": "", "name": "junk", "selected": True},  # dropped (no id)
        ]
        asyncio.run(cw.write_selection(None, "u1", "slack", selections))

        # 9 — round-trip: read_selection returns the full set minus the no-id row
        read_back = asyncio.run(cw.read_selection(None, "u1", "slack"))
        out.append(_check(
            "9 write→read round-trip preserves selections (no-id row dropped)",
            len(read_back) == 3 and {s["id"] for s in read_back} == {"C001", "C002", "C003"},
            f"read_back={read_back}"))

        # 10 — the Phase-3 consumer: only `selected: true` ids
        ids = asyncio.run(cw.read_selected_ids(None, "u1", "slack"))
        out.append(_check(
            "10 read_selected_ids returns only selected:true (the capture consumer)",
            set(ids) == {"C001", "C003"}, f"ids={ids}"))

        # 11 — empty declaration reads as [] (never raises)
        empty = asyncio.run(cw.read_selection(None, "u1", "notion"))
        out.append(_check(
            "11 unset declaration reads as [] (never raises)", empty == []))
    finally:
        ws.UserMemory = original

    return out


def _test_write_ready():
    """D9 — every kernel-universal write_{platform} capability has a write-ready
    OAuth connection (the connect flow requests write scope up front).

    The load-bearing guard: if a provider ships a write_{platform} capability but
    read-only OAuth scopes, the capability is gate-available yet fails at execution
    — a re-auth trap. This fails loudly instead.
    """
    from integrations.core.oauth import connection_is_write_ready, OAUTH_CONFIGS
    from services.orchestration import CAPABILITIES

    out = []

    # 19 — the three first-party providers are write-ready
    ok19 = all(connection_is_write_ready(p) for p in ("slack", "notion", "github"))
    out.append(_check(
        "19 slack/notion/github connections are write-ready by construction", ok19))

    # 20 — cross-check: every write_{platform} kernel capability whose provider has
    #      an OAuth config is write-ready (the regression guard for new providers).
    offenders = []
    for cap_name, cap in CAPABILITIES.items():
        if not cap_name.startswith("write_"):
            continue
        req = cap.get("platform_connection_requirement")
        if not req:
            continue
        provider = req.get("platform")
        if provider not in OAUTH_CONFIGS:
            continue  # API-key providers (commerce/trading) — no OAuth scope model
        if not connection_is_write_ready(provider):
            offenders.append((cap_name, provider))
    out.append(_check(
        "20 every OAuth write_{platform} capability has a write-ready connection",
        not offenders, f"offenders={offenders}"))

    return out


def _test_retention():
    """D8 — the retention dial (default/override/pricing-clamp) + derive-then-prune.

    Uses an in-memory UserMemory fake seeded with a mix of fresh/stale and
    cited/uncited raw files; asserts only stale+cited connector raws are pruned,
    mcp/web siblings are untouched, and the pricing clamp works.
    """
    import asyncio
    import services.workspace as ws
    from services import connector_retention as cr

    out = []

    # 12 — default when unset
    store = {}

    class _FakeUM:
        def __init__(self, db, user_id):
            pass

        async def read(self, filename):
            return store.get(filename)

        async def write(self, filename, content, **kw):
            store[filename] = content
            return True

        async def delete(self, filename):
            store.pop(filename, None)
            return True

        async def list(self, relative_path="", recursive=False):
            prefix = relative_path if relative_path.endswith("/") else relative_path + "/"
            return [
                k[len(prefix):] for k in store
                if k.startswith(prefix) and k != prefix
            ]

    original = ws.UserMemory
    ws.UserMemory = _FakeUM
    try:
        # 12 — unset → default 30
        d = asyncio.run(cr.resolve_retention_days(None, "u1"))
        out.append(_check("12 retention default = 30 when unset", d == 30, f"got {d}"))

        # 13 — operator override read from governance/_retention.yaml
        store[cr.RETENTION_POLICY_PATH] = "retention_days: 7\n"
        d7 = asyncio.run(cr.resolve_retention_days(None, "u1"))
        out.append(_check("13 operator override retention_days: 7 honored", d7 == 7, f"got {d7}"))

        # 14 — pricing-seam clamp: tier_max caps the declared value (ADR-391 seam)
        store[cr.RETENTION_POLICY_PATH] = "retention_days: 90\n"
        d_clamped = asyncio.run(cr.resolve_retention_days(None, "u1", tier_max_days=30))
        out.append(_check(
            "14 pricing-seam clamp: declared 90 clamped to tier_max 30",
            d_clamped == 30, f"got {d_clamped}"))

        # --- evidence-bounded GC (ADR-394 D4 / ADR-401 D4 polarity) ---
        store.clear()
        # now = 2026-07-01; window 30d. Build the raw lane.
        NOW = "2026-07-01T00:00:00Z"
        # stale (60d old) + CITED → KEEP forever (evidence in a provenance chain)
        stale_cited = "inbound/slack/daily-work/2026-05-02T00:00:00Z.md"
        # stale (60d) + UN-cited → PRUNE (nothing engaged it — presumed noise)
        stale_uncited = "inbound/slack/random/2026-05-02T00:00:00Z.md"
        # fresh (5d) + un-cited → keep (within window)
        fresh_uncited = "inbound/slack/eng/2026-06-26T00:00:00Z.md"
        # an mcp sibling, stale + un-cited → MUST NOT be touched (not connector lane)
        mcp_sibling = "inbound/mcp/claude.ai/2026-05-02T00:00:00Z.md"
        for p in (stale_cited, stale_uncited, fresh_uncited, mcp_sibling):
            store[p] = "raw"

        cited = {
            f"/workspace/{stale_cited}",
        }
        res = asyncio.run(cr.prune_raw_lane(
            None, "u1", NOW, retention_days=30, cited_paths=cited,
        ))

        out.append(_check(
            "15 evidence-bounded GC: only stale+UN-cited connector raw pruned (1)",
            res["pruned"] == 1 and stale_uncited not in store,
            f"res={res} stale_uncited_present={stale_uncited in store}"))
        out.append(_check(
            "16 stale-but-CITED raw KEPT (evidence — derived_from/trace chain intact)",
            stale_cited in store and res["kept_cited"] == 1,
            f"res={res} stale_cited_present={stale_cited in store}"))
        out.append(_check(
            "17 fresh raw KEPT (within window) + mcp/web siblings untouched",
            fresh_uncited in store and mcp_sibling in store and res["scanned"] == 3,
            f"scanned={res['scanned']} (should exclude the mcp sibling)"))

        # 18 — fail-safe: cited_paths=None (unknown citation state) prunes NOTHING
        store[stale_uncited] = "raw"  # restore
        res_none = asyncio.run(cr.prune_raw_lane(
            None, "u1", NOW, retention_days=30, cited_paths=None,
        ))
        out.append(_check(
            "18 fail-safe: cited_paths=None prunes nothing (unknown ≠ un-cited)",
            res_none["pruned"] == 0 and stale_uncited in store))
    finally:
        ws.UserMemory = original

    return out


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    main()
