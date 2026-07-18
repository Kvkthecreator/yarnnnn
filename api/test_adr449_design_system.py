"""
ADR-449 — the design-system contract: Skin as a workspace convention.

Structural gate, pure-Python (no DB). Run directly:
`python test_adr449_design_system.py` (checks print but pytest would pass
them — the ADR-415 lesson).

Asserts:
  1. The manifest convention: `_design.yaml` parses (name + ordered css);
     junk / css-less yaml is NOT a design system.
  2. The marked element (D2): compose_skin_element carries data-skin="true" +
     data-ref → the MANIFEST path (absolute), optional pin.
  3. The apply rule (D3, executable spec): insert-before-</head> when absent;
     replace exactly the marked element when present; the UNMARKED layout
     <style> is never touched; non-artifact html is returned unchanged;
     remove is the inverse.
  4. The ADR-448 integration: an artifact wearing a skin yields the manifest
     path from the write-door lift (extract_data_ref_paths) — the edge rides
     free; and _resolve_derived_from keeps the artifact 'authored' (a citation
     is not a provenance class).
  5. The posture face (D4): build_design_system_section teaches the contract;
     lane_runner composes it ONLY for bound lanes, additively, outside
     services/studio.py (the ADR-447 collision carve).
  6. Purity: design_systems has no write path (no write_revision import).
"""

