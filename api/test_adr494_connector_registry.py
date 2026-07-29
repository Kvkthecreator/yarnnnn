"""
ADR-494 regression gate — the connector registry is SINGULAR, and retirement
is enforced.

Run: `python3 api/test_adr494_connector_registry.py` (prints ✓/✗ and exits
non-zero on failure — the studio/check() gate convention in this repo; pytest
would report a pass even on ✗ lines).

What this defends
-----------------
1. **No drift between the two registries.** The offered set lives in TWO
   languages (a .tsx the browser needs, a .py the API needs). That is a real
   duplication we cannot delete — so it is CI-gated instead: this test PARSES
   the frontend registry and asserts provider-for-provider, status-for-status
   equality. Adding the Nth connector to one side only fails here.
2. **The old hardcoded lists stay dead.** Three separate literals used to
   encode the offered set (`SUPPORTED_PLATFORMS`, the summary emission tuple,
   and the FE array). Two are deleted; a banned-pattern check keeps them from
   growing back.
3. **Retirement actually closes the connect verb** — `is_offered` is false for
   retired providers, and both api-key connect endpoints call the guard.
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.connector_registry import (  # noqa: E402
    CONNECTOR_PROVIDERS,
    CONNECTOR_REGISTRY,
    OFFERED_PROVIDERS,
    is_offered,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FE_REGISTRY = os.path.join(REPO, "web", "lib", "connectors", "registry.tsx")
INTEGRATIONS = os.path.join(REPO, "api", "routes", "integrations.py")

_failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"✓ {label}")
    else:
        print(f"✗ {label}" + (f" — {detail}" if detail else ""))
        _failures.append(label)


def parse_fe_registry() -> dict[str, str]:
    """Extract {provider: status} from the FE registry's entry literals."""
    src = open(FE_REGISTRY).read()
    body = src[src.index("export const CONNECTOR_REGISTRY"):]
    body = body[: body.index("\n];")]
    out: dict[str, str] = {}
    for block in re.finditer(
        r'provider:\s*"([^"]+)".*?status:\s*"([^"]+)"', body, re.DOTALL
    ):
        out[block.group(1)] = block.group(2)
    return out


# --- 1. the two registries agree -------------------------------------------

fe = parse_fe_registry()

check(
    "FE registry parsed (non-empty)",
    len(fe) > 0,
    "the .tsx entry shape changed — update parse_fe_registry",
)
check(
    "FE and BE registries name the SAME providers",
    set(fe) == set(CONNECTOR_REGISTRY),
    f"fe={sorted(fe)} be={sorted(CONNECTOR_REGISTRY)}",
)
check(
    "FE and BE agree on every provider's STATUS",
    all(fe.get(p) == s for p, s in CONNECTOR_REGISTRY.items()),
    f"fe={fe} be={dict(CONNECTOR_REGISTRY)}",
)
check(
    "registry order matches (positional parity)",
    list(fe) == list(CONNECTOR_REGISTRY),
    f"fe={list(fe)} be={list(CONNECTOR_REGISTRY)}",
)

# --- 2. ADR-494 D2: commerce + trading are retired --------------------------

check("commerce is retired", CONNECTOR_REGISTRY.get("commerce") == "retired")
check("trading is retired", CONNECTOR_REGISTRY.get("trading") == "retired")
check("slack/notion/github are live", OFFERED_PROVIDERS == ("slack", "notion", "github"),
      f"offered={OFFERED_PROVIDERS}")
check("is_offered() is False for retired", not is_offered("commerce") and not is_offered("trading"))
check("is_offered() is True for live", all(is_offered(p) for p in OFFERED_PROVIDERS))
check(
    "a retired provider is still RECOGNIZED (readable + disconnectable)",
    "commerce" in CONNECTOR_PROVIDERS and "trading" in CONNECTOR_PROVIDERS,
    "retiring must not orphan an existing connection",
)
check("is_offered() is False for an unknown provider", not is_offered("myspace"))

# --- 3. the deleted literals stay deleted -----------------------------------

integrations_src = open(INTEGRATIONS).read()

check(
    "the hardcoded SUPPORTED_PLATFORMS set literal is gone",
    'SUPPORTED_PLATFORMS = {"slack"' not in integrations_src,
    "the second offered-set source grew back",
)
check(
    "the summary emission tuple literal is gone (ADR-494 D3)",
    'for provider in ("slack", "notion", "github")' not in integrations_src,
    "the third offered-set source grew back — connected commerce/trading "
    "would again never be emitted as active",
)
check(
    "the summary loop iterates the registry",
    "for provider in CONNECTOR_REGISTRY:" in integrations_src,
)
check(
    "both api-key connect endpoints call the retirement guard",
    integrations_src.count("_reject_if_retired(") >= 3,  # def + 2 call sites
    "a retired connector could still be newly connected",
)

# --- 4. the FE derives its offered list, never re-filtering by hand ---------

fe_src = open(FE_REGISTRY).read()
check(
    "FE exports OFFERED_CONNECTORS derived from status",
    "export const OFFERED_CONNECTORS" in fe_src and 'c.status === "live"' in fe_src,
)

section = open(
    os.path.join(REPO, "web", "components", "settings", "ConnectedIntegrationsSection.tsx")
).read()
check(
    "the 'New connection' list reads OFFERED_CONNECTORS",
    "OFFERED_CONNECTORS.filter((m) => !isConnected(m))" in section,
)
check(
    "the connected list still reads the FULL registry",
    "CONNECTOR_REGISTRY.filter(isConnected)" in section,
    "a historical connection to a retired connector must still render",
)

# --- 5. ADR-494 D4: the capture-lane flag has ONE reader --------------------

check(
    "the capture-lane flag is read directly (getCaptureLane now has a caller)",
    "api.integrations.getCaptureLane()" in section,
)
check(
    "the per-signal flag inference is deleted (one source for one fact)",
    "if (s.connector_capture_enabled) setCaptureEnabled(true)" not in section,
)
check(
    "the connected row's freshness is gated on captureEnabled",
    "captureEnabled ? freshness[meta.provider] : undefined" in section,
    "a dormant connector would keep displaying a frozen pre-dormancy signal",
)

# --- 6. ADR-494 D5: settings.pane is ephemeral, normalizers deleted ---------

prefs = open(os.path.join(REPO, "web", "lib", "shell", "surface-preferences.ts")).read()
check(
    "settings.pane is in the EPHEMERAL set (the door opens itself)",
    re.search(r"settings:\s*\['pane',\s*'connector'\]", prefs) is not None,
)
check(
    "workspace-settings.pane is in the EPHEMERAL set",
    re.search(r"'workspace-settings':\s*\['pane'\]", prefs) is not None,
)

account_page = open(os.path.join(REPO, "web", "app", "(authenticated)", "settings", "page.tsx")).read()
ws_page = open(
    os.path.join(REPO, "web", "app", "(authenticated)", "workspace-settings", "page.tsx")
).read()
check(
    "the ADR-491 billing/usage clearing effect is deleted",
    'accountParam.set({ pane: null })' not in account_page,
    "a per-value normalizer is a symptom; ephemeral removes the class",
)
check(
    "the ADR-491 budget→usage normalizer is deleted",
    'wsParam.set({ pane: "usage" })' not in ws_page,
)
check("the account door still defaults to Account", 'defaultPane="account"' in account_page)

print()
if _failures:
    print(f"FAILED {len(_failures)} check(s): {_failures}")
    sys.exit(1)
print("ADR-494 gate: all checks passed")
