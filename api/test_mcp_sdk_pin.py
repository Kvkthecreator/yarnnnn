"""
Regression gate — the MCP SDK stays pinned below 2.0.

Run: `python3 api/test_mcp_sdk_pin.py`

## The outage this defends against (2026-07-29)

`api/requirements.txt` carried `mcp>=1.0.0` — an unpinned MAJOR floor. When the
SDK published 2.0.0, the next `yarnnn-mcp-server` deploy resolved to it and
crash-looped on boot:

    File "/opt/render/project/src/api/mcp_server/server.py", line 49
      from mcp.server.fastmcp import Context, FastMCP
    ModuleNotFoundError: No module named 'mcp.server.fastmcp'

No yarnnn code changed. The deploy that surfaced it (`cf9f170`) was an unrelated
billing commit — the floor simply let an upstream major in, so ANY deploy would
have done it. Verified against the published wheels: 2.0.0 REMOVES
`mcp/server/fastmcp/` (while keeping `mcp/server/auth/`); 1.29.0 has every
module `mcp_server/` imports.

Migrating to the 2.x surface is a genuine port (fastmcp, lowlevel,
transport_security, server.auth) and belongs in its own ADR — not in a
dependency resolution decided by whatever PyPI serves on deploy day.

## Why a gate and not just a comment

The comment explains; only a gate enforces. The failure mode is silent at
author time (nothing breaks locally — the venv already holds a 1.x wheel) and
total at deploy time (the service does not boot). That gap is exactly what a
banned-pattern check is for.
"""

from __future__ import annotations

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQS = os.path.join(REPO, "api", "requirements.txt")

_failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"✓ {label}")
    else:
        print(f"✗ {label}" + (f" — {detail}" if detail else ""))
        _failures.append(label)


src = open(REQS).read()
lines = [
    ln.strip()
    for ln in src.splitlines()
    if ln.strip() and not ln.strip().startswith("#")
]

mcp_lines = [ln for ln in lines if re.match(r"^mcp\b", ln)]

check("requirements.txt declares mcp exactly once", len(mcp_lines) == 1, f"found {mcp_lines}")

spec = mcp_lines[0] if mcp_lines else ""

check(
    "the mcp spec carries an UPPER bound",
    "<" in spec,
    f"`{spec}` is an unpinned floor — the 2026-07-29 outage shape",
)
check(
    "the upper bound excludes the 2.x major",
    "<2" in spec.replace(" ", ""),
    f"`{spec}` would admit mcp 2.x, which removed mcp.server.fastmcp",
)
check(
    "the floor is at least 1.28.0 (the version the code is written against)",
    ">=1.28" in spec.replace(" ", "") or ">=1.29" in spec.replace(" ", ""),
    f"`{spec}`",
)
check(
    "the exact regressed spec is gone from the DIRECTIVES",
    # Scan the parsed requirement lines, not the raw file — the comment above the
    # pin quotes `mcp>=1.0.0` deliberately (naming the regression is why the pin
    # is legible), and a raw substring scan would flag that documentation.
    not any(ln.replace(" ", "") == "mcp>=1.0.0" for ln in lines),
)

# The import that actually crashed in prod must still be the one the code uses —
# if a future port moves off fastmcp, this gate should be revisited deliberately
# (and this check is what forces that conversation).
server_py = os.path.join(REPO, "api", "mcp_server", "server.py")
server_src = open(server_py).read()
check(
    "mcp_server/server.py still imports from mcp.server.fastmcp (1.x surface)",
    "from mcp.server.fastmcp import" in server_src,
    "if this moved, re-evaluate the <2.0.0 pin in its own ADR",
)

print()
if _failures:
    print(f"FAILED {len(_failures)} check(s): {_failures}")
    sys.exit(1)
print("MCP SDK pin gate: all checks passed")
