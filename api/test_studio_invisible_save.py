"""Regression gate — the Studio invisible-save foundation.

The felt bug: every commit reloaded the iframe (srcDoc swap) — blank flash,
caret jump, scroll reset — so saving read as a jarring, displaced event. The
worst case was the idle-2s auto-commit firing mid-typing. The fix separates the
two write paths:

  1. TEXT edits (a member typed into the live DOM) commit WITHOUT reloading —
     the canvas already shows the result. A durable revision still lands; the
     FE advances its CAS base in place from the returned head_version_id.
  2. STRUCTURAL ops + FOREIGN (lane) writes still reload (the DOM shape changed
     or someone else wrote) — but the runtime reports its scroll and the canvas
     restores it, so even those reloads don't jump to the top.

Static/structural checks (no DB, no LLM):
  A. The write endpoint returns head_version_id (write_revision's return, no
     longer discarded) + the client type carries it.
  B. The surface holds a local CAS-base override; the shared writeAndAdvance
     core advances it; TEXT edits pass reload=false, STRUCTURAL ops reload=true.
  C. Scroll preservation: the runtime reports yarnnn-scroll-pos + accepts
     yarnnn-restore-scroll; the canvas tracks the latest and restores on load.

Run:  cd api && python3 test_studio_invisible_save.py
Exit code is authoritative (0 = pass).
"""

import re
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    root = Path(__file__).resolve().parent.parent
    web = root / "web"
    studio_route = (root / "api/routes/studio.py").read_text()
    client = (web / "lib/api/client.ts").read_text()
    surface = (web / "components/studio/StudioSurface.tsx").read_text()
    canvas = (web / "components/studio/StudioCanvas.tsx").read_text()
    proj = (web / "components/workspace/viewers/projection.ts").read_text()

    # ── A. the endpoint returns the new head version ─────────────────────
    _check(
        "write_artifact captures write_revision's return (new head id)",
        "new_head_version_id = write_revision(" in studio_route,
    )
    _check(
        "write_artifact returns head_version_id in the response body",
        '"head_version_id": new_head_version_id' in studio_route,
    )
    _check(
        "the client writeArtifact type carries head_version_id",
        "head_version_id: string" in client
        and "writeArtifact:" in client,
    )

    # ── B. the local CAS-base override + the two write paths ─────────────
    _check(
        "the surface holds a local override (anchorHead + content + head)",
        "localOverride" in surface
        and "anchorHead" in surface
        and "headVersionId" in surface,
    )
    _check(
        "the shared write core advances the override from the returned head",
        "writeAndAdvance" in surface
        and "headVersionId: res.head_version_id" in surface,
    )
    _check(
        "the override anchors to the LOADED head (stable across a chain), not baseHead",
        "const anchorHead = loadedFile?.head_version_id ?? null" in surface,
    )
    _check(
        "the merge guard keys validity on the loaded head (foreign reload supersedes)",
        "localOverride.anchorHead === (loadedFile.head_version_id ?? null)" in surface,
    )
    # TEXT edits: reload=false; STRUCTURAL ops: reload=true. Assert both calls.
    _check(
        "TEXT edit (onEdit) writes with reload=false (no iframe reload)",
        bool(re.search(r"`Studio: edit \$\{blockId\} block`,\s*\n\s*false", surface)),
    )
    # A STRUCTURAL op does NOT reload either (2026-07-15). The reload was
    # redundant — the canvas re-projects on every CONTENT change and the
    # override carries the new content — AND actively harmful: the [reloadKey]
    # effect nulls the override, so `file` fell back to the PRE-EDIT content,
    # the canvas re-projected the old shape, and the refetch re-applied the
    # bytes we had computed locally a moment earlier. Every insert/move/delete
    # flashed backwards and scrolled to the top. reloadKey now serves only the
    # two cases that genuinely need authoritative server state: a FOREIGN (lane)
    # write, and a 409.
    _check(
        "STRUCTURAL op (applyOp) does NOT reload — the override IS the canvas",
        bool(re.search(r"await writeAndAdvance\(\s*\n\s*\(liveHtml\) => compute\(liveHtml\)\?\.html \?\? null,\s*\n\s*message,\s*\n\s*false", surface)),
    )
    # Exactly four bump sites, each EARNED — every one is a write the FE did not
    # compute locally, so there is no override to show and the server's bytes
    # are the only truth:
    #   1. the FOREIGN (lane) write
    #   2. the 409 resync
    #   3. the caller-gated `if (reload)` — now only a split/merge whose half
    #      carries a citation (it must re-project to resolve)
    #   4. the retitle (2026-07-15) — a SERVER-side write (the h1-is-a-title
    #      knowledge lives with the layout registry), so it is foreign-shaped
    #      from the FE's point of view even though the member triggered it.
    # A member's own computed op must never appear here — that was the flash.
    _check(
        "reloadKey survives ONLY for writes the FE did not compute (4, each earned)",
        "// A FOREIGN write (the lane) genuinely changed the file — reload." in surface
        and len(re.findall(r"setReloadKey\(\(k\) => k \+ 1\);", surface)) == 4
        and "if (reload) setReloadKey((k) => k + 1);" in surface
        and "if (r.retitled) setReloadKey((k) => k + 1); // a foreign-shaped write" in surface,
    )
    # The write QUEUE: two ops can be emitted from one gesture in the same tick
    # (a drag's handle-press blurs a live edit → blur-commit + reorder). Firing
    # them concurrently made both carry the same expected head, so the loser
    # 409'd on a perfectly good gesture. Serialize + recompute off the result.
    _check(
        "writes are serialized through a tail promise (no same-tick collision)",
        "const writeTail = useRef<Promise<boolean>>" in surface
        and "writeTail.current.then(run, run)" in surface,
    )
    _check(
        "the CAS base is read FRESH from a ref, not a render closure",
        "const liveRef = useRef<{ content: string; head: string | null } | null>(null)" in surface
        and "const live = liveRef.current;" in surface
        and "const baseHead = live ? live.head : null;" in surface,
    )
    _check(
        "a landed write advances the ref SYNCHRONOUSLY (the next queued op sees it)",
        "liveRef.current = { content: html, head: res.head_version_id };" in surface,
    )
    _check(
        "every op RECOMPUTES against live html (queued ops apply to the prior result)",
        "const computed = compute(live?.content ?? '');" in surface,
    )
    _check(
        "a foreign (lane) write still reloads (onArtifactWrite bumps reloadKey)",
        "A FOREIGN write" in surface and "setReloadKey((k) => k + 1)" in surface,
    )
    _check(
        "a fresh load / foreign reload drops any stale override",
        "setLocalOverride(null)" in surface
        and "[artifactPath, reloadKey]" in surface,
    )

    # ── C. scroll preservation across the reloads that remain ────────────
    _check(
        "the runtime reports its scroll (yarnnn-scroll-pos, throttled)",
        "yarnnn-scroll-pos" in proj and "window.scrollY" in proj,
    )
    _check(
        "the runtime accepts yarnnn-restore-scroll",
        "yarnnn-restore-scroll" in proj and "window.scrollTo(0, d.y)" in proj,
    )
    _check(
        "the canvas tracks the latest scroll + restores it on (re)load",
        "scrollYRef" in canvas
        and "yarnnn-restore-scroll" in canvas
        and "d.type === 'yarnnn-scroll-pos'" in canvas,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
