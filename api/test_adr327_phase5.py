"""ADR-327 Phase 5 gate — self-improving loop (D6).

Covers:
  - SYSTEM_CALIBRATION_PATH constant
  - mirror_calibration primitive composes evidence diff-aware (fake client)
  - kernel_mirrors exposes mirror_calibration_for_all_users
  - scheduler tick wires the calibration mirror
  - reviewer envelope carries calibration_md slot
  - ReviewerContext.calibration_md field
  - reviewer_agent renders _calibration.md + minimal-frame posture cites it
  - bundle MANIFEST declares substrate_abi.ground_truth + reader resolves it
  - workspace guide pedagogy updated (calibration + budget reframe)

Usage:
    cd api
    python test_adr327_phase5.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))
_REPO_ROOT = _API_ROOT.parent
try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
except Exception:
    pass

PASSED = 0
FAILED = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        FAILED += 1


# ─── Fake client: serves canned tables for the mirror's queries ──────────────


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def gte(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        class _R:
            pass
        r = _R()
        r.data = self._rows
        return r


class _FakeClient:
    """Returns per-table canned data; records writes."""
    def __init__(self, tables):
        self._tables = tables
        self.writes = []

    def table(self, name):
        return _FakeQuery(self._tables.get(name, []))


class _Auth:
    def __init__(self, client, user_id="u" * 36):
        self.client = client
        self.user_id = user_id


# ─── Constant + imports ──────────────────────────────────────────────────────


def test_constant() -> None:
    print("\n[const] SYSTEM_CALIBRATION_PATH")
    from services.workspace_paths import SYSTEM_CALIBRATION_PATH
    check("path == system/_calibration.md", SYSTEM_CALIBRATION_PATH == "system/_calibration.md")


def test_mirror_composes(monkeypatch_writes=None) -> None:
    print("\n[mirror] handle_mirror_calibration composes + writes evidence")
    from services.primitives import mirror_calibration as mc

    # Patch write_revision to capture instead of hitting the DB.
    captured = {}

    def _fake_write_revision(client, **kw):
        captured.update(kw)
        return {"ok": True}

    import services.authored_substrate as asub
    orig = asub.write_revision
    asub.write_revision = _fake_write_revision

    # Patch the recurrence walker + ground-truth reader to avoid DB.
    import services.recurrence as rec_mod
    import services.bundle_reader as br

    class _Rec:
        def __init__(self, slug, mode="judgment"):
            self.slug = slug
            self.mode = mode

    orig_walk = rec_mod.walk_workspace_recurrences
    orig_gt = br.get_ground_truth_for_workspace
    rec_mod.walk_workspace_recurrences = lambda c, u: [_Rec("signal-evaluation"), _Rec("track-x", "mechanical")]
    br.get_ground_truth_for_workspace = lambda u, c: "operation/trading/_money_truth.md"

    try:
        client = _FakeClient({
            "workspace_file_versions": [
                {"created_at": "2026-06-07T10:00:00Z", "authored_by": "reviewer:ai-v1", "message": "tightened signal-evaluation window"},
            ],
            "execution_events": [
                {"status": "success", "funnel_decision": "escalate", "created_at": "2026-06-08T13:45:00Z"},
                {"status": "success", "funnel_decision": "escalate", "created_at": "2026-06-07T13:45:00Z"},
                {"status": "success", "funnel_decision": "escalate", "created_at": "2026-06-06T13:45:00Z"},
            ],
            "action_proposals": [],  # zero proposals → should flag miscalibration
            "workspace_files": [{"content": "## Money Truth\n7d P&L: +$120\n"}],
        })
        result = asyncio.run(mc.handle_mirror_calibration(_Auth(client), {"diff_aware": False}))
        check("mirror returns success", result.get("success") is True, str(result))
        check("correlated the judgment slug", result.get("slugs_correlated") == 1, str(result.get("slugs_correlated")))
        content = captured.get("content", "")
        check("wrote to _calibration.md path", captured.get("path", "").endswith("system/_calibration.md"))
        check("authored_by system:mirror-calibration", captured.get("authored_by") == "system:mirror-calibration")
        check("evidence names signal-evaluation", "signal-evaluation" in content)
        check("flags miscalibration (fired+escalated, 0 proposals)", "miscalibrated" in content or "no proposals" in content)
        check("includes cadence-authoring trail", "tightened signal-evaluation window" in content)
        check("includes ground-truth head", "Money Truth" in content)
        check("mechanical slug excluded from per-recurrence", "**track-x**" not in content)
    finally:
        asub.write_revision = orig
        rec_mod.walk_workspace_recurrences = orig_walk
        br.get_ground_truth_for_workspace = orig_gt


def test_kernel_mirrors_runner() -> None:
    print("\n[kernel_mirrors] mirror_calibration_for_all_users exported")
    import services.kernel_mirrors as km
    check("runner exists", hasattr(km, "mirror_calibration_for_all_users"))


def test_scheduler_wiring() -> None:
    print("\n[scheduler] tick wires calibration mirror")
    src = (_API_ROOT / "jobs/unified_scheduler.py").read_text()
    check("imports mirror_calibration_for_all_users", "mirror_calibration_for_all_users" in src)
    check("calls cal_summary", "cal_summary" in src)


def test_envelope_slot() -> None:
    print("\n[envelope] calibration_md slot")
    from services.reviewer_envelope import _UNIVERSAL_ENVELOPE_DECLS
    decls = dict(_UNIVERSAL_ENVELOPE_DECLS)
    check("calibration_md in envelope", "calibration_md" in decls)
    check("→ system/_calibration.md", decls.get("calibration_md") == "system/_calibration.md")


def test_reviewer_context_field() -> None:
    print("\n[contract] ReviewerContext.calibration_md")
    from agents.occupant_contract import ReviewerContext
    check("calibration_md field present", "calibration_md" in ReviewerContext.__annotations__)


def test_reviewer_agent_renders_and_posture() -> None:
    print("\n[reviewer_agent] renders _calibration.md + posture cites it")
    src = (_API_ROOT / "agents/reviewer_agent.py").read_text()
    check("renders _calibration.md header", "_calibration.md" in src)
    check("reads ctx calibration_md", 'ctx.get("calibration_md")' in src)
    check("minimal-frame posture cites calibration", "_calibration.md" in src and "falsified" in src)


def test_bundle_ground_truth() -> None:
    print("\n[bundle] substrate_abi.ground_truth declared + reader resolves")
    import yaml
    manifest_path = _REPO_ROOT / "docs/programs/alpha-trader/MANIFEST.yaml"
    raw = manifest_path.read_text()
    parsed = yaml.safe_load(raw)
    abi = parsed.get("substrate_abi") or {}
    check("ground_truth declared", abi.get("ground_truth") == "operation/trading/_money_truth.md", str(abi.get("ground_truth")))


def test_workspace_guide_pedagogy() -> None:
    print("\n[guide] workspace guide updated for calibration + budget")
    guide = (_REPO_ROOT / "docs/programs/alpha-trader/reference-workspace/_workspace_guide.md").read_text()
    check("Pulse Discipline names _calibration.md", "_calibration.md" in guide)
    check("cadence section reframed to Budget", "Budget + Autonomy + Identity" in guide)
    check("names the self-improving loop", "self-improving loop" in guide)
    check("no stale 'within the operator's pace' heading", "within the operator's pace (Pace + Autonomy + Persona" not in guide)


def main() -> int:
    print("=" * 64)
    print("ADR-327 Phase 5 — self-improving loop (D6)")
    print("=" * 64)
    test_constant()
    test_mirror_composes()
    test_kernel_mirrors_runner()
    test_scheduler_wiring()
    test_envelope_slot()
    test_reviewer_context_field()
    test_reviewer_agent_renders_and_posture()
    test_bundle_ground_truth()
    test_workspace_guide_pedagogy()
    print("\n" + "=" * 64)
    print(f"  PASSED={PASSED}  FAILED={FAILED}")
    print("=" * 64)
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
