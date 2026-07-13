"""
ADR-450 — the derive-recipe registry: "Learn from" as a kernel verb.

Structural gate, pure-Python (no DB). Run directly:
`python test_adr450_derive_recipes.py` (the ADR-415 lesson — __main__, not pytest).

Asserts:
  1. The registry: exactly the three v1 recipes (context-brief · design-system
     · prd), each with the D2 row shape and non-trivial SKILL.md-grade
     instructions.
  2. The chooser payload (list_recipes) is light — slug/label/description/
     accepts, NEVER the instructions (those are turn-time posture, not FE
     payload).
  3. build_derive_section: recipe instructions + the ABSOLUTE source + the two
     shared mechanics (projection note, derived_from citation); unknown recipe
     → empty string.
  4. Cross-ADR coherence: the design-system recipe teaches the ADR-449
     contract (_design.yaml + ordered css); the citation line rides the
     ADR-448 edge (derived_from).
  5. The lane binding (D3): CreateLaneRequest carries derive_recipe +
     derive_source; create validates against the registry and requires the
     pair; the lane dict exposes them; the capability envelope serves recipes;
     the turn threads them to the runner.
  6. The runner: build_lane_conventions + run_lane_turn + run_lane_turn_stream
     accept the params; conventions compose build_derive_section; derive turns
     get the authoring token profile.
  7. Kernel-internal discipline: the module is pure data + composition — no
     write path, no workspace substrate writes.
"""

import inspect
import sys


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def run() -> int:
    passed = True

    from services.derive_recipes import (
        DERIVE_RECIPES,
        build_derive_section,
        get_recipe,
        list_recipes,
    )

    # ── 1. the registry ───────────────────────────────────────────────────
    passed &= _check(
        "the v1 recipes (ADR-452 added deck)",
        set(DERIVE_RECIPES.keys()) == {"context-brief", "design-system", "prd", "deck"},
        detail=str(sorted(DERIVE_RECIPES.keys())),
    )
    for slug, r in DERIVE_RECIPES.items():
        shape_ok = (
            isinstance(r.get("label"), str) and r["label"]
            and isinstance(r.get("description"), str) and r["description"]
            and isinstance(r.get("accepts"), list) and r["accepts"]
            and isinstance(r.get("target"), str) and r["target"]
            and isinstance(r.get("instructions"), str) and len(r["instructions"]) > 400
        )
        passed &= _check(f"row shape + non-trivial instructions: {slug}", shape_ok)
        passed &= _check(
            f"instructions carry a quality bar + anti-patterns: {slug}",
            "Quality bar" in r["instructions"] and "Anti-patterns" in r["instructions"],
        )

    # ── 2. the chooser payload is light ───────────────────────────────────
    payload = list_recipes()
    passed &= _check("list_recipes has all rows", len(payload) == len(DERIVE_RECIPES))
    passed &= _check(
        "chooser payload excludes instructions",
        all(set(p.keys()) == {"slug", "label", "description", "accepts"} for p in payload),
    )
    passed &= _check("get_recipe unknown → None", get_recipe("nope") is None)

    # ── 3 + 4. the section ────────────────────────────────────────────────
    s = build_derive_section("design-system", "inbound/uploads/operator/brand.pdf")
    passed &= _check(
        "section carries the ABSOLUTE source",
        'SOURCE: /workspace/inbound/uploads/operator/brand.pdf' in s,
    )
    passed &= _check(
        "section teaches the projection fallback",
        ".extracted.md" in s,
    )
    passed &= _check(
        "section enforces the ADR-448 citation",
        'derived_from=["/workspace/inbound/uploads/operator/brand.pdf"]' in s,
    )
    passed &= _check(
        "design-system recipe teaches the ADR-449 contract",
        "_design.yaml" in s and "ORDERED list" in s,
    )
    passed &= _check("unknown recipe → empty section", build_derive_section("nope", "x.md") == "")

    # ADR-452 D3 — the studio mode: an artifact-bound derive lane gets the
    # target override; a plain derive lane never does.
    so = build_derive_section("prd", "inbound/uploads/operator/brief.pdf",
                              artifact_path="/workspace/operation/brief/document.html")
    passed &= _check(
        "studio mode: target override names the bound artifact",
        "TARGET OVERRIDE" in so and "/workspace/operation/brief/document.html" in so
        and "TARGET: the bound artifact" in so,
    )
    passed &= _check("plain mode: no override", "TARGET OVERRIDE" not in s)

    # ── 5. the lane binding ───────────────────────────────────────────────
    import routes.lanes as lanes_mod

    req_fields = lanes_mod.CreateLaneRequest.model_fields
    passed &= _check(
        "CreateLaneRequest carries the derive binding",
        "derive_recipe" in req_fields and "derive_source" in req_fields,
    )
    create_src = inspect.getsource(lanes_mod.create_lane)
    passed &= _check(
        "create validates against the registry + requires the pair",
        "get_recipe" in create_src and "must be passed together" in create_src,
    )
    passed &= _check(
        "lane dict exposes the binding",
        '"derive_recipe"' in inspect.getsource(lanes_mod._lane_row_to_dict),
    )
    passed &= _check(
        "capability envelope serves the recipes",
        "list_recipes" in inspect.getsource(lanes_mod.list_lanes),
    )
    turn_src = inspect.getsource(lanes_mod.lane_turn)
    passed &= _check(
        "the turn threads the binding to the runner",
        'derive_recipe=lane_meta.get("derive_recipe")' in turn_src
        and 'derive_source=lane_meta.get("derive_source")' in turn_src,
    )

    # ── 6. the runner ─────────────────────────────────────────────────────
    from services import lane_runner

    for fn in (lane_runner.build_lane_conventions, lane_runner.run_lane_turn, lane_runner.run_lane_turn_stream):
        params = inspect.signature(fn).parameters
        passed &= _check(
            f"{fn.__name__} accepts the derive binding",
            "derive_recipe" in params and "derive_source" in params,
        )
    conv_src = inspect.getsource(lane_runner.build_lane_conventions)
    passed &= _check(
        "conventions compose the recipe section",
        "build_derive_section" in conv_src,
    )
    rt_src = inspect.getsource(lane_runner.run_lane_turn)
    passed &= _check(
        "derive turns get the authoring token profile",
        "artifact_path or derive_recipe" in rt_src,
    )

    # ── 7. kernel-internal discipline ─────────────────────────────────────
    from services import derive_recipes as mod

    mod_src = inspect.getsource(mod)
    passed &= _check(
        "derive_recipes is pure data + composition (no write path)",
        "write_revision" not in mod_src and ".insert(" not in mod_src and ".update(" not in mod_src,
    )

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(run())
