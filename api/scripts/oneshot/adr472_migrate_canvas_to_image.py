"""
ADR-472 — migrate existing canvas artifacts to IMAGES stages.

The canvas doc type left Studio (ADR-472 D1/D7): `data-template="canvas"` is no
longer a registered layout, and the `aspect` slug token is deleted (D3). Any
artifact authored before the carve still says `canvas` on its root and still
carries `data-aspect`. This one-shot converts them, as ATTRIBUTED REVISIONS —
never a silent UPDATE (ADR-209: every mutation is authored and retained; the
prior revision stays walkable, so this is reversible by revert-as-write).

Per artifact:
  data-template="canvas"        → data-template="image"
  data-aspect="wide|portrait|…" → real dimensions (data-w/data-h + --stage-*)
  (no data-aspect)              → the square default

The aspect→dimensions map is the honest reading of what those slugs MEANT at
the width the canvas actually rendered (736px artboard, ADR-471): a ratio
becomes a concrete box. Members can resize afterward — dimensions are data now,
not an enumerated token.

DRY-RUN IS THE DEFAULT. `--apply` writes.

Usage:
    cd api && python3 scripts/oneshot/adr472_migrate_canvas_to_image.py
    cd api && python3 scripts/oneshot/adr472_migrate_canvas_to_image.py --apply
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

env_path = Path(__file__).resolve().parents[2] / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

# The ADR-471 aspect slugs, resolved to real boxes (ADR-472 D3). Widths follow
# the preset table so a migrated stage matches a newly-created one of the same
# shape rather than being a bespoke size.
ASPECT_DIMENSIONS = {
    "wide": (1600, 900),        # 16:9  → the Wide preset
    "portrait": (1080, 1350),   # 4:5   → the Portrait preset
    "story": (1080, 1920),      # 9:16  → the Story preset
    None: (1080, 1080),         # absence was square (ADR-471 D-c default)
}


def get_client():
    from supabase import create_client
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def migrate_html(html: str) -> tuple[str, tuple[int, int]]:
    """Rewrite one canvas artifact's root. Returns (new_html, (w, h))."""
    from services.images import stage_root_attrs

    m = re.search(r'<html([^>]*)>', html)
    root_attrs = m.group(1) if m else ""
    aspect_m = re.search(r'\bdata-aspect="(\w+)"', root_attrs)
    aspect = aspect_m.group(1) if aspect_m else None
    w, h = ASPECT_DIMENSIONS.get(aspect, ASPECT_DIMENSIONS[None])

    new_attrs = re.sub(r'\s*\bdata-aspect="\w+"', "", root_attrs)
    new_attrs = new_attrs.replace('data-template="canvas"', 'data-template="image"')
    new_root = f'<html{new_attrs} {stage_root_attrs(w, h)}>'
    return html.replace(m.group(0), new_root, 1) if m else html, (w, h)


def main() -> int:
    apply = "--apply" in sys.argv
    client = get_client()

    rows = (
        client.table("workspace_files")
        .select("path, user_id, content, head_version_id")
        .ilike("content", '%data-template="canvas"%')
        .limit(500)
        .execute()
    ).data or []

    print(f"canvas artifacts found: {len(rows)}")
    if not rows:
        print("nothing to migrate.")
        return 0

    from services.authored_substrate import write_revision

    for r in rows:
        new_html, (w, h) = migrate_html(r.get("content") or "")
        print(f"  {r['path']} → image, {w}×{h}")
        if apply:
            write_revision(
                client,
                user_id=r["user_id"],
                path=r["path"],
                content=new_html,
                authored_by="system:adr472-migrate",
                message="ADR-472: canvas → IMAGES stage (aspect slug → real dimensions)",
            )

    if not apply:
        print("\nDRY RUN — nothing written. Re-run with --apply.")
    else:
        print(f"\nmigrated {len(rows)} artifact(s) as attributed revisions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
