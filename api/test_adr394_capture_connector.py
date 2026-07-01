"""ADR-394 regression gate — CaptureConnector (connector fan-out capture).

ADR-394 D1 closes the connector reader gap: SyncPlatformState iterates ONE
tool result as a list (a state mirror), but Slack's get_channel_history takes a
single channel_id — capturing N selected channels means looping N tool calls
over the operator's _watch.yaml selection. CaptureConnector is the new sibling
primitive that does that fan-out; SyncPlatformState stays free of the watch.

Pure-Python + in-memory-fake gate (no DB, no platform APIs). Asserts:
  1. Registration: CaptureConnector in HANDLERS + HEADLESS_PRIMITIVES +
     FREDDIE_PRIMITIVES, NOT CHAT_PRIMITIVES (operators don't invoke capture).
  2. The capability gate derives the platform from CaptureConnector's platform=
     arg (so a disconnected platform skips, not fires-and-fails).
  3. SyncPlatformState is unchanged by the gate extension (its tool= convention
     still resolves).
  4. Fan-out: 2 selected ids → 2 read-tool calls → 2 raws in
     inbound/{platform}/{id}/{observed_at}.md.
  5. The per-selector raw lands in the id's own sub-lane (never operation/,
     never a locked root).
  6. Diff-aware: a byte-identical re-run skips (no revision noise).
  7. Empty selection → success, zero items (watched but nothing in scope — not
     an error).
  8. All-selectors-error → success=False (health signal reflects a dead feed);
     partial error → success=True with the good ids captured.
  9. observed_at is caller-stamped (the primitive never reads the clock).
"""

import asyncio
import sys


def _check(label, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail and not ok else ""))
    return bool(ok)


def _test_registration(results):
    from services.primitives.registry import (
        HANDLERS, HEADLESS_PRIMITIVES, FREDDIE_PRIMITIVES, CHAT_PRIMITIVES,
    )
    from services.primitives.capture_connector import (
        CAPTURE_CONNECTOR_TOOL, handle_capture_connector,
    )

    headless_names = {t["name"] for t in HEADLESS_PRIMITIVES}
    freddie_names = {t["name"] for t in FREDDIE_PRIMITIVES}
    chat_names = {t["name"] for t in CHAT_PRIMITIVES}

    results.append(_check(
        "1a CaptureConnector handler registered",
        HANDLERS.get("CaptureConnector") is handle_capture_connector))
    results.append(_check(
        "1b in HEADLESS_PRIMITIVES + FREDDIE_PRIMITIVES",
        "CaptureConnector" in headless_names and "CaptureConnector" in freddie_names))
    results.append(_check(
        "1c NOT in CHAT_PRIMITIVES (operators don't invoke capture directly)",
        "CaptureConnector" not in chat_names))
    results.append(_check(
        "1d tool schema requires platform + read_tool + selector_arg",
        set(CAPTURE_CONNECTOR_TOOL["input_schema"]["required"])
        == {"platform", "read_tool", "selector_arg"}))


def _test_capability_gate(results):
    from services.capture.lane import _required_platform_for_primitive

    # CaptureConnector: platform derived from platform= arg directly.
    p = _required_platform_for_primitive(
        "CaptureConnector",
        {"platform": "slack", "read_tool": "platform_slack_get_channel_history",
         "selector_arg": "channel_id"},
    )
    results.append(_check(
        "2 capability gate derives platform from CaptureConnector.platform= arg",
        p == "slack", f"got {p!r}"))

    # SyncPlatformState convention untouched.
    p2 = _required_platform_for_primitive(
        "SyncPlatformState", {"tool": "platform_trading_get_positions"},
    )
    results.append(_check(
        "3 SyncPlatformState tool= convention unchanged by the extension",
        p2 == "trading", f"got {p2!r}"))

    # No-platform primitive → None (unchanged).
    p3 = _required_platform_for_primitive("MirrorSignalState", {})
    results.append(_check(
        "3b non-platform primitive → None (no cap gate)", p3 is None, f"got {p3!r}"))


