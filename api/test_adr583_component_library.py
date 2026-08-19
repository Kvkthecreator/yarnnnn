"""ADR-583 — a component is a workspace file (the citation discipline).

What this gate defends
======================
1. D3 — the `component` registry row is RE-CUT: cites="fragment", group derives
   "component", the ADR-581 family formula lands it CITED (the ADD door), and
   its markup is a citation of a `*.component.html` file — never inline card
   markup. MEDIA_BLOCK_KINDS is untouched (fragment is not picture).
2. D2 — the citable endpoint serves the library by suffix (the `.csv`
   precedent), and the wire carries `components`.
3. D4 — the projection inlines a cited component through the SANITIZER, in
   BOTH the live path and the pinned fallback (the ADR-538 dangling-citation
   lesson), and the sanitizer is the shared executable strip.
4. The picker lists the library for cites='fragment' and its empty state
   teaches the compose act; the surface's single-pick ladder KEEPS the
   component kind (the ADR-538 D2 collapse lesson).
5. D1/D5 — the posture carries the law recut (never a raw colour; geometry
   free) and the component contract + the reverse-engineer act.
6. Falsifiers — comment-stripped sources; wired expressions, not labels.

Run from api/:  python3 test_adr583_component_library.py     (NOT pytest)
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import services.authoring as st  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROJECTION = (ROOT / "web/components/workspace/viewers/projection.ts").read_text()
PICKER = (ROOT / "web/components/authoring/StudioCitablePicker.tsx").read_text()
SURFACE = (ROOT / "web/components/authoring/StudioSurface.tsx").read_text()
CLIENT = (ROOT / "web/lib/api/client.ts").read_text()
ROUTE = (ROOT / "api/routes/studio.py").read_text()

PASS = 0
FAIL = 0


def t(name: str, ok: bool) -> None:
    global PASS, FAIL
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    PASS += ok
    FAIL += not ok


def strip_comments(ts: str) -> str:
    """Drop /* */ blocks and // line tails so an assertion can never match its
    own explanatory comment (the recorded gate lesson)."""
    ts = re.sub(r"/\*.*?\*/", "", ts, flags=re.DOTALL)
    return re.sub(r"(?m)^\s*//.*$|(?<=[\s;{(])//[^\n]*$", "", ts)


PROJ_NC = strip_comments(PROJECTION)
PICKER_NC = strip_comments(PICKER)
SURFACE_NC = strip_comments(SURFACE)

print("=== 1. D3 — the registry re-cut ===")

comp = st.STUDIO_BLOCKS.get("component", {})
t("component declares cites='fragment'", comp.get("cites") == "fragment")
t("group derives 'component' from the fragment citation",
  st.block_group(comp) == "component"
  and st.GROUP_BY_CITES.get("fragment") == "component")
t("the ADR-581 family formula lands it CITED (the ADD door, by construction)",
  comp.get("cites") != "none")
t("its markup is a CITATION of a *.component.html file, pinned",
  "data-ref=" in comp.get("markup", "")
  and 'data-ref-kind="component"' in comp.get("markup", "")
  and ".component.html" in comp.get("markup", "")
  and "data-ref-rev=" in comp.get("markup", ""))
t("the inline-card skeleton is GONE from the markup",
  "<header>" not in comp.get("markup", "") and 'class="row"' not in comp.get("markup", ""))
t("MEDIA_BLOCK_KINDS untouched — fragment is not picture",
  "component" not in st.MEDIA_BLOCK_KINDS
  and st.MEDIA_BLOCK_KINDS == {"figure", "gallery", "logo-row"})

print("\n=== 2. D2 — the citable library ===")

t("the endpoint queries by the suffix (the .csv precedent)",
  '"%.component.html"' in ROUTE)
t("the wire carries components", '"components": [_row(r) for r in components]' in ROUTE)
t("the FE client types the components list", "components: Array<{" in CLIENT)

print("\n=== 3. D4 — the projection inlines through the sanitizer ===")

t("the live path inlines a cited component",
  re.search(r"if \(kind === 'component'\) \{[\s\S]{0,400}?sanitizeFragmentHtml\(file\.content\)", PROJ_NC) is not None)
t("the pinned fallback draws the component too (no raw-source dump)",
  re.search(r"kind === 'component'[\s\S]{0,200}?sanitizeFragmentHtml\(rev\.content\)", PROJ_NC) is not None)
t("the sanitizer is the SHARED executable strip, over a carrier",
  re.search(r"function sanitizeFragmentHtml[\s\S]{0,400}?stripExecutable\(carrier\)", PROJ_NC) is not None)
t("a dangling component marks broken rather than falling to <pre>",
  re.search(r"if \(kind === 'component'\) \{[\s\S]{0,500}?markBroken\(el, ref\)", PROJ_NC) is not None)

print("\n=== 4. The picker + the surface keep the kind ===")

t("the picker lists the library for cites='fragment'",
  "c.components" in PICKER_NC and "cites === 'fragment'" in PICKER_NC)
t("the picker names the act", "'Insert a component from the workspace'" in PICKER)
t("the empty state teaches the compose act (screenshot / source)",
  "compose one from a screenshot or a source" in PICKER)
t("the single-pick ladder KEEPS component (the ADR-538 collapse lesson)",
  re.search(r"cp\.kind === 'component'\s*\?\s*'component'", SURFACE_NC) is not None)
t("kindCites speaks the fourth value",
  "'none' | 'source' | 'picture' | 'fragment'" in SURFACE)

print("\n=== 5. D1/D5 — the posture: law recut + the act ===")

posture = st._POSTURE_FRAME
t("the colour law is stated absolutely (never a raw colour/face/radius)",
  "NEVER a raw colour" in posture)
t("geometry is freed, homed in the component file",
  "GEOMETRY" in posture and "component" in posture.split("GEOMETRY")[1][:200])
t("the Components section exists and cites by reference",
  "## Components" in posture
  and 'data-ref-kind="component"' in posture
  and "Never paste a component's markup" in posture)
t("the contract: scoped style, slots, no script, no inner block ids",
  "SCOPED under the root" in posture
  and "design-system slots" in posture
  and "no <script>" in posture
  and "data-block-id inside" in posture)
t("the reverse-engineer act is taught (screenshot / source component)",
  "reverse-engineer" in posture)
t("editing the FILE updates every citing artifact (reference, never copy)",
  "updates every" in posture)

print("\n=== 6. Falsifiers ===")

# F1 — the family formula would land a fragment-citing row in ADD: run the
# ADR-581 derivation verbatim over the live row.
fam = ("cited" if comp.get("cites") != "none"
       else ("composed" if comp.get("tier") == "object" else "prose"))
t("F1 the derivation (not this gate) puts component in the cited family", fam == "cited")

# F2 — collapsing the ladder (component → figure) would be caught: the wired
# expression must name component on BOTH sides of the ternary arm.
t("F2 removing the ladder arm is detectable",
  re.search(r"cp\.kind === 'component'\s*\?\s*'figure'", SURFACE_NC) is None)

# F3 — the sanitizer actually strips: simulate its contract on the strip rules
# (script element + on* attr must not survive the strip regexes the shared
# helper enforces; asserted structurally since TS does not execute here).
strip_src = re.search(r"function stripExecutable\(doc: Document\): void \{[\s\S]*?\n\}", PROJ_NC)
t("F3 the shared strip removes script elements and on* handlers",
  strip_src is not None
  and "'script, iframe, object, embed'" in strip_src.group(0)
  and 'name.startsWith("on")' in strip_src.group(0).replace("'", '"'))

# F4 — the comment-stripper works (an absence assertion must not match prose).
t("F4 strip_comments removes a token that appears only in a comment",
  "cp.kind === 'component'" not in strip_comments("// cp.kind === 'component'\nconst x = 1;"))

print(f"\n{PASS}/{PASS + FAIL} passed")
sys.exit(0 if FAIL == 0 else 1)
