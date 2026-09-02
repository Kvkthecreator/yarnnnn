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

    # Sections 2-5 (the steward's wake-time embed post-step) retired with the
    # wake stack — ADR-632. Lanes and strings embed in their own write paths.

    passed = sum(1 for r in results if r); total = len(results)
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
