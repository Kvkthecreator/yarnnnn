"""The desktop app's sign-in hand-off — ADR-661 §7r.

The desktop app never signs in by itself: the member's browser does, on
`/auth/desktop`, and hands the app a way in over `yarnnn://auth/session`
(ADR-661 §7i, §7p). What crosses that boundary is decided here.

It used to be the browser's OWN refresh token. That made the browser and the
app two holders of one session, and Supabase rotates a refresh token on every
use and revokes the whole session when a spent one is presented again. So the
first time the browser refreshed after the hand-off — the `/auth/desktop` tab
left open does it within the hour — it presented the token the app had
already spent, and both were signed out. The app found out at its next launch.

Now the browser asks this endpoint for a ONE-TIME sign-in code and hands the
app that instead. The app redeems it (`verifyOtp`) for a session of its own —
its own refresh-token chain, independent of the browser's, the way every
desktop client keeps its own device session. Signing out in one no longer
signs out the other.

⚠️ This mints a sign-in for an account, so the caller is verified BY SUPABASE
(`auth.get_user`), never by decoding the JWT locally as `get_user_client`
does: a forged token must not be able to name someone else's email. The code
is minted only for the email of the verified caller.

No email is sent: `admin.generate_link` returns the link's hashed token and
delivers nothing. The code is single-use and expires with the project's OTP
lifetime.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from services.supabase import get_service_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/handoff")
def desktop_handoff(authorization: Optional[str] = Header(None)) -> dict:
    """A one-time code the desktop app redeems for its own session."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    jwt = authorization.removeprefix("Bearer ").strip()

    service = get_service_client()
    try:
        user = service.auth.get_user(jwt).user
    except Exception:
        user = None
    if not user:
        raise HTTPException(status_code=401, detail="Sign in again to open the app")
    if not user.email:
        raise HTTPException(status_code=400, detail="This account has no email to sign the app in with")

    try:
        link = service.auth.admin.generate_link({"type": "magiclink", "email": user.email})
    except Exception as exc:
        logger.error("[desktop handoff] could not mint a code for %s: %s", user.id, exc)
        raise HTTPException(status_code=502, detail="Could not sign the app in just now")
    return {"token_hash": link.properties.hashed_token}
