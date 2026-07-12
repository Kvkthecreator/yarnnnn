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
        m == {"name": "Acme DS", "css": ["styles.css", "tokens/colors.css"]},
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

    # ── 6. purity: no write path in the module ────────────────────────────
    mod_src = inspect.getsource(ds_mod)
    passed &= _check(
        "design_systems has no write path (pure/read-only)",
        "write_revision" not in mod_src and ".insert(" not in mod_src and ".update(" not in mod_src,
    )

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(run())
