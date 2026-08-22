"""Action-feedback layer gate — docs/design/ACTION-FEEDBACK.md (amended 2026-08-22).

Script-style (python3 test_action_feedback_layer.py from api/). Locks the
transient-surfacing streamline:
  1. The toast corridor is TOP-RIGHT, always-mounted (live-region rule),
     reduced-motion aware.
  2. The native dialog trio stays dead (window.confirm/alert; prompt has one
     NAMED survivor in FlowEditor, owed an inline replacement).
  3. The migrated offenders stay migrated (no hand-rolled toast/confirm
     re-growth at the swept sites).
  4. Copy-flip micro-feedback rides the one duration token.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
WEB = API.parent / "web"

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
    return (WEB / rel).read_text(encoding="utf-8")


def _strip_comments(src: str) -> str:
    """Drop // and /* */ comments so a check can never pass (or fail) on prose
    — the assert-the-composition-not-the-comment lesson."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"(?m)^\s*//.*$", "", src)
    src = re.sub(r"(?m)\s//(?![:/]).*$", "", src)  # trailing //, spare URLs
    return src


def test_corridor() -> None:
    print("\n[1] the toast corridor — top-right, always-mounted, motion-aware")
    fc = _read("contexts/FeedbackContext.tsx")
    code = _strip_comments(fc)
    _assert("top-[4.25rem] right-4" in code,
            "the stack renders top-right below the top bar (operator ruling 2026-08-22)")
    _assert("fixed bottom-4 right-4" not in code,
            "the bottom-right default is gone")
    # The live-region rule: the viewport must not unmount on empty — the
    # broken form gated the portal on `toasts.length === 0`.
    m = re.search(r"function ToastViewport.*?createPortal", code, flags=re.DOTALL)
    _assert(bool(m) and "toasts.length === 0" not in (m.group(0) if m else ""),
            "the viewport mounts EMPTY (a live region must pre-exist its first message)")
    _assert("aria-live" in code, "the viewport is a live region")
    _assert("slide-in-from-top-2" in code and "motion-reduce:animate-none" in code,
            "entrance slides from the top and respects prefers-reduced-motion")
    _assert("COPY_FEEDBACK_MS = 2000" in code,
            "the copy-flip duration token is declared here (2000ms)")


def test_native_trio_dead() -> None:
    print("\n[2] the native dialog trio stays dead")
    offenders_confirm: list[str] = []
    offenders_alert: list[str] = []
    offenders_prompt: list[str] = []
    for sub in ("components", "app", "hooks", "contexts", "lib"):
        root = WEB / sub
        if not root.exists():
            continue
        for f in root.rglob("*.tsx"):
            rel = f.relative_to(WEB).as_posix()
            src = _strip_comments(f.read_text(encoding="utf-8", errors="ignore"))
            if "window.confirm(" in src:
                offenders_confirm.append(rel)
            if "window.alert(" in src:
                offenders_alert.append(rel)
            if "window.prompt(" in src:
                offenders_prompt.append(rel)
    _assert(not offenders_confirm, f"no window.confirm in product surfaces ({offenders_confirm})")
    _assert(not offenders_alert, f"no window.alert in product surfaces ({offenders_alert})")
    _assert(offenders_prompt == ["components/authoring/FlowEditor.tsx"],
            f"window.prompt has exactly its ONE named survivor, owed an inline replacement ({offenders_prompt})")


def test_swept_sites_stay_swept() -> None:
    print("\n[3] the migrated offenders stay migrated")
    settings = _strip_comments(_read("app/(authenticated)/settings/page.tsx"))
    _assert("fixed bottom-4 right-4" not in settings and "purgeSuccess" not in settings,
            "Settings: the hand-rolled bottom-right toast is gone")
    _assert("fixed inset-0" not in settings,
            "Settings: the bespoke confirm modal is gone (the canonical gate confirms)")
    _assert("runAction" in settings and "danger: true" in settings,
            "Settings: danger zone gates + reports through the canonical layer")

    trash = _strip_comments(_read("components/workspace/TrashView.tsx"))
    _assert("confirmingDelete" not in trash and "confirmingEmpty" not in trash,
            "TrashView: the inline second-click gates are gone")
    _assert("confirmDialog" in trash and trash.count("danger: true") >= 2,
            "TrashView: permanent delete + empty trash carry the styled danger gate")

    conn = _strip_comments(_read("components/settings/ConnectedIntegrationsSection.tsx"))
    _assert("confirmDialog({" in conn and "runAction(" in conn,
            "Connector disconnect: canonical gate + reported outcome (no more silent failure)")

    _assert("confirmDialog({" in _strip_comments(_read("components/subscription/SubscriptionCard.tsx")),
            "Plan cancellation: canonical danger gate")
    _assert("confirmDialog({" in _strip_comments(_read("components/authoring/PagedNavigator.tsx")),
            "Multi-slide delete: canonical danger gate")

    rec = _strip_comments(_read("app/(authenticated)/recurrence/page.tsx"))
    _assert("ActionNotice" not in rec and "runAction(" in rec,
            "Recurrence: the hand-rolled runAction clone is gone; outcomes ride the layer")
    _assert("actionNotice" not in _strip_comments(_read("components/library/WorkDetailActionsContext.tsx")),
            "WorkDetailActionsContext: the second feedback channel is out of the contract")

    text = _strip_comments(_read("components/text/TextEditor.tsx"))
    _assert("fixed bottom-4 left-1/2" not in text and "csvLoading" not in text,
            "Text: the bottom-center CSV notice div is gone")
    _assert("reportAction(" in text and "nothing was inserted" in text,
            "Text: the CSV read reports through the layer, D18 contract intact (failure inserts nothing)")


def test_one_duration_token() -> None:
    print("\n[4] copy-flip micro-feedback rides the one token")
    sites = [
        "components/text/TextExport.tsx",
        "components/workspace/CopyField.tsx",
        "components/authoring/StudioShareExport.tsx",
        "components/chat-surface/LanePanel.tsx",
        "components/agents/AgentRunDisplay.tsx",
        "components/workspace/ShareDialog.tsx",
    ]
    for rel in sites:
        src = _strip_comments(_read(rel))
        # The token must be a CALL ARGUMENT (`, COPY_FEEDBACK_MS)`), not just
        # an import — the falsifier that reverted one call site to `1600)`
        # left the import intact and slipped a first draft of this check.
        uses_token = ", COPY_FEEDBACK_MS)" in src
        stray = re.search(r",\s*(1500|1600|2000|2500)\)", src)
        _assert(uses_token and not stray, f"{rel}: uses COPY_FEEDBACK_MS as the duration, no literal")


def test_canon_updated() -> None:
    print("\n[5] the canon carries the ruling")
    doc = (API.parent / "docs/design/ACTION-FEEDBACK.md").read_text(encoding="utf-8")
    _assert("TOP-RIGHT" in doc and "attention corridor" in doc,
            "placement ruling recorded (top-right, the attention corridor)")
    _assert("Self-act toast" in doc and "In-surface banner" in doc and "Micro-feedback" in doc,
            "the lane taxonomy is written down")
    _assert("ADR-593" in doc and "ADR-405 D4" in doc,
            "the split is tied to the notifications canon (self vs peer)")


if __name__ == "__main__":
    test_corridor()
    test_native_trio_dead()
    test_swept_sites_stay_swept()
    test_one_duration_token()
    test_canon_updated()
    print("\n" + "=" * 60)
    print(f"Action-feedback gate: {_passed} passed, {_failed} failed")
    print("=" * 60)
    sys.exit(1 if _failed else 0)
