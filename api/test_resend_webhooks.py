import base64
import hashlib
import hmac

from routes.webhooks import verify_resend_signature, _merge_export_outcome


def _sign(secret: str, svix_id: str, svix_timestamp: str, payload: bytes) -> str:
    raw = secret[6:] if secret.startswith("whsec_") else secret
    key = base64.b64decode(raw)
    signed = f"{svix_id}.{svix_timestamp}.{payload.decode('utf-8')}"
    digest = hmac.new(key, signed.encode("utf-8"), hashlib.sha256).digest()
    return f"v1,{base64.b64encode(digest).decode('utf-8')}"


def test_verify_resend_signature_valid(monkeypatch):
    secret = "whsec_" + base64.b64encode(b"test-signing-secret").decode("utf-8")
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", secret)

    payload = b'{"type":"email.delivered","data":{"email_id":"abc"}}'
    svix_id = "msg_123"
    svix_timestamp = "1710000000"
    signature = _sign(secret, svix_id, svix_timestamp, payload)

    assert verify_resend_signature(payload, svix_id, svix_timestamp, signature) is True


def test_verify_resend_signature_invalid(monkeypatch):
    secret = "whsec_" + base64.b64encode(b"test-signing-secret").decode("utf-8")
    monkeypatch.setenv("RESEND_WEBHOOK_SECRET", secret)

    payload = b'{"type":"email.delivered","data":{"email_id":"abc"}}'
    svix_id = "msg_123"
    svix_timestamp = "1710000000"

    assert verify_resend_signature(payload, svix_id, svix_timestamp, "v1,invalid") is False


# RE-CUT 2026-09-21. `test_resend_event_status_mappings` imported
# `_map_resend_event_to_delivery_status` and `_map_resend_event_to_log_status`,
# BOTH deleted 2026-08-26 when migration 248 dropped `agent_runs` and took their
# only consumer with them. The import is at module scope, so this file errored at
# COLLECTION and reported nothing for 26 days — a dead gate, not a failing one,
# and the two live signature arms below went unrun with it.
#
# The event type is no longer mapped to a status at all: it rides raw into
# `_merge_export_outcome`, and `export_log.outcome` is the whole delivery record.
# So the mapping test has no subject and is not restorable. What IS still true —
# that an event lands on the outcome record under its own name — is asserted
# instead, over the function that replaced them.
#
# ⭐A module-scope import of a deleted symbol makes a gate silent, not red.


def test_merge_export_outcome_records_the_event_under_its_own_name():
    """The mapper's successor: the raw event type IS the record (2026-08-26)."""
    merged = _merge_export_outcome(None, "email.delivered", {"data": {}}, "2026-09-21T00:00:00Z")
    assert merged, "an event produced no outcome record"
    assert "email.delivered" in str(merged), \
        "the event type is not recoverable from the outcome it wrote"

    # A second event must not erase the first — the record accumulates.
    again = _merge_export_outcome(merged, "email.clicked", {"data": {}}, "2026-09-21T00:01:00Z")
    assert "email.delivered" in str(again), "the earlier event was overwritten"
    assert "email.clicked" in str(again), "the later event was not recorded"
