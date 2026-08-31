"""ADR-622 — the upload handshake: mint a capability, carry the bytes beside it.

THE PROBLEM. The connector speaks text. `save` writes text and refuses a binary
head (ADR-621 D3), so a principal holding bytes — an image, a video, a PDF — had
no door at all. Base64 through the conversation is not the answer: it is measured
to corrupt (Box, at 175KB), MCP tool INPUTS have no blob type, and yarnnn's MCP
server is REMOTE, so it cannot read the caller's disk either.

THE SHAPE. Control channel mints a short-lived single-use capability; a separate
authenticated HTTP channel carries the bytes into the ONE existing upload
pipeline. Box, Notion, Dropbox, S3 and SEP-2631 all converge here.

WHAT IS GATED
  1. The ticket is a ROW, not a signed string — statelessness cannot be
     single-use, and single-use is the property that makes a write capability
     safe to hand out.
  2. The claim is a COMPARE-AND-SET (update … where redeemed_at is null), not a
     read-then-write: two concurrent redemptions of one ticket must not both
     proceed.
  3. Authorization happens at MINT and is FROZEN — the redeemer supplies bytes
     and nothing else, so a leaked ticket is bounded to the one write its minter
     was already allowed to make.
  4. The redemption goes through `_process_single_upload` — the SAME pipeline
     the browser upload uses. No second intake path (Singular Implementation).
  5. The ticket points at a yarnnn endpoint, never at a storage bucket — a
     bucket URL would bypass type-derivation-from-bytes, the caps,
     write_revision, attribution and the ADR-395 projection.
  6. `request_upload` is scoped files:write — gating the ticket below the write
     it authorizes would be a door around the write scope.

Usage:  cd api && python3 test_adr622_upload_handshake.py
"""

from __future__ import annotations

import inspect
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_ROOT = Path(__file__).parent
sys.path.insert(0, str(API_ROOT))

FAILURES: list[str] = []
PASSES = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASSES
    if ok:
        PASSES += 1
        print(f"PASS  {label}  {detail}")
    else:
        FAILURES.append(label)
        print(f"FAIL  {label}  {detail}")


# ---------------------------------------------------------------------------
# An in-memory ticket table that behaves like the real one for the CAS.
# ---------------------------------------------------------------------------

class _FakeTable:
    def __init__(self, store): self.store, self._f, self._upd, self._op = store, {}, None, "select"
    def select(self, *a, **k): self._op = "select"; return self
    def insert(self, row): self.store.append(dict(row)); self._op = "insert"; return self
    def update(self, patch): self._op, self._upd = "update", patch; return self
    def delete(self): self._op = "delete"; return self
    def eq(self, c, v): self._f[c] = v; return self
    def is_(self, c, v): self._f[c] = ("__isnull__", v); return self
    def gt(self, c, v): self._f[(c, "gt")] = v; return self
    def limit(self, *a, **k): return self

    def _match(self, r):
        for c, v in self._f.items():
            if isinstance(c, tuple):
                col, _ = c
                if not (r.get(col) and str(r[col]) > str(v)):
                    return False
            elif isinstance(v, tuple) and v[0] == "__isnull__":
                if r.get(c) is not None:
                    return False
            elif r.get(c) != v:
                return False
        return True

    def execute(self):
        class R: pass
        r = R()
        if self._op == "insert":
            r.data = [self.store[-1]]
        elif self._op == "update":
            hit = [x for x in self.store if self._match(x)]
            for x in hit:
                x.update(self._upd)
            r.data = [dict(x) for x in hit]
        elif self._op == "delete":
            keep = [x for x in self.store if not self._match(x)]
            self.store[:] = keep
            r.data = []
        else:
            r.data = [dict(x) for x in self.store if self._match(x)]
        return r


class _FakeClient:
    def __init__(self): self.rows = []
    def table(self, name): return _FakeTable(self.rows)


