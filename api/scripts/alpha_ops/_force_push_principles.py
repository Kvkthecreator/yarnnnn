"""One-shot harness: force-push the alpha-author bundle's principles.md to a persona workspace.

Workaround for an ADR-292 gap surfaced 2026-05-20: the `is_skeleton_content`-
based bundle-update gate can't distinguish "old bundle content" from
"operator-customized content," so it skips re-forking files like
`review/principles.md` whose content has diverged simply because the
bundle was updated. Until ADR-292 v2 ships a version-tracking gate
(or a per-file `--force` mode), the developer-side workaround is to
write the bundle file directly with `system:substrate-update` attribution.

This is a HAT-B developer-side script — used during alpha-author demonstration
setup to make sure the workspace runs the latest hardened ADR-295 principles
content. Real operator workflow flows through the cockpit Settings → Workspace
"Update bundle" button (ADR-292 Phase 2, deferred).

Usage:
    .venv/bin/python -m api.scripts.alpha_ops._force_push_principles \\
        --persona yarnnn-author
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parents[1]
_REPO_ROOT = _THIS_DIR.parents[2]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_API_ROOT / ".env.alpha-ops")

sys.path.insert(0, str(_THIS_DIR))
from _shared import load_registry  # noqa: E402


async def main_async(persona_slug: str) -> int:
    from services.supabase import get_service_client
    from services.authored_substrate import write_revision

    reg = load_registry()
    persona = reg.require(persona_slug)

    bundle_principles_path = (
        _REPO_ROOT / "docs" / "programs" / persona.program /
        "reference-workspace" / "review" / "principles.md"
    )
    if not bundle_principles_path.is_file():
        print(f"bundle principles.md not found at {bundle_principles_path}", file=sys.stderr)
        return 2

    content = bundle_principles_path.read_text(encoding="utf-8")
    client = get_service_client()
    revision_id = write_revision(
        client,
        user_id=persona.user_id,
        path="/workspace/review/principles.md",
        content=content,
        authored_by="system:substrate-update",
        message=(
            f"force-push principles.md from {persona.program} bundle "
            f"(ADR-292 gap workaround — content-equality gate can't distinguish "
            f"old-bundle-content from operator-customized-content; pushes "
            f"hardened ADR-295 D6 Self-Improvement Posture into live workspace)"
        ),
    )
    print(f"persona={persona_slug} program={persona.program} revision={revision_id}")
    print(f"new principles.md length: {len(content)} chars")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", required=True)
    args = ap.parse_args()
    return asyncio.run(main_async(args.persona))


if __name__ == "__main__":
    raise SystemExit(main())
