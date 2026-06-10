"""ADR-333 — Compose as a Lazy Projection: rewiring the orphaned production half.

Regression gate for the implementation:

  D2 — the eager session-close auto-compose push is RETIRED. `_maybe_auto_compose`
       no longer exists in `services/wake.py`; the dispatch result carries no
       `composed_html_path`; the dispatch path imports no compose helper.
  D3 — `compose_task_output_html` is root-agnostic: an `artifact_kind` param
       selects report vs authored root + default surface_type.
  D4 — `conventions.py` has the `authored_*` family mirroring `report_*`, and
       it is exported in `__all__`.
  D6 — `routes/authored.py` mounts the consumption-pull surface; the composer
       is called with `artifact_kind="authored"` there.

Pure-Python / source-level assertions. No DB, no network, no LLM. The
behavioral claims (paths, signatures, absence of the deleted symbol) are
checked against the actual modules + sources.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parent


# =============================================================================
# D3 + D4 — root-agnostic composer + authored conventions
# =============================================================================


def test_authored_conventions_exist_and_mirror_report_shape():
    from services import conventions as c

    assert c.authored_root("foo") == "/workspace/operation/authored/foo"
    assert c.authored_content_path("foo") == "/workspace/operation/authored/foo/content.md"
    assert c.authored_profile_path("foo") == "/workspace/operation/authored/foo/profile.md"
    # dated-folder family mirrors report_* shape
    assert c.authored_sections_dir("foo").endswith("/sections")
    assert c.authored_sys_manifest_path("foo").endswith("/sys_manifest.json")
    assert c.authored_manifest_path("foo").endswith("/manifest.json")
    # all under the authored root, never the report root
    for fn in (
        c.authored_dated_folder, c.authored_sections_dir,
        c.authored_sys_manifest_path, c.authored_manifest_path,
    ):
        assert fn("foo").startswith("/workspace/operation/authored/foo/")


def test_authored_conventions_exported():
    from services import conventions as c

    for name in (
        "authored_root", "authored_content_path", "authored_profile_path",
        "authored_dated_folder", "authored_sections_dir",
        "authored_sys_manifest_path", "authored_manifest_path",
    ):
        assert name in c.__all__, f"{name} missing from conventions.__all__"


def test_composer_is_root_agnostic():
    from services.compose.task_html import compose_task_output_html

    sig = inspect.signature(compose_task_output_html)
    assert "artifact_kind" in sig.parameters, "composer must accept artifact_kind"
    # default preserves report back-compat for the existing report callers
    assert sig.parameters["artifact_kind"].default == "report"


def test_composer_selects_authored_root_for_authored_kind():
    """The composer body must resolve authored_root for artifact_kind='authored'
    and default the surface to 'article' (per the piece-composition spec)."""
    src = (API_ROOT / "services" / "compose" / "task_html.py").read_text()
    assert "authored_root" in src, "composer must import/use authored_root"
    assert 'artifact_kind == "authored"' in src
    assert '"article"' in src, "authored pieces default to surface_type=article"


# =============================================================================
# D2 — the eager push is retired
# =============================================================================


def test_eager_auto_compose_deleted_from_wake():
    src = (API_ROOT / "services" / "wake.py").read_text()
    assert "_maybe_auto_compose" not in src, (
        "the eager session-close auto-compose must be fully removed (ADR-333 D2)"
    )
    assert "composed_html_path" not in src, (
        "the dispatch result must not carry composed_html_path post-D2"
    )
    # The render service must NOT be driven at session-close: the dispatch
    # body imports no compose helper.
    assert "compose_task_output_html" not in src, (
        "wake.py dispatch must not call the composer (render is pulled, not pushed)"
    )


def test_wake_module_imports_clean():
    """Sanity: the module still imports after the deletion (no dangling refs)."""
    import importlib
    import services.wake as wake
    importlib.reload(wake)  # re-exec to catch import-time breakage
    # public entry points survive the deletion
    assert hasattr(wake, "submit_wake_proposal")
    assert hasattr(wake, "stream_addressed_wake")


# =============================================================================
# D6 — the authored consumption-pull surface
# =============================================================================


def test_authored_route_mounted_with_pull_endpoints():
    from routes import authored

    paths = {r.path for r in authored.router.routes}
    assert "/{slug}" in paths
    assert "/{slug}/render" in paths
    assert "/{slug}/render/{date_folder}" in paths
    assert "/{slug}/export" in paths


def test_authored_route_pulls_authored_kind_composition():
    src = (API_ROOT / "routes" / "authored.py").read_text()
    # every composer call in the pull surface is authored-kind
    assert 'artifact_kind="authored"' in src
    assert "compose_task_output_html" in src


def test_authored_router_included_in_main():
    src = (API_ROOT / "main.py").read_text()
    assert "authored" in src
    assert 'prefix="/api/authored"' in src


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
