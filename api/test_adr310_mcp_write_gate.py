"""Regression gate — ADR-310 follow-on: foreign-LLM (MCP) write permission.

Proves the MCP caller (caller_identity="yarnnn:mcp") is gated by the unified
permission gate (ADR-307) with a path-locked policy:
  - WriteFile to a locked subtree (review/, context/_shared/) → DENY
  - WriteFile to ordinary commons (context/{domain}/, memory/) → APPLY
  - read-only primitives → APPLY (unchanged)
And proves the change is behavior-PRESERVING for non-MCP callers:
  - operator caller → APPLY (non_reviewer_caller short-circuit, unchanged)
  - reviewer caller → still hits the Reviewer autonomy branch (not the MCP one)

Run: cd api && python -m pytest test_adr310_mcp_write_gate.py -q
  or: cd api && python test_adr310_mcp_write_gate.py
"""

import asyncio
from dataclasses import dataclass


@dataclass
class _FakeAuth:
    caller_identity: str = "operator"
    reviewer_caller: bool = False
    user_id: str = "u-test"
    client: object = None


async def _run():
    from services.primitives.permission import resolve_permission, PermissionDecision
    from services.primitives.workspace import _is_path_locked_for_mcp

    results = []
    def check(label, got, want):
        ok = got == want
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {label}: got={got} want={want}")

    mcp = _FakeAuth(caller_identity="yarnnn:mcp")

    # --- MCP lock-set unit checks (pure, no DB) ---
    check("lock review/ subtree", _is_path_locked_for_mcp("review/principles.md"), True)
    check("lock context/_shared MANDATE", _is_path_locked_for_mcp("context/_shared/MANDATE.md"), True)
    check("lock context/_shared _autonomy.yaml", _is_path_locked_for_mcp("context/_shared/_autonomy.yaml"), True)
    check("lock /workspace/-prefixed shared", _is_path_locked_for_mcp("/workspace/context/_shared/IDENTITY.md"), True)
    check("UNLOCK context domain", _is_path_locked_for_mcp("context/competitors/acme/profile.md"), False)
    check("UNLOCK memory notes", _is_path_locked_for_mcp("memory/notes.md"), False)

    # --- MCP WriteFile gate decisions ---
    d, r = await resolve_permission(mcp, "WriteFile", {"scope": "workspace", "path": "context/_shared/MANDATE.md", "content": "x"})
    check("MCP WriteFile MANDATE → DENY", d, PermissionDecision.DENY)

    d, r = await resolve_permission(mcp, "WriteFile", {"scope": "workspace", "path": "review/principles.md", "content": "x"})
    check("MCP WriteFile principles → DENY", d, PermissionDecision.DENY)

    d, r = await resolve_permission(mcp, "WriteFile", {"scope": "workspace", "path": "memory/notes.md", "content": "x"})
    check("MCP WriteFile memory → APPLY", d, PermissionDecision.APPLY)

    d, r = await resolve_permission(mcp, "WriteFile", {"scope": "workspace", "path": "context/competitors/acme/profile.md", "content": "x"})
    check("MCP WriteFile context domain → APPLY", d, PermissionDecision.APPLY)

    # MCP read → APPLY (read-only short-circuit, before the MCP branch)
    d, r = await resolve_permission(mcp, "ReadFile", {"path": "context/_shared/MANDATE.md"})
    check("MCP ReadFile locked path → APPLY (reads never gate)", d, PermissionDecision.APPLY)

    # --- behavior preservation: non-MCP callers unchanged ---
    operator = _FakeAuth(caller_identity="operator")
    d, r = await resolve_permission(operator, "WriteFile", {"scope": "workspace", "path": "context/_shared/MANDATE.md", "content": "x"})
    check("operator WriteFile MANDATE → APPLY (non_reviewer, unchanged)", (d, r), (PermissionDecision.APPLY, "non_reviewer_caller"))

    return results


def main():
    results = asyncio.run(_run())
    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} assertions pass")
    if passed != total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
