#!/usr/bin/env python3
"""Gate: ADR-629 D4 — the product wears a beta annotation, from ONE declaration.

Operator's sister, 2026-09-12: "we should have a badge showing it's explicitly a
beta before we share it with friends and family." The audit found no product-
level marker on any surface a friend walks, the only "beta" on the public site
describing a feature ADR-632 deleted, and the brand mark hand-spelled in
fourteen files — so there was nowhere to say anything ABOUT the brand.

What must hold:
  1. ONE HOME — `BRAND.stage` in web/lib/metadata.ts, optional on the type so
     graduation (deleting the line) compiles; `STAGE_NOTICE` derives from it;
     no other file declares a product stage.
  2. ONE RENDERER — the Pacifico mark (`font-brand`) renders in exactly one
     component, Wordmark.tsx, which reads the stage; `bare` has exactly one
     caller (the landing hero the canon lock governs).
  3. TWO GRAINS, TWO SHAPES — the product annotation is NOT the app chip
     (ADR-629 D1's Launcher chip is a discriminator; the product stage is a
     constant; the same chip at both grains cancels). Asserted both ways so
     the negative is not vacuous.
  4. THE DOOR — one feedback form (`FEEDBACK_FORM` in lib/cta.ts), reached from
     the landing footer AND the account menu; the literal id lives once. The
     stage's mobile home is the account-menu header, because the top bar hides
     the mark below `sm`.
  5. SAID ONCE, AT THE DOOR — AuthForm speaks the notice in signup mode only;
     the FAQ and llms.txt derive from the stage; the retired "Freddie (in
     beta)" copy and its dead /freddie link are gone; llms.txt no longer
     enumerates the retired verbs (ADR-635 D9).
  6. GATES NOTHING — every reader of the stage is a presentation file: nothing
     under lib/api, lib/shell, lib/routes.ts or middleware.ts reads it.

Script-style (pytest silently passes side-effect asserts in this repo's gates —
run `python3 -B api/test_adr629_the_product_wears_beta.py`).
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

PASSED = 0
FAILED: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASSED
    if cond:
        PASSED += 1
        print(f"  ok   {label}")
    else:
        FAILED.append(label + (f" — {detail}" if detail else ""))
        print(f"  FAIL {label}" + (f" — {detail}" if detail else ""))


def read(rel: str) -> str:
    p = WEB / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)
# Own-line `// …` and ` // …` comments. Never `://` — that is a URL.
_LINE = re.compile(r"(?m)^\s*//[^\n]*|(?<=\s)//\s[^\n]*")


def code(src: str) -> str:
    """Strip comments so a check never matches its own documentation."""
    return _LINE.sub("", _BLOCK.sub("", src))


def web_sources(*roots: str):
    for root in roots:
        base = WEB / root
        if base.is_file():
            yield base
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in {"node_modules", ".next"}]
            for f in filenames:
                if f.endswith((".ts", ".tsx")):
                    yield Path(dirpath) / f


def rel(p: Path) -> str:
    return str(p.relative_to(WEB))


# ---------------------------------------------------------------------------
print("1. ONE HOME — BRAND.stage in lib/metadata.ts")
meta = read("lib/metadata.ts")
meta_code = code(meta)

check("the Brand type declares `stage` OPTIONAL (graduation = deleting a line, and it compiles)",
      bool(re.search(r"stage\?\s*:\s*ProductStage", meta_code)))
check("BRAND declares the stage today (retire this check with the line when the product graduates)",
      bool(re.search(r'^\s*stage:\s*"beta",?\s*$', meta_code, re.M)))
check("STAGE_NOTICE derives from BRAND.stage (the sentence is null once there is no stage)",
      "STAGE_NOTICE" in meta_code
      and bool(re.search(r"STAGE_NOTICE[^=]*=\s*BRAND\.stage\s*\?", meta_code)))

second_homes = sorted(
    rel(p) for p in web_sources("app", "components", "lib")
    if rel(p) != "lib/metadata.ts"
    and re.search(r"""\bstage\s*:\s*["']beta["']""", code(p.read_text(encoding="utf-8")))
)
check("no second home declares a product stage literal", not second_homes, ", ".join(second_homes))

# ---------------------------------------------------------------------------
print("\n2. ONE RENDERER — the mark renders in Wordmark.tsx and nowhere else")
WORDMARK = "components/shared/Wordmark.tsx"
wm = read(WORDMARK)
wm_code = code(wm)
check("Wordmark.tsx exists", bool(wm))

brand_font_sites = sorted(
    rel(p) for p in web_sources("app", "components")
    if "font-brand" in code(p.read_text(encoding="utf-8"))
)
check("`font-brand` appears in exactly ONE component (a hand-spelled mark elsewhere is a second renderer)",
      brand_font_sites == [WORDMARK], ", ".join(brand_font_sites))
check("Wordmark reads BRAND.stage and STAGE_NOTICE (the annotation derives, it is not typed in)",
      "BRAND.stage" in wm_code and "STAGE_NOTICE" in wm_code)
check("Wordmark exports StageAnnotation (the one shape, reusable where the mark is hidden)",
      bool(re.search(r"export function StageAnnotation\b", wm_code)))

bare_callers = sorted(
    rel(p) for p in web_sources("app", "components")
    if rel(p) != WORDMARK
    and re.search(r"<Wordmark\b[^>]*\bbare\b", code(p.read_text(encoding="utf-8")))
)
check("`bare` has exactly one caller — the landing hero the canon lock governs",
      bare_callers == ["app/page.tsx"], ", ".join(bare_callers) or "none")

