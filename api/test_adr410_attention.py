"""ADR-410 + ADR-412 D6 regression gate — attention derives from the timeline.

One derivation, N mounts (ADR-410 §2): "what wants me" = the witness queue;
"what happened" = the workspace timeline, filtered per viewer. Plus the
ADR-412 D6 viewer-resolution layer both ride on.

  D1 — the bell's ACTIVITY re-sources to the timeline, peer-first
       (chat.globalHistory derivation deleted; self excluded via the viewer
       layer).
  D2 — TO DO is the honest witness queue (proposer + dial line); the
       hygiene one-shot exists (applied 2026-07-06: 7/7 pre-D3 substrate
       zombies expired with reason).
  D3 — the `notifications` table returns to outbound transport: witness.py
       writes NO in_app rows; the recipient derivation survives as the seam.
  D4 — vocabulary: actor-first lines, no internal enums in bell rows.
  D6 — timeline entries carry stable ids + actor_id; human-write routes
       thread author_identity_uuid (operator-class acts stop being
       ambiguous between humans).

Run: .venv/bin/python api/test_adr410_attention.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_passed = 0
_failed = 0


def _assert(cond: bool, msg: str) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {msg}")
    else:
        _failed += 1
        print(f"  FAIL  {msg}")


def _read(rel: str) -> str:
    with open(os.path.join(REPO, rel)) as f:
        return f.read()


def test_d1_bell_resources_to_timeline() -> None:
    print("\n[D1] the bell derives ACTIVITY from the timeline, peer-first")
    bell = _read("web/components/shell/AttentionCenter.tsx")
    _assert("api.chat.globalHistory(" not in bell, "chat.globalHistory derivation deleted (comment mentions allowed)")
    _assert("api.workspace.timeline" in bell, "timeline is the 'what happened' source")
    _assert("resolveActorForViewer" in bell, "viewer resolution applied (ADR-412 D6)")
    _assert("isSelf" in bell and "filter" in bell, "self-acts excluded by construction (ADR-405 D4)")
    _assert("unseenPeer" in bell, "badge counts unseen PEER acts (+ witness queue)")


def test_d2_witness_queue_honest() -> None:
    print("\n[D2] TO DO is the honest witness queue")
    bell = _read("web/components/shell/AttentionCenter.tsx")
    _assert("proposalQueuedByDialLine" in bell, "queue rows carry the dial line (agent's dial product)")
    _assert("source" in bell, "queue rows carry the proposer")
    _assert(
        os.path.exists(
            os.path.join(REPO, "api/scripts/oneshot/adr410_d2_expire_stale_substrate_proposals.py")
        ),
        "the hygiene one-shot exists (expired-with-reason, auditable)",
    )
    sweep = _read("api/scripts/oneshot/adr410_d2_expire_stale_substrate_proposals.py")
    _assert('"expired"' in sweep and "rejection_reason" in sweep, "sweep expires with reason, never deletes")
    _assert('.eq("family", "substrate")' in sweep, "sweep touches ONLY the substrate family (capital queue is real)")


def test_d3_notifications_outbound_only() -> None:
    print("\n[D3] the notifications table returns to outbound transport")
    w = _read("api/services/witness.py")
    _assert("send_notification" not in w, "witness emission writes NO in_app rows")
    _assert('channel="in_app"' not in w, "no in_app channel usage")
    _assert("workspace_witnesses" in w, "the recipient derivation survives (the outbound seam)")
    _assert("ADR-410 D3" in w, "the retirement is attributed in-source")


def test_d4_vocabulary() -> None:
    print("\n[D4] actor-first vocabulary, no internal enums")
    bell = _read("web/components/shell/AttentionCenter.tsx")
    _assert("activityLine" in bell, "actor-first line composer exists")
    _assert("trigger_type" not in bell, "wake-source / trigger enums never render in the bell")
    _assert("ADDRESSED" not in bell, "no wake_source vocabulary")


def test_d6_timeline_ids_and_identity() -> None:
    print("\n[D6] stable timeline ids + acting-principal identity")
    ws = _read("api/routes/workspace.py")
    _assert('id=f"revision:' in ws and 'id=f"invocation:' in ws and 'id=f"proposal:' in ws,
            "entries carry derived stable ids (kind:natural-key:at)")
    _assert("author_identity_uuid" in ws.split("class TimelineEntry", 1)[1][:2000] or "actor_id" in ws,
            "TimelineEntry carries actor_id")
    _assert('.select("path, authored_by, author_identity_uuid, message, created_at")' in ws,
            "revision read selects the acting principal's uuid")

    # Human-write routes thread identity — operator-class acts stop being
    # ambiguous between humans in a multi-member commons.
    _assert("author_identity_uuid=auth.user_id" in ws, "PATCH /workspace/file threads the acting human")
    mem = _read("api/routes/memory.py")
    _assert("author_identity_uuid=auth.user_id" in mem, "identity/brand edits thread the acting human")
    docs = _read("api/routes/documents.py")
    _assert("author_identity_uuid=auth.user_id" in docs, "document writes thread the acting human")
    svc = _read("api/services/workspace.py")
    _assert("author_identity_uuid=author_identity_uuid" in svc, "UserMemory.write passes identity through")

    client = _read("web/lib/api/client.ts")
    _assert("actor_id: string | null" in client, "FE timeline type carries actor_id")


def test_viewer_layer() -> None:
    print("\n[D6/ADR-412] the viewer-resolution layer")
    v = _read("web/lib/workspace/viewer.ts")
    _assert("useWorkspaceRoster" in v, "roster hook exists (module-cached, membership not presence)")
    _assert("resolveActorForViewer" in v, "first-person resolver exists")
    _assert("memberEmbodiment" in v, "lane embodiments resolve ('You via ‹model›')")
    _assert("isSelf: true" in v, "legacy identity-less operator rows resolve as self (quiet default)")
    _assert("formatAuthorLabelOrSystem" in v, "non-human classes pass through the existing labeler (ADR-388 D3)")


if __name__ == "__main__":
    test_d1_bell_resources_to_timeline()
    test_d2_witness_queue_honest()
    test_d3_notifications_outbound_only()
    test_d4_vocabulary()
    test_viewer_layer()
    test_d6_timeline_ids_and_identity()
    print("\n" + "=" * 60)
    print(f"ADR-410 gate: {_passed} passed, {_failed} failed")
    print("=" * 60)
    sys.exit(1 if _failed else 0)
