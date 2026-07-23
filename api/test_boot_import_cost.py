#!/usr/bin/env python3
"""
Boot-import cost gate — the API's resident baseline is a budget, not an accident.

WHY THIS EXISTS
The 2026-07-22 OOM (fourth occurrence of the pool-leak class, see
docs/infrastructure/memory-and-client-lifecycle.md) was caused by a leak, but it
was made *lethal* by the baseline: the process booted at ~112 MB against a
512 MiB cap, so it had barely 4x headroom before the first request. Auditing that
baseline found two heavy SDKs imported at MODULE scope on the boot path for
symbols used only inside one function each:

  services/primitives/web_search.py  ->  `from services.anthropic import ...`
      pulls the Anthropic SDK: ~861 `anthropic.types.*` Pydantic model modules.
  routes/mcp.py                      ->  `from mcp.server.auth.provider import ...`
      pulls the MCP SDK (~600 modules) for ONE helper on the OAuth callback path.

Deferring both to call time: 112.2 MB -> 81.2 MB, 2132 -> 931 modules (-28%).

WHAT THIS GATE DEFENDS
That the heavy SDKs stay OFF the import path of `main`. It is easy to
re-introduce the cost by accident — a new module-scope `import anthropic` in any
of the ~28 routers restores all 31 MB silently, and no existing test would notice.

HOW IT CHECKS (measured, not grepped)
Boots the app in a SUBPROCESS with a stub environment and asks the live
`sys.modules` whether each heavy SDK is resident. That is the actual invariant —
a grep for import lines cannot see transitive pulls, which is exactly how these
two survived (neither file names `anthropic` or `mcp` in a way a naive grep for
`^import anthropic` would flag).

The deferred imports are separately proven to still RESOLVE AT CALL TIME by
test_client_lifecycle.py (which drives the Anthropic wrappers) and by the
call-time probe recorded in the ADR-less commit message for this change; a
deferred import that does not resolve is a request-time crash, so "it booted"
is never sufficient evidence on its own.

Run: python3 test_boot_import_cost.py    (NOT pytest — this prints ✓/✗ and exits)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PASS = 0
FAIL = 0


def check(label: str, ok: bool) -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}")


API_ROOT = Path(__file__).resolve().parent

# Heavy SDKs that must NOT be resident after `import main`. Each is imported
# somewhere in the codebase — the requirement is that the import is DEFERRED to
# call time, not that the dependency is absent.
FORBIDDEN_AT_BOOT = [
    # ~861 anthropic.types.* modules. Deferred in
    # services/primitives/web_search.py::_execute_web_search.
    "anthropic",
    # ~600 modules for one OAuth-callback helper. Deferred in
    # routes/mcp.py::mcp_oauth_callback.
    "mcp",
    # Already deferred before this gate existed (services/model_router.py notes
    # "~3s cold import must not tax API boot") — pinned here so it stays that way.
    "litellm",
    # Reachable only via services/embeddings.py, which is not on the boot path.
    "openai",
]

_PROBE = r"""
import sys, json, resource
import main  # noqa: F401  — full app boot, exactly as uvicorn does it
rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024 * 1024)
print("__PROBE__" + json.dumps({
    "modules": len(sys.modules),
    "rss_mb": round(rss_mb, 1),
    "resident": sorted(
        m for m in sys.modules
        if m in ("anthropic", "mcp", "litellm", "openai", "numpy", "tiktoken")
    ),
}))
"""

# A stub env: enough for _validate_environment() to pass. No network is touched —
# nothing here connects, we only import.
_ENV = {
    "PATH": "/usr/bin:/bin:/usr/local/bin",
    "INTEGRATION_ENCRYPTION_KEY": "x",
    "SUPABASE_URL": "http://stub.invalid",
    "SUPABASE_SERVICE_KEY": "x",
    "SUPABASE_ANON_KEY": "x",
}

print("\n── boot import cost: the heavy SDKs stay off the boot path ──")

proc = subprocess.run(
    [sys.executable, "-c", _PROBE],
    cwd=API_ROOT,
    env=_ENV,
    capture_output=True,
    text=True,
    timeout=300,
)

payload = None
for line in proc.stdout.splitlines():
    if line.startswith("__PROBE__"):
        import json

        payload = json.loads(line[len("__PROBE__"):])

if payload is None:
    # Booting the app is itself the precondition. If this fails the gate must be
    # loud rather than silently vacuous — the no-op-scan lesson from the sibling
    # leak gate (a check that measures nothing must never pass).
    check("the app boots under the probe (precondition)", False)
    print(f"\n  stderr tail:\n{proc.stderr[-1500:]}")
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1)

check("the app boots under the probe (precondition)", True)

resident = set(payload["resident"])
for mod in FORBIDDEN_AT_BOOT:
    check(
        f"{mod}: NOT resident after `import main` (deferred to call time)",
        mod not in resident,
    )

# A module-count ceiling catches the general case — a new heavy dependency that
# is not on the FORBIDDEN list above. The measured value at the time of writing
# is 931; the ceiling leaves ordinary headroom for new first-party modules while
# still tripping on an SDK-sized regression (anthropic alone is +1200).
MODULE_CEILING = 1200
check(
    f"module count at boot is under {MODULE_CEILING} "
    f"(measured {payload['modules']}, was 2132 before the deferral)",
    payload["modules"] < MODULE_CEILING,
)

print(f"\n  measured: {payload['rss_mb']} MB RSS, {payload['modules']} modules at boot")
print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