import services.upload_tickets as ut  # noqa: E402

svc = _FakeClient()
USER, WS = "11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222"

# --- 1. mint --------------------------------------------------------------
t = ut.mint_upload_ticket(svc, user_id=USER, workspace_id=WS, filename="clip.mp4",
                          minted_by="yarnnn:mcp:probe", destination="marketing/assets",
                          declared_bytes=1024)
check("1a mint returns an opaque token + expiry",
      bool(t["token"]) and len(t["token"]) >= 32 and t["destination"] == "marketing/assets")
row = svc.rows[0]
check("1b the row records WHO minted it (provenance, not authorization)",
      row["minted_by"] == "yarnnn:mcp:probe" and row["user_id"] == USER)
check("1c the ticket is short-lived (<= 1h)",
      (datetime.fromisoformat(row["expires_at"]) - datetime.now(timezone.utc))
      <= timedelta(seconds=ut.TICKET_TTL_SECONDS + 5))

# --- 2. the mint refuses what it must -------------------------------------
for bad, why in [("../etc/passwd", "traversal"), ("a/b.png", "a path, not a name"), ("", "empty")]:
    try:
        ut.mint_upload_ticket(svc, user_id=USER, workspace_id=WS, filename=bad,
                              minted_by="p", destination=None)
        check(f"2 filename refused ({why})", False, f"accepted {bad!r}")
    except ut.TicketError as e:
        check(f"2 filename refused ({why})", e.code == "invalid_filename")

try:
    ut.mint_upload_ticket(svc, user_id=USER, workspace_id=WS, filename="x.png",
                          minted_by="p", declared_bytes=ut.MAX_DECLARED_BYTES + 1)
    check("2d an over-cap size is refused at MINT (before any transfer)", False)
except ut.TicketError as e:
    check("2d an over-cap size is refused at MINT (before any transfer)", e.code == "too_large")

# ⭐ The destination is authorized at MINT, against the SAME gate the browser
# upload door uses — so the two doors cannot disagree about where a principal
# may write.
try:
    ut.mint_upload_ticket(svc, user_id=USER, workspace_id=WS, filename="x.png",
                          minted_by="p", destination="system")
    check("2e a system-managed destination is refused at MINT", False, "accepted 'system'")
except ut.TicketError as e:
    check("2e a system-managed destination is refused at MINT", e.code == "destination_denied")

# --- 3. claim + single-use ------------------------------------------------
claimed = ut.claim_upload_ticket(svc, t["token"])
check("3a a live ticket claims once", claimed["filename"] == "clip.mp4")
check("3b the claim carries the FROZEN destination, not a caller's",
      claimed["destination"] == "marketing/assets")
try:
    ut.claim_upload_ticket(svc, t["token"])
    check("3c a second claim is REFUSED (single-use)", False, "replayed!")
except ut.TicketError as e:
    check("3c a second claim is REFUSED (single-use)", e.code == "already_redeemed")

try:
    ut.claim_upload_ticket(svc, "nope")
    check("3d an unknown token is refused", False)
except ut.TicketError as e:
    check("3d an unknown token is refused", e.code == "unknown_ticket")

# An expired ticket names its OWN state — not "unknown", which would send a
# caller retrying something that can never work (ADR-373 D6).
exp = ut.mint_upload_ticket(svc, user_id=USER, workspace_id=WS, filename="old.png",
                            minted_by="p")
