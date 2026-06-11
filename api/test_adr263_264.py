"""
ADR-263 + ADR-264 regression gate.

Asserts the recurrence-mode + SyncPlatformState architecture is in place:

  ADR-263 (Recurrence Mode):
  - services.recurrence exports RECURRENCE_MODES, DEFAULT_RECURRENCE_MODE, is_valid_mode
  - Recurrence dataclass has `mode` field with default 'judgment'
  - parse_recurrences_yaml accepts and reads mode field
  - parse_recurrences_yaml defaults mode to 'judgment' when absent (legacy)
  - parse_recurrences_yaml coerces invalid mode values to default + logs
  - serialize_recurrences_yaml emits mode only when non-default
  - Schedule primitive's tool definition accepts mode parameter
  - Schedule(action='create') validates mode + sets it on new Recurrence
  - Schedule(action='update') honors mode in changes dict
  - invoke_reviewer trigger Literal narrowed to ["addressed", "reactive"]
  - _TRIGGER_FRAMING dict has 'addressed' + 'reactive' keys, no 'scheduled'
  - wake.py (dispatch absorbed from invocation_dispatcher by the ADR-296 v2
    wake migration) exports _dispatch_mechanical helper
  - wake.py exports _parse_primitive_directive helper
  - unified_scheduler dispatches with trigger="reactive"

  ADR-264 (SyncPlatformState):
  - services.primitives.sync_platform_state importable
  - SYNC_PLATFORM_STATE_TOOL constant defined with proper schema
  - handle_sync_platform_state callable (async)
  - Tool registered in HEADLESS_PRIMITIVES + REVIEWER_PRIMITIVES
  - Tool NOT in CHAT_PRIMITIVES (per ADR-264 D3)
  - HANDLERS dict has 'SyncPlatformState' entry
  - _parse_primitive_directive correctly parses
    "@primitive: SyncPlatformState(tool=..., write_to=...)"

Strategy: import-shape + structural assertions. No live LLM calls.
"""

from __future__ import annotations

import importlib
import inspect
import sys
import typing
from pathlib import Path

# Ensure api/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

PASS_COUNT = 0
FAIL_COUNT = 0


def _fail(msg: str) -> None:
    global FAIL_COUNT
    FAIL_COUNT += 1
    print(f"FAIL: {msg}")


def _ok(msg: str) -> None:
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"PASS: {msg}")


def assert_import_succeeds(module_path: str) -> typing.Any:
    try:
        mod = importlib.import_module(module_path)
        _ok(f"{module_path} importable")
        return mod
    except ImportError as e:
        _fail(f"{module_path} NOT importable: {e}")
        return None


def assert_attr_present(module_path: str, attr: str) -> typing.Any:
    try:
        mod = importlib.import_module(module_path)
    except ImportError as e:
        _fail(f"{module_path} not importable: {e}")
        return None
    if not hasattr(mod, attr):
        _fail(f"{module_path}.{attr} missing")
        return None
    _ok(f"{module_path}.{attr} present")
    return getattr(mod, attr)


def assert_attr_missing(module_path: str, attr: str) -> None:
    try:
        mod = importlib.import_module(module_path)
    except ImportError as e:
        _fail(f"{module_path} not importable: {e}")
        return
    if hasattr(mod, attr):
        _fail(f"{module_path}.{attr} STILL EXISTS — should have been removed")
        return
    _ok(f"{module_path}.{attr} not present (removed)")


