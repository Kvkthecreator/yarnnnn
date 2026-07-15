#!/usr/bin/env python3
"""Gate: the citation carries its PIN.

ADR-440 D5 — the Studio's founding structural bet: "the artifact is a
projection over living substrate references", and `data-ref-rev` is what makes
a citation survive its path moving or being deleted. It is the whole difference
between a yarnnn artifact and a tool that bakes a copy.

THE FAILURE THIS GATE EXISTS FOR (found 2026-07-15):

  Live count across every artifact in the workspace: 4 citations carrying the
  attribute, **0 populated**. The pin had never once been written.

Three causes, all of them "unattended" rather than "blocked":

  1. The write path was delegated ENTIRELY to the lane, via a posture that
     said "stamp it when you have the head revision id... **otherwise leave it
     empty**" — a self-fulfilling opt-out.
  2. Every kernel-constant example the posture showed the model had
     `data-ref-rev=""`. **The examples taught the opposite of the instruction.**
  3. The mechanical insert path (Media+ → figure/table/gallery) had no rev to
     stamp: `/studio/citable` served `path` + `updated_at` and no head.

And nobody noticed, because the READ path only fires on a DANGLING ref
(projection.ts resolves HEAD on the happy path and consults the pin only in the
catch) — a case rare enough to never surface the omission.

It was also widely believed to be blocked by ADR-427 Ph2/3. It is not:
ADR-457 §10.5 gates "before any media block", never publish; and ADR-440:54
says plainly "v1's pin is fully real for text-native objects (md/svg/csv)".
The binary half is genuinely blocked; the pin act is not.

Static/structural checks (no DB, no LLM — this repo has no FE test runner).
Run: python3 api/test_studio_citation_pin.py
"""

import re
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


def run() -> bool:
    sys.path.insert(0, str(ROOT / "api"))
    from services.studio import STUDIO_BLOCKS, build_studio_posture

    routes = (ROOT / "api/routes/studio.py").read_text()
    ops = (WEB / "components/studio/artifactOps.ts").read_text()
    surface = (WEB / "components/studio/StudioSurface.tsx").read_text()
    toolbar = (WEB / "components/studio/StudioToolbar.tsx").read_text()
    client = (WEB / "lib/api/client.ts").read_text()

    # ── 1. the rev REACHES the FE (cause 3) ────────────────────────────────
    print("\n-- the pin is served --")
    citable = re.search(r"async def list_citable\([\s\S]*?\n\n\n", routes)
    citable_body = citable.group(0) if citable else ""
    _check("the citable endpoint is findable", bool(citable))
    _check(
        "/studio/citable SELECTS head_version_id (the insert needs a rev to stamp)",
        "head_version_id" in citable_body,
    )
    _check(
        "/studio/citable RETURNS head_version_id on every row",
        citable_body.count("head_version_id") >= 2,
    )
    _check(
        "the FE client types the pin on both images and tables",
        client.count("head_version_id: string | null") >= 2,
    )

    # ── 2. the mechanical insert STAMPS it (cause 3) ───────────────────────
    print("\n-- the mechanical insert stamps --")
    _check(
        "the toolbar passes the picked row's pin to onInsertCited",
        "it.head_version_id" in toolbar,
    )
    _check(
        "the gallery insert passes a pin map",
        re.search(r"onInsertGallery\(galleryPick,\s*pins\)", toolbar) is not None,
    )
    cited = re.search(r"const handleInsertCited = useCallback\(([\s\S]*?)\n  \);", surface)
    cited_body = cited.group(1) if cited else ""
    _check("the cited-insert handler is findable", bool(cited))
    _check(
        "the cited insert REWRITES data-ref-rev with the pin (not just data-ref)",
        "data-ref-rev=" in cited_body and "pin" in cited_body,
    )
    _check(
        "galleryFragment accepts pins and stamps per-path",
        "pins?: Record<string, string | null>" in ops
        and "pins?.[p] ?? ''" in ops,
    )

    # ── 3. the posture TEACHES it (causes 1 + 2) ───────────────────────────
    # The regression that let this ship: the instruction said "stamp it" while
    # every example showed `data-ref-rev=""`. An example outweighs a sentence.
    print("\n-- the posture teaches the pin --")
    for kind, b in STUDIO_BLOCKS.items():
        if "data-ref-rev" not in b["markup"]:
            continue
        _check(
            f"block '{kind}' example does NOT teach an empty pin",
            'data-ref-rev=""' not in b["markup"],
        )
    posture = build_studio_posture(
        artifact_path="/workspace/operation/x/deck.html",
        artifact_content='<html data-template="deck"></html>',
    )
    _check(
        "the posture shows NO empty-pin example anywhere",
        'data-ref-rev=""' not in posture,
    )
    _check(
        "the posture does not tell the lane to leave the pin empty",
        "otherwise leave it empty" not in posture,
    )
    _check(
        "the posture instructs ALWAYS stamp",
        "ALWAYS stamp" in posture,
    )

    # ── 4. the read side is unchanged (it was never the problem) ───────────
    print("\n-- the read path still resolves the pin --")
    proj = (WEB / "components/workspace/viewers/projection.ts").read_text()
    _check(
        "the projection still reads the pin",
        "data-ref-rev" in proj,
    )
    _check(
        "the projection still NEVER writes pins back (reads must not write)",
        "setAttribute('data-ref-rev'" not in proj,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
