"""
GET/PATCH /api/workspace/file path-normalization regression gate.

The 2026-04-29 alpha-trader-2 E2E observation surfaced asymmetry:
WriteFile(scope="workspace", path="context/_shared/MANDATE.md") writes
to /workspace/context/_shared/MANDATE.md (canonical UserMemory storage),
but a readback via GET /api/workspace/file?path=context/_shared/MANDATE.md
404'd because the route required the absolute form.

Fix (2026-04-30): both GET and PATCH normalize a missing leading slash
by prepending /workspace/, matching services.workspace.UserMemory._full_path.

This test asserts the normalization stays in place.

Strategy: static source check — we don't spin up a FastAPI test client
(slow, fragile, requires DB). We assert that the route handlers contain
the normalization rule. If someone deletes it, this test fails before
the regression hits operators.
"""

from __future__ import annotations

import re
from pathlib import Path


WORKSPACE_ROUTES = Path(__file__).resolve().parent / "routes" / "workspace.py"


def _route_handler_source(handler_name: str) -> str:
    """Extract the source of one handler function from routes/workspace.py."""
    text = WORKSPACE_ROUTES.read_text()
    pattern = re.compile(
        rf"async def {handler_name}\(.*?(?=\n(?:async )?def |\nclass |\Z)",
        re.DOTALL,
    )
    match = pattern.search(text)
    assert match, f"handler {handler_name!r} not found in routes/workspace.py"
    return match.group(0)


def test_get_handler_normalizes_missing_leading_slash():
    """GET /workspace/file must prepend /workspace/ when path is workspace-relative."""
    src = _route_handler_source("get_workspace_file")
    # The fix uses `if not path.startswith("/"):` followed by f"/workspace/{path}"
    assert "not path.startswith" in src, (
        "get_workspace_file lost its leading-slash normalization. "
        "Workspace-relative paths (WriteFile scope='workspace' convention) "
        "will 404 again — the asymmetry the 2026-04-29 observation flagged."
    )
    assert 'f"/workspace/{path}"' in src, (
        "get_workspace_file must prepend /workspace/ to bring relative paths "
        "into the canonical UserMemory._full_path shape."
    )


def test_patch_handler_normalizes_missing_leading_slash():
    """PATCH /workspace/file must apply the same normalization, otherwise
    a writer following the GET-route's relative convention will hit 403
    on the editable-prefixes check (every prefix is absolute)."""
    src = _route_handler_source("edit_workspace_file")
    assert "not raw_path.startswith" in src or "not body.path.startswith" in src, (
        "edit_workspace_file lost its leading-slash normalization — "
        "asymmetric with GET handler. Relative-path writers will 403."
    )
    assert 'f"/workspace/{raw_path}"' in src or 'f"/workspace/{body.path}"' in src, (
        "edit_workspace_file must prepend /workspace/ to align with "
        "the GET handler and UserMemory._full_path convention."
    )


def test_normalization_rule_matches_user_memory_convention():
    """The normalization rule (`/workspace/` prefix) must match
    services.workspace.UserMemory._full_path. If UserMemory's convention
    changes, both routes + this test must update together (singular
    implementation rule 1)."""
    user_memory_src = (
        Path(__file__).resolve().parent / "services" / "workspace.py"
    ).read_text()
    # UserMemory.__init__ sets self._base = "/workspace"
    assert 'self._base = "/workspace"' in user_memory_src, (
        "UserMemory base path changed in services.workspace — update "
        "routes/workspace.py GET + PATCH normalization to match, then "
        "update this test."
    )
