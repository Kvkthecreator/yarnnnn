#!/usr/bin/env python3
"""ADR-512 — the MCP envelope contract, EXECUTED (not grepped).

Found live 2026-08-03 during the ADR-512/513/465 click-pass: every ADR-512 verb
(`open`, `save`, `share`) failed at the MCP boundary with

    "outputSchema defined but no structured output returned"

while `trace` / `recall` / `remember` worked. The discriminator was
`presentation.affordances.AFFORDANCES`: `_present` returned a BARE DICT for any
tool with no affordance, but the vendored mcp lowlevel handler validates the
return against the advertised `outputSchema` and hard-errors unless the return is
a CallToolResult. `open`/`save`/`share` declare schemas and have no affordance,
so all three were unreachable from every MCP host.

Worse, the failure was NOT read-only: `save` COMMITTED its revision and then
returned an error to the caller (receipt: workspace_file_versions row authored
`yarnnn:mcp:Claude` at 2026-08-03T04:17:03Z for a call the client saw fail).
An AI client that retries on error double-writes.

Why the shipped gates missed it: they exercise the composition handlers directly
in Python and never cross the presentation layer. This gate asserts the ENVELOPE
— the thing the protocol actually validates.

Standalone (sys.exit), per repo convention: `python3 test_adr512_mcp_envelope.py`
"""
from __future__ import annotations

import sys

failures: list[str] = []
checks = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global checks
    checks += 1
    if not cond:
        failures.append(f"{label}{(' — ' + detail) if detail else ''}")


# ── 1. The invariant, stated structurally ────────────────────────────────────
# Any tool advertising an outputSchema MUST get a CallToolResult envelope.
from mcp_server.presentation import affordances as aff  # noqa: E402

import re  # noqa: E402

src = open("mcp_server/server.py").read()
schema_block = re.search(r"_OUTPUT_SCHEMAS = \{(.*?)\n\}", src, re.S)
check("1a. _OUTPUT_SCHEMAS block is parseable", schema_block is not None)
schema_names = set(re.findall(r'\n    "(\w+)": \{', schema_block.group(1))) if schema_block else set()
check("1b. schemas declared for the ADR-512 verbs",
      {"open", "save", "share"} <= schema_names,
      f"declared={sorted(schema_names)}")

affordance_names = set(aff.AFFORDANCES)
schema_only = schema_names - affordance_names
check("1c. the break-class is non-empty (this gate has something to defend)",
      len(schema_only) > 0,
      "if every schema'd tool gained an affordance this gate is vacuous — "
      "keep it anyway, it re-arms the moment a new schema lands")

# ── 2. _present returns an ENVELOPE for schema-only tools (the actual bug) ───
# The `mcp` package is Render-only (not in the local dev env). Section 1 + 5 are
# source-level and always run; sections 2-4 need the real CallToolResult type.
# When mcp is absent we SAY SO rather than silently reporting a green run — an
# unrun gate must never read as a passing one.
try:
    from mcp.types import CallToolResult  # noqa: E402

    from mcp_server import server as srv  # noqa: E402
    _RUNTIME = True
except ModuleNotFoundError:
    _RUNTIME = False
    print("NOTE: `mcp` not installed (Render-only) — sections 2-4 SKIPPED, "
          "not passed. Sections 1 + 5 (source-level) still assert the invariant.")

for name in sorted(schema_only) if _RUNTIME else []:
    out = srv._present(name, {"success": True, "probe": name}, client_name="claude.ai")
    check(f"2.{name}. _present returns CallToolResult (not a bare dict)",
          isinstance(out, CallToolResult),
          f"got {type(out).__name__} — this is the exact live break")
    if isinstance(out, CallToolResult):
        check(f"2.{name}.structured. structuredContent is populated",
              out.structuredContent == {"success": True, "probe": name},
              f"got {out.structuredContent!r}")
        check(f"2.{name}.text. content carries the JSON text channel",
              bool(out.content) and out.content[0].type == "text")
        check(f"2.{name}.meta. no widget pointer for an affordance-less tool",
              out.meta is None,
              "a non-widget host chokes on a pointer it cannot render (ADR-372 D4 amended)")

# ── 3. Affordance-bearing tools keep BOTH channels + their widget gate ──────
for name in sorted(affordance_names) if _RUNTIME else []:
    out = srv._present(name, {"success": True, "probe": name}, client_name="claude.ai")
    check(f"3.{name}. affordance tool still returns CallToolResult",
          isinstance(out, CallToolResult))
    if isinstance(out, CallToolResult):
        check(f"3.{name}.structured. structuredContent populated",
              out.structuredContent == {"success": True, "probe": name})

# ── 4. A tool with NEITHER schema NOR affordance still returns a bare dict ──
if _RUNTIME:
    bare = srv._present("__not_a_real_tool__", {"success": True})
    check("4. no-schema no-affordance tool returns the bare dict (unchanged)",
          bare == {"success": True} and not isinstance(bare, CallToolResult),
          f"got {type(bare).__name__}")

# ── 5. FALSIFIER — the gate must fail if the fix is reverted ────────────────
# Reverting means keying the envelope on the affordance alone. Simulate by
# asking: would the OLD predicate have returned a bare dict for a schema'd tool?
old_predicate_would_break = [n for n in schema_names if n not in affordance_names]
check("5a. falsifier: the pre-fix predicate is provably wrong for >=1 tool",
      len(old_predicate_would_break) > 0,
      f"tools the old code broke: {sorted(old_predicate_would_break)}")

# 5b runs everywhere (no mcp import): the early-return in _present must consult
# the SCHEMA registry, not the affordance alone. Reverting to
# `if affordance is None: return result` turns this red.
present_body = re.search(r"def _present\(.*?\n(.*?)\n\ndef ", src, re.S)
check("5b. _present body is parseable", present_body is not None)
if present_body:
    body = present_body.group(1)
    early_return = re.search(r"if affordance is None(.*?):\s*\n\s*return result", body)
    check("5c. the early-return exists", early_return is not None)
    if early_return:
        check("5d. the early-return is gated on _OUTPUT_SCHEMAS too (THE FIX)",
              "_OUTPUT_SCHEMAS" in early_return.group(1),
              "a bare `if affordance is None: return result` re-arms the live break — "
              "every schema'd tool would fail at every MCP host")

print(f"ADR-512 MCP envelope gate: {checks - len(failures)}/{checks} passed")
for f in failures:
    print(f"  FAIL {f}")
sys.exit(1 if failures else 0)
