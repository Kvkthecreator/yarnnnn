"""ADR-325 follow-on regression gate — the wake-time derived-file embed.

The 2026-06-29 finding (docs/evaluations/2026-06-29-recall-empty-embedding-gap.md):
the seat derives understanding into operation/ from a foreign `remember`, but
nothing embedded those files, so semantic `recall` matched nothing (642/642
embeddings NULL). Fix: services/wake.py::_embed_derived_files mechanically embeds
the eligible files the seat just authored, after a substrate-event wake — NOT a
Reviewer tool call (Embed stays out of FREDDIE_PRIMITIVES; the 2026-05-25 canary
showed an extra Reviewer tool collapses judgment).

This gate asserts the post-step is correctly TARGETED:
  1. embeds reviewer-authored, eligible operation/ files written since wake start;
  2. does NOT embed ineligible files (yaml / system/ / raw inbound/ / too-short);
  3. does NOT embed non-reviewer writes (e.g. the raw yarnnn:mcp dump itself);
  4. eligibility is the SAME logic as the Embed primitive (Singular Impl);
  5. it never raises (best-effort) and respects the daily cost cap.

Runs without `mcp` or network — the Supabase client + the embed helper are faked.
"""

import asyncio
import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


# --- minimal fake Supabase query surface (mirrors the .table().select()... chain) -
class _Resp:
    def __init__(self, data=None, count=None):
        self.data = data or []
        self.count = count


class _Query:
    def __init__(self, table, store):
        self._t, self._s = table, store
        self._filters = {}
        self._gte = None

    def select(self, *a, **k): return self
    def eq(self, c, v): self._filters[c] = v; return self
    def gte(self, c, v): self._gte = (c, v); return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self

    def execute(self):
        if self._t == "workspace_file_versions":
            rows = self._s["versions"]
            if self._gte:
                col, val = self._gte
                rows = [r for r in rows if r.get(col, "") >= val]
            return _Resp(data=list(rows))
        if self._t == "workspace_files":
            path = self._filters.get("path")
            row = self._s["files"].get(path)
            return _Resp(data=[{"content": row}] if row is not None else [])
        if self._t == "execution_events":
            return _Resp(count=self._s.get("embed_calls_today", 0))
        return _Resp()


class _Client:
    def __init__(self, store): self._s = store
    def table(self, name): return _Query(name, self._s)


