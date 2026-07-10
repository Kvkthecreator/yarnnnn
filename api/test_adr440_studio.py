"""ADR-440 regression gate — the Studio, the first authoring app.

Static/structural checks (no DB, no LLM):
  1. The Studio program module: three templates, self-describing skeletons,
     pure posture builder with the reference syntax + patch discipline.
  2. The lane binding threads end-to-end: CreateLaneRequest → lane meta →
     run_lane_turn(_stream) → build_lane_conventions posture hook.
  3. The `studio` kernel surface row (window-grade, primary, /studio).
  4. The routes module registers (templates + artifact creation, region-gated).
  5. Program-not-substrate (D6): the studio module never writes files itself.

Run:  cd api && ./venv/bin/python test_adr440_studio.py
Exit code is authoritative (0 = pass).
"""

import inspect
import sys

_results: list[tuple[str, bool, str]] = []


def _check(label: str, cond: bool, detail: str = "") -> None:
    _results.append((label, bool(cond), detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail and not cond else ""))


def run() -> bool:
    # ── 1. The program module ────────────────────────────────────────────
    from services.studio import (
        STUDIO_ARTIFACT_REGION,
        STUDIO_LANE_MAX_TOKENS,
        STUDIO_TEMPLATES,
        build_studio_posture,
        extract_outline,
        extract_template,
    )

    _check("three templates: document/deck/article",
           set(STUDIO_TEMPLATES) == {"document", "deck", "article"})
    for slug, t in STUDIO_TEMPLATES.items():
        _check(f"template '{slug}' has label/description/skeleton",
               all(t.get(k) for k in ("label", "description", "skeleton")))
        _check(f"skeleton '{slug}' is self-describing (data-template)",
               f'data-template="{slug}"' in t["skeleton"])
        _check(f"skeleton '{slug}' is script-free (sandboxed canvas)",
               "<script" not in t["skeleton"].lower())
    _check("extract_template round-trips",
           extract_template(STUDIO_TEMPLATES["deck"]["skeleton"]) == "deck")
    _check("extract_outline finds headings",
           len(extract_outline(STUDIO_TEMPLATES["deck"]["skeleton"])) >= 2)

    posture = build_studio_posture(
        "/workspace/operation/x/deck.html", STUDIO_TEMPLATES["deck"]["skeleton"]
    )
    _check("posture: carries the bound path", "operation/x/deck.html" in posture)
    _check("posture: reference syntax (data-ref + pin)",
           "data-ref" in posture and "data-ref-rev" in posture)
    _check("posture: patch-over-rewrite discipline", "EditFile" in posture and "PATCH" in posture)
    _check("posture: relative-assets rule (./)", './assets/' in posture)
    _check("posture: never-copy rule", "base64" in posture)
    empty_posture = build_studio_posture("/workspace/operation/x/deck.html", "")
    _check("posture: empty artifact still postures (create-at-path)",
           "empty or missing" in empty_posture)
    _check("authoring token profile > chat profile", STUDIO_LANE_MAX_TOKENS > 2048)
    _check("artifact region is operation/ (no app namespace)",
           STUDIO_ARTIFACT_REGION == "/workspace/operation/")

    # ── 2. The lane binding threads end-to-end ───────────────────────────
    from routes.lanes import CreateLaneRequest
    req = CreateLaneRequest(name="x", model="anthropic/claude-sonnet-4-6",
                            artifact_path="/workspace/operation/x/deck.html")
    _check("CreateLaneRequest accepts artifact_path",
           req.artifact_path == "/workspace/operation/x/deck.html")
    _check("CreateLaneRequest: artifact_path optional (plain lanes unchanged)",
           CreateLaneRequest(name="x", model="m").artifact_path is None)

    from services import lane_runner
    for fn_name in ("run_lane_turn", "run_lane_turn_stream", "build_lane_conventions"):
        sig = inspect.signature(getattr(lane_runner, fn_name))
        _check(f"{fn_name} threads artifact_path", "artifact_path" in sig.parameters)
    _check("conventions frame has the posture seam",
           "{posture_section}" in lane_runner._CONVENTIONS_FRAME)

    import routes.lanes as lanes_mod
    lanes_src = inspect.getsource(lanes_mod)
    _check("lane turn passes the binding to the runner",
           'artifact_path=lane_meta.get("artifact_path")' in lanes_src)
    _check("lane row dict exposes the binding",
           '"artifact_path": lane_meta.get("artifact_path")' in lanes_src)

    # ── 3. The kernel surface row ────────────────────────────────────────
    from services.kernel_surfaces import KERNEL_SURFACES
    rows = [r for r in KERNEL_SURFACES if r.get("slug") == "studio"]
    _check("exactly one studio registry row", len(rows) == 1)
    if rows:
        row = rows[0]
        _check("studio: window-grade (no pane_of)", "pane_of" not in row)
        _check("studio: launcher primary", row.get("launcher_tier") == "primary")
        _check("studio: register application", row.get("register") == "application")
        _check("studio: route /studio", row.get("route") == "/studio")
        _check("studio: icon resolves FE-side (palette)", row.get("icon_key") == "palette")

    # ── 4. The routes module ─────────────────────────────────────────────
    import routes.studio as studio_routes
    src = inspect.getsource(studio_routes)
    _check("GET /studio/templates registered", '"/studio/templates"' in src)
    _check("POST /studio/artifacts registered", '"/studio/artifacts"' in src)
    _check("GET /studio/artifacts (recents list) registered",
           "list_artifacts" in src and "updated_at" in src)
    _check("creation refuses overwrite (409)", "409" in src)
    _check("creation region-gated", "STUDIO_ARTIFACT_REGION" in src)
    _check("creation writes via write_revision (authored substrate)",
           "write_revision" in src)
    # Read main.py as text — importing it runs env validation (needs prod env).
    from pathlib import Path
    main_src = (Path(__file__).parent / "main.py").read_text()
    _check("studio router mounted in main.py", "studio.router" in main_src)

    # ── 5. Program, not substrate (D6) ───────────────────────────────────
    import services.studio as studio_mod
    studio_src = inspect.getsource(studio_mod)
    _check("studio module is pure program (no write_revision/DB imports)",
           "write_revision" not in studio_src and ".table(" not in studio_src)

    failed = [r for r in _results if not r[1]]
    print(f"\n{len(_results) - len(failed)}/{len(_results)} checks passed"
          + (f" — {len(failed)} FAILED" if failed else ""))
    return not failed


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
