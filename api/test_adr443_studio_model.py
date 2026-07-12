"""ADR-443 regression gate — the Studio axiomatic model (blocks + layouts).

Static/structural checks (no DB, no LLM):
  1. The block vocabulary: 8 launch kinds, valid groups, teaching markup
     carrying data-block + data-block-id (the annotation spec, D4).
  2. The layout registry: 3 layouts with skin/flow/scaffold; skeleton assembly
     (template = layout × starter blocks); STUDIO_TEMPLATES derives from it.
  3. Posture v2: block grammar + id discipline + layout-switch rule composed
     from the registries (one home, R4).
  4. The served vocabulary endpoint (R4's FE half).
  5. Block-grain pointing: the projection pointer runtime carries blockId +
     blockKind (D6) — read as text from the FE file.
  6. Grammar-not-schema: no validation gate anywhere in the studio module.

Run:  cd api && ./venv/bin/python test_adr443_studio_model.py
Exit code is authoritative (0 = pass).
"""

import inspect
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    from services.studio import (
        STUDIO_BLOCKS,
        STUDIO_LAYOUTS,
        STUDIO_TEMPLATES,
        build_skeleton,
        build_studio_posture,
    )

    # ── 1. The vocabulary (D4) ───────────────────────────────────────────
    _check("8 launch block kinds",
           set(STUDIO_BLOCKS) == {"prose", "callout", "quote", "checklist",
                                  "table", "metrics", "chart", "figure"})
    for kind, b in STUDIO_BLOCKS.items():
        _check(f"block '{kind}': label/group/description/markup complete",
               all(b.get(k) for k in ("label", "group", "description", "markup")))
        _check(f"block '{kind}': group valid", b.get("group") in ("content", "data", "media"))
        _check(f"block '{kind}': markup teaches the annotation spec",
               f'data-block="{kind}"' in b["markup"] and "data-block-id=" in b["markup"])
    _check("citation-backed kinds cite, never paste",
           'data-ref' in STUDIO_BLOCKS["table"]["markup"]
           and 'data-ref' in STUDIO_BLOCKS["figure"]["markup"]
           and './assets/' in STUDIO_BLOCKS["chart"]["markup"])

    # ── 2. Layouts + skeleton assembly (D5) ──────────────────────────────
    _check("3 layouts: document/deck/article",
           set(STUDIO_LAYOUTS) == {"document", "deck", "article"})
    for slug, lay in STUDIO_LAYOUTS.items():
        _check(f"layout '{slug}': label/description/flow/skin/scaffold complete",
               all(lay.get(k) for k in ("label", "description", "flow", "skin", "scaffold")))
        sk = build_skeleton(slug)
        _check(f"skeleton '{slug}': self-describing + annotated + script-free",
               f'data-template="{slug}"' in sk
               and 'data-block=' in sk and 'data-block-id=' in sk
               and "<script" not in sk.lower())
    _check("STUDIO_TEMPLATES derives from layouts (template = layout × starters)",
           set(STUDIO_TEMPLATES) == set(STUDIO_LAYOUTS)
           and all(STUDIO_TEMPLATES[s]["skeleton"] == build_skeleton(s) for s in STUDIO_LAYOUTS))

    # ── 3. Posture v2 (one home, R4) ─────────────────────────────────────
    posture = build_studio_posture(
        "/workspace/operation/x/deck.html", STUDIO_TEMPLATES["deck"]["skeleton"]
    )
    _check("posture: block grammar section present",
           "Blocks (the component grammar)" in posture)
    _check("posture: every kind's grammar composed in",
           all(f"- {k} — " in posture for k in STUDIO_BLOCKS))
    _check("posture: id discipline (stamp + preserve)",
           "data-block-id" in posture and "PRESERVE" in posture)
    posture_flat = " ".join(posture.split())  # wrap-tolerant matching
    _check("posture: patch-within-block discipline",
           "WITHIN block boundaries" in posture_flat)
    _check("posture: layout-switch rule (preserve blocks, swap skin, update data-template)",
           "change the layout" in posture and "data-template" in posture)
    _check("posture: current layout's flow composed from the registry",
           STUDIO_LAYOUTS["deck"]["flow"][:40] in posture)
    _check("posture: grammar not schema (never rejects)",
           "never rejects" in posture or "may stay" in posture)

    # ── 4. The served vocabulary (R4 FE half) ────────────────────────────
    import routes.studio as studio_routes
    src = inspect.getsource(studio_routes)
    _check("GET /studio/vocabulary registered", '"/studio/vocabulary"' in src)
    _check("vocabulary serves blocks + layouts",
           "STUDIO_BLOCKS" in src and "STUDIO_LAYOUTS" in src)

    # ── 5. Block-grain pointing (D6) — FE receipts as text ───────────────
    repo = Path(__file__).parent.parent
    projection = (repo / "web/components/workspace/viewers/projection.ts").read_text()
    _check("pointer runtime walks to the enclosing block",
           "closest('[data-block]')" in projection)
    _check("pointer payload carries blockId + blockKind",
           "blockId" in projection and "blockKind" in projection)
    surface = (repo / "web/components/studio/StudioSurface.tsx").read_text()
    _check("selection seed speaks operator words (Selected the … block)",
           "Selected the ${kind} block" in surface or "Selected the " in surface)
    _check("the Change-layout bar action exists (operator word)",
           "'Change layout'" in surface or '"Change layout"' in surface)
    menu = (repo / "web/components/studio/StudioInsertMenu.tsx").read_text()
    _check("palette renders from the served vocabulary",
           "vocabulary()" in menu and "groupedBlocks" in menu)

    # ── 6. Grammar, not schema ───────────────────────────────────────────
    import services.studio as studio_mod
    studio_src = inspect.getsource(studio_mod)
    _check("studio module stays pure program (no DB, no write_revision)",
           "write_revision" not in studio_src and ".table(" not in studio_src)
    _check("no validation gate on blocks (grammar not schema — zero raises)",
           studio_src.count("raise") == 0)

    failed = [r for r in _results if not r[1]]
    print(f"\n{len(_results) - len(failed)}/{len(_results)} checks passed"
          + (f" — {len(failed)} FAILED" if failed else ""))
    return not failed


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