for r in svc.rows:
    if r["filename"] == "old.png":
        r["expires_at"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
try:
    ut.claim_upload_ticket(svc, exp["token"])
    check("3e an expired ticket is refused AS expired", False)
except ut.TicketError as e:
    check("3e an expired ticket is refused AS expired", e.code == "expired", e.code)

# --- 4. the claim is a CAS, not a read-then-write -------------------------
src = inspect.getsource(ut.claim_upload_ticket)
check("4a the claim UPDATEs filtered on redeemed_at IS NULL (compare-and-set)",
      ".update(" in src and 'is_("redeemed_at"' in src)
check("4b it does NOT read-then-write (no select before the update)",
      src.index(".update(") < src.index("# Nothing claimed"),
      "the update is the claim")

# --- 5. one pipeline, one door -------------------------------------------
route_src = (API_ROOT / "routes/documents.py").read_text()
_redeem = route_src.split("async def redeem_upload_ticket(")[1].split("\n@router.")[0]
check("5a redemption goes through _process_single_upload (the ONE pipeline)",
      "_process_single_upload(" in _redeem)
check("5b the redeemer supplies BYTES ONLY — path/owner come from the ticket",
      'filename=ticket["filename"]' in route_src and 'user_id=ticket["user_id"]' in route_src
      and 'destination=ticket.get("destination")' in route_src)
# ⭐ A bucket URL would bypass type-derivation, the caps, write_revision,
# attribution and the projection — a SECOND intake path.
tickets_src = (API_ROOT / "services/upload_tickets.py").read_text()
check("5c no signed-BUCKET upload url anywhere (that would bypass the pipeline)",
      "create_signed_upload_url" not in tickets_src and "create_signed_upload_url" not in route_src)
check("5d the claim happens BEFORE the bytes are processed (spent by the attempt)",
      _redeem.index("claim_upload_ticket(") < _redeem.index("_process_single_upload("))

# --- 6. the verb is bound, scoped and rendered ---------------------------
scopes_src = (API_ROOT / "services/mcp_scopes.py").read_text()
m = re.search(r'"request_upload":\s*(SCOPE_\w+)', scopes_src)
check("6a request_upload is scoped files:write (not below the write it authorizes)",
      bool(m) and m.group(1) == "SCOPE_WRITE", f"scope={m.group(1) if m else 'ABSENT'}")

server_src = (API_ROOT / "mcp_server/server.py").read_text()
check("6b the verb is on the roster AND registered as a tool",
      '"request_upload",' in server_src and "async def request_upload(" in server_src)
check("6c its handler passes the verb to resolve_request_client (the scope gate)",
      'resolve_request_client(verb="request_upload")' in server_src)

aff_src = (API_ROOT / "mcp_server/presentation/affordances.py").read_text()
check("6d it has a written TEXT_ONLY reason (ADR-533 D4 rendering story)",
      '"request_upload": (' in aff_src)

# ⭐ The narrative must record a MINT, never an upload — nothing has landed yet.
# ⚠️ Scope this to the narrative CALL, not the whole function: the docstring
# WARNS the model not to claim the file was uploaded, and a comment explains why
# the summary avoids the word — so a function-wide substring test matches its own
# subject matter and can never pass. Test the expression that becomes the entry.
_ru = server_src.split("async def request_upload(")[1].split("\n@mcp.tool")[0]
_narr = _ru.split("_emit_mcp_narrative(")[1].split(")\n    return")[0]
check("6e the narrative records a MINT, not an upload",
      "requested an upload link for" in _ru and "upload" not in _narr.split("summary=")[1][:80],
      "summary names the request, never a landed file")

# --- 7. the answer tells the truth about who can redeem ------------------
import services.mcp_composition as mc  # noqa: E402
comp = inspect.getsource(mc.compose_request_upload)
check("7a the answer warns the bytes cannot travel through the conversation",
      "cannot send the bytes through this conversation" in comp)
check("7b it hands over a ready-to-run curl (not prose to reconstruct)",
      '"curl"' in comp and "-F 'file=@" in comp)
check("7c save's binary refusal now names request_upload as the remedy",
      "request_upload" in inspect.getsource(mc.compose_save))

print()
print("=" * 62)
if FAILURES:
    print(f"ADR-622: FAIL — {len(FAILURES)} assertion(s): {FAILURES}")
    sys.exit(1)
print(f"ADR-622 upload handshake: {PASSES}/{PASSES} assertions pass")
