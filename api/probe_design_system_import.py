"""Hat-B probe — import a REAL design system and wear it (ADR-462 D11).

THE QUESTION (operator, 2026-07-16): the design-system machinery has been built
since ADR-449 and NEVER USED — zero design systems exist in the live workspace,
so the whole feature is unfalsifiable. Does the contract survive a real export?

THE SUBJECT: ~/Downloads/YARNNN Design System — 11 items, the operator's own
brand system (Claude-Design-exported): styles.css (@import manifest), tokens/
(5 files), assets/fonts/Pacifico-Regular.ttf, plus components/, ui_kits/,
guidelines/ and a 508KB _ds_bundle.js the skin contract does not consume.

WHAT THIS DOES: reads the real folder off disk, plans the import, writes the
design system into the live workspace through the ONE door (write_revision),
resolves it, applies it to a real deck skeleton, and checks what came out.

CRITERION (declared BEFORE the run):
  1. flatten  — the @import graph resolves; ZERO @import survive into the skin
                (an inline <style> cannot resolve a relative @import: the v1
                contract would have shipped dead lines and styled NOTHING).
  2. urls     — every relative url() becomes an absolute workspace path;
                external urls are KEPT + WARNED, never silently faked.
  3. apply    — the marked element lands last in <head>, the UNMARKED layout
                style is untouched, and a re-apply replaces rather than stacks.
  4. edge     — the skin's data-ref points at the manifest, so the ADR-448
                write-door lift records the artifact → design-system edge.
  PASS = all four. Anything else FAILS and says which.

Run: cd api && python3 probe_design_system_import.py [--write]
     (--write persists into the live workspace; default is dry.)
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SRC = os.path.expanduser("~/Downloads/YARNNN Design System")
FOLDER = "/workspace/design-system/yarnnn"
USER = "2abf3f96-118b-4987-9d95-40f2d9be9a18"

_results: list = []


def _check(label: str, ok: bool, detail: str = "") -> None:
    _results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}")
    if detail:
        print(f"         {detail}")


def read_source_tree() -> dict:
    """The real folder → {rel_path: content}. Text only; binaries noted."""
    out = {}
    for root, _dirs, names in os.walk(SRC):
        for n in names:
            if n == ".DS_Store":
                continue
            p = os.path.join(root, n)
            rel = os.path.relpath(p, SRC)
            try:
                out[rel] = open(p, encoding="utf-8").read()
            except (UnicodeDecodeError, OSError):
                out[rel] = None  # binary (fonts, images) — path matters, bytes don't
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    from services.design_systems import (
        apply_skin_to_html,
        build_manifest_yaml,
        compose_skin_element,
        flatten_css,
        parse_design_manifest,
        plan_import,
    )
    from services.studio import build_skeleton

    print("=" * 72)
    print("PROBE — importing the real YARNNN Design System")
    print("=" * 72)

    if not os.path.isdir(SRC):
        print(f"source folder not found: {SRC}")
        return 1

    files = read_source_tree()
    text = {k: v for k, v in files.items() if v is not None}
    binaries = [k for k, v in files.items() if v is None]
    print(f"source: {len(files)} files ({len(binaries)} binary)")

    plan = plan_import(text, folder_name=os.path.basename(SRC))
    print(f"plan:   entry={plan['entry']}  name={plan['name']}")
    print(f"        css found: {plan['css_all']}")
    print(f"        skipping {len(plan['skipped'])} non-skin files")
    print()

    # ── 1. flatten ────────────────────────────────────────────────────────
    def read_from_disk(abs_path: str):
        rel = abs_path[len(FOLDER):].lstrip("/")
        return text.get(rel)

    css, sources, warns = flatten_css(plan["entry"], read_from_disk, FOLDER)
    _check(
        "flatten: the @import graph resolved",
        len(sources) == 6 and css.count("@import") == 0,
        f"{len(sources)} sources, {len(css)} bytes, {css.count('@import')} @import left",
    )
    _check(
        "flatten: cascade ORDER preserved (fonts → colors → type → spacing → effects)",
        [s.split("/")[-1] for s in sources]
        == ["styles.css", "fonts.css", "colors.css", "typography.css", "spacing.css", "effects.css"],
        " → ".join(s.split("/")[-1] for s in sources),
    )
    _check(
        "flatten: a CSS COMMENT is not code",
        not any("manifest;" in w for w in warns),
        f"warnings: {warns or 'none'}",
    )

    # ── 2. urls ───────────────────────────────────────────────────────────
    urls = re.findall(r'url\("([^"]+)"\)', css)
    _check(
        "urls: the relative @font-face src resolved to an absolute workspace path",
        urls == [f"{FOLDER}/assets/fonts/Pacifico-Regular.ttf"],
        f"{urls}",
    )
    _check(
        "urls: the font it points at is REALLY in the import",
        "assets/fonts/Pacifico-Regular.ttf" in files,
        f"{len(binaries)} binaries incl. the font",
    )

    # ── 3. apply ──────────────────────────────────────────────────────────
    manifest_yaml = build_manifest_yaml(plan["name"] or "YARNNN", [plan["entry"]])
    parsed = parse_design_manifest(manifest_yaml)
    _check(
        "manifest: what we WRITE is what we can READ (our contract round-trips)",
        bool(parsed) and parsed["css"] == [plan["entry"]],
        manifest_yaml.replace("\n", " | ").strip(),
    )
    _check(
        "manifest: the name is one a MEMBER would recognise, not a vendor id",
        bool(plan["name"]) and "_36fab3" not in (plan["name"] or ""),
        f"name = {plan['name']!r}",
    )

    skin = compose_skin_element(f"{FOLDER}/_design.yaml", css)
    deck = build_skeleton("deck")
    worn = apply_skin_to_html(deck, skin)

    _check(
        "apply: the marked element lands LAST in <head> (cascade beats the layout)",
        worn.find('data-skin="true"') > 0
        and worn.find('data-skin="true"') < worn.find("</head>")
        and worn.find('data-skin="true"') > worn.rfind("<style>", 0, worn.find("</head>")),
    )
    unmarked_before = len(re.findall(r"<style>", deck))
    unmarked_after = len(re.findall(r"<style>", worn))
    _check(
        "apply: the UNMARKED layout style is untouched",
        unmarked_before == unmarked_after and unmarked_after > 0,
        f"unmarked <style> count {unmarked_before} → {unmarked_after}",
    )
    twice = apply_skin_to_html(worn, skin)
    _check(
        "apply: re-applying REPLACES, never stacks",
        twice.count('data-skin="true"') == 1,
        f"{twice.count('data-skin=')} marked elements after two applies",
    )

    # ── 4. edge ───────────────────────────────────────────────────────────
    _check(
        "edge: the skin cites the MANIFEST (ADR-448 lift records artifact → system)",
        f'data-ref="{FOLDER}/_design.yaml"' in worn,
    )

    print()
    if args.write:
        from services.authored_substrate import write_revision
        from services.supabase import get_service_client

        client = get_service_client()
        n = 0
        for rel, content in text.items():
            if rel.endswith(".css") or rel == "readme.md":
                write_revision(
                    client, user_id=USER, path=f"{FOLDER}/{rel}", content=content,
                    authored_by="operator", message=f"Import YARNNN Design System: {rel}",
                )
                n += 1
        write_revision(
            client, user_id=USER, path=f"{FOLDER}/_design.yaml", content=manifest_yaml,
            authored_by="operator", message="Import YARNNN Design System: the manifest",
        )
        n += 1
        print(f"WROTE {n} files into the live workspace at {FOLDER}")
        print("(the font binary is NOT written — ADR-427 Phase 2/3 is the binary lane)")

    ok = all(_results)
    print(f"{'PASS' if ok else 'FAIL'}: {sum(_results)}/{len(_results)} checks")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
