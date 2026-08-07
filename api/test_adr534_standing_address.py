"""ADR-534 gate — the share link is a standing address, and an honest one when it breaks.

Guards the four decisions that have code behind them:

  D1  the dialog opens on the link that EXISTS, and the reuse lookup keys on
      (path, ROLE) — never path alone. A path-only match would hand a
      view-only requester a full-access link, so the lookup is run as a REAL
      DECISION over a live/live · live/none · none/none matrix rather than
      asserted structurally.
  D2  `list_shares` carries the token so a live link can be re-copied — and the
      PUBLIC projection still does not. Asserted AS A PAIR: widening one
      without the other is the failure this pins, and a gate that checked only
      the first would go green on exactly that regression.
  D3  every live link is copyable, not only revocable.
  D4  a share whose file is gone goes DARK, not blank — and the three dark
      states stay DISTINCT (404 no-token · 410 revoked · 410 file-gone).
      Collapsing them is what makes "why can't my client see this"
      undebuggable (grants-and-reach.md §8a).

Also pins the REFUSAL (ADR-534 §3): no path-chasing helper exists, and no
relocation verb references the share table. That check is the structural proof
that D4 imposes no obligation on future verbs — if someone later "fixes" a
broken link by syncing paths on move, this goes red and points at the ADR.

Executed, not grepped, wherever the claim is behavioural.

Run:  cd api && python3 test_adr534_standing_address.py
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
    """Code only. Several checks below name the very symbol they forbid, and an
    assertion that matches its own explanatory comment is a documented trap."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)
    return src


