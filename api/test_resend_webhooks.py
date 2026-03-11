import base64
import hashlib
import hmac

from routes.webhooks import (
    verify_resend_signature,
    _map_resend_event_to_delivery_status,
    _map_resend_event_to_log_status,
)


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


def test_resend_event_status_mappings():
    assert _map_resend_event_to_delivery_status("email.delivered") == "delivered"
    assert _map_resend_event_to_delivery_status("email.bounced") == "failed"
    assert _map_resend_event_to_delivery_status("email.complained") == "failed"
    assert _map_resend_event_to_delivery_status("email.opened") is None

    assert _map_resend_event_to_log_status("email.delivered") == "delivered"
    assert _map_resend_event_to_log_status("email.clicked") == "clicked"
