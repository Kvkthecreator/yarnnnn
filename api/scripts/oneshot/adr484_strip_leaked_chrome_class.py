"""
One-shot: strip the leaked `yarnnn-pointed` chrome class out of saved artifacts.

Context (2026-07-23, ADR-484): the pointer runtime paints `yarnnn-pointed` on
the live DOM as a transient selection cue. `readSourceInner` — the ONE
serializer both commit paths use — restored citation islands but stripped no
runtime chrome, so whichever block happened to be selected at commit time
carried the class into the SAVED file.

That is worse than a live-session artifact: the outline renders for every future
reader of the document, and it sits in the substrate attributed as the member's
own authored content. Found because an operator reported still seeing "outlined
block selections" on a newly-created flow document, and the stored HTML for
`operation/test-new-doc/document.html` showed `<h2 ... class="yarnnn-pointed">`.

The code fix (ADR-484) closes the source. This closes the three files already
written. Idempotent: a second run finds nothing.

Attribution: `system:adr484-chrome-strip` — a mechanical repair of runtime
leakage, NOT an authored edit. The member did not write this class and must not
be recorded as having removed it.

Usage:
    cd api
    python -m scripts.oneshot.adr484_strip_leaked_chrome_class            # dry run
    python -m scripts.oneshot.adr484_strip_leaked_chrome_class --execute  # apply
"""

from __future__ import annotations

import re
import sys

CHROME_CLASS = "yarnnn-pointed"

# Three shapes to clear, in order — the class alone, the class leading a list,
# and the class trailing/among others. The attribute is dropped entirely when it
# held only chrome (an empty class="" is noise in an attributed diff).
_CLASS_ATTR = re.compile(r'\s*class="([^"]*)"')


def strip_chrome(html: str) -> str:
    """Remove the chrome class from every `class` attribute, token-wise.

    Token-wise rather than by substring surgery: a naive
    `class="a yarnnn-pointed b"` → `class="ab"` fuses two unrelated classes into
    one that never existed (caught by this script's own test pass before it ran
    against anything). Splitting on whitespace is the only way the separator
    cannot be lost. An attribute left with no tokens is dropped entirely — an
    empty `class=""` is noise in an attributed revision diff.
    """

    def _sub(m: re.Match) -> str:
        kept = [c for c in m.group(1).split() if c != CHROME_CLASS]
        return f' class="{" ".join(kept)}"' if kept else ""

    return _CLASS_ATTR.sub(_sub, html)


def main() -> int:
    execute = "--execute" in sys.argv

    from services.supabase import get_service_client
    from services.authored_substrate import write_revision

    client = get_service_client()

    rows = (
        client.table("workspace_files")
        .select("path, content, user_id, workspace_id")
        .like("content", f"%{CHROME_CLASS}%")
        .execute()
    ).data or []

    if not rows:
        print("Nothing to do — no artifact carries the chrome class.")
        return 0

    print(f"{len(rows)} artifact(s) carry the leaked class:\n")
    changed = 0
    for r in rows:
        path = r["path"]
        before = r["content"] or ""
        after = strip_chrome(before)
        hits = before.count(CHROME_CLASS)
        if after == before:
            print(f"  SKIP  {path} — matched the LIKE but no strippable occurrence")
            continue
        if CHROME_CLASS in after:
            print(f"  WARN  {path} — {after.count(CHROME_CLASS)} occurrence(s) survived; inspect")
            continue
        changed += 1
        print(f"  {'STRIP' if execute else 'would strip'}  {path}  ({hits} occurrence(s))")
        if execute:
            write_revision(
                client,
                user_id=r["user_id"],
                workspace_id=r.get("workspace_id"),
                path=path,
                content=after,
                authored_by="system:adr484-chrome-strip",
                message=(
                    "ADR-484: strip the leaked yarnnn-pointed selection cue — "
                    "runtime chrome that the serializer wrote into the artifact"
                ),
            )

    print(f"\n{changed} artifact(s) {'repaired' if execute else 'would be repaired'}.")
    if not execute:
        print("Dry run — re-run with --execute to apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