def main():
    results = []
    import services.wake as wake
    from services.primitives import embed as embed_mod

    # ---- 1: eligibility logic is shared with the Embed primitive (Singular Impl) -
    # operation/ prose eligible; yaml / system/ / inbound/ / short NOT.
    long = "x" * 300
    cases = {
        ("operation/memory/acme.md", long): True,
        ("operation/competitors/acme/profile.md", long): True,
        ("operation/_spec.yaml", long): False,         # yaml kind
        ("system/_recent_execution.md", long): False,  # system root
        ("governance/MANDATE.md", long): False,        # governance root
        ("inbound/mcp/claude/inbox.md", long): False,  # not an eligible root
        ("operation/memory/tiny.md", "short"): False,  # too short
    }
    elig_ok = all(embed_mod.is_embed_eligible(p, c)[0] is exp for (p, c), exp in cases.items())
    results.append(_check(
        "1 is_embed_eligible: operation/ prose YES; yaml/system/governance/inbound/short NO (ADR-325 D5)",
        elig_ok))

    # ---- 2-4: the wake-time post-step is correctly targeted --------------------
    WAKE_START = "2026-06-29T00:00:00+00:00"
    store = {
        "embed_calls_today": 0,
        # versions written during the wake (created_at >= WAKE_START) + one before
        "versions": [
            # reviewer-derived, eligible → SHOULD embed
            {"path": "/workspace/operation/memory/acme.md", "authored_by": "freddie:ai:freddie-sonnet-v8", "created_at": "2026-06-29T00:05:00+00:00"},
            # reviewer-derived but yaml → INELIGIBLE
            {"path": "/workspace/operation/competitors/_index.yaml", "authored_by": "freddie:ai:freddie-sonnet-v8", "created_at": "2026-06-29T00:06:00+00:00"},
            # reviewer-derived but system/ → INELIGIBLE
            {"path": "/workspace/system/_recent_execution.md", "authored_by": "system:mirror-recent-execution", "created_at": "2026-06-29T00:07:00+00:00"},
            # the RAW dump itself (yarnnn:mcp) → NOT reviewer-authored, skip
            {"path": "/workspace/inbound/mcp/claude/inbox.md", "authored_by": "yarnnn:mcp:Claude", "created_at": "2026-06-29T00:01:00+00:00"},
            # reviewer-derived eligible but written BEFORE the wake → excluded by gte
            {"path": "/workspace/operation/memory/old.md", "authored_by": "freddie:ai:freddie-sonnet-v8", "created_at": "2026-06-28T23:00:00+00:00"},
        ],
        "files": {
            "/workspace/operation/memory/acme.md": "x" * 400,
            "/workspace/operation/competitors/_index.yaml": "a: 1\n" * 50,
            "/workspace/system/_recent_execution.md": "x" * 400,
            "/workspace/inbound/mcp/claude/inbox.md": "x" * 400,
            "/workspace/operation/memory/old.md": "x" * 400,
        },
    }

    embedded_paths = []

    async def fake_embed(client, user_id, abs_path, content):
        embedded_paths.append(abs_path)

    # stub the execution arm + the ledger marker (no network)
    import services.primitives.workspace as wsmod
    import services.telemetry as telemetry
    real_ws_embed = wsmod._embed_workspace_file
    real_rec = telemetry.record_execution_event
    wsmod._embed_workspace_file = fake_embed
    telemetry.record_execution_event = lambda *a, **k: None  # no-network ledger
    try:
        n = asyncio.run(wake._embed_derived_files(
            _Client(store), "user-1234abcd", since_iso=WAKE_START))
    finally:
        wsmod._embed_workspace_file = real_ws_embed
        telemetry.record_execution_event = real_rec

    results.append(_check(
        "2 embeds ONLY the reviewer-derived ELIGIBLE operation/ file written during the wake",
        embedded_paths == ["/workspace/operation/memory/acme.md"] and n == 1,
        f"embedded={embedded_paths}"))
    results.append(_check(
        "3 does NOT embed yaml / system/ / raw inbound dump / pre-wake files",
        "/workspace/operation/competitors/_index.yaml" not in embedded_paths
        and "/workspace/system/_recent_execution.md" not in embedded_paths
        and "/workspace/inbound/mcp/claude/inbox.md" not in embedded_paths
        and "/workspace/operation/memory/old.md" not in embedded_paths))

    # ---- 5: respects the daily cost cap + never raises -------------------------
    store_capped = dict(store)
    store_capped["embed_calls_today"] = embed_mod._EMBED_DAILY_CAP  # at cap
    embedded_paths.clear()
    wsmod._embed_workspace_file = fake_embed
    telemetry.record_execution_event = lambda *a, **k: None
    try:
        n_capped = asyncio.run(wake._embed_derived_files(
            _Client(store_capped), "user-1234abcd", since_iso=WAKE_START))
    finally:
        wsmod._embed_workspace_file = real_ws_embed
        telemetry.record_execution_event = real_rec
    results.append(_check(
        "5 honors the daily embed cap (ADR-325 D4) — embeds nothing when at cap",
        n_capped == 0 and embedded_paths == []))

    # never raises on a broken client
    class _Boom:
        def table(self, *a, **k): raise RuntimeError("db down")
    try:
        safe = asyncio.run(wake._embed_derived_files(_Boom(), "u", since_iso=WAKE_START))
        raised = False
    except Exception:
        raised = True
    results.append(_check(
        "6 best-effort: a DB failure returns 0, never raises (must not fail the wake)",
        not raised and safe == 0))

    total, passed = len(results), sum(results)
    print(f"\n{passed}/{total} ADR-325 derived-embed assertions pass")
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:  # noqa: BLE001
        pass
    main()
