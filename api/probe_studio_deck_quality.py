"""Hat-B probe — can the bound Studio lane author a deck the Studio can operate?

THE QUESTION (operator, 2026-07-16): "make me a deck" is a flagship path. Is the
LLM's draft good enough, or do we need a dedicated skill?

WHY A PROBE AND NOT AN AUDIT: the live deck at /workspace/operation/yarrnnnn-decl
was drafted 2026-07-11 09:06; the block grammar landed in the posture 2026-07-12
(09a20db). That artifact measures a prompt that no longer exists. And the
2026-07-16 test-deck was authored from the CHAT surface (via openai/gpt-5, one
revision) — no artifact_path, so `lane_runner.py:331 if artifact_path:` never
fired and it never saw the posture either. Neither sample can answer the question.

WHAT THIS DOES: drives the REAL bound lane (run_lane_turn with artifact_path set)
against a real skeleton, then measures the artifact it produced against the
kernel's own registries. No mocks — the point is what the model actually does.

CRITERION (declared BEFORE the run, per docs/evaluations/README.md):
  A deck is OPERABLE when the Studio's shipped affordances can act on it:
    1. every slide carries a data-arrange from the registry   (re-arrange, D9 carry)
    2. every content unit carries data-block + data-block-id  (gutter, grip,
                                                                right-click, trace)
    3. the deck skin survives (aspect-ratio 16/9, not invented CSS)
    4. no citation is fabricated (a data-ref must name a real file)
  PASS = 1,2,3 hold and 4 is not violated. Partial = 1,2 hold, 3 fails.
  FAIL  = 1 or 2 fails — an unannotated slide is INERT: no gutter, no grip, no
          menu rows, no block-grain trace, and D9's carry has nothing to carry.

Run:  cd api && python3 probe_studio_deck_quality.py [--model X] [--write]
      (--write persists the artifact for eyeballing; default is read-only.)
"""

import argparse
import asyncio
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PROMPT = (
    "Draft a 6-slide investor deck for a seed-stage company called Northwind that "
    "makes warehouse robotics. Cover: the title, the problem, the solution, some "
    "proof/traction numbers, the roadmap, and the ask. Use real-sounding placeholder "
    "content — this is a template."
)


def measure(html: str) -> dict:
    """Score an artifact against the kernel's registries. Pure — no I/O.

    The self-test earned its keep twice here. Both fixes are about NOT counting
    the stylesheet as content:
      · EVERY <style> must go, not just the kernel's — build_skeleton's layout
        skin is a plain <style> whose selectors ([data-block="callout"] { … })
        my first regex counted as blocks. That is what produced a nonsense
        "5/14 blocks carry an id" on the kernel's own skeleton.
      · `heading` is NOT in STUDIO_BLOCKS — it is a structural kind the posture
        teaches separately (titles/kickers/subtitles, so they are selectable).
        Scoring it "unknown" would have failed every correct deck.
    """
    from services.studio import STUDIO_ARRANGEMENTS, STUDIO_BLOCKS

    # The artifact's own skin, kept for the aspect-ratio check…
    artifact_css = re.search(r"<style>(.*?)</style>", html, re.S)
    css = artifact_css.group(1) if artifact_css else ""
    # …then EVERY stylesheet leaves the body before anything is counted.
    body = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.S)

    # `heading` is structural (posture-taught), not a palette kind.
    known_kinds = set(STUDIO_BLOCKS.keys()) | {"heading"}

    slides = re.findall(r"<section[^>]*class=\"[^\"]*slide[^\"]*\"[^>]*>", body)
    arranges = re.findall(r'data-arrange="([^"]+)"', body)
    known = set(STUDIO_ARRANGEMENTS.get("deck", {}).keys())
    blocks = re.findall(r'data-block="([^"]+)"', body)
    ids = re.findall(r'data-block-id="([^"]+)"', body)
    refs = re.findall(r'data-ref="([^"]*)"', body)

    return {
        "slides": len(slides),
        "arranges": arranges,
        "arrange_unknown": [a for a in arranges if a not in known],
        "arrange_coverage": (len(arranges) / len(slides)) if slides else 0.0,
        "blocks": Counter(blocks),
        "block_unknown": [b for b in blocks if b not in known_kinds],
        "n_blocks": len(blocks),
        "n_ids": len(ids),
        "dup_ids": [i for i, c in Counter(ids).items() if c > 1],
        "has_aspect": "aspect-ratio" in css or not css,
        "invented_vh": bool(re.search(r"\.slide\s*\{[^}]*\bvh\b", css)),
        "refs": refs,
        "bytes": len(html),
    }


