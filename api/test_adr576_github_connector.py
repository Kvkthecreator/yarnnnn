"""ADR-576 regression gate — the GitHub connector reads, and the selection binds.

Pure-Python structural + behavioral gate (no DB, no GitHub API). The aperture
assertions DRIVE the real handler through a fake auth + monkeypatched client,
because the defect this gate exists to prevent was invisible to source
inspection: `list_repos` looked correct in isolation and simply never consulted
the selection.

Asserts:
  1. The dead write path is gone (create_issue absent from the GitHub client).
  2. The four other unreferenced client methods are gone.
  3. GitHub's OAuth scopes contain no `repo` write scope.
  4. WRITE_SCOPE_MARKERS["github"] is None AND no write_github capability exists.
  5. BIDIRECTIONAL D9 — derived from both registries, no hardcoded provider list.
  6. list_repos honors a declared selection; unrestricted when none.
  7. A repo-addressed tool REFUSES an unselected repo, legibly.
  8. GitHub resolves in PLATFORM_REGISTRY and _test_read has a GitHub branch.
"""

import asyncio
import inspect
import sys


def _check(label, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail and not ok else ""))
    return bool(ok)


# ---------------------------------------------------------------------------
# D1 — the dead write path is deleted, the scope narrows
# ---------------------------------------------------------------------------

def _test_dead_write_path():
    from integrations.core import github_client as gc

    out = []
    client_cls = gc.GitHubAPIClient

    # 1 — create_issue is gone. Checked on the CLASS, not the module source, so
    #     a re-added method is caught however it is spelled.
    out.append(_check(
        "1 create_issue absent from GitHubClient (the unwired write path)",
        not hasattr(client_cls, "create_issue")))

    # 2 — the four other unreferenced methods are gone.
    dead = ["get_user", "get_issue_comments", "list_pull_requests", "get_languages"]
    still_there = [m for m in dead if hasattr(client_cls, m)]
    out.append(_check(
        "2 the four other dead client methods are absent",
        not still_there, f"still present={still_there}"))

    return out


def _test_scope_narrowed():
    from integrations.core.oauth import OAUTH_CONFIGS, WRITE_SCOPE_MARKERS
    from services.orchestration import CAPABILITIES

    out = []
    scopes = list(OAUTH_CONFIGS["github"].scopes)

    # 3 — no `repo` write scope. Exact-match: `repo:status` and `public_repo`
    #     are READ scopes that merely contain the substring, so a substring test
    #     here would fail against correct output.
    out.append(_check(
        "3 github OAuth scopes carry no bare `repo` write scope",
        "repo" not in scopes, f"scopes={scopes}"))

    # read:user is still required by the callback (login/id/avatar).
    out.append(_check(
        "3b read:user retained (the callback populates github_user_id from it)",
        "read:user" in scopes, f"scopes={scopes}"))

    # 4 — no write marker, and no write capability.
    out.append(_check(
        "4 WRITE_SCOPE_MARKERS['github'] is None (no write capability ships)",
        WRITE_SCOPE_MARKERS.get("github", "MISSING") is None))
    out.append(_check(
        "4b no write_github capability is declared",
        "write_github" not in CAPABILITIES))

    return out


def _test_bidirectional_d9():
    """5 — ADR-576 D1.a: a write capability and its write scope imply each other.

    Derived from BOTH registries. The replaced ADR-392 check 19 hardcoded
    ('slack','notion','github') and so asserted its own conclusion — a provider
    list baked into an assertion is the shape that let the over-broad `repo`
    scope survive.
    """
    from integrations.core.oauth import (
        OAUTH_CONFIGS, WRITE_SCOPE_MARKERS, connection_is_write_ready,
    )
    from services.orchestration import CAPABILITIES

    out = []

    write_providers = set()
    for cap_name, cap in CAPABILITIES.items():
        if not cap_name.startswith("write_"):
            continue
        req = cap.get("platform_connection_requirement") or {}
        provider = req.get("platform")
        if provider and provider in OAUTH_CONFIGS:
            write_providers.add(provider)

    # Forward: every OAuth write capability is write-ready.
    forward = [p for p in sorted(write_providers) if not connection_is_write_ready(p)]
    out.append(_check(
        "5 forward — every OAuth write_{platform} capability is write-ready",
        not forward, f"offenders={forward}"))

    # Reverse (the half that was structurally blind): every declared write scope
    # marker has a matching write capability.
    reverse = [
        p for p, markers in sorted(WRITE_SCOPE_MARKERS.items())
        if markers is not None and p not in write_providers
    ]
    out.append(_check(
        "5b reverse — no write scope is held without a write capability",
        not reverse, f"scope-without-capability={reverse}"))

    return out


# ---------------------------------------------------------------------------
# D2 — the selection binds tool reach (driven, not inspected)
# ---------------------------------------------------------------------------

class _FakeAuth:
    def __init__(self, user_id="u1"):
        self.user_id = user_id
        self.client = object()  # never dereferenced — read_selected_ids is patched