def _test_fanout(results):
    """Fan-out execution against in-memory fakes (no DB, no Slack API)."""
    import services.workspace as ws
    import services.platform_tools as pt
    import services.connector_watch as cw
    from services.primitives import capture_connector as cc

    # In-memory substrate keyed by relative path.
    store: dict[str, str] = {}

    class _FakeUM:
        def __init__(self, db, user_id):
            pass

        async def read(self, filename):
            return store.get(filename)

        async def write(self, filename, content, **kw):
            store[filename] = content

    # Fake platform tool: return a per-channel message list; one channel errors.
    calls: list[dict] = []

    async def _fake_handle_platform_tool(auth, tool_name, tool_input):
        calls.append({"tool": tool_name, "input": dict(tool_input)})
        cid = tool_input.get("channel_id")
        if cid == "C_DEAD":
            return {"success": False, "error": "channel_not_found"}
        return {"success": True, "result": {"messages": [
            {"user": "u", "text": f"hello from {cid}", "ts": "1"}]}}

    async def _fake_read_selected_ids(client, user_id, platform):
        return _SELECTED[:]

    class _Auth:
        user_id = "u1"
        client = object()  # truthy
        caller_identity = "system:capture-slack"

    orig_um = ws.UserMemory
    orig_pt = pt.handle_platform_tool
    orig_ids = cw.read_selected_ids
    ws.UserMemory = _FakeUM
    pt.handle_platform_tool = _fake_handle_platform_tool
    cw.read_selected_ids = _fake_read_selected_ids

    try:
        # --- 4/5: two selected → two calls → two raws in per-id sub-lanes ---
        global _SELECTED
        _SELECTED = ["C_ENG", "C_RANDOM"]
        store.clear()
        calls.clear()
        res = asyncio.run(cc.handle_capture_connector(_Auth(), {
            "platform": "slack",
            "read_tool": "platform_slack_get_channel_history",
            "selector_arg": "channel_id",
            "tool_args": {"limit": 50},
            "observed_at": "2026-07-01T10:00:00Z",
        }))
        two_calls = len(calls) == 2 and all(
            c["input"].get("limit") == 50 for c in calls)
        results.append(_check(
            "4 fan-out: 2 selected ids → 2 read-tool calls (static args merged)",
            two_calls and res["items_processed"] == 2,
            f"calls={len(calls)} items={res['items_processed']}"))

        eng = "inbound/slack/c-eng/2026-07-01T10:00:00Z.md"
        rnd = "inbound/slack/c-random/2026-07-01T10:00:00Z.md"
        landed = eng in store and rnd in store
        results.append(_check(
            "5 each raw lands in inbound/slack/{id}/{observed_at}.md (own sub-lane)",
            landed and len(res["paths_written"]) == 2,
            f"store_keys={list(store.keys())}"))

        LOCKED = ("governance/", "constitution/", "persona/", "system/", "operation/")
        no_leak = all(
            k.startswith("inbound/slack/") and not any(r in k for r in LOCKED)
            for k in store)
        results.append(_check(
            "5b no raw leaked into operation/ or a locked root", no_leak,
            f"keys={list(store.keys())}"))

        # --- 6: diff-aware re-run skips ---
        calls.clear()
        res2 = asyncio.run(cc.handle_capture_connector(_Auth(), {
            "platform": "slack",
            "read_tool": "platform_slack_get_channel_history",
            "selector_arg": "channel_id",
            "tool_args": {"limit": 50},
            "observed_at": "2026-07-01T10:00:00Z",
        }))
        results.append(_check(
            "6 diff-aware: byte-identical re-run writes nothing (2 skipped)",
            len(res2["paths_written"]) == 0 and len(res2["paths_skipped"]) == 2,
            f"written={res2['paths_written']} skipped={res2['paths_skipped']}"))

        # --- 7: empty selection → success, zero items, not an error ---
        _SELECTED = []
        store.clear()
        res3 = asyncio.run(cc.handle_capture_connector(_Auth(), {
            "platform": "slack",
            "read_tool": "platform_slack_get_channel_history",
            "selector_arg": "channel_id",
            "observed_at": "2026-07-01T10:00:00Z",
        }))
        results.append(_check(
            "7 empty selection → success, 0 items (watched, nothing in scope)",
            res3["success"] and res3["items_processed"] == 0))

        # --- 8a: all selectors error → success=False (dead feed) ---
        _SELECTED = ["C_DEAD"]
        store.clear()
        res4 = asyncio.run(cc.handle_capture_connector(_Auth(), {
            "platform": "slack",
            "read_tool": "platform_slack_get_channel_history",
            "selector_arg": "channel_id",
            "observed_at": "2026-07-01T10:00:00Z",
        }))
        results.append(_check(
            "8a all-selectors-error → success=False (health reflects dead feed)",
            res4["success"] is False and res4["items_processed"] == 0
            and res4.get("error"),
            f"res={res4}"))

        # --- 8b: partial error → success=True, good id captured ---
        _SELECTED = ["C_ENG", "C_DEAD"]
        store.clear()
        res5 = asyncio.run(cc.handle_capture_connector(_Auth(), {
            "platform": "slack",
            "read_tool": "platform_slack_get_channel_history",
            "selector_arg": "channel_id",
            "observed_at": "2026-07-01T10:00:00Z",
        }))
        results.append(_check(
            "8b partial error → success=True, the good id captured (1 written)",
            res5["success"] and res5["items_processed"] == 1
            and "inbound/slack/c-eng/2026-07-01T10:00:00Z.md" in store,
            f"res={res5} keys={list(store.keys())}"))

        # --- 9: observed_at is caller-stamped (path carries it verbatim) ---
        _SELECTED = ["C_ENG"]
        store.clear()
        asyncio.run(cc.handle_capture_connector(_Auth(), {
            "platform": "slack",
            "read_tool": "platform_slack_get_channel_history",
            "selector_arg": "channel_id",
            "observed_at": "2026-12-25T00:00:00Z",
        }))
        results.append(_check(
            "9 observed_at caller-stamped (no clock read in the primitive)",
            "inbound/slack/c-eng/2026-12-25T00:00:00Z.md" in store,
            f"keys={list(store.keys())}"))
    finally:
        ws.UserMemory = orig_um
        pt.handle_platform_tool = orig_pt
        cw.read_selected_ids = orig_ids


