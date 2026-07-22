"""ADR-445 gate — the billing seat count is SERVICE-scoped, never RLS-scoped.

The bug this locks out (2026-07-22): `count_human_seats(auth.client, ...)` reads
`principal_grants`, whose RLS policy is `principal_id = auth.uid()` — a user client
sees only its OWN grant row. So the count returned 1 for the owner regardless of
real headcount. The Billing pane read "1 seat — just you" on a 3-human workspace
whose avatar menu (SERVICE-client-served) correctly read "3 people" — and, worse,
the checkout seat quantity was computed the same way, so a 3-human team was billed
for 1 seat. Migration 221 fixed the policy for a member's VIEW; this gate pins the
stronger rule for the CHARGE.

The invariant:
  Every `count_human_seats(...)` call in the money paths (subscription.py) reads
  through the SERVICE client — the same path seat-sync + the webhook drift check
  always used. A billing count must not depend on the request's RLS scope being
  complete; one client, one behavior, no under- or over-billing on a visibility
  edge.

This is a SOURCE guard (the older ADR-445 gates test pure functions with a fake
client, which is exactly why they could not see this — the fake client returned
the right rows). Assert the CALLER, not the function.

Usage:
    cd api
    python test_adr445_seat_count_is_service_scoped.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"  {'PASS' if cond else 'FAIL'} {label}")


def _decommented(src: str) -> str:
    # Drop docstrings/blocks and # lines so a comment NAMING the banned pattern
    # (this file's own prose, and the routes' explanatory comments) is not counted
    # as an instance of it.
    src = re.sub(r'"""(?:.|\n)*?"""', "", src)
    src = re.sub(r"^\s*#.*$", "", src, flags=re.M)
    return src


def main() -> bool:
    print("\nADR-445 — the billing seat count is service-scoped\n")

    sub = _decommented((_ROOT / "routes/subscription.py").read_text())

    # (1) No money path counts seats through the request client.
    _check(
        "no `count_human_seats(auth.client, ...)` survives in subscription.py "
        "(the RLS-scoped under-count that read '1 seat' on a 3-human team)",
        "count_human_seats(auth.client" not in sub,
    )

    # (2) Every count_human_seats CALL passes a service-scoped client. The
    # allowed clients are the ones with BYPASSRLS in this route: an explicit
    # get_service_client(), or the `svc`/`client` a service-context helper is
    # already holding (seat-sync + the webhook, which run off a service client).
    calls = re.findall(r"count_human_seats\(\s*([a-zA-Z_][\w.]*)", sub)
    allowed = {"get_service_client()"}  # normalized below
    bad = []
    for arg in calls:
        a = arg.strip()
        # get_service_client() shows up as the token `get_service_client` before the ')'
        ok = a in ("svc", "client") or a == "get_service_client"
        if not ok:
            bad.append(a)
    _check(
        f"every count_human_seats() call reads a service client "
        f"(found args: {sorted(set(calls)) or 'none'})",
        len(calls) > 0 and not bad,
    )

    # (3) The two money-decision sites explicitly reach get_service_client — the
    # status pane + the checkout charge. Pin them by name so a refactor that
    # drops the explicit fetch is caught.
    _check(
        "the status + checkout seat counts fetch the service client explicitly "
        "(get_service_client appears at least twice in the seat-count region)",
        sub.count("get_service_client()") >= 2,
    )

    # (4) The RLS policy migration exists and is recursion-safe (SECURITY DEFINER
    # predicate), so a member's own VIEW of the roster is correct too.
    mig = next(_ROOT.parent.glob("supabase/migrations/*_member_reads_co_member_grants.sql"), None)
    _check("migration 221 (member reads co-member grants) is present", mig is not None)
    if mig:
        m = mig.read_text()
        _check(
            "the membership predicate is SECURITY DEFINER (breaks the RLS "
            "recursion on principal_grants)",
            "SECURITY DEFINER" in m and "is_workspace_member" in m,
        )
        _check(
            "the co-member policy is SELECT-only (a member gains READ, never the "
            "power to grant/narrow/revoke — writes stay service-role-only)",
            "FOR SELECT" in m and "FOR INSERT" not in m and "FOR UPDATE" not in m,
        )

    print()
    ok = all(c for _, c in _results)
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