def _drive_github(monkey_selection, tool, tool_input, repos_returned=None):
    """Call the REAL _handle_github_tool with the selection + client patched."""
    from services import platform_tools as pt
    from integrations.core import github_client as gc
    from integrations.core import tokens as tk
    import services.connector_watch as cw
    import services.platform_credentials as pc

    async def fake_read_selected_ids(client, user_id, platform):
        return list(monkey_selection)

    class _FakeClient:
        async def list_repos(self, token, max_repos=50, **kw):
            return list(repos_returned or [])

        async def get_repo_metadata(self, token, repo):
            return {"full_name": repo, "reached": True}

    orig = {
        "sel": cw.read_selected_ids,
        "cred": pc.resolve_platform_credential,
        "tok": tk.get_token_manager,
        "cli": gc.get_github_client,
    }
    cw.read_selected_ids = fake_read_selected_ids
    pc.resolve_platform_credential = lambda auth, p: {"credentials_encrypted": "x"}
    tk.get_token_manager = lambda: type("_T", (), {"decrypt": lambda s, v: "tok"})()
    gc.get_github_client = lambda: _FakeClient()
    try:
        return asyncio.get_event_loop().run_until_complete(
            pt._handle_github_tool(_FakeAuth(), tool, tool_input)
        )
    finally:
        cw.read_selected_ids = orig["sel"]
        pc.resolve_platform_credential = orig["cred"]
        tk.get_token_manager = orig["tok"]
        gc.get_github_client = orig["cli"]


def _test_selection_binds():
    out = []

    all_repos = [
        {"full_name": "Kvk/yarnnnn", "private": False},
        {"full_name": "Kvk/secret-side-project", "private": True},
    ]

    # 6 — a DECLARED selection filters list_repos. The pre-576 code returned
    #     both repos here, including the explicitly deselected private one.
    res = _drive_github(["Kvk/yarnnnn"], "list_repos", {}, repos_returned=all_repos)
    names = [r.get("name") for r in (res.get("result", {}).get("repos") or [])]
    out.append(_check(
        "6 list_repos returns ONLY selected repos when a selection exists",
        res.get("success") and names == ["Kvk/yarnnnn"], f"names={names}"))
    out.append(_check(
        "6b the deselected private repo is NOT returned",
        "Kvk/secret-side-project" not in names, f"names={names}"))

    # 6c — EMPTY selection means UNRESTRICTED, never deny-all. An operator who
    #      never opened the pane must not have a boundary spring shut on them.
    res_open = _drive_github([], "list_repos", {}, repos_returned=all_repos)
    open_names = [r.get("name") for r in (res_open.get("result", {}).get("repos") or [])]
    out.append(_check(
        "6c empty selection = unrestricted (both repos returned)",
        res_open.get("success") and len(open_names) == 2, f"names={open_names}"))

    # 7 — a repo-addressed tool REFUSES an unselected repo, and the refusal is
    #     legible (names the aperture + where to widen it), never a silent empty.
    denied = _drive_github(
        ["Kvk/yarnnnn"], "get_repo_metadata", {"repo": "Kvk/secret-side-project"})
    err = str(denied.get("error", ""))
    out.append(_check(
        "7 an unselected repo is refused (not silently reached)",
        denied.get("success") is False and not denied.get("result"),
        f"got={denied}"))
    out.append(_check(
        "7b the refusal is legible — names the in-scope set and the pane",
        "aperture" in err.lower() and "Kvk/yarnnnn" in err and "SCOPE" in err,
        f"error={err!r}"))

    # 7c — a SELECTED repo still passes through (the guard is a boundary, not a
    #      blanket denial). Falsifies "everything is refused".
    allowed = _drive_github(
        ["Kvk/yarnnnn"], "get_repo_metadata", {"repo": "Kvk/yarnnnn"})
    out.append(_check(
        "7c a selected repo is still reachable",
        allowed.get("success") and (allowed.get("result") or {}).get("reached"),
        f"got={allowed}"))

    # 7d — case-insensitive: GitHub full names are case-insensitive, so a model
    #      echoing different casing must not be spuriously refused.
    cased = _drive_github(
        ["Kvk/yarnnnn"], "get_repo_metadata", {"repo": "kvk/YARNNNN"})
    out.append(_check(
        "7d aperture comparison is case-insensitive",
        cased.get("success") is True, f"got={cased}"))

    return out


# ---------------------------------------------------------------------------
# D3 — the probe reads
# ---------------------------------------------------------------------------

def _test_validation_registry():
    from integrations.platform_registry import get_platform_config
    from integrations import validation

    out = []

    cfg = get_platform_config("github")
    out.append(_check(
        "8 github resolves in PLATFORM_REGISTRY (the Unknown-provider cause)",
        bool(cfg)))

    # 8b — the registry key alone is NOT enough: without a read branch the probe
    #      clears the unknown guard and then reports a skipped read.
    out.append(_check(
        "8b validation has a _test_github_read branch",
        hasattr(validation, "_test_github_read")))

    src = inspect.getsource(validation._test_read)
    out.append(_check(
        "8c _test_read dispatches to it for provider == 'github'",
        "github" in src and "_test_github_read" in src))

    # 8d — the fossil MCP-gateway fields are NOT copied into the new entry.
    out.append(_check(
        "8d the github entry declares no ADR-050 mcp_server/transport fossil",
        not (cfg or {}).get("mcp_server") and not (cfg or {}).get("transport")))

    return out


def main():
    results = []
    results += _test_dead_write_path()
    results += _test_scope_narrowed()
    results += _test_bidirectional_d9()
    results += _test_selection_binds()
    results += _test_validation_registry()

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\n{passed}/{total} ADR-576 assertions pass")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