def _test_seed_at_select(results):
    """Seed-at-select (ADR-394 D2): the connector capture declaration is an
    idempotent function of the operator's selection. Exercises against an
    in-memory _captures.yaml, with materialize_capture_index stubbed."""
    import services.workspace as ws
    import services.capture.scheduling as csched
    from services import connector_watch as cw
    from services.capture.lane import parse_primitive_directive
    from services.capture.declarations import parse_captures_yaml
    from services.conventions import CAPTURES_PATH

    store: dict[str, str] = {}
    rel = CAPTURES_PATH.lstrip("/").removeprefix("workspace/")

    class _FakeUM:
        def __init__(self, db, user_id):
            pass

        async def read(self, filename):
            return store.get(filename)

        async def write(self, filename, content, **kw):
            store[filename] = content

    materialize_calls = []

    async def _fake_materialize(client, user_id, **kw):
        materialize_calls.append(user_id)
        return 1

    orig_um = ws.UserMemory
    orig_mat = csched.materialize_capture_index
    ws.UserMemory = _FakeUM
    csched.materialize_capture_index = _fake_materialize

    try:
        # --- 10: bare workspace, 2 selected → active capture-slack entry ---
        store.clear()
        materialize_calls.clear()
        slug = asyncio.run(cw.seed_connector_capture(None, "u1", "slack", selected_count=2))
        seeded_body = store.get(rel)
        decls = parse_captures_yaml(seeded_body or "")
        by_slug = {d.slug: d for d in decls}
        cap = by_slug.get("capture-slack")
        results.append(_check(
            "10 seed: bare ws + 2 selected → active capture-slack entry + index materialized",
            slug == "capture-slack" and cap is not None and not cap.paused
            and materialize_calls == ["u1"],
            f"slug={slug} decls={list(by_slug)} mat={materialize_calls}"))

        # --- 11: the seeded directive parses to CaptureConnector with our args ---
        parsed = parse_primitive_directive(cap.primitive) if cap else None
        ok_directive = (
            parsed is not None
            and parsed[0] == "CaptureConnector"
            and parsed[1].get("platform") == "slack"
            and parsed[1].get("read_tool") == "platform_slack_get_channel_history"
            and parsed[1].get("selector_arg") == "channel_id"
            and parsed[1].get("tool_args") == {"limit": 50}
        )
        results.append(_check(
            "11 seeded @primitive directive round-trips through the lane parser",
            ok_directive, f"parsed={parsed}"))

        # --- 12: deselect-to-empty → entry PAUSED (kept for legibility) ---
        asyncio.run(cw.seed_connector_capture(None, "u1", "slack", selected_count=0))
        decls2 = parse_captures_yaml(store.get(rel) or "")
        cap2 = {d.slug: d for d in decls2}.get("capture-slack")
        results.append(_check(
            "12 deselect-all → capture-slack PAUSED (kept, not deleted)",
            cap2 is not None and cap2.paused,
            f"cap2={cap2}"))

        # --- 13: idempotent + bundle entries untouched ---
        # Seed a pre-existing bundle capture, then re-seed slack; the bundle
        # entry must survive and slack must be replaced (not duplicated).
        store[rel] = (
            "captures:\n"
            "  - slug: track-positions\n"
            "    schedule: \"@every 1min\"\n"
            "    primitive: |\n"
            "      @primitive: SyncPlatformState(tool=\"platform_trading_get_positions\", write_to=\"operation/x.yaml\")\n"
        )
        asyncio.run(cw.seed_connector_capture(None, "u1", "slack", selected_count=3))
        decls3 = parse_captures_yaml(store.get(rel) or "")
        slugs3 = [d.slug for d in decls3]
        results.append(_check(
            "13 idempotent + bundle entries untouched (track-positions survives, one capture-slack)",
            "track-positions" in slugs3 and slugs3.count("capture-slack") == 1
            and len(slugs3) == 2,
            f"slugs={slugs3}"))

        # --- 14: no-binding platform → no-op (None), file untouched ---
        store[rel] = "captures: []\n"
        before = store[rel]
        slug_n = asyncio.run(cw.seed_connector_capture(None, "u1", "notion", selected_count=2))
        results.append(_check(
            "14 no-binding platform (notion) → no-op, _captures.yaml untouched",
            slug_n is None and store[rel] == before,
            f"slug={slug_n}"))

        # --- 15: unparseable existing file → refuse (never clobber) ---
        store[rel] = "captures: [ this is: not valid yaml : :\n"
        before_bad = store[rel]
        slug_bad = asyncio.run(cw.seed_connector_capture(None, "u1", "slack", selected_count=1))
        results.append(_check(
            "15 unparseable _captures.yaml → refuse to seed (no clobber)",
            slug_bad is None and store[rel] == before_bad,
            f"slug={slug_bad}"))
    finally:
        ws.UserMemory = orig_um
        csched.materialize_capture_index = orig_mat


_SELECTED: list[str] = []


def main():
    results: list[bool] = []
    print("ADR-394 — CaptureConnector (connector fan-out capture)")
    _test_registration(results)
    _test_capability_gate(results)
    _test_fanout(results)
    _test_seed_at_select(results)

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\n  {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
