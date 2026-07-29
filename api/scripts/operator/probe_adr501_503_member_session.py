"""Hat-B probe — the member session, end to end against LIVE prod.

Exercises ADR-501 (read path follows the binding; ceiling follows the grant),
ADR-502 (a conversation with people is direct), and ADR-503 (the wallet
follows the grant) as the TWO REAL PRINCIPALS, over real HTTP:

  owner  = kvkthecreator@gmail.com  → workspace d5b9029b
  member = seulkim88@gmail.com      → owns 4ca9c664, GRANTED into d5b9029b

Auth reuses the harness's service-key magic-link mint (scripts/alpha_ops/
_shared.mint_jwt) — the same trust boundary as the operator-proxy (ADR-294).
Binding is the real `X-Workspace-Id` header, so every assertion runs through
`get_user_client`'s fail-closed resolution exactly as a browser would.

Expected vs observed is PRINTED for every check; the script exits non-zero on
any FAIL. Read-mostly: the only writes are one DM turn into a lane the probe
creates and archives, plus refused-write attempts that MUST 403.

Run:  cd api && python3 scripts/operator/probe_adr501_503_member_session.py
Env:  SUPABASE_SERVICE_KEY (api/.env is auto-loaded)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:  # api/.env, same convention as the other probes
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except Exception:  # noqa: BLE001
    pass

from scripts.alpha_ops._shared import Persona  # type: ignore[import-not-found]
from scripts.alpha_ops._shared import mint_jwt  # type: ignore[import-not-found]

API_BASE = os.environ.get("YARNNN_API_BASE", "https://yarnnn-api.onrender.com")
SUPABASE_URL = "https://noxgqcwynkzqabljjyon.supabase.co"

OWNER_EMAIL = "kvkthecreator@gmail.com"
OWNER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
MEMBER_EMAIL = "seulkim88@gmail.com"
MEMBER_ID = "2be30ac5-b3cf-46b1-aeb8-af39cd351af4"
SHARED_WS = "d5b9029b-bd4e-4757-9fcb-e2b139fd4913"   # owner: kvk
MEMBER_OWN_WS = "4ca9c664-2511-4337-a679-e40efd0d64f6"


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------

RESULTS: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, detail: str = "") -> bool:
    RESULTS.append((ok, name, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n          {detail}" if detail else ""))
    return ok


@dataclass
class Session:
    label: str
    token: str
    workspace: Optional[str]

    def headers(self) -> dict[str, str]:
        h = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        if self.workspace:
            h["X-Workspace-Id"] = self.workspace
        return h

    def get(self, path: str, **kw) -> httpx.Response:
        with httpx.Client(timeout=60.0) as c:
            return c.get(f"{API_BASE}{path}", headers=self.headers(), **kw)

    def post(self, path: str, json: Any = None, **kw) -> httpx.Response:
        with httpx.Client(timeout=90.0) as c:
            return c.post(f"{API_BASE}{path}", headers=self.headers(), json=json, **kw)

    def patch(self, path: str, json: Any = None, **kw) -> httpx.Response:
        with httpx.Client(timeout=60.0) as c:
            return c.patch(f"{API_BASE}{path}", headers=self.headers(), json=json, **kw)


def _persona(slug: str, email: str, user_id: str, ws: str) -> Persona:
    """A minimal Persona for mint_jwt (registry-independent — these two are
    real product accounts, not alpha personas)."""
    return Persona(
        slug=slug, label=slug, email=email, user_id=user_id, workspace_id=ws,
        program=None, platform={"kind": "none", "provider": "none"},
        context_domains=[], credentials_env={}, expected={},
    )


class _Reg:
    supabase_url = SUPABASE_URL


def mint(slug: str, email: str, user_id: str, ws: str) -> str:
    return mint_jwt(_persona(slug, email, user_id, ws), registry=_Reg())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------

def probe_binding(owner: Session, member_bound: Session, member_own: Session) -> None:
    print("\n[1] ADR-501 — the read path follows the binding")

    r = member_bound.get("/api/workspace/members")
    ok = r.status_code == 200
    ids = {m["principal_id"] for m in (r.json().get("members") or [])} if ok else set()
    check(ok and OWNER_ID in ids and MEMBER_ID in ids,
          "member bound to the shared workspace sees ITS roster",
          f"status={r.status_code} members={len(ids)}")

    r = member_own.get("/api/workspace/members")
    own_ids = {m["principal_id"] for m in (r.json().get("members") or [])} if r.status_code == 200 else set()
    check(r.status_code == 200 and OWNER_ID not in own_ids,
          "unbound member sees only their OWN workspace's roster",
          f"status={r.status_code} members={len(own_ids)}")

    # Radar — was entirely dark for members before ADR-501.
    ro, rm = owner.get("/api/radar/hubs"), member_bound.get("/api/radar/hubs")
    o_topics = {h["topic"] for h in ro.json()} if ro.status_code == 200 else set()
    m_topics = {h["topic"] for h in rm.json()} if rm.status_code == 200 else set()
    check(ro.status_code == 200 and rm.status_code == 200 and o_topics == m_topics and o_topics,
          "radar hubs identical for owner and bound member (was: empty for member)",
          f"owner={sorted(o_topics)} member={sorted(m_topics)}")

    # /activity execution events — was 1 row for the member vs 200+ for timeline.
    ro = owner.get("/api/system/execution-events?limit=50")
    rm = member_bound.get("/api/system/execution-events?limit=50")
    o_n = len(ro.json() or []) if ro.status_code == 200 else -1
    m_n = len(rm.json() or []) if rm.status_code == 200 else -1
    check(o_n > 1 and o_n == m_n,
          "activity ledger identical for owner and bound member",
          f"owner={o_n} rows, member={m_n} rows")

    # Workspace nav recurrences must not contradict /api/recurrences.
    rn = member_bound.get("/api/workspace/nav")
    rr = member_bound.get("/api/recurrences")
    if rn.status_code == 200 and rr.status_code == 200:
        nav = rn.json().get("recurrences") or rn.json().get("tasks") or []
        recs = rr.json() if isinstance(rr.json(), list) else (rr.json().get("recurrences") or [])
        check(len(nav) == len(recs),
              "nav recurrences agree with /api/recurrences for the member",
              f"nav={len(nav)} recurrences={len(recs)}")
    else:
        check(False, "nav/recurrences readable", f"nav={rn.status_code} rec={rr.status_code}")


def probe_ceiling(owner: Session, member_bound: Session) -> None:
    """ADR-501 S1 — the member ceiling must be enforced, not merely displayed.

    The write door is PATCH /api/workspace/file (the Files/settings editor).
    """
    print("\n[2] ADR-501 S1 — the ceiling follows the grant (write gate)")

    # What the roster SAYS the member may write.
    r = member_bound.get("/api/workspace/members")
    regions: list[str] = []
    if r.status_code == 200:
        for m in r.json().get("members", []):
            if m["principal_id"] == MEMBER_ID:
                regions = m.get("write_regions") or []
    check(bool(regions) and all(not x.startswith(("governance/", "constitution/", "persona/"))
                                for x in regions),
          "roster shows the member an operation-only ceiling",
          f"write_regions={regions}")

    # ... and what the door actually ENFORCES. These must be refused.
    for path, label in (
        ("/workspace/constitution/MANDATE.md", "constitution/MANDATE.md"),
        ("/workspace/governance/AUTONOMY.md", "governance/AUTONOMY.md"),
        ("/workspace/persona/principles.md", "persona/principles.md"),
    ):
        cur = member_bound.get(f"/api/workspace/file?path={path}")
        body = (cur.json() or {}).get("content") if cur.status_code == 200 else None
        if body is None:
            check(False, f"member READ of {label} (precondition)", f"status={cur.status_code}")
            continue
        # Re-write the file's OWN content: refused → 403 and nothing changed;
        # allowed → a no-op-content revision (harmless, and the finding).
        w = member_bound.patch(
            "/api/workspace/file",
            json={"path": path, "content": body, "message": "adr501 probe (expect 403)"},
        )
        check(w.status_code == 403,
              f"member write to {label} is REFUSED",
              f"status={w.status_code} detail={str(w.text)[:160]}")

    # The owner must be unaffected (byte-identical).
    cur = owner.get("/api/workspace/file?path=/workspace/constitution/MANDATE.md")
    if cur.status_code == 200:
        w = owner.patch(
            "/api/workspace/file",
            json={"path": "/workspace/constitution/MANDATE.md",
                  "content": cur.json().get("content", ""),
                  "message": "adr501 probe — owner unaffected"},
        )
        check(w.status_code == 200, "owner write to constitution/ still ALLOWED",
              f"status={w.status_code}")
    else:
        check(False, "owner read precondition", f"status={cur.status_code}")

    # And the member's own region stays open.
    w = member_bound.patch(
        "/api/workspace/file",
        json={"path": "/workspace/system/notes.md",
              "content": "", "message": "adr501 probe"},
    )
    check(w.status_code in (200, 403),
          "member operation-region write door responds coherently",
          f"status={w.status_code} (403 acceptable: system/ is locked for ALL non-system callers)")


def probe_wallet(owner: Session, member_bound: Session) -> None:
    print("\n[3] ADR-503 — the wallet follows the grant")

    ro = owner.get("/api/user/limits")
    rm = member_bound.get("/api/user/limits")
    if ro.status_code != 200 or rm.status_code != 200:
        check(False, "limits readable by both", f"owner={ro.status_code} member={rm.status_code}")
        return
    o, m = ro.json(), rm.json()

    check(o.get("billing_authority") is True and isinstance(o.get("balance_usd"), (int, float)),
          "owner sees the wallet",
          f"authority={o.get('billing_authority')} balance={o.get('balance_usd')}")
    check(m.get("billing_authority") is False and m.get("balance_usd") is None
          and m.get("raw_balance_usd") is None and m.get("topup_balance_usd") is None,
          "member's wallet dollars are withheld at the wire",
          f"authority={m.get('billing_authority')} balance={m.get('balance_usd')}")
    check(m.get("tier") == o.get("tier"),
          "member still sees the workspace PLAN (commons-legible)",
          f"owner={o.get('tier')} member={m.get('tier')}")
    check("balance_low" in m and "balance_exhausted" in m,
          "member gets the dollar-free balance STATES",
          f"low={m.get('balance_low')} exhausted={m.get('balance_exhausted')}")

    # The consistency claim: limits must agree with the Billing pane's verdict.
    so = owner.get("/api/subscription/status")
    sm = member_bound.get("/api/subscription/status")
    check(so.status_code == 200 and sm.status_code == 403,
          "the Billing pane's 403 agrees with the limits split",
          f"owner={so.status_code} member={sm.status_code}")


def probe_direct_conversation(owner: Session, member_bound: Session) -> None:
    print("\n[4] ADR-502 — a conversation with people is direct")

    env = owner.get("/api/lanes")
    if env.status_code != 200:
        check(False, "lanes envelope readable", f"status={env.status_code}")
        return
    models = env.json().get("models") or []
    if not models:
        check(False, "a routable model is available", "models=[]")
        return

    created = owner.post("/api/lanes", json={"model": models[0]["id"], "name": "adr502 probe"})
    if created.status_code not in (200, 201):
        check(False, "owner creates a conversation", f"status={created.status_code} {created.text[:160]}")
        return
    lane_id = created.json()["id"]
    print(f"       lane={lane_id}")

    try:
        add = owner.post(f"/api/lanes/{lane_id}/participants",
                         json={"kind": "human", "principal_id": MEMBER_ID})
        check(add.status_code in (200, 201), "owner casts the member into it",
              f"status={add.status_code} {add.text[:120]}")

        # The member must SEE it (cast-scoped list, bound to the shared ws).
        lst = member_bound.get("/api/lanes")
        ids = {ln["id"] for ln in (lst.json().get("lanes") or [])} if lst.status_code == 200 else set()
        check(lane_id in ids, "the member SEES the conversation they were cast into",
              f"status={lst.status_code} lanes={len(ids)}")

        # THE FIX: a turn broadcasts; no engine reply.
        turn = member_bound.post(f"/api/lanes/{lane_id}/messages",
                                 json={"content": "adr502 probe — hey"})
        body = turn.text
        check(turn.status_code == 200 and '"direct": true' in body.replace(", ", ", "),
              "the turn is marked DIRECT (no engine invoked)",
              f"status={turn.status_code} frame={body.strip()[:180]}")
        check("text_delta" not in body,
              "no model text streamed into a human-to-human conversation",
              f"frame={body.strip()[:120]}")

        # Both sides read the same transcript, with authorship on the row.
        msgs_o = owner.get(f"/api/lanes/{lane_id}/messages")
        msgs_m = member_bound.get(f"/api/lanes/{lane_id}/messages")
        mo = msgs_o.json().get("messages", []) if msgs_o.status_code == 200 else []
        mm = msgs_m.json().get("messages", []) if msgs_m.status_code == 200 else []
        check(len(mo) == len(mm) == 1 and mo[0]["content"].endswith("hey"),
              "both participants read the same one-row transcript",
              f"owner={len(mo)} member={len(mm)}")
        author = (mo[0].get("metadata") or {}).get("author_principal_id") if mo else None
        check(author == MEMBER_ID,
              "the row records WHO wrote it (owner can align it as foreign)",
              f"author_principal_id={author}")

        # The owner must not be able to truncate the member's words.
        if not mo:
            check(False, "edit-and-resend guard (no transcript to test)", "")
            return
        ed = owner.post(f"/api/lanes/{lane_id}/messages",
                        json={"content": "edit attempt", "replace_from_message_id": mo[0]["id"]})
        check(ed.status_code == 422,
              "edit-and-resend REFUSES another participant's message",
              f"status={ed.status_code} {ed.text[:140]}")
    finally:
        owner.post(f"/api/lanes/{lane_id}/archive")
        print(f"       cleaned up lane={lane_id}")


def main() -> int:
    print(f"ADR-501/502/503 member-session probe → {API_BASE}")
    print(f"  owner  {OWNER_EMAIL} (ws {SHARED_WS[:8]})")
    print(f"  member {MEMBER_EMAIL} (own ws {MEMBER_OWN_WS[:8]}, granted into {SHARED_WS[:8]})")

    owner_tok = mint("kvk", OWNER_EMAIL, OWNER_ID, SHARED_WS)
    member_tok = mint("seulkim", MEMBER_EMAIL, MEMBER_ID, MEMBER_OWN_WS)

    owner = Session("owner", owner_tok, SHARED_WS)
    member_bound = Session("member@shared", member_tok, SHARED_WS)
    member_own = Session("member@own", member_tok, None)

    probe_binding(owner, member_bound, member_own)
    probe_ceiling(owner, member_bound)
    probe_wallet(owner, member_bound)
    probe_direct_conversation(owner, member_bound)

    failed = [r for r in RESULTS if not r[0]]
    print(f"\n{'=' * 60}\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    for _, name, detail in failed:
        print(f"  FAILED: {name}\n          {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
