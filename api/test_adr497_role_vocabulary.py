"""
ADR-497 regression gate — the rendered role vocabulary matches what can exist.

Run: `python3 api/test_adr497_role_vocabulary.py`

## The drift this defends against

`principal_grants.role` has six values in its CHECK constraint. Only some have a
creation path:

| role          | who creates it                                        | live rows |
|---------------|-------------------------------------------------------|-----------|
| owner/member  | signup / invites / shares                             | 12        |
| foreign-llm   | `oauth_provider.py::_ensure_foreign_llm_grant`        | 2         |
| own-agent     | `programs.py::mint_hire_grant` (ADR-414 D5)           | 0 (reachable) |
| a2a, platform | **nothing, anywhere**                                 | 0         |

Before ADR-497 the roster carried full presentation for `a2a` and `platform` —
labels, icons, and one-line kind hints describing principals the system cannot
create. Invisible to operators (no row can render), but it told the next reader
of `AI_ROLES` that four AI kinds exist when two do. That is vocabulary drift:
the surface describing a world the substrate doesn't have.

## The asymmetry this gate encodes

**Display narrows; defensive sweeps stay broad.** The eviction sweep
(`principal_grants.py::cascade_member_ai_connections`) must keep matching
`a2a`/`platform` — if such a row ever came to exist, it must still be cleaned up
on member eviction. Narrowing *that* list would be a real bug. So this gate
asserts BOTH directions: the FE list shrank, the sweep did not.

A reserved seat (ADR-382 persona agents, ADR-401 D1 platform-as-principal) is a
SUBSTRATE fact — it lives in the CHECK constraint and the sweep. It is not a
RENDERED fact until something can mint it.
"""

from __future__ import annotations

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROSTER = os.path.join(REPO, "web", "components", "workspace-concepts", "WorkspaceMembersCard.tsx")
GRANTS = os.path.join(REPO, "api", "services", "principal_grants.py")
PROGRAMS = os.path.join(REPO, "api", "services", "programs.py")
OAUTH = os.path.join(REPO, "api", "mcp_server", "oauth_provider.py")

_failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    if ok:
        print(f"✓ {label}")
    else:
        print(f"✗ {label}" + (f" — {detail}" if detail else ""))
        _failures.append(label)


roster = open(ROSTER).read()
grants = open(GRANTS).read()
programs = open(PROGRAMS).read()
oauth = open(OAUTH).read()

# --- 1. the rendered vocabulary is exactly the creatable AI roles -----------

m = re.search(r"const AI_ROLES = \[([^\]]*)\]", roster)
check("AI_ROLES is parseable", m is not None)
rendered = set(re.findall(r"'([^']+)'", m.group(1))) if m else set()

check(
    "AI_ROLES renders exactly {foreign-llm, own-agent}",
    rendered == {"foreign-llm", "own-agent"},
    f"got {sorted(rendered)}",
)
check(
    "`a2a` carries no presentation in the roster",
    "'a2a'" not in roster and '"a2a"' not in roster,
    "a label for a principal nothing can create",
)
check(
    "`platform` carries no AI-class presentation in the roster",
    "platform: { label:" not in roster,
)

# --- 2. the roles it DOES render are genuinely creatable --------------------

check(
    "foreign-llm has a creation path (MCP OAuth mint)",
    'role="foreign-llm"' in oauth,
)
check(
    "own-agent has a creation path (program activation, ADR-414 D5)",
    "HIRE_GRANT_ROLE" in programs and "own-agent" in programs,
)

# --- 3. the DEFENSIVE sweep stays broad (the asymmetry) --------------------

check(
    "the eviction sweep still matches a2a + platform",
    '"foreign-llm", "a2a", "platform"' in grants,
    "narrowing the sweep would orphan a row that later comes to exist — "
    "display narrows, defensive cleanup does not",
)

# --- 4. the DB keeps the reserved seats ------------------------------------

migrations = os.path.join(REPO, "supabase", "migrations")
constraint_seen = any(
    "own-agent" in open(os.path.join(migrations, f)).read()
    for f in os.listdir(migrations)
    if f.endswith(".sql")
)
check(
    "the role CHECK constraint (substrate) still carries the reserved seats",
    constraint_seen,
    "a reserved seat is a substrate fact; only its RENDERING was removed",
)

# --- 5. no orphaned import left behind -------------------------------------

check(
    "the now-unused Plug icon import is removed",
    "Plug" not in roster,
)

print()
if _failures:
    print(f"FAILED {len(_failures)} check(s): {_failures}")
    sys.exit(1)
print("ADR-497 gate: all checks passed")
