"""Canary Phase 4 v2 — targeted hooks-update + re-fire.

Phase 4 v1 (canary_phase4_operator_email.py) went RED for an unexpected reason:
the live workspace's _hooks.yaml was at the pre-2026-05-22 version (fork
dated 2026-05-20T10:41Z). The bundle template had been updated this session
with the ReturnVerdict structural binding (commit 9776788's L5-F1 fix) that
forces the Reviewer to call ReturnVerdict instead of producing a text-only
response. The pre-fix prompt was the actual root cause of the Reviewer's
zero-substrate-write outcome.

This v2 canary surgically updates the live _hooks.yaml to match the current
bundle template (operator-proxy substrate-update for one file, NOT the full
ADR-292 flow), then re-fires the pre-ship-audit hook. Validates whether the
fixed prompt produces the expected end-to-end chain.

Operator opt-in via operator_notifications:pre_ship_audit_summary active:true
was already done by v1 (revision f02d7c7b on _preferences.yaml). That state
persists from v1; this v2 only needs to update _hooks.yaml + re-fire.
"""

from __future__ import annotations

import asyncio
import re
import sys
from datetime import datetime, timezone

import os
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from services.operator_proxy.client import OperatorProxy  # noqa: E402


HOOKS_PATH = "/workspace/_hooks.yaml"
CANARY_PROFILE_PATH = "/workspace/context/authored/governance-as-trust/profile.md"
BUNDLE_TEMPLATE_PATH = os.path.join(
    API_DIR, "..", "docs", "programs", "alpha-author", "reference-workspace", "_hooks.yaml"
)


def _flip_status(content: str, new_value: str) -> str:
    pattern = re.compile(r"^status:\s*\S+", re.MULTILINE)
    if not pattern.search(content):
        raise ValueError("No `status:` line found in profile.md frontmatter")
    return pattern.sub(f"status: {new_value}", content, count=1)


def _extract_status(content: str) -> str | None:
    m = re.search(r"^status:\s*(\S+)", content, flags=re.MULTILINE)
    return m.group(1) if m else None


async def main() -> int:
    proxy = OperatorProxy.from_persona("yarnnn-author", caller="claude-opus-4-7")
    async with proxy:
        # =====================================================================
        # Step 1 — Update live _hooks.yaml to bundle template (targeted)
        # =====================================================================
        print("=== Step 1 — Update live _hooks.yaml to bundle template ===")
        with open(BUNDLE_TEMPLATE_PATH, "r") as f:
            template_content = f.read()
        print(f"Bundle template length: {len(template_content)} bytes")

        # Quick sanity: confirm template has the ReturnVerdict binding
        rv_count = template_content.count("ReturnVerdict(verdict=")
        if rv_count < 3:
            print(f"FATAL: template has {rv_count} ReturnVerdict bindings; expected >= 3")
            return 1
        print(f"Template has {rv_count} ReturnVerdict bindings (sanity check passed)")

        live_hooks = await proxy.read_file(HOOKS_PATH)
        if live_hooks is None:
            print(f"FATAL: {HOOKS_PATH} not found")
            return 1
        if live_hooks.strip() == template_content.strip():
            print(f"[T0] Live _hooks.yaml already matches template — skipping write")
        else:
            print(f"[T0] Live length: {len(live_hooks)}; template length: {len(template_content)}; updating")
            write1 = await proxy.write_substrate(
                path=HOOKS_PATH,
                content=template_content,
                message=(
                    "canary phase 4 v2 — targeted operator-proxy substrate-update "
                    "of _hooks.yaml to current bundle template. Brings ReturnVerdict "
                    "structural binding (commit 9776788 L5-F1) into live workspace "
                    "for canary v2 re-fire. Per ADR-294 operator-proxy precedent + "
                    "ADR-292 substrate-update model (manual targeted shape, not full "
                    "bundle re-apply)."
                ),
            )
            print(f"[T1] _hooks.yaml updated @ {datetime.now(timezone.utc).isoformat()}")
            print(f"     revision_id: {write1['revision_id']}")
            print(f"     authored_by: {write1['authored_by']}")

        # =====================================================================
        # Step 2 — Re-fire substrate-event canary on governance-as-trust
        # =====================================================================
        print()
        print("=== Step 2 — Re-fire substrate-event canary ===")
        baseline = await proxy.read_file(CANARY_PROFILE_PATH)
        if baseline is None:
            print(f"FATAL: {CANARY_PROFILE_PATH} not found")
            return 1
        print(f"[T2a] canary baseline status: {_extract_status(baseline)}")

        # Priming flip (whatever state it's in, flip to draft first)
        priming = _flip_status(baseline, "draft")
        if priming == baseline:
            print(f"[T2b] baseline already draft — fine")
        write2 = await proxy.write_substrate(
            path=CANARY_PROFILE_PATH,
            content=priming,
            message="canary phase 4 v2 — Write 2: priming flip to draft",
        )
        now2 = datetime.now(timezone.utc).isoformat()
        print(f"[T2] Priming fired @ {now2}")
        print(f"     revision_id: {write2['revision_id']}")

        # Canary transition
        final = _flip_status(priming, "ready_for_review")
        write3 = await proxy.write_substrate(
            path=CANARY_PROFILE_PATH,
            content=final,
            message="canary phase 4 v2 — Write 3: CANARY transition (post-hook-update)",
        )
        now3 = datetime.now(timezone.utc).isoformat()
        print(f"[T3] CANARY transition fired @ {now3}")
        print(f"     revision_id: {write3['revision_id']}")
        print()
        print("=== Canary v2 fired ===")
        print(f"Expected Reviewer wake within ~1-5 min of {now3}.")
        print(f"Watch:")
        print(f"  wake_queue WHERE dedup_key = '{write3['revision_id']}'")
        print(f"  reviewer substrate writes (this time SHOULD include ReturnVerdict-driven content)")
        print(f"  notifications (email opt-in still active from v1; THIS time the prompt also")
        print(f"   correctly binds verdict-emission to ReturnVerdict, so email should fire if")
        print(f"   the Reviewer chooses to surface the audit verdict via operator-update channel)")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
