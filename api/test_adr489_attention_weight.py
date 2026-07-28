"""ADR-489 regression gate — attention weight, the third axis of the one derivation.

D1 — the kernel classifier is BEHAVIORALLY tested (imported and CALLED on the
     audit's literal symptom rows), not text-grepped: `_recent_execution.md`
     must classify housekeeping, a radar brief derivation material, a failed
     run material.
D2 — the mounts pick depth by weight: bell = material only (badge included);
     workbench = "What matters" default with "Everything" one click away.
D3 — the radar face: `system:radar` labels as Researcher (fact stays the ledger).
D4 — the outbound witness seam sends (email transport), still writes NO
     in_app rows (ADR-410 D3 intent preserved).
D5 — one prefs store: member_state['notification_prefs']; the legacy
     user_notification_preferences surface is deleted.

Run: .venv/bin/python api/test_adr489_attention_weight.py
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


def test_d1_classifier_behavior() -> None:
    print("\n[D1] the classifier, executed on the audit's literal symptoms")
    from services.attention import classify_weight

    # The screenshot rows that started this ADR — machine bookkeeping.
    for path in (
        "operation/_shared/_recent_execution.md",
        "system/_schedule_index.md",
        "radar/ai-frontier/_watch_signal.yaml",
    ):
        _assert(
            classify_weight("revision", path=path) == "housekeeping",
            f"underscore machine state is housekeeping: {path}",
        )

    # System-zone roots are housekeeping even without the underscore.
    from services.workspace_paths import WORKSPACE_ROOTS

    system_roots = [r for r, m in WORKSPACE_ROOTS.items() if m.get("group") == "system"]
    _assert(bool(system_roots), "WORKSPACE_ROOTS declares at least one system-zone root")
    if system_roots:
        _assert(
            classify_weight("revision", path=f"{system_roots[0]}/back-office.yaml") == "housekeeping",
            f"system-zone revision is housekeeping ({system_roots[0]}/)",
        )

    # Raw arrivals (DP32 retained intake) are routine — legible, not demanding.
    _assert(
        classify_weight(
            "revision",
            path="downloads/web/2026-07-27T225809Z.xml",
            revision_kind="observation",
        )
        == "routine",
        "observation (raw arrival) is routine",
    )

    # The Researcher's brief — a derivation the member did NOT author — is
    # material (ADR-486: notification after-witness by default).
    _assert(
        classify_weight(
            "revision",
            path="radar/ai-frontier/briefs/2026-07-27-claude-opus-5-release.md",
            revision_kind="derivation",
        )
        == "material",
        "a radar brief derivation is material",
    )

    # An authored act by any principal is material.
    _assert(
        classify_weight("revision", path="operation/documents/hello.md") == "material",
        "an authored document write is material",
    )

    # Invocations: failures demand attention; judgment runs are legibility;
    # mechanical machinery is housekeeping.
    _assert(classify_weight("invocation", mode="mechanical", status="failed") == "material",
            "a failed run is material regardless of mode")
    _assert(classify_weight("invocation", mode="judgment", status="success") == "routine",
            "a judgment run is routine (its output surfaces as a revision)")
    _assert(classify_weight("invocation", mode="mechanical", status="success") == "housekeeping",
            "a mechanical run is housekeeping")

    # Witness events + fail-open defaults.
    _assert(classify_weight("proposal") == "material", "proposals are material")
    _assert(classify_weight("someday-new-kind") == "material",
            "unknown kinds fail OPEN to material (never silently hidden)")
    _assert(classify_weight("revision", path="new-meaning-folder/note.md") == "material",
            "unknown roots fail open (a future meaning-folder is never demoted)")


def test_d1_timeline_stamps_weight() -> None:
    print("\n[D1] the timeline derivation stamps weight (derived, never stored)")
    ws = _read("api/routes/workspace.py")
    _assert("from services.attention import classify_weight" in ws,
            "the endpoint uses the ONE classifier")
    _assert("revision_kind, created_at" in ws,
            "the revision read selects revision_kind (ADR-423 fact, now consumed)")
    _assert('weight: str = "material"' in ws, "TimelineEntry carries weight, default material")
    _assert(ws.count("classify_weight(") >= 2,
            "revisions AND invocations classify (proposals ride the material default)")


def test_d2_mounts_pick_depth() -> None:
    print("\n[D2] the mounts pick their depth by weight")
    bell = _read("web/components/shell/AttentionCenter.tsx")
    _assert("isMaterial" in bell, "the bell has the material-only gate")
    _assert("if (!isMaterial(e.weight)) continue;" in bell,
            "bell ACTIVITY (and therefore the badge) admits material acts only")

    ledger = _read("web/components/notifications/ActivityLedger.tsx")
    _assert("WeightLens" in ledger and "'matters'" in ledger,
            "the workbench has a weight lens, default 'What matters'")
    _assert("What matters" in ledger and "Everything" in ledger,
            "the complete record stays one click away")
    _assert("e.weight === 'housekeeping'" in ledger,
            "housekeeping filters (and recedes when shown)")

    client = _read("web/lib/api/client.ts")
    _assert("weight?: 'material' | 'routine' | 'housekeeping'" in client,
            "the FE timeline type carries weight")


def test_d3_radar_face() -> None:
    print("\n[D3] the face is the resident, the fact is the ledger")
    attr = _read("web/lib/workspace/attribution.ts")
    _assert("system:radar" in attr and "'Researcher'" in attr,
            "system:radar labels as Researcher (authored_by unchanged)")


def test_d4_witness_transport_real() -> None:
    print("\n[D4] the outbound witness seam is real — and writes no in_app rows")
    w = _read("api/services/witness.py")
    _assert('pref="witness"' in w and "send_notification" in w,
            "the send loop landed, routed through the ONE gated send path")
    _assert('channel="in_app"' not in w and "'in_app'" not in w,
            "no in_app rows from the witness path (ADR-410 D3 intent preserved)")
    _assert("workspace_id=workspace_id" in w,
            "transport rows are workspace-stamped (ADR-407 D8)")

    # The dial itself lives in the singular prefs reader (not duplicated in
    # witness.py) — one gate, N callers.
    notif = _read("api/services/notifications.py")
    _assert("notification_prefs" in notif and "member_state" in notif,
            "prefs read from member_state (the ADR-407 D7 home)")
    _assert('"witness_email"' in notif and '"high"' in notif,
            "witness_email dial (all|high|none), default 'high' — quiet by default")

    # Behavioral: the pref gate logic is pure — call it.
    from services.notifications import DEFAULT_NOTIFICATION_PREFS, _pref_allows

    _assert(_pref_allows(DEFAULT_NOTIFICATION_PREFS, "witness", "normal") is False,
            "default dial ('high') stays quiet at normal urgency")
    _assert(_pref_allows(DEFAULT_NOTIFICATION_PREFS, "witness", "high") is True,
            "default dial sends at high urgency")
    _assert(_pref_allows({"witness_email": "all"}, "witness", "low") is True,
            "'all' opts into every after-witness push")
    _assert(_pref_allows({"witness_email": "none"}, "witness", "high") is False,
            "'none' silences even high urgency")
    _assert(_pref_allows({"delivery_email": False}, "delivery", "normal") is False,
            "delivery pref honored")
    _assert(_pref_allows(DEFAULT_NOTIFICATION_PREFS, "failure", "high") is True,
            "failure pref defaults on")


def test_d4_dial_open_sends() -> None:
    """Behavioral: with witness_email='all', emit_after_witness actually
    sends — one workspace-stamped transport row per told recipient, actor
    excluded. Email + user-lookup are faked; the DB surface is a sink."""
    print("\n[D4] dial open — the send loop delivers (faked transports)")
    import asyncio
    import types

    WS = "00000000-0000-0000-0000-00000000aaaa"
    OWNER = "00000000-0000-0000-0000-000000000001"
    MEMBER = "00000000-0000-0000-0000-000000000002"

    class _Q:
        def __init__(self, sink, table, rows):
            self._sink, self._table, self._rows = sink, table, rows

        def select(self, *a, **k):
            return self

        def insert(self, row):
            self._sink.setdefault("inserts", []).append((self._table, row))
            self._rows = [{"id": "n-1", **row}]
            return self

        def update(self, row):
            return self

        def eq(self, *a):
            return self

        def in_(self, *a):
            return self

        def limit(self, *a):
            return self

        def execute(self):
            r = types.SimpleNamespace()
            r.data = self._rows
            return r

    class _Client:
        def __init__(self):
            self.sink = {}

        def table(self, name):
            rows = []
            if name == "principal_grants":
                rows = [
                    {"principal_id": OWNER, "role": "owner"},
                    {"principal_id": MEMBER, "role": "member"},
                ]
            elif name == "workspaces":
                rows = [{"owner_id": OWNER}]
            elif name == "member_state":
                rows = [{"value": {"witness_email": "all"}}]
            return _Q(self.sink, name, rows)

    # Fake the two transports the send path reaches for: the user-email
    # lookup (jobs.unified_scheduler) and the Resend send.
    async def _fake_get_user_email(client, user_id):
        return f"{user_id[:8]}@example.com"

    sys.modules.setdefault("jobs", types.ModuleType("jobs"))
    fake_sched = types.ModuleType("jobs.unified_scheduler")
    fake_sched.get_user_email = _fake_get_user_email
    sys.modules["jobs.unified_scheduler"] = fake_sched

    import services.notifications as notif_mod

    async def _fake_email(**kw):
        return types.SimpleNamespace(success=True, error=None)

    original_email = notif_mod._send_notification_email
    notif_mod._send_notification_email = _fake_email
    try:
        from services.witness import emit_after_witness

        client = _Client()
        reached = asyncio.new_event_loop().run_until_complete(
            emit_after_witness(
                client,
                workspace_id=WS,
                actor_user_id=MEMBER,
                message="Proposal decided by a workspace principal",
                context={"proposal_id": "p-1"},
            )
        )
        rows = [r for t, r in client.sink.get("inserts", []) if t == "notifications"]
        _assert(reached == 1, "one recipient told (owner; the actor excluded)")
        _assert(len(rows) == 1, "exactly one transport row — a record of an actual send")
        if rows:
            _assert(rows[0].get("channel") == "email", "transport channel is email (in_app is dead)")
            _assert(rows[0].get("workspace_id") == WS, "the row is workspace-stamped (ADR-407 D8)")
            _assert(rows[0].get("user_id") == OWNER, "the row's user_id IS the recipient principal")
    finally:
        notif_mod._send_notification_email = original_email
        del sys.modules["jobs.unified_scheduler"]


def test_d5_one_prefs_store() -> None:
    print("\n[D5] one prefs store — the legacy surface is deleted")
    notif = _read("api/services/notifications.py")
    _assert("user_notification_preferences" not in notif,
            "the send path reads member_state, not the dropped table")
    _assert("_insert_chat_notification" not in notif,
            "the private-thread email echo is deleted (no second attention store)")
    _assert('channel: Literal["email", "in_app"]' not in notif,
            "the in_app channel branch is deleted")

    account = _read("api/routes/account.py")
    _assert("notification-preferences" not in account,
            "the legacy account routes are deleted")

    sched = _read("api/jobs/unified_scheduler.py")
    _assert("def should_send_email" not in sched,
            "should_send_email moved out of the scheduler module")
    _assert("get_notification_preferences" not in sched,
            "the dropped RPC has no reader")

    client = _read("web/lib/api/client.ts")
    _assert("notification-preferences" not in client,
            "the dead FE client methods are deleted")

    migration = os.path.join(REPO, "supabase/migrations/223_adr489_notification_prefs_fold.sql")
    _assert(os.path.exists(migration), "migration 223 exists")
    if os.path.exists(migration):
        sql = _read("supabase/migrations/223_adr489_notification_prefs_fold.sql")
        _assert("DROP TABLE" in sql and "user_notification_preferences" in sql,
                "the legacy prefs table drops")
        _assert("workspace_id" in sql and "notifications" in sql,
                "the transport table gains the workspace stamp")


if __name__ == "__main__":
    test_d1_classifier_behavior()
    test_d1_timeline_stamps_weight()
    test_d2_mounts_pick_depth()
    test_d3_radar_face()
    test_d4_witness_transport_real()
    test_d4_dial_open_sends()
    test_d5_one_prefs_store()
    print("\n" + "=" * 60)
    print(f"ADR-489 gate: {_passed} passed, {_failed} failed")
    print("=" * 60)
    sys.exit(1 if _failed else 0)