sites = sorted(
    rel(p) for p in web_sources("app", "components")
    if rel(p) != WORDMARK and "<Wordmark" in code(p.read_text(encoding="utf-8"))
)
check(f"the mark is rendered through the component at many doors ({len(sites)} files; a rename that orphans the sites goes red)",
      len(sites) >= 10, ", ".join(sites))

# ---------------------------------------------------------------------------
print("\n3. TWO GRAINS, TWO SHAPES — the product annotation is not the app chip")
launcher_code = code(read("components/shell/Launcher.tsx"))
check("the APP chip is still a chip (surface.badge, uppercase) — so the negative below is not vacuous",
      "surface.badge" in launcher_code and "uppercase" in launcher_code)
check("the PRODUCT annotation carries neither of the chip's identity classes (uppercase, bg-primary)",
      "uppercase" not in wm_code and "bg-primary" not in wm_code)
check("the annotation is set in the body sans, not the script face (`font-sans` inside a `font-brand` mark)",
      "font-sans" in wm_code and "font-brand" in wm_code)

# ---------------------------------------------------------------------------
print("\n4. THE DOOR — one feedback form, two ways in; the stage's mobile home")
cta = read("lib/cta.ts")
cta_code = code(cta)
m = re.search(r'FEEDBACK_FORM_ID\s*=\s*"([A-Za-z0-9]+)"', cta_code)
check("FEEDBACK_FORM is declared in lib/cta.ts with its id spelled once",
      bool(m) and "export const FEEDBACK_FORM" in cta_code)
form_id = m.group(1) if m else "<no-id>"
literal_elsewhere = sorted(
    rel(p) for p in web_sources("app", "components", "lib")
    if rel(p) != "lib/cta.ts" and form_id in p.read_text(encoding="utf-8")
)
check("the form id literal appears in no other file (both doors derive from the constant)",
      not literal_elsewhere, ", ".join(literal_elsewhere))
footer_code = code(read("components/landing/LandingFooter.tsx"))
check("the landing footer opens the form by FEEDBACK_FORM.id",
      "FEEDBACK_FORM.id" in footer_code)
menu_code = code(read("components/shell/UserMenu.tsx"))
check("the account menu links FEEDBACK_FORM.url in a new tab (a plain link, no embed script in the shell)",
      "FEEDBACK_FORM.url" in menu_code and 'target="_blank"' in menu_code
      and "tally.so/widgets" not in menu_code)
check("the account-menu header renders StageAnnotation (the stage's home on phones)",
      "<StageAnnotation" in menu_code and "shared/Wordmark" in menu_code)
top = code(read("components/shell/chrome/TopBarSurface.tsx"))
wm_line = next((i for i, l in enumerate(top.splitlines()) if "<Wordmark" in l), None)
above = "\n".join(top.splitlines()[max(0, (wm_line or 0) - 8):(wm_line or 0)]) if wm_line is not None else ""
check("the top bar renders the Wordmark inside a wrapper hidden below `sm` (the premise for the menu's mobile home)",
      wm_line is not None and "hidden sm:" in above)

# ---------------------------------------------------------------------------
print("\n5. SAID ONCE, AT THE DOOR — and the stale beta copy is gone")
auth_code = code(read("components/auth/AuthForm.tsx"))
check("AuthForm speaks STAGE_NOTICE in signup mode only",
      bool(re.search(r'mode === "signup" && STAGE_NOTICE', auth_code)))
faq = read("app/faq/page.tsx")
llms = read("app/llms.txt/route.ts")
check("the FAQ's beta entry derives from BRAND.stage", "BRAND.stage" in code(faq))
check("llms.txt states the stage from STAGE_NOTICE", "STAGE_NOTICE" in code(llms))
check("no 'Freddie (in beta)' copy survives on the FAQ or llms.txt (ADR-632 retired the seat)",
      "freddie" not in faq.lower() and "freddie" not in llms.lower())
dead_links = sorted(
    rel(p) for p in web_sources("app", "components")
    if "/freddie" in code(p.read_text(encoding="utf-8"))
)
check("no /freddie link remains (the route does not exist)",
      not dead_links and not (WEB / "app" / "freddie").exists(), ", ".join(dead_links))
check("llms.txt does not enumerate the retired verbs (ADR-635 D9: a copy of the roster drifts)",
      "Three verbs" not in llms
      and not re.search(r'"\s+- (remember|recall|trace) —', llms))

# ---------------------------------------------------------------------------
print("\n6. GATES NOTHING — every reader of the stage is presentation")
readers = sorted(
    rel(p) for p in web_sources("app", "components", "lib", "middleware.ts")
    if re.search(r"BRAND\.stage|STAGE_NOTICE|StageAnnotation", code(p.read_text(encoding="utf-8")))
)
print("     readers:", ", ".join(readers))
non_presentation = [
    r for r in readers
    if not (r.startswith("components/") or r.startswith("app/") or r == "lib/metadata.ts")
]
check("readers are components, pages/routes, or the declaration itself — never lib/api, lib/shell, routes.ts, middleware",
      not non_presentation, ", ".join(non_presentation))
check("no reader is a route guard or an API client", not any(
    r.startswith(("lib/api", "lib/shell")) or r in {"lib/routes.ts", "middleware.ts"} for r in readers
))

# ---------------------------------------------------------------------------
print(f"\n{PASSED} passed, {len(FAILED)} failed")
for f in FAILED:
    print(f"  ✗ {f}")
sys.exit(1 if FAILED else 0)
