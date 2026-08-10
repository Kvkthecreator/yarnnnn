"""Principal display gate — one resolution, no UUIDs, no emails, three species.

The 2026-08-10 identity-rendering pass: the ledger stores identity canonically
(`authored_by` taxonomy + `author_identity_uuid`, ADR-209/410/411/460) and
`services/principal_display.py` is the ONE server-side resolution into display.
Both the MCP surface (list/open/history/save conflicts) and the desk's revision
endpoint render through it.

The operator-specified contract this gate holds:
  1. For a file whose revisions span all three species (human direct, human via
     their agent, external LLM) plus a system lane, the MCP `history` output
     contains NO raw UUID and NO email — anywhere in the payload.
  2. The three species are distinguishable FROM THE STRINGS ALONE:
       "Kevin" · "Kevin via Claude Sonnet" · "Claude (via MCP)" · "system:radar".
  3. An unresolvable member degrades to "a workspace member", never the UUID.
  4. Legacy stored forms (capitalized `yarnnn:mcp:Claude`, pre-ADR-411
     `<email> via <model>`) normalize/degrade — the ledger is not rewritten,
     the boundary is.

Run: python3 test_principal_display.py  (from api/)
"""

import asyncio
import re
import sys
import types

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
EMAIL_RE = re.compile(r"[^\s@\"']+@[^\s@\"']+\.[^\s@\"']+")

KVK = "2abf3f96-118b-4987-9d95-40f2d9be9a18"


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


class _AdminUser:
    def __init__(self, name, email):
        self.user = types.SimpleNamespace(user_metadata={"full_name": name}, email=email)


class _FakeAuthAdmin:
    def __init__(self, users):
        self._users = users

    def get_user_by_id(self, uid):
        if uid in self._users:
            return self._users[uid]
        raise RuntimeError("no such user")


class _FakeClient:
    def __init__(self, users):
        self.auth = types.SimpleNamespace(admin=_FakeAuthAdmin(users))

    def table(self, name):  # compose_history's derived_from head read
        class _Q:
            def select(self, *a, **k): return self
            def eq(self, *a, **k): return self
            def limit(self, *a, **k): return self
            def execute(self): return types.SimpleNamespace(data=[])
        return _Q()


def main():
    results = []
    from services import principal_display as pd

    users = {KVK: _AdminUser("Kevin", "kvkthecreator@gmail.com")}
    client = _FakeClient(users)

    # ── unit: the resolver's species × display table ──────────────────────────
    names = pd.resolve_member_names(client, [KVK, "00000000-0000-4000-8000-000000000000"])
    results.append(_check(
        "1 member name resolves from auth metadata; unknown id is absent (not a UUID)",
        names.get(KVK) == "Kevin"
        and "00000000-0000-4000-8000-000000000000" not in names))

    cases = {
        # human direct — identity rides the separate column (ADR-410)
        ("operator", KVK): "Kevin",
        # human via their agent — the member's hands (ADR-411/460)
        (f"member:{KVK} via anthropic/claude-sonnet-4-6", None): "Kevin via Claude Sonnet",
        # external LLM principal — a separate principal
        ("yarnnn:mcp:chatgpt", None): "ChatGPT (via MCP)",
        # legacy capitalized registered-name row → normalized through the registry
        ("yarnnn:mcp:Claude", None): "Claude (via MCP)",
        # system lane — as-is per spec
        ("system:radar", None): "system:radar",
        # steward
        ("freddie:ai:freddie-sonnet-v8", None): "Freddie",
        ("freddie:ai-sonnet-v1", None): "Freddie",
        # unresolvable member degrades human, never UUID
        ("member:00000000-0000-4000-8000-000000000000 via openai/gpt-4o-mini", None):
            "a workspace member via GPT-4o mini",
        ("operator", None): "a workspace member",
        # legacy pre-ADR-411 free-text — the email NEVER crosses
        ("kvkthecreator@gmail.com via anthropic/claude-sonnet-4-6", None):
            "a workspace member via Claude Sonnet",
        # unknown model slug degrades readably (provider stripped)
        (f"member:{KVK} via anthropic/claude-opus-9", None): "Kevin via claude-opus-9",
    }
    all_ok = True
    for (authored, uuid), want in cases.items():
        got = pd.display_author(authored, author_identity_uuid=uuid, member_names=names)
        if got != want:
            all_ok = False
            print(f"      [!] {authored!r} → {got!r}, want {want!r}")
    results.append(_check("2 display table (all species + legacy forms)", all_ok))

    results.append(_check(
        "3 species classification is machine-legible and three-way distinct",
        pd.classify_author("operator") == "member"
        and pd.classify_author(f"member:{KVK} via x/y") == "member-via-agent"
        and pd.classify_author("yarnnn:mcp:claude.ai") == "external-llm"
        and pd.classify_author("system:radar") == "system"))

    # ── the claude alias fix (storage-side casing bug) ────────────────────────
    from mcp_server.presentation.hosts import resolve_host_id
    results.append(_check(
        "4 registered name 'Claude' now resolves to the claude.ai host id "
        "(the yarnnn:mcp:Claude storage bug closed at the source)",
        resolve_host_id("Claude") == "claude.ai"
        and resolve_host_id("claude desktop") == "claude_desktop"
        and resolve_host_id("Claude Code") == "claude_code"))

    # ── end-to-end: compose_history over all three species ────────────────────
    from services import mcp_composition as m
    import services.primitives.registry as preg

    revisions = [
        {"id": "r3", "authored_by": f"member:{KVK} via anthropic/claude-sonnet-4-6",
         "author_identity_uuid": None, "created_at": "t3", "message": "desk pass",
         "revision_kind": "authored"},
        {"id": "r2", "authored_by": "operator", "author_identity_uuid": KVK,
         "created_at": "t2", "message": "edited", "revision_kind": "authored"},
        {"id": "r1", "authored_by": "yarnnn:mcp:Claude", "author_identity_uuid": None,
         "created_at": "t1", "message": "arrived", "revision_kind": "observation"},
        {"id": "r0", "authored_by": "system:radar", "author_identity_uuid": None,
         "created_at": "t0", "message": "swept", "revision_kind": "authored"},
    ]

    async def fake_exec(auth_, name, args):
        if name == "ListRevisions":
            return {"success": True, "revisions": revisions}
        if name == "DiffRevisions":
            return {"success": True, "diff": "@@"}
        return {"success": False}

    auth = types.SimpleNamespace(user_id=KVK, client=client)
    saved = preg.execute_primitive
    preg.execute_primitive = fake_exec
    try:
        out = asyncio.run(m.compose_history(
            auth, reference="operation/fundraising/embed-application-2026-08-10.md"))
    finally:
        preg.execute_primitive = saved

    import json
    payload = json.dumps(out)
    results.append(_check(
        "5 history payload carries NO raw UUID and NO email",
        not UUID_RE.search(payload) and not EMAIL_RE.search(payload),
        "" if (not UUID_RE.search(payload) and not EMAIL_RE.search(payload))
        else f"leak in: {payload[:200]}"))

    authors = [h["authored_by"] for h in out["history"]]
    results.append(_check(
        "6 the three species are distinguishable from the strings alone",
        authors == ["Kevin via Claude Sonnet", "Kevin", "Claude (via MCP)", "system:radar"],
        f"got {authors}"))

    classes = [h["author_class"] for h in out["history"]]
    results.append(_check(
        "7 species also ride machine-legible (author_class)",
        classes == ["member-via-agent", "member", "external-llm", "system"],
        f"got {classes}"))

    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} principal-display assertions pass")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