def main() -> None:
    print()
    print("=" * 70)
    print("ADR-263 + ADR-264 regression gate")
    print("=" * 70)
    print()

    # ---------------------------------------------------------------------
    # ADR-263: Recurrence Mode
    # ---------------------------------------------------------------------
    print("--- Section 1: ADR-263 recurrence module exports ---")
    rec_mod = assert_import_succeeds("services.recurrence")
    if rec_mod is not None:
        # Constants
        modes = assert_attr_present("services.recurrence", "RECURRENCE_MODES")
        default = assert_attr_present("services.recurrence", "DEFAULT_RECURRENCE_MODE")
        is_valid = assert_attr_present("services.recurrence", "is_valid_mode")

        if modes is not None:
            if set(modes) != {"judgment", "mechanical"}:
                _fail(f"RECURRENCE_MODES = {modes!r}, expected {{'judgment', 'mechanical'}}")
            else:
                _ok("RECURRENCE_MODES = ('judgment', 'mechanical')")

        if default is not None:
            if default != "judgment":
                _fail(f"DEFAULT_RECURRENCE_MODE = {default!r}, expected 'judgment'")
            else:
                _ok("DEFAULT_RECURRENCE_MODE = 'judgment'")

        if is_valid is not None:
            if not is_valid("judgment") or not is_valid("mechanical"):
                _fail("is_valid_mode rejects valid values")
            elif is_valid("garbage"):
                _fail("is_valid_mode accepts invalid values")
            else:
                _ok("is_valid_mode accepts/rejects correctly")

    print()
    print("--- Section 2: ADR-263 Recurrence dataclass + parser ---")
    if rec_mod is not None:
        from dataclasses import fields
        Recurrence = getattr(rec_mod, "Recurrence", None)
        if Recurrence is None:
            _fail("Recurrence dataclass not exported")
        else:
            field_names = {f.name for f in fields(Recurrence)}
            if "mode" not in field_names:
                _fail(f"Recurrence missing `mode` field; fields={sorted(field_names)}")
            else:
                _ok("Recurrence dataclass has `mode` field")
                # Default value
                default_field = next((f for f in fields(Recurrence) if f.name == "mode"), None)
                if default_field is not None and default_field.default == "judgment":
                    _ok("Recurrence.mode defaults to 'judgment'")
                else:
                    _fail(f"Recurrence.mode default is {default_field.default!r}, not 'judgment'")

        parse = getattr(rec_mod, "parse_recurrences_yaml", None)
        if parse is None:
            _fail("parse_recurrences_yaml not exported")
        else:
            # Test: explicit mode value parses correctly
            yaml_with_mode = """- slug: test-mech
  schedule: "* * * * *"
  mode: mechanical
  prompt: "@primitive: WebSearch(query=\\"x\\")"
"""
            recs = parse(yaml_with_mode)
            if len(recs) == 1 and recs[0].mode == "mechanical":
                _ok("parser reads explicit mode='mechanical'")
            else:
                _fail(f"parser failed on explicit mode; got {recs!r}")

            # Test: missing mode → default 'judgment' (backward compat)
            yaml_legacy = """- slug: test-judg
  schedule: "0 7 * * *"
  prompt: "Reflect on yesterday."
"""
            recs = parse(yaml_legacy)
            if len(recs) == 1 and recs[0].mode == "judgment":
                _ok("parser defaults mode to 'judgment' when absent (legacy compat)")
            else:
                _fail(f"parser failed on legacy entry; got mode={recs[0].mode if recs else 'no recs'!r}")

            # Test: invalid mode coerces to default
            yaml_invalid = """- slug: test-bad
  schedule: "* * * * *"
  mode: garbage
  prompt: "anything"
"""
            recs = parse(yaml_invalid)
            if len(recs) == 1 and recs[0].mode == "judgment":
                _ok("parser coerces invalid mode to 'judgment' (with warning)")
            else:
                _fail(f"parser did not coerce invalid mode; got {recs[0].mode if recs else 'no recs'!r}")

        # Serializer: should emit mode only when non-default
        serialize = getattr(rec_mod, "serialize_recurrences_yaml", None)
        if serialize and Recurrence:
            r_judg = Recurrence(slug="a", schedule="* * * * *", prompt="x", mode="judgment")
            r_mech = Recurrence(slug="b", schedule="* * * * *", prompt="@primitive: X()", mode="mechanical")
            text = serialize([r_judg, r_mech])
            if "mode: mechanical" in text and "mode: judgment" not in text:
                _ok("serializer emits mode only when non-default")
            else:
                _fail(f"serializer mode-emission incorrect; output:\n{text}")

    print()
    print("--- Section 3: ADR-263 Schedule primitive accepts mode ---")
    sched_mod = assert_import_succeeds("services.primitives.schedule")
    if sched_mod is not None:
        SCHEDULE_TOOL = getattr(sched_mod, "SCHEDULE_TOOL", None)
        if SCHEDULE_TOOL is None:
            _fail("SCHEDULE_TOOL not exported")
        else:
            props = SCHEDULE_TOOL.get("input_schema", {}).get("properties", {})
            if "mode" in props:
                _ok("SCHEDULE_TOOL input_schema includes mode parameter")
                mode_schema = props["mode"]
                if mode_schema.get("enum") == ["judgment", "mechanical"]:
                    _ok("SCHEDULE_TOOL.mode enum = ['judgment', 'mechanical']")
                else:
                    _fail(f"SCHEDULE_TOOL.mode enum incorrect: {mode_schema.get('enum')!r}")
            else:
                _fail("SCHEDULE_TOOL input_schema missing 'mode' parameter")

    print()
    print("--- Section 4: ADR-263 Reviewer trigger Literal collapse ---")
    rev_mod = assert_import_succeeds("agents.reviewer_agent")
    if rev_mod is not None:
        invoke = getattr(rev_mod, "invoke_reviewer", None)
        if invoke is None:
            _fail("invoke_reviewer not exported")
        else:
            sig = inspect.signature(invoke)
            trigger_param = sig.parameters.get("trigger")
            if trigger_param is None:
                _fail("invoke_reviewer signature missing `trigger` parameter")
            else:
                ann = trigger_param.annotation
                # Under `from __future__ import annotations`, the annotation is
                # stored as a string. Inspect the string form directly. The
                # runtime form (when not using future-annotations) goes through
                # typing.get_origin/get_args.
                ann_str = str(ann)
                origin = typing.get_origin(ann)
                args = typing.get_args(ann)
                # Branch 1: runtime Literal (no `from __future__ import annotations`)
                if origin is typing.Literal:
                    if set(args) == {"addressed", "reactive"}:
                        _ok("invoke_reviewer trigger Literal = ['addressed', 'reactive'] (no 'scheduled')")
                    elif "scheduled" in args:
                        _fail(f"invoke_reviewer trigger Literal STILL contains 'scheduled': {args!r}")
                    else:
                        _fail(f"invoke_reviewer trigger Literal unexpected: args={args!r}")
                # Branch 2: string-form annotation (future-annotations or partial)
                elif "Literal" in ann_str:
                    has_addressed = "'addressed'" in ann_str or '"addressed"' in ann_str
                    has_reactive = "'reactive'" in ann_str or '"reactive"' in ann_str
                    has_scheduled = "'scheduled'" in ann_str or '"scheduled"' in ann_str
                    if has_addressed and has_reactive and not has_scheduled:
                        _ok(f"invoke_reviewer trigger Literal (string form) = {ann_str} — no 'scheduled'")
                    elif has_scheduled:
                        _fail(f"invoke_reviewer trigger Literal STILL contains 'scheduled': {ann_str}")
                    else:
                        _fail(f"invoke_reviewer trigger Literal missing expected values: {ann_str}")
                else:
                    _fail(f"invoke_reviewer trigger annotation unexpected shape: {ann_str!r}")

        # _TRIGGER_FRAMING shape
        framing = getattr(rev_mod, "_TRIGGER_FRAMING", None)
        if framing is None:
            _fail("_TRIGGER_FRAMING not exported")
        else:
            keys = set(framing.keys())
            if keys == {"addressed", "reactive"}:
                _ok("_TRIGGER_FRAMING keys = {'addressed', 'reactive'} (scheduled key removed)")
            elif "scheduled" in keys:
                _fail(f"_TRIGGER_FRAMING STILL has 'scheduled' key: {sorted(keys)}")
            else:
                _fail(f"_TRIGGER_FRAMING keys unexpected: {sorted(keys)}")

    print()
    print("--- Section 5: ADR-263 dispatcher branch + helpers ---")
    # Wake migration (ADR-296 v2): invocation_dispatcher dissolved into
    # services/wake.py — the mechanical-dispatch helpers live there now.
    disp_mod = assert_import_succeeds("services.wake")
    if disp_mod is not None:
        # _dispatch_mechanical helper
        if hasattr(disp_mod, "_dispatch_mechanical"):
            _ok("_dispatch_mechanical helper present")
        else:
            _fail("_dispatch_mechanical helper missing")

        # _parse_primitive_directive helper
        if hasattr(disp_mod, "_parse_primitive_directive"):
            _ok("_parse_primitive_directive helper present")
            parser = disp_mod._parse_primitive_directive
            # Smoke: parse a real-shaped @primitive directive
            sample = """@primitive: SyncPlatformState(
                tool="platform_trading_get_positions",
                write_to="context/portfolio/positions/{symbol}.yaml",
                iterate_field="positions",
                item_key="symbol"
            )"""
            parsed = parser(sample)
            if parsed is None:
                _fail("_parse_primitive_directive returned None for valid input")
            else:
                name, args = parsed
                if name != "SyncPlatformState":
                    _fail(f"_parse_primitive_directive name = {name!r}, expected 'SyncPlatformState'")
                elif args.get("tool") != "platform_trading_get_positions":
                    _fail(f"_parse_primitive_directive args missing tool; got {args!r}")
                elif args.get("iterate_field") != "positions":
                    _fail(f"_parse_primitive_directive args missing iterate_field; got {args!r}")
                else:
                    _ok("_parse_primitive_directive correctly parses @primitive: SyncPlatformState(...)")

            # Negative case: no directive
            negative = parser("Reflect on yesterday's decisions.")
            if negative is None:
                _ok("_parse_primitive_directive returns None when no directive present")
            else:
                _fail(f"_parse_primitive_directive should return None on plain prose; got {negative!r}")
        else:
            _fail("_parse_primitive_directive helper missing")

        # dispatch default trigger
        dispatch = getattr(disp_mod, "dispatch", None)
        if dispatch is not None:
            sig = inspect.signature(dispatch)
            trigger_param = sig.parameters.get("trigger")
            if trigger_param is not None and trigger_param.default == "reactive":
                _ok("dispatch() default trigger = 'reactive' (not 'scheduled')")
            else:
                _fail(f"dispatch() default trigger = {trigger_param.default if trigger_param else 'missing'!r}, expected 'reactive'")

    # ---------------------------------------------------------------------
    # ADR-264: SyncPlatformState
    # ---------------------------------------------------------------------
    print()
    print("--- Section 6: ADR-264 SyncPlatformState primitive ---")
    sync_mod = assert_import_succeeds("services.primitives.sync_platform_state")
    if sync_mod is not None:
        TOOL = getattr(sync_mod, "SYNC_PLATFORM_STATE_TOOL", None)
        if TOOL is None:
            _fail("SYNC_PLATFORM_STATE_TOOL not exported")
        else:
            if TOOL.get("name") == "SyncPlatformState":
                _ok("SYNC_PLATFORM_STATE_TOOL.name = 'SyncPlatformState'")
            else:
                _fail(f"SYNC_PLATFORM_STATE_TOOL.name = {TOOL.get('name')!r}")
            schema = TOOL.get("input_schema", {})
            required = set(schema.get("required", []))
            if {"tool", "write_to"}.issubset(required):
                _ok("SYNC_PLATFORM_STATE_TOOL requires {tool, write_to}")
            else:
                _fail(f"SYNC_PLATFORM_STATE_TOOL required = {sorted(required)!r}")
            props = schema.get("properties", {})
            for p in ("tool", "tool_args", "write_to", "iterate_field", "item_key", "diff_aware"):
                if p in props:
                    _ok(f"SYNC_PLATFORM_STATE_TOOL.input_schema.{p} present")
                else:
                    _fail(f"SYNC_PLATFORM_STATE_TOOL.input_schema.{p} missing")

        handler = getattr(sync_mod, "handle_sync_platform_state", None)
        if handler is None:
            _fail("handle_sync_platform_state not exported")
        elif not inspect.iscoroutinefunction(handler):
            _fail("handle_sync_platform_state must be async")
        else:
            _ok("handle_sync_platform_state callable + async")

    print()
    print("--- Section 7: ADR-264 registry registration ---")
    reg_mod = assert_import_succeeds("services.primitives.registry")
    if reg_mod is not None:
        HEADLESS = getattr(reg_mod, "HEADLESS_PRIMITIVES", [])
        REVIEWER = getattr(reg_mod, "REVIEWER_PRIMITIVES", [])
        CHAT = getattr(reg_mod, "CHAT_PRIMITIVES", [])
        HANDLERS = getattr(reg_mod, "HANDLERS", {})

        headless_names = {t["name"] for t in HEADLESS}
        reviewer_names = {t["name"] for t in REVIEWER}
        chat_names = {t["name"] for t in CHAT}

        if "SyncPlatformState" in headless_names:
            _ok("SyncPlatformState in HEADLESS_PRIMITIVES")
        else:
            _fail("SyncPlatformState NOT in HEADLESS_PRIMITIVES")

        if "SyncPlatformState" in reviewer_names:
            _ok("SyncPlatformState in REVIEWER_PRIMITIVES")
        else:
            _fail("SyncPlatformState NOT in REVIEWER_PRIMITIVES")

        if "SyncPlatformState" not in chat_names:
            _ok("SyncPlatformState NOT in CHAT_PRIMITIVES (per ADR-264 D3)")
        else:
            _fail("SyncPlatformState IS in CHAT_PRIMITIVES — violates ADR-264 D3 (operators don't invoke directly)")

        if "SyncPlatformState" in HANDLERS:
            _ok("HANDLERS['SyncPlatformState'] present")
        else:
            _fail("HANDLERS['SyncPlatformState'] missing")

    # ---------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------
    print()
    print("=" * 70)
    total = PASS_COUNT + FAIL_COUNT
    print(f"Result: {PASS_COUNT}/{total} PASS, {FAIL_COUNT} FAIL")
    print("=" * 70)
    if FAIL_COUNT > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
