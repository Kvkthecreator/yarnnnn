"""ADR-537 gate — the share sheet asks what you are doing.

Guards the five decisions that have code behind them:

  D1  two tabs, Link default, People badged. The badge is the mitigation for
      the trade the tab makes (simplicity bought with a discoverability cost) —
      without it an operator never learns a join link is live on this file.
  D2  `FileReach` MOVED into the dialog, not copied. Asserted as a PAIR: gone
      from NodeDetailsPanel AND present in ShareDialog. A gate checking only
      the second would go green on a duplicate, which is the dual-surface
      problem ADR-529 D4 deleted.
  D3  the two doors to membership agree on who may open them — invite-creation
      adopts `assert_may_mint_share`, while narrow/revoke-member/cap KEEP
      `_require_owner_workspace` (its docstring carries a receipted production
      incident: a member widened their own grant via /narrow).
  D4  the join link states its redemption — and NEVER a redeemer's name, since
      `accepted_principal_id` is overwritten on every accept.
  D5  the copy states workspace scope, seat cost, forwardability, and what
      revoke does NOT do.

Run:  cd api && python3 test_adr537_share_sheet_tabs.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

API = Path(__file__).parent
WEB = API.parent / "web"


def _check(label: str, cond: bool, detail: str = "") -> bool:
    print(f"{'PASS' if cond else 'FAIL'}  {label}  {detail}")
    return bool(cond)


def _strip_ts_comments(src: str) -> str:
    """Code only — several checks name the very symbol they forbid."""
    src = re.sub(r"/\*[\s\S]*?\*/", "", src)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)
    return src


def _strip_py_comments(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    return re.sub(r"^\s*#.*$", "", src, flags=re.MULTILINE)


def main() -> int:
    results: list[bool] = []

    dialog_raw = (WEB / "components/workspace/ShareDialog.tsx").read_text(encoding="utf-8")
    dialog = _strip_ts_comments(dialog_raw)
    details_raw = (WEB / "components/workspace/NodeDetailsPanel.tsx").read_text(encoding="utf-8")
    details = _strip_ts_comments(details_raw)
    ws_route_raw = (API / "routes/workspace.py").read_text(encoding="utf-8")
    ws_route = _strip_py_comments(ws_route_raw)
    shares_rt = (API / "routes/shares.py").read_text(encoding="utf-8")

    # ── D1 — the tabs ────────────────────────────────────────────────────────
    results.append(_check(
        "D1a two tabs exist (link · people)",
        "'link' | 'people'" in dialog or '"link" | "people"' in dialog))
    results.append(_check(
        "D1b Link is the DEFAULT tab",
        re.search(r"useState<Tab>\('link'\)", dialog) is not None,
        "the simple act must be the one that costs no clicks"))
    results.append(_check(
        "D1c the People tab carries a count badge",
        "peopleBadge" in dialog and re.search(r"peopleBadge\s*>\s*0", dialog) is not None,
        "tabs hide things; the hidden one here is the consequential one"))

    # The badge must count BOTH outstanding things — a badge that counted only
    # invites would leave a live join link invisible, which is the exact state
    # the badge exists to surface.
    badge = re.search(r"const peopleBadge = ([^;]+);", dialog)
    results.append(_check(
        "D1d the badge counts pending invites AND a live join link",
        badge is not None and "invites" in badge.group(1) and "joinLink" in badge.group(1),
        badge.group(1).strip() if badge else "not found"))

    # The role RADIO is gone: the sheet no longer asks "how much access".
    results.append(_check(
        "D1e the permission radio stack is gone",
        "SHAPES" not in dialog and "aria-pressed" not in dialog,
        "the question was never 'how much', it was 'what are you doing'"))

    # ── D2 — FileReach MOVED, asserted as a pair ─────────────────────────────
    results.append(_check(
        "D2a FileReach is GONE from NodeDetailsPanel",
        "function FileReach" not in details and "<FileReach" not in details))
    results.append(_check(
        "D2b the roster lives in the ShareDialog (getMembers by path)",
        "getMembers(path)" in dialog,
        "computed by the same powerbox matcher the gate consults"))
    results.append(_check(
        "D2c the dialog crosslinks the rail (ADR-515 D6's half-view)",
        "Workspace Settings" in dialog_raw,
        "per-file and per-principal views were never linked before"))

    # ── D3 — the two doors agree ─────────────────────────────────────────────
    invite_fn = ws_route[ws_route.index("async def invite_member"):]
    invite_fn = invite_fn[: invite_fn.index("@router")]
    results.append(_check(
        "D3a invite-creation gates on assert_may_mint_share",
        "assert_may_mint_share" in invite_fn,
        "one outcome (a new member) must not have two authorities"))
    results.append(_check(
        "D3b invite-creation no longer uses the owner-only helper",
        "_require_owner_workspace" not in invite_fn))

    # The receipted-incident protections MUST survive. `_require_owner_workspace`
    # exists because a member widened their own grant via /narrow on production
    # (2026-07-31). Widening the INVITE door must not widen these.
    for verb, marker in (
        ("narrow", "change a member's access"),
        ("revoke-member", "revoke a member"),
    ):
        results.append(_check(
            f"D3c {verb} KEEPS the owner-only gate",
            f'_require_owner_workspace(auth, "{marker}")' in ws_route,
            "receipted incident: a member widened their own grant"))
    results.append(_check(
        "D3d the owner-only helper still exists and is still used",
        ws_route.count("_require_owner_workspace(auth") >= 4,
        "cap + invite-list + invite-revoke + the two above"))

    # The seat gate is DECIDED in the service, so widening WHO may invite cannot
    # widen billing. The route may still TRANSLATE the refusal (it maps
    # upgrade_required → 402 so the FE can branch to an upgrade CTA) — asserting
    # the string is absent from the route would delete that branch, which is why
    # this checks where the DECISION is made, not where the word appears.
    invites_svc = (API / "services/workspace_invites.py").read_text(encoding="utf-8")
    decides_in_service = (
        "tier_included_seats" in invites_svc
        and 'raise InviteError(\n                    "upgrade_required"' in invites_svc
    )
    results.append(_check(
        "D3e the seat cap is DECIDED in the service, not the route",
        decides_in_service and "tier_included_seats" not in invite_fn,
        "widening WHO may invite must not widen the free-tier cap"))

    # ── D4 — redemption stated, never a name ─────────────────────────────────
    results.append(_check(
        "D4a last_accepted_at is projected to the FE",
        "last_accepted_at" in shares_rt,
        "list_shares already SELECTED it; nothing rendered it"))
    results.append(_check(
        "D4b the dialog renders the redemption state",
        "last_accepted_at" in dialog and "No one has joined yet" in dialog_raw))
    results.append(_check(
        "D4c a redeemer's NAME is never rendered",
        "accepted_principal_id" not in dialog_raw,
        "the column is OVERWRITTEN per accept — one name would imply a list"))

    # ── D5 — the copy states the consequences ────────────────────────────────
    for label, needle in (
        ("workspace scope + seat cost", "uses a\n                  seat"),
        ("forwardability", "not just\n                      the person you send it to"),
        ("revoke does not remove members", "does not remove\n                      anyone who already joined"),
    ):
        # Copy is wrapped by the formatter, so match on a distinctive fragment
        # rather than the whole sentence.
        frag = needle.split("\n")[0].strip()
        results.append(_check(
            f"D5 the copy states {label}",
            frag in dialog_raw, frag))

    ok = all(results)
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — {sum(results)}/{len(results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
