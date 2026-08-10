"""MCP write-path signature gate — the 2026-08-10 P0's regression test.

THE BUG CLASS: a mutating primitive passed a kwarg (`author_identity_uuid`)
that `UserMemory.write` did not accept. Every WriteFile/EditFile workspace
write — MCP save/edit AND the desk chat lane — died at the signature the
moment the identity-stamp deploy landed. Kernel-level tests missed it because
they stubbed `execute_primitive`; the pre-ship check missed it because it
grepped the file and matched the SIBLING class's signature
(`AgentWorkspace.write` accepts the kwarg; `UserMemory.write` didn't).

This gate exercises the REAL call chain — handler → real `UserMemory.write`
signature — with a foreign-principal identity attached, stubbing ONLY the DB
boundary (`write_revision` / head-read / content-read / activity emit). A
signature mismatch anywhere between the handler and the substrate call is a
TypeError here, not a prod incident.

Plus a standing AST sweep: every kwarg any call site in
`services/primitives/workspace.py` passes to `um.write` / `ws.write` /
`write_revision` must exist in the callee's signature — so the next stamp-like
change cannot ship a leaked kwarg to ANY of the three, whichever class it
targets.

Run: python3 test_mcp_write_path_signatures.py  (from api/)
"""

import ast
import asyncio
import inspect
import sys
import types


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def main():
    results = []
    import services.workspace as w
    import services.authored_substrate as asub
    import services.primitives.workspace as wsprim

    # ── 1. signature parity: both write classes accept the identity stamp ─────
    sig_um = set(inspect.signature(w.UserMemory.write).parameters)
    sig_aw = set(inspect.signature(w.AgentWorkspace.write).parameters)
    sig_wr = set(inspect.signature(asub.write_revision).parameters)
    results.append(_check(
        "1 UserMemory.write + AgentWorkspace.write + write_revision all accept author_identity_uuid",
        "author_identity_uuid" in sig_um
        and "author_identity_uuid" in sig_aw
        and "author_identity_uuid" in sig_wr))

    # ── 2. AST sweep: no call site passes a kwarg its callee lacks ────────────
    src = open("services/primitives/workspace.py").read()
    tree = ast.parse(src)
    mismatches = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        kwargs = {k.arg for k in node.keywords if k.arg}
        if node.func.attr == "write":
            target = getattr(node.func.value, "id", None)
            callee = {"um": sig_um, "ws": sig_aw}.get(target)
            if callee and (kwargs - callee):
                mismatches.append((target, node.lineno, sorted(kwargs - callee)))
        elif node.func.attr == "write_revision" or (
            isinstance(node.func, ast.Attribute) is False and False
        ):
            if kwargs - sig_wr:
                mismatches.append(("write_revision", node.lineno, sorted(kwargs - sig_wr)))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "write_revision":
            kwargs = {k.arg for k in node.keywords if k.arg}
            if kwargs - sig_wr:
                mismatches.append(("write_revision", node.lineno, sorted(kwargs - sig_wr)))
    results.append(_check(
        "2 every write call site's kwargs exist in its callee's signature",
        not mismatches, f"{mismatches}"))

    # ── 3. LIVE chain: real handler → real UserMemory.write, DB stubbed ───────
    captured: list[dict] = []

    def fake_write_revision(client, **kwargs):
        captured.append(kwargs)
        return types.SimpleNamespace(id="rev-new")

    async def fake_read(self, path):
        return "before ANCHOR after"

    async def fake_activity(*a, **k):
        return None

    saved = (asub.write_revision, asub.read_head_revision_id,
             w.UserMemory.read, wsprim._emit_workspace_activity)
    asub.write_revision = fake_write_revision
    asub.read_head_revision_id = lambda *a, **k: "head-1"
    w.UserMemory.read = fake_read
    wsprim._emit_workspace_activity = fake_activity
    try:
        auth = types.SimpleNamespace(
            user_id="u-kvk", client=None, agent=None,
            caller_identity="yarnnn:mcp:claude.ai",
        )
        save_res = asyncio.run(wsprim.handle_write_file(auth, {
            "scope": "workspace", "path": "operation/probe.md",
            "content": "hello", "mode": "overwrite",
        }))
        edit_res = asyncio.run(wsprim.handle_edit_file(auth, {
            "scope": "workspace", "path": "operation/probe.md",
            "old_string": "ANCHOR", "new_string": "REPLACED",
        }))
    finally:
        (asub.write_revision, asub.read_head_revision_id,
         w.UserMemory.read, wsprim._emit_workspace_activity) = saved

    results.append(_check(
        "3a WriteFile succeeds through the REAL UserMemory.write with a foreign identity",
        save_res.get("success") is True,
        f"got {save_res.get('error')}: {str(save_res.get('message'))[:90]}" if not save_res.get("success") else ""))
    results.append(_check(
        "3b EditFile succeeds through the REAL UserMemory.write with a foreign identity",
        edit_res.get("success") is True,
        f"got {edit_res.get('error')}: {str(edit_res.get('message'))[:90]}" if not edit_res.get("success") else ""))
    stamps = [k.get("author_identity_uuid") for k in captured]
    authors = [k.get("authored_by") for k in captured]
    results.append(_check(
        "3c both writes stamped the connecting member + the mcp species",
        stamps == ["u-kvk", "u-kvk"]
        and all(a == "yarnnn:mcp:claude.ai" for a in authors),
        f"stamps={stamps} authors={authors}"))

    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} MCP write-path signature assertions pass")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