def _strip_py_comments(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    return re.sub(r"^\s*#.*$", "", src, flags=re.MULTILINE)


def main() -> int:
    results: list[bool] = []

    shares_svc = (API / "services/workspace_shares.py").read_text(encoding="utf-8")
    shares_rt = (API / "routes/shares.py").read_text(encoding="utf-8")
    dialog = (WEB / "components/workspace/ShareDialog.tsx").read_text(encoding="utf-8")
    preview_ts = (WEB / "app/s/[token]/share-preview.ts").read_text(encoding="utf-8")

    # ── D1 — the reuse lookup, EXECUTED over the matrix ──────────────────────
    #
    # The real decision, transcribed from `liveFor` in ShareDialog.tsx.
    #
    # KNOWN LIMIT, measured by falsification 2026-08-07 — do not mistake this
    # matrix for a test of the component. Rewriting `liveFor` to key on path
    # alone left every row below GREEN (the transcription does not import the
    # TS) and was caught only by the structural check that follows. The two
    # defend different things and BOTH are required:
    #
    #   this matrix        the CONTRACT — what the right answer is, per shape
    #   the structural check   the CODE — that the component still keys on role
    #
    # If a future session extends the reuse rule, it must edit both, and the
    # structural check is the one that fails loudly when only one moves.
    def live_for(links: list[dict], role: str) -> dict | None:
        return next(
            (l for l in links if l["role"] == role and l.get("share_link")), None
        )

    P = "/workspace/operation/notes/x.md"
    both = [
        {"id": "v", "role": "viewer", "artifact_path": P, "share_link": "https://y/s/V"},
        {"id": "m", "role": "member", "artifact_path": P, "share_link": "https://y/s/M"},
    ]
    only_member = [both[1]]
    matrix = [
        ("both live -> viewer gets the VIEWER link", both, "viewer", "v"),
        ("both live -> member gets the MEMBER link", both, "member", "m"),
        ("only member live -> viewer gets NOTHING (mints)", only_member, "viewer", None),
        ("only member live -> member reuses", only_member, "member", "m"),
        ("none live -> viewer gets nothing", [], "viewer", None),
        ("none live -> member gets nothing", [], "member", None),
    ]
    for label, links, role, expect in matrix:
        got = live_for(links, role)
        results.append(_check(
            f"D1 {label}", (got or {}).get("id") == expect if expect else got is None))

    # A link with no URL is not reusable — it cannot be handed back, so it must
    # not suppress the mint button (the operator would be stranded with no way
    # to get a link at all).
    results.append(_check(
        "D1 a tokenless row is not treated as reusable",
        live_for([{"id": "x", "role": "viewer", "artifact_path": P, "share_link": None}],
                 "viewer") is None))

    code = _strip_ts_comments(dialog)
    results.append(_check(
        "D1 the lookup keys on ROLE, not path alone",
        re.search(r"l\.role === r\b", code) is not None,
        "a path-only match hands the wrong shape's link back"))
    results.append(_check(
        "D1 the dialog no longer offers 'Create another'",
        "Create another" not in code,
        "that label made duplication the path of least resistance"))
    results.append(_check(
        "D1 the deliberate second link stays reachable",
        "Create a separate link" in code and "forceMint" in code,
        "per-recipient links must stay expressible"))

    # ── D2 — the token widening, asserted AS A PAIR ──────────────────────────
    sel = re.search(r'\.select\(\s*"([^"]*token[^"]*)"\s*\)', shares_svc)
    results.append(_check(
        "D2a list_shares selects the token", sel is not None))
    results.append(_check(
        "D2b the list route builds the URL from app_url (one spelling)",
        "app_url()" in shares_rt and 'share_link=f"{base}/s/{r[' in shares_rt,
        "a second URL-shaped string would be free to drift"))

    # The other half. `SharePreviewResponse` IS the public boundary (ADR-513
    # D2) — a token there would hand an anonymous reader a capability.
    import routes.shares as r  # noqa: E402

    public_fields = set(r.SharePreviewResponse.model_fields.keys())
    results.append(_check(
        "D2c the PUBLIC projection carries no token",
        not any("token" in f for f in public_fields),
        str(sorted(public_fields))))

    # ── D3 — copyable, not only revocable ────────────────────────────────────
    list_block = code[code.index("Active links to this file"):] if \
        "Active links to this file" in code else ""
    results.append(_check(
        "D3 each live link row offers Copy beside Revoke",
        "copy(l.share_link" in list_block and "revoke(l.id)" in list_block,
        "an operator could previously destroy a link they could not read"))

    # ── D4 — dark, not blank; and the states stay distinct ───────────────────
    rt = _strip_py_comments(shares_rt)
    results.append(_check(
        "D4a a resolved-but-missing file raises 410",
        re.search(r"if not rows:\s*raise HTTPException\(\s*status_code=410", rt) is not None,
        "the fall-through returned 200 with an empty body"))
    results.append(_check(
        "D4b the file-gone 410 carries the capability headers",
        rt.count("headers=dict(_CAPABILITY_HEADERS)") >= 3,
        "a bare raise ships without no-store (the 2026-08-03 defect class)"))

    # The three dark states must not collapse into one sentence.
    moved = "moved or deleted" in shares_rt
    revoked_distinct = re.search(r'detail=f"This share link is \{share\[.status.\]\}"', shares_rt)
    results.append(_check(
        "D4c revoked and file-gone are DIFFERENT messages",
        moved and revoked_distinct is not None,
        "the operator must know which happened (grants-and-reach.md §8a)"))

    prev = _strip_ts_comments(preview_ts)
    results.append(_check(
        "D4d the FE carries the server's detail, not one hardcoded line",
        "darkMessage" in prev and "body?.detail" in prev,
        "a fixed string here would discard the distinction the API just made"))
    results.append(_check(
        "D4e a 404 keeps the generic line (it has no detail worth showing)",
        re.search(r"if \(res\.status === 404\) return GENERIC_DARK", prev) is not None))
    results.append(_check(
        "D4f the dialog warns when the shared file is gone",
        "stale" in code and "moved, renamed, or deleted" in dialog,
        "the operator learns at the moment they look"))
    results.append(_check(
        "D4g only a 404 marks a link stale (403/500/offline are inconclusive)",
        re.search(r"e\.status === 404\) setStale\(true\)", code) is not None,
        "claiming a healthy link is broken would make them revoke a working one"))

    # ── §3 — the REFUSAL is structural, not merely documented ────────────────
    #
    # If a future session "fixes" a broken link by syncing paths on move, these
    # go red and point at the ADR that refused it. That is the whole reason D4
    # imposes no obligation: there is nothing to remember, so nothing can be
    # forgotten.
    for rel in ("routes/documents.py", "routes/studio.py", "services/primitives/workspace.py"):
        src = _strip_py_comments((API / rel).read_text(encoding="utf-8"))
        results.append(_check(
            f"§3 {rel} does not touch workspace_shares",
            "workspace_shares" not in src,
            "path-chasing is an obligation every future verb must remember"))
    results.append(_check(
        "§3 no repoint/sync helper exists",
        not re.search(r"def (repoint_shares|sync_share_paths|_repoint)", shares_svc),
        "brokenness is DERIVED at read time, never maintained"))

    ok = all(results)
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — {sum(results)}/{len(results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
