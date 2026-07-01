"""ADR-321 regression gate — path-native file primitives.

Asserts the post-implementation invariants:
  (a) WriteFile scope enum is {workspace, agent} — no 'context' value.
  (b) No 'domain' param in the WriteFile schema.
  (c) handle_write_file has no scope=='context' branch.
  (d) directory_registry domains re-rooted to operation/ (get_domain_folder).
  (e) conventions.py domain path-builders return operation/ paths.
  (f) QueryKnowledge resolves the operation/ prefix.
  (g) grep gate — zero `context/` workspace-root references in the primitive
      tool DESCRIPTIONS (the LLM-facing surface). (Defensive path-normalization
      comments that *tolerate* a legacy absolute path are allowed.)

Run: python -m pytest api/test_adr321_path_native_primitives.py -q
"""
from __future__ import annotations

import re
from pathlib import Path

API = Path(__file__).parent


def _read(*parts: str) -> str:
    return (API / Path(*parts)).read_text()


# ---------------------------------------------------------------------------
# (a) + (b) WriteFile schema: scope enum {workspace, agent}, no domain param
# ---------------------------------------------------------------------------

def test_writefile_scope_enum_is_two_value():
    from services.primitives.workspace import WRITE_FILE_TOOL

    enum = WRITE_FILE_TOOL["input_schema"]["properties"]["scope"]["enum"]
    assert set(enum) == {"workspace", "agent"}, (
        f"WriteFile scope enum must be {{workspace, agent}} per ADR-321; got {enum}"
    )
    assert "context" not in enum, "scope='context' must be deleted (ADR-321)"


def test_writefile_has_no_domain_param():
    from services.primitives.workspace import WRITE_FILE_TOOL

    props = WRITE_FILE_TOOL["input_schema"]["properties"]
    assert "domain" not in props, (
        "WriteFile must not carry a 'domain' param — ADR-321 made domain context "
        "path-native (operation/{domain}/)."
    )


# ---------------------------------------------------------------------------
# (c) handle_write_file has no scope=='context' branch
# ---------------------------------------------------------------------------

def test_handle_write_file_has_no_context_branch():
    src = _read("services", "primitives", "workspace.py")
    # The deleted branch's signature line must be absent.
    assert 'if scope == "context"' not in src, (
        "handle_write_file must not have a scope=='context' branch (ADR-321 deleted it)."
    )
    # The missing_domain error (only reachable from the deleted branch) must be gone.
    assert "missing_domain" not in src, (
        "The scope='context' missing_domain error path must be deleted."
    )


# ---------------------------------------------------------------------------
# (d) directory_registry re-rooted to operation/
# ---------------------------------------------------------------------------

def test_directory_registry_domains_rooted_at_operation():
    from services.directory_registry import get_domain_folder

    # Known kernel domains resolve under operation/, not context/.
    for domain in ("competitors", "market", "relationships"):
        folder = get_domain_folder(domain)
        assert folder is not None, f"domain '{domain}' should resolve"
        assert folder.startswith("operation/"), (
            f"get_domain_folder('{domain}') must return an operation/ path "
            f"(ADR-321 re-root); got {folder!r}"
        )
        assert not folder.startswith("context/"), (
            f"get_domain_folder('{domain}') must NOT return a context/ path; got {folder!r}"
        )


def test_directory_registry_no_context_path_values():
    src = _read("services", "directory_registry.py")
    # No declared directory may carry a "path": "context/..." value.
    assert '"path": "context/' not in src, (
        "directory_registry must not declare any context/ path (ADR-321 re-root)."
    )


# ---------------------------------------------------------------------------
# (e) conventions.py domain builders return operation/
# ---------------------------------------------------------------------------

def test_conventions_domain_builders_rooted_at_operation():
    from services import conventions

    assert conventions.domain_root("competitors") == "/workspace/operation/competitors"
    assert conventions.domain_entity_path("market", "acme") == "/workspace/operation/market/acme.md"
    assert conventions.domain_synthesis_path("market", "_landscape") == "/workspace/operation/market/__landscape.md"


# ---------------------------------------------------------------------------
# (f) QueryKnowledge resolves operation/ prefix
# ---------------------------------------------------------------------------

def test_query_knowledge_prefix_is_operation():
    src = _read("services", "primitives", "workspace.py")
    # ADR-321: a DOMAIN-scoped QueryKnowledge call resolves under operation/{domain}/,
    # never the dissolved context/ root.
    assert 'domain_folder = get_domain_folder(domain) or f"operation/{domain}"' in src, (
        "QueryKnowledge domain-scoped search must resolve under /workspace/operation/{domain}/ (ADR-321)."
    )
    assert 'prefix = "/workspace/context/"' not in src, (
        "QueryKnowledge handler must not default to the dissolved /workspace/context/ root."
    )
    # ADR-395: the DEFAULT (no-domain) sweep spans the searchable surface (so upload
    # text projections under inbound/uploads/ are reachable), post-filtered to the
    # embed-eligible/searchable roots — not hard-locked to operation/ alone.
    assert "is_searchable_root" in src, (
        "QueryKnowledge default sweep must post-filter to searchable roots (ADR-395)."
    )


# ---------------------------------------------------------------------------
# (g) grep gate — no context/ workspace-root in LLM-facing primitive descriptions
# ---------------------------------------------------------------------------

# Tool-description string keys whose VALUES are LLM-facing. We scan the tool
# dicts' description fields for a `context/` or `/workspace/context/` workspace
# root. Defensive path-normalization in handler CODE (tolerating a legacy
# absolute path passed by the model) is allowed — only the DESCRIPTIONS are gated.

_PRIMITIVE_DESC_FILES = [
    ("services", "primitives", "workspace.py"),
    ("services", "primitives", "read.py"),
    ("services", "primitives", "search.py"),
    ("services", "primitives", "list.py"),
]


def test_no_context_root_in_primitive_descriptions():
    # Collect every tool description from the primitive modules and assert none
    # references context/ as a workspace root.
    from services.primitives import workspace as ws
    from services.primitives import read as rd
    from services.primitives import search as se

    tool_objs = [
        ws.WRITE_FILE_TOOL, ws.SEARCH_FILES_TOOL, ws.LIST_FILES_TOOL,
        ws.QUERY_KNOWLEDGE_TOOL, ws.READ_FILE_TOOL,
        rd.LOOKUP_ENTITY_TOOL,
        se.SEARCH_ENTITIES_TOOL,
    ]
    offenders = []
    pat = re.compile(r"/workspace/context/|(?<![\w.])context/\{?domain")
    for tool in tool_objs:
        desc = tool.get("description", "") or ""
        # also scan nested property descriptions
        blob = desc + " " + " ".join(
            (p.get("description", "") or "")
            for p in tool.get("input_schema", {}).get("properties", {}).values()
        )
        if pat.search(blob):
            offenders.append(tool.get("name", "?"))
    assert not offenders, (
        f"These primitive tool descriptions still reference a context/ workspace "
        f"root (ADR-321 re-root incomplete): {offenders}"
    )
