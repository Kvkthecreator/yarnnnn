"""Probe: a cold sign-up gets a workspace, and can open a lane (ADR-465 D2 am. 2026-09-12).

THE BUG THIS WATCHES FOR. Owner-genesis sat on `GET /api/workspace/state`;
ADR-437 Phase A deleted the last surface that fetched it on login, so from
2026-07-11 every cold sign-up landed workspace-less and discovered it three
screens later as a 500 from `add_participant`. The mint now lives in
`get_user_client` (the one dependency every authenticated request passes).

WHY A PROBE AND NOT ONLY A GATE. The gate is structural — it reads source. It
cannot tell you that a real principal, holding a real JWT, hitting the real
deployed API, ends up with a workspace. That is the claim that actually failed,
so that is the claim this drives.

Creates a throwaway auth user, calls the API as them, asserts:
  1. before: the user resolves NO workspace (a true cold principal)
  2. GET /api/lanes  (any authenticated call) mints it — the door is the
     dependency, not a particular route
  3. POST /api/lanes succeeds and the lane carries the workspace + a cast
  4. no NULL-workspace chat_sessions row is left behind
Then deletes the user and everything minted for them.

Run:  python3 scripts/operator/probe_cold_user_genesis.py [--api URL]
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _load_env() -> None:
    env = Path(__file__).resolve().parents[2] / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _req(method, url, headers=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(r) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw[:400]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="https://yarnnn-api.onrender.com")
    args = ap.parse_args()
    _load_env()

    SB = os.environ["SUPABASE_URL"]
    KEY = os.environ["SUPABASE_SERVICE_KEY"]
    ANON = os.environ["SUPABASE_ANON_KEY"]
    SVC = {"apikey": KEY, "Authorization": f"Bearer {KEY}",
           "Content-Type": "application/json", "Prefer": "return=representation"}

    email = f"probe-cold-{uuid.uuid4().hex[:10]}@yarnnn-probe.invalid"
    password = uuid.uuid4().hex + "Aa1!"
    results, uid = [], None

    def check(label, ok, detail=""):
        print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
        results.append(bool(ok))

    try:
        # ── create a genuinely cold principal ──────────────────────────────
        st, user = _req("POST", f"{SB}/auth/v1/admin/users", SVC,
                        {"email": email, "password": password,
                         "email_confirm": True})
        if st >= 300:
            print(f"FATAL could not create probe user: {st} {user}")
            return 2
        uid = user["id"]
        print(f"probe user {email}  id={uid}")

        def ws_rows():
            _, rows = _req("GET", f"{SB}/rest/v1/workspaces?owner_id=eq.{uid}&select=id", SVC)
            return rows or []

        def grant_rows():
            _, rows = _req("GET", f"{SB}/rest/v1/principal_grants?principal_id=eq.{uid}&select=id", SVC)
            return rows or []

        # 1. cold: no owner row, no grant
        check("1 the principal starts COLD (no workspace, no grant)",
              not ws_rows() and not grant_rows())

        # sign in for a real user JWT
        st, sess = _req("POST", f"{SB}/auth/v1/token?grant_type=password",
                        {"apikey": ANON, "Content-Type": "application/json"},
                        {"email": email, "password": password})
        if st >= 300 or not sess.get("access_token"):
            print(f"FATAL sign-in failed: {st} {sess}")
            return 2
        AUTH = {"Authorization": f"Bearer {sess['access_token']}",
                "Content-Type": "application/json"}

        # 2. ANY authenticated call mints — deliberately NOT /workspace/state,
        #    because the whole point is that the door is no longer a route.
        st, _ = _req("GET", f"{args.api}/api/lanes", AUTH)
        rows = ws_rows()
        check("2 one ordinary authenticated call minted the workspace",
              st < 300 and len(rows) == 1, f"GET /api/lanes -> {st}, workspaces={len(rows)}")

        # 2b THE OWNER GRANT. `workspaces.owner_id` says who owns it;
        #    `principal_grants` says who may REACH it, and `is_workspace_member`
        #    (which migration 236's lane policy ANDs) reads ONLY the second.
        #    A workspace minted without this row is reachable by nobody.
        _, grants = _req("GET",
                         f"{SB}/rest/v1/principal_grants?principal_id=eq.{uid}"
                         f"&role=eq.owner&status=eq.active&select=id", SVC)
        check("2b the mint also granted the owner REACH", len(grants or []) == 1,
              f"owner grants={len(grants or [])}")

        # 3. the act that actually broke: open a new chat
        st, lane = _req("POST", f"{args.api}/api/lanes", AUTH,
                        {"name": "probe", "model": "anthropic/claude-sonnet-5"})
        ok = st < 300 and isinstance(lane, dict) and lane.get("id")
        check("3 POST /api/lanes succeeds (the reported 500)", ok, f"-> {st}")
        if ok:
            _, row = _req("GET",
                          f"{SB}/rest/v1/chat_sessions?id=eq.{lane['id']}&select=workspace_id", SVC)
            _, cast = _req("GET",
                           f"{SB}/rest/v1/conversation_members?conversation_id=eq.{lane['id']}&select=id", SVC)
            check("3b the lane carries its workspace AND a cast",
                  row and row[0].get("workspace_id") and len(cast or []) >= 1,
                  f"ws={bool(row and row[0].get('workspace_id'))} cast={len(cast or [])}")

        # 4. no orphan left anywhere
        _, orphans = _req("GET", f"{SB}/rest/v1/chat_sessions?workspace_id=is.null&select=id", SVC)
        check("4 no NULL-workspace lane rows exist", not (orphans or []),
              f"{len(orphans or [])} found")

    finally:
        # ── teardown: the probe owns everything it made ───────────────────
        if uid:
            _, mine = _req("GET", f"{SB}/rest/v1/workspaces?owner_id=eq.{uid}&select=id", SVC)
            for w in mine or []:
                _req("DELETE", f"{SB}/rest/v1/workspace_files?workspace_id=eq.{w['id']}", SVC)
                _req("DELETE", f"{SB}/rest/v1/conversation_members?workspace_id=eq.{w['id']}", SVC)
            _req("DELETE", f"{SB}/rest/v1/chat_sessions?user_id=eq.{uid}", SVC)
            for w in mine or []:
                _req("DELETE", f"{SB}/rest/v1/workspaces?id=eq.{w['id']}", SVC)
            _req("DELETE", f"{SB}/auth/v1/admin/users/{uid}", SVC)
            _, left = _req("GET", f"{SB}/rest/v1/workspaces?owner_id=eq.{uid}&select=id", SVC)
            print(f"teardown: probe user removed, workspaces left={len(left or [])}")

    ok = all(results) and results
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — {sum(results)}/{len(results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
