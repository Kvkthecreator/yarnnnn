"""ADR-417 regression gate — the render service is retired; generation is
rented, not owned.

Permanent guard that the render-service teardown stays torn down:
  1. No `RuntimeDispatch` primitive in the registry (tool lists + handler map).
  2. No live import of the deleted modules (`runtime_dispatch`, `render_assets`).
  3. No live `RENDER_SERVICE_URL` / `RENDER_SERVICE_SECRET` reference in service
     or route code (env-var strings are gone; nothing POSTs to the dead service).
  4. no capability carries category=="asset" (the predicate that asserted this
     per-role was deleted with its callers, ADR-464 cleanup — a tautology once
     the source is checked directly).
  5. Compose resolves in-API (`services.compose.engine.compose_html`), no HTTP.
  6. `render_usage` appears only in migrations + historical docs, never live code.

Scope: scans `api/services/`, `api/routes/`, `api/agents/`, `api/jobs/` for the
live code surface; migrations, tests, CHANGELOG, and docs are lineage and exempt.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

API = Path(__file__).resolve().parent
LIVE_DIRS = [API / "services", API / "routes", API / "agents", API / "jobs"]


def _live_py_files():
    for d in LIVE_DIRS:
        if not d.exists():
            continue
        for p in d.rglob("*.py"):
            if any(part in (".venv", "venv", "venv-mcp") for part in p.parts):
                continue
            if p.name.startswith("test_"):
                continue
            yield p


def test_runtime_dispatch_removed_from_registry():
    from services.primitives.registry import CHAT_PRIMITIVES, HEADLESS_PRIMITIVES, HANDLERS

    names = {t["name"] for t in CHAT_PRIMITIVES} | {t["name"] for t in HEADLESS_PRIMITIVES}
    assert "RuntimeDispatch" not in names, "RuntimeDispatch still in a primitive registry list"
    assert "RuntimeDispatch" not in HANDLERS, "RuntimeDispatch still in the handler map"


def test_deleted_modules_gone():
    assert not (API / "services" / "primitives" / "runtime_dispatch.py").exists(), \
        "runtime_dispatch.py must be deleted (ADR-417)"
    assert not (API / "services" / "render_assets.py").exists(), \
        "render_assets.py must be deleted (ADR-417)"


def test_render_service_dir_gone():
    # the whole render/ service tree is decommissioned
    assert not (API.parent / "render").exists(), "render/ service tree must be deleted (ADR-417)"


def test_no_live_render_service_refs():
    offenders = []
    for p in _live_py_files():
        text = p.read_text(encoding="utf-8", errors="ignore")
        for pat in ("RENDER_SERVICE_URL", "RENDER_SERVICE_SECRET"):
            if pat in text:
                offenders.append(f"{p.relative_to(API.parent)}: {pat}")
    assert not offenders, "live render-service env-var references remain:\n" + "\n".join(offenders)


def test_no_import_of_deleted_modules():
    offenders = []
    imp = re.compile(r"(import\s+.*\b(runtime_dispatch|render_assets)\b|from\s+\S*\b(runtime_dispatch|render_assets)\b)")
    for p in _live_py_files():
        for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if imp.search(line):
                offenders.append(f"{p.relative_to(API.parent)}:{i}: {line.strip()}")
    assert not offenders, "live import of a deleted module:\n" + "\n".join(offenders)


def test_asset_capabilities_removed_from_registry():
    from services.orchestration import CAPABILITIES

    for cap in ("chart", "mermaid", "image", "video_render"):
        assert cap not in CAPABILITIES, f"asset capability {cap!r} still in CAPABILITIES (ADR-417)"


def test_compose_is_in_api_no_http():
    # the engine imports and composes without any HTTP dependency
    from services.compose.engine import compose_html, SectionContent

    html = compose_html("# hi\n\ntext", title="t", surface_type="report")
    assert "<html" in html.lower() and "hi" in html
    # a chart-kind section degrades to a table, never an image
    secs = [SectionContent(kind="trend-chart", title="T",
                           content="| M | R |\n|---|---|\n| Jan | 1 |")]
    html2 = compose_html("", title="r", surface_type="report", sections=secs)
    assert "data:image" not in html2 and "matplotlib" not in html2, \
        "chart kind must degrade to a table, not generate an image (ADR-417)"


def test_render_usage_only_in_lineage():
    offenders = []
    for p in _live_py_files():
        if "render_usage" in p.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(str(p.relative_to(API.parent)))
    assert not offenders, "render_usage referenced in live code (dropped by ADR-417 migration 207):\n" + "\n".join(offenders)