import inspect
import re
import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def run() -> int:
    passed = True

    from services.design_systems import (
        DESIGN_MANIFEST_BASENAME,
        apply_skin_to_html,
        compose_skin_element,
        parse_design_manifest,
        remove_skin_from_html,
    )

    # ── 1. the manifest convention ────────────────────────────────────────
    passed &= _check("manifest basename is _design.yaml", DESIGN_MANIFEST_BASENAME == "_design.yaml")
    m = parse_design_manifest("name: Acme DS\ncss:\n  - styles.css\n  - tokens/colors.css\n")
    passed &= _check(
        "manifest parses: name + ordered css",
        # Invariant, not exact-dict: name + ordered css parse, and a manifest
        # with no maps: block defaults maps to {} (the §5 field is optional).
        m is not None
        and m["name"] == "Acme DS"
        and m["css"] == ["styles.css", "tokens/colors.css"]
        and m["maps"] == {},
    )
    # ── the §5 synonym bridge (maps:) ─────────────────────────────────────
    mm = parse_design_manifest(
        "name: Y\ncss:\n  - s.css\nmaps:\n  accent: --yarn-orange\n  bogus: --x\n  radius-pill: radius-full\n"
    )
    passed &= _check(
        "manifest parses maps:, drops unknown targets, normalises bare names",
        mm is not None
        and mm["maps"] == {"accent": "--yarn-orange", "radius-pill": "--radius-full"},
    )
    passed &= _check("css-less yaml is not a design system", parse_design_manifest("name: X\n") is None)
    passed &= _check("junk content is not a design system", parse_design_manifest("{{nope") is None)
    passed &= _check("empty css list is not a design system", parse_design_manifest("css: []\n") is None)

    # ── 2. the marked element ─────────────────────────────────────────────
    el = compose_skin_element("design-system/_design.yaml", ":root{--x:1}")
    passed &= _check(
        "element is marked + cites the ABSOLUTE manifest path",
        'data-skin="true"' in el and 'data-ref="/workspace/design-system/_design.yaml"' in el,
    )
    el_pinned = compose_skin_element("/workspace/ds/_design.yaml", "a{}", rev_id="rev-9")
    passed &= _check("optional pin rides data-ref-rev", 'data-ref-rev="rev-9"' in el_pinned)

    # ── 3. the apply rule ─────────────────────────────────────────────────
    layout_style = "<style>\n.slide{display:grid}\n</style>"
    artifact = f"<!doctype html>\n<html><head>\n{layout_style}\n</head>\n<body><h1 data-block-id='t1'>T</h1></body></html>"
    applied = apply_skin_to_html(artifact, el)
    passed &= _check(
        "absent → inserted before </head>, AFTER the layout style",
        el in applied and applied.index(layout_style) < applied.index(el) < applied.index("</head>"),
    )
    passed &= _check("layout <style> untouched on apply", layout_style in applied)
    el2 = compose_skin_element("other-ds/_design.yaml", "body{color:red}")
    reapplied = apply_skin_to_html(applied, el2)
    passed &= _check(
        "present → exactly the marked element replaced",
        el2 in reapplied and el not in reapplied and layout_style in reapplied,
    )
    passed &= _check(
        "replacement is escape-safe (css with backslashes)",
        r"\2014" in apply_skin_to_html(artifact, compose_skin_element("ds/_design.yaml", r'q::before{content:"\2014"}')),
    )
    passed &= _check("non-artifact html unchanged", apply_skin_to_html("plain text", el) == "plain text")
    removed = remove_skin_from_html(reapplied)
    passed &= _check(
        "remove is the inverse (marked gone, layout stays)",
        el2 not in removed and layout_style in removed,
    )

    # ── 4. the ADR-448 integration: the edge rides free ───────────────────
    from services.authored_substrate import _resolve_derived_from, extract_data_ref_paths

    refs = extract_data_ref_paths(applied)
    passed &= _check(
        "the write-door lift extracts the manifest citation",
        "/workspace/design-system/_design.yaml" in refs,
    )
    edges, kind = _resolve_derived_from("/workspace/operation/artifacts/deck.html", applied, None, "authored")
    passed &= _check(
        "skinned artifact revision: edge lands, kind stays authored",
        edges is not None
        and "/workspace/design-system/_design.yaml" in edges
        and kind == "authored",
    )

    # ── 5. the posture face ───────────────────────────────────────────────
    from services import design_systems as ds_mod

    section_src = inspect.getsource(ds_mod.build_design_system_section)
    passed &= _check(
        "empty workspace → empty section (zero dilution)",
        'return ""' in section_src,
    )
    from services import lane_runner

    lr_src = inspect.getsource(lane_runner.build_lane_conventions)
    passed &= _check(
        "lane_runner composes the section for bound lanes only (inside the artifact_path branch)",
        "build_design_system_section" in lr_src
        and lr_src.index("if artifact_path:") < lr_src.index("build_design_system_section"),
    )
    # (No "studio.py untouched" ratchet: the ADR-447 D7 inspector pass is
    # EXPECTED to wire these functions into studio-side files — the collision
    # carve was a session-scoped discipline, not durable canon.)

    # ── 5b. the flatten contract (ADR-462 D11) ───────────────────────────
    # v1 concatenated the manifest's `css:` list VERBATIM. Every real export
    # (the live YARNNN + Concorn folders both) makes its entry point an
    # @import manifest and nothing else — so v1 would have inlined five dead
    # import lines and styled NOTHING, silently. These pin the fix.
    FOLDER = "/workspace/ds"
    tree = {
        f"{FOLDER}/styles.css": '/* it is an @import manifest; prose */\n@import "./tokens/a.css";\n',
        f"{FOLDER}/tokens/a.css": '@font-face { src: url("../assets/f.ttf"); }\n.a { color: red }\n',
    }
    css, srcs, warns = ds_mod.flatten_css("styles.css", tree.get, FOLDER)
    passed &= _check(
        "flatten: a relative @import is INLINED (an inline <style> cannot resolve one)",
        css.count("@import") == 0 and ".a { color: red }" in css and len(srcs) == 2,
    )
    passed &= _check(
        "flatten: a url() resolves against ITS OWN file's dir, not the entry's",
        f'url("{FOLDER}/assets/f.ttf")' in css,
    )
    passed &= _check(
        "flatten: prose mentioning @import in a COMMENT is not an import",
        not any("manifest" in w for w in warns),
    )
    cyc = {f"{FOLDER}/a.css": '@import "./b.css";', f"{FOLDER}/b.css": '@import "./a.css";.b{}'}
    c2, _s2, _w2 = ds_mod.flatten_css("a.css", cyc.get, FOLDER)
    passed &= _check("flatten: an @import cycle terminates", ".b{}" in c2)
    ext = {f"{FOLDER}/e.css": '@font-face { src: url("https://cdn/x.woff2"); }'}
    c3, _s3, w3 = ds_mod.flatten_css("e.css", ext.get, FOLDER)
    passed &= _check(
        "flatten: an EXTERNAL url is kept + WARNED, never silently faked "
        "(a CDN font is a real third-party dep in a self-contained artifact)",
        "https://cdn/x.woff2" in c3 and any("external" in w for w in w3),
    )
    passed &= _check(
        "import: the manifest we write round-trips through our own parser",
        (ds_mod.parse_design_manifest(ds_mod.build_manifest_yaml("X", ["styles.css"])) or {})
        .get("css") == ["styles.css"],
    )
    passed &= _check(
        "import: the display name prefers the FOLDER over a vendor id "
        "(the live export's only name field is `namespace: YARNNNDesignSystem_36fab3`)",
        ds_mod.plan_import({"_ds_manifest.json": '{"namespace":"X_36fab3"}'},
                           folder_name="My System")["name"] == "My System",
    )

    # ── 5b′. the widened theme contract (DESIGN-SYSTEMS.md §5 Move 1) ─────
    # The one invariant that must not break: a skin-LESS artifact is
    # byte-identical after the widen. Every literal became var(--slot, LITERAL),
    # so with no skin every slot falls back to its original value. This asserts
    # the property that guarantees it: no widened slot appears BARE (only ever
    # inside a var() with a fallback) in any layout's rendered CSS.
    from services.studio import STUDIO_LAYOUTS, build_skeleton

    WIDENED = ("--text-xs", "--text-sm", "--text-base", "--text-lg", "--text-xl",
               "--text-2xl", "--text-3xl", "--text-4xl", "--text-5xl",
               "--ink-10", "--radius-sm", "--radius-md", "--radius-pill", "--deck-stage")
    bare_offenders = []
    for layout in STUDIO_LAYOUTS:
        html = build_skeleton(layout, "T")
        for slot in WIDENED:
            for mm2 in re.finditer(re.escape(slot), html):
                # every occurrence must be preceded by `var(` within the rule
                if "var(" not in html[max(0, mm2.start() - 6):mm2.start()]:
                    bare_offenders.append((layout, slot))
    passed &= _check(
        "widen: every themable slot is var()-guarded — a skin-less artifact "
        "falls back to its exact prior literal (byte-identical)",
        not bare_offenders,
        f"bare: {bare_offenders[:3]}",
    )

    # ── 5b″. the synonym bridge (DESIGN-SYSTEMS.md §5 Move 2) ─────────────
    bridge = ds_mod.compose_maps_bridge({"accent": "--yarn-orange", "paper": "--bg"})
    passed &= _check(
        "bridge: a maps: block composes a :root aliasing the kernel category "
        "onto the skin's own name",
        ":root" in bridge
        and "--accent: var(--yarn-orange)" in bridge
        and "--paper: var(--bg)" in bridge,
    )
    passed &= _check(
        "bridge: nothing to map → empty string (zero cost, no dead :root)",
        ds_mod.compose_maps_bridge({}) == "",
    )
    # seed_maps is EVIDENCE, not a decision: it only seeds a category the skin
    # does NOT already name directly (bridging --accent onto itself is noise).
    passed &= _check(
        "seed: a --brand accent with no direct --accent SEEDS a bridge",
        ds_mod.seed_maps(":root{--brand:#f05;--background:#fff}") == {
            "accent": "--brand", "paper": "--background"},
    )
    passed &= _check(
        "seed: a skin that already names --accent directly seeds NO accent bridge "
        "(the real YARNNN export is exactly this — Move 1 is its whole fix)",
        "accent" not in ds_mod.seed_maps(":root{--accent:#f05;--yarn-orange:#f05}"),
    )

    # ── 5c. the import (ADR-462 D13) ─────────────────────────────────────
    import services.design_system_import as imp

    imp_src = inspect.getsource(imp)
    passed &= _check(
        "import: an SVG is TEXT, not a bucket binary (the bucket rejects "
        "image/svg+xml — verified live — and an svg needs no bucket)",
        imp.classify("assets/logos/mark.svg") == "doc"
        and imp.classify("assets/logos/mark.png") == "image",
    )
    passed &= _check(
        "import: a font is named as a font, a bundle is vendor",
        imp.classify("assets/fonts/X.ttf") == "font"
        and imp.classify("_ds_bundle.js") == "vendor"
        and imp.classify("components/forms/Input.prompt.md") == "vendor",
    )
    passed &= _check(
        "import: the mime is the BUCKET's, not a guess (an octet-stream PNG "
        "is a 415, which is how the first real import lost five logos)",
        imp.binary_mime("a/b.png") == "image/png"
        and imp.binary_mime("a/b.woff2") == "font/woff2",
    )
    # The INVARIANT, not the state: whichever way the flag sits, an unsupported
    # font must WARN rather than half-land a design system whose @font-face
    # points at nothing. (The flag flipped True on 2026-07-16 when the operator
    # opened the bucket; a gate pinned to `is False` would have gone red on a
    # correct change — the ADR-461 lesson, one arc later.)
    passed &= _check(
        "import: a font the lane cannot take is WARNED, never silently dropped",
        "fonts_deferred" in imp_src and "font not uploaded" in imp_src
        and "FONT_UPLOAD_SUPPORTED" in imp_src,
    )
    passed &= _check(
        "import: a folder with no CSS entry point REFUSES (half-writing one "
        "would make the picker offer what cannot resolve)",
        '"ok": False' in imp_src and "No CSS entry point found" in imp_src,
    )
    passed &= _check(
        "import: every write is the ONE door (write_revision), never a second",
        "write_revision" in imp_src
        and ".table(\"workspace_files\").insert" not in imp_src,
    )

    # ── 5d. the import DOOR (ADR-462 D14) ────────────────────────────────
    import routes.studio as studio_routes

    passed &= _check(
        "the zip's wrapper folder is stripped (a manifest saying `css: "
        "[styles.css]` cannot resolve `<folder>/My System/styles.css`)",
        list(studio_routes._strip_common_root(
            {"My System/styles.css": b"a", "My System/tokens/c.css": b"b"}
        ).keys()) == ["styles.css", "tokens/c.css"],
    )
    passed &= _check(
        "macOS resource forks never reach the workspace",
        "__MACOSX" not in str(studio_routes._strip_common_root(
            {"x/styles.css": b"a", "__MACOSX/._styles.css": b"junk"}
        )),
    )
    passed &= _check(
        "a FLAT zip (no wrapper) is left alone — the live export is exactly "
        "this shape, and stripping a non-existent root would eat a real file",
        set(studio_routes._strip_common_root(
            {"styles.css": b"a", "tokens/c.css": b"b"}
        )) == {"styles.css", "tokens/c.css"},
    )
    routes_src = inspect.getsource(studio_routes)
    passed &= _check(
        "the display name falls back to the FILENAME (the live export zips "
        "at the root, so there is no wrapper folder to name it)",
        're.sub(r"\\.zip$", "", (file.filename or "")' in routes_src,
    )
    passed &= _check(
        "a non-zip is refused in the member's words, not a stack trace",
        "is not a .zip" in routes_src and "BadZipFile" in routes_src,
    )

    # ── 6. purity: no write path in the module ────────────────────────────
    mod_src = inspect.getsource(ds_mod)
    passed &= _check(
        "design_systems has no write path (pure/read-only)",
        "write_revision" not in mod_src and ".insert(" not in mod_src and ".update(" not in mod_src,
    )

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(run())
