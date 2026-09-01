#!/usr/bin/env python3
"""Gate: ADR-627 — Blogger, the publish medium returns as a desk.

The pairing the ADR-599 D5 deletion named as its future: the outward type
(ADR-505 D2's merged article/page, deleted with the `web` medium) returns as
`post` under its own app, with its own being as the desk's voice.

What must hold:
  1. the being — a row like every other (whitelisted keys, priced engine,
     no authority shape), offered False, home = the blogger desk.
  2. the app — registered through the one door, resident resolvable, the
     standing executor derives (a declaration naming `blogger` works, ADR-603).
  3. the medium — `post` resolves (paged, band-first, no geometry), its
     arrangement family is live, and the retired outward slugs alias to it.
  4. the exposure — stage `beta` (a tile, no Dock icon), served and auth-
     covered via the roster-derived prefixes (desk.ts's list).
  5. what is REFUSED — no outbound reach from this arc (ADR-627 D5/ADR-628:
     the blogger module touches no platform client, no credential path).

Script-style (pytest silently passes side-effect asserts in this repo's
gates — run `python3 test_adr627_blogger_pairing.py`).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

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


import services.apps  # noqa: F401,E402  (registration side-effect)
from services.agents_registry import (  # noqa: E402
    AGENT_ROW_KEYS,
    homes_for_agent,
    is_promoted,
    resolve_agent,
)
from services.authoring import (  # noqa: E402
    all_layouts,
    canonical_layout_slug,
    resident_for_app,
    resolve_arrangements,
    resolve_layout,
    standing_executor_for_app,
)

print("1. the being (ADR-627 D2)")
being = resolve_agent("blogger")
check("blogger resolves", being is not None)
check("the row carries exactly the whitelisted keys (no authority shape)",
      being is not None and set(being) == AGENT_ROW_KEYS,
      f"keys={sorted(being or {})}")
check("kernel-authored, met at its desk, never invited",
      bool(being and being["kernel"] and not being["offered"]))
from services.lane_runner import LANE_MODELS, unpriced_lane_model  # noqa: E402
check("its engine is routable and priced",
      bool(being) and being["model"] in LANE_MODELS
      and not unpriced_lane_model(being["model"]))
check("its home is the blogger desk alone",
      homes_for_agent("blogger") == ["blogger"])

print("2. the app (ADR-627 D1 via ADR-562)")
check("the app pins the being as resident",
      resident_for_app("blogger") == "blogger")
check("the standing executor derives (a declaration naming `blogger` works)",
      standing_executor_for_app("blogger") == "blogger")
from services.standing_declarations import resident_for_declaration  # noqa: E402
check("…through the declaration door too (ADR-603 D2)",
      resident_for_declaration("blogger") == "blogger")

print("3. the medium (ADR-627 D1)")
post = resolve_layout("post")
check("`post` resolves, owned by blogger, paged",
      bool(post) and post.get("app") == "blogger" and post.get("mode") == "paged")
bands = resolve_arrangements("post")
check("the band family is live (long-form + landing bands)",
      {"prose-header", "prose", "hero", "content", "cta"} <= set(bands),
      f"bands={sorted(bands)}")
check("the scaffold is ARTICLE-first (prose-header opens it, no hero)",
      bool(post)
      and 'data-arrange="prose-header"' in post.get("scaffold", "")
      and 'data-arrange="hero"' not in post.get("scaffold", ""))
check("band-first, never object-first: the skin styles bands, not slides",
      bool(post) and "section[data-arrange]" in post.get("skin", "")
      and ".slide" not in post.get("skin", ""))
check("the retired outward slugs alias to `post`, single-hop, never offered",
      all(canonical_layout_slug(s) == "post" for s in ("article", "page", "web"))
      and not ({"article", "page", "web"} & set(all_layouts())))

print("4. the exposure (ADR-627 D3 via ADR-592)")
from services.app_stage import launcher_tier_for, resolve_stage  # noqa: E402
from services.kernel_surfaces import KERNEL_SURFACES, kernel_surface_slugs  # noqa: E402
row = next((e for e in KERNEL_SURFACES if e.get("slug") == "blogger"), None)
check("the surface row exists and DECLARES stage beta",
      bool(row) and row.get("stage") == "beta")
check("beta serves: on the roster, a launcher tile, never pinned",
      "blogger" in kernel_surface_slugs()
      and bool(row) and launcher_tier_for(row) == "primary"
      and resolve_stage(row) == "beta")
check("the being's promotion derives from the desk (ADR-602 D3)",
      is_promoted("blogger"))
check("the route is /blogger", bool(row) and row.get("route") == "/blogger")

print("5. the FE seams (roster-derived auth cover + the app wrapper)")
WEB = ROOT / "web"
desk_ts = (WEB / "types" / "desk.ts").read_text()
check("desk.ts lists the slug (SURFACE_PREFIXES derives the auth gate from it)",
      "'blogger'" in desk_ts.split("KernelSurfaceSlug[] = [")[1].split("] as const")[0])
check("the union carries it (window-grade slug)",
      "| 'blogger'" in desk_ts)
check("SurfaceRegistry mounts the page",
      "blogger: BloggerPage" in (WEB / "components" / "shell" / "SurfaceRegistry.tsx").read_text())
page = (WEB / "app" / "(authenticated)" / "blogger" / "page.tsx").read_text()
check("the page is the thin Docs-shape wrapper (Studio parameterized)",
      "StudioSurface app={BLOGGER_APP}" in page)
surface = (WEB / "components" / "authoring" / "StudioSurface.tsx").read_text()
check("BLOGGER_APP is declared with the blogger slug",
      "slug: 'blogger'" in surface and "'blogger'" in surface.split("interface AuthoringApp")[1].split("label:")[0])
check("the type→app association carries blogger (artifacts open at the desk)",
      "blogger: { surface: 'blogger'" in (WEB / "lib" / "file-types" / "index.ts").read_text())
check("the launcher glyph resolves (icon_key mapped)",
      "newspaper: Newspaper" in (WEB / "lib" / "shell" / "surface-icons.tsx").read_text())
check("the being's glyph resolves (BeingIcon mapped)",
      "feather: Feather" in (WEB / "components" / "agents" / "BeingIcon.tsx").read_text())

print("6. what is REFUSED (ADR-627 D5 / ADR-628 — no outbound reach)")
blogger_src = (ROOT / "api" / "services" / "apps" / "blogger.py").read_text()
check("the blogger module reaches no platform client and no credential path",
      "integrations" not in blogger_src
      and "platform_credentials" not in blogger_src
      and "httpx" not in blogger_src and "requests" not in blogger_src)

print()
if FAILED:
    print(f"ADR-627 gate RED — {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"    - {f}")
    sys.exit(1)
print(f"ALL PASS — {PASSED} checks — ADR-627 holds")