def verdict(m: dict) -> tuple[str, list[str]]:
    notes = []
    ok_arrange = m["slides"] > 0 and m["arrange_coverage"] >= 0.99 and not m["arrange_unknown"]
    ok_blocks = m["n_blocks"] > 0 and m["n_ids"] == m["n_blocks"] and not m["dup_ids"]
    ok_skin = m["has_aspect"] and not m["invented_vh"]

    if not ok_arrange:
        notes.append(
            f"arrangement: {len(m['arranges'])}/{m['slides']} slides annotated"
            + (f", unknown={m['arrange_unknown']}" if m["arrange_unknown"] else "")
        )
    if not ok_blocks:
        notes.append(
            f"blocks: {m['n_ids']}/{m['n_blocks']} carry an id"
            + (f", dup ids={m['dup_ids']}" if m["dup_ids"] else "")
            + (f", unknown kinds={set(m['block_unknown'])}" if m["block_unknown"] else "")
        )
    if not ok_skin:
        notes.append("skin: the lane invented slide CSS (no aspect-ratio / vh-sized)")
    if m["block_unknown"]:
        notes.append(f"unknown block kinds: {sorted(set(m['block_unknown']))}")

    if ok_arrange and ok_blocks and ok_skin:
        return "PASS", notes
    if ok_arrange and ok_blocks:
        return "PARTIAL (operable, wrong skin)", notes
    return "FAIL (inert — the Studio cannot act on this)", notes


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="anthropic/claude-sonnet-4-6")
    ap.add_argument("--user", default=os.environ.get("PROBE_USER_ID", ""))
    ap.add_argument("--write", action="store_true", help="persist the artifact")
    args = ap.parse_args()

    from services.studio import build_skeleton
    from services.supabase import get_service_client

    skeleton = build_skeleton("deck")
    print("=" * 72)
    print("PROBE — bound Studio lane, deck authoring")
    print("=" * 72)
    print(f"model:    {args.model}")
    print(f"skeleton: {len(skeleton)} bytes (build_skeleton('deck'))")

    # The BASELINE the probe exists to beat: what the skeleton already carries.
    base = measure(skeleton)
    print(f"baseline: {base['slides']} slide(s), arranges={base['arranges']}, "
          f"blocks={dict(base['blocks'])}, aspect-ratio={base['has_aspect']}")
    print()

    if not args.user:
        print("NO PROBE_USER_ID — cannot drive a real lane (it needs a member's")
        print("AuthenticatedClient for the write door). Re-run with:")
        print("  PROBE_USER_ID=<uuid> python3 probe_studio_deck_quality.py")
        print()
        print("Measuring the SKELETON only, as a harness self-test:")
        v, notes = verdict(base)
        print(f"  skeleton verdict: {v}")
        for n in notes:
            print(f"    - {n}")
        return 0

    client = get_service_client()
    path = "/workspace/operation/_probe-deck/deck.html"

    from services.authored_substrate import write_revision
    write_revision(
        client, user_id=args.user, path=path, content=skeleton,
        authored_by="system:probe", message="probe: deck skeleton",
    )

    from services.lane_runner import run_lane_turn
    from services.supabase import AuthenticatedClient

    auth = AuthenticatedClient(client=client, user_id=args.user, principal_id=args.user)
    print("driving the bound lane (artifact_path set — the posture WILL load)…")
    res = await run_lane_turn(
        auth, model=args.model, history=[], user_message=PROMPT,
        member_label="probe", artifact_path=path,
    )
    print(f"  turn done: {str(res)[:160]}")
    if isinstance(res, dict) and not res.get("success", True):
        print("\nLANE DID NOT RUN — no artifact to measure. Fix the env and re-run.")
        client.table("workspace_files").delete().eq("user_id", args.user).eq("path", path).execute()
        return 1

    row = (
        client.table("workspace_files").select("content").eq("user_id", args.user)
        .eq("path", path).limit(1).execute()
    )
    html = (row.data or [{}])[0].get("content", "")
    m = measure(html)
    v, notes = verdict(m)

    print()
    print("── RESULT ──────────────────────────────────────────────────────────")
    print(f"bytes:       {m['bytes']}")
    print(f"slides:      {m['slides']}")
    print(f"arrangements: {m['arranges']}")
    print(f"coverage:    {m['arrange_coverage']:.0%} of slides annotated")
    print(f"blocks:      {dict(m['blocks'])}  ({m['n_ids']}/{m['n_blocks']} with ids)")
    print(f"citations:   {m['refs'] or 'none'}")
    print(f"skin:        aspect-ratio={m['has_aspect']}  invented-vh={m['invented_vh']}")
    print()
    print(f"VERDICT: {v}")
    for n in notes:
        print(f"  - {n}")

    if not args.write:
        client.table("workspace_files").delete().eq("user_id", args.user).eq("path", path).execute()
        print("\n(probe artifact removed; --write to keep it)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
