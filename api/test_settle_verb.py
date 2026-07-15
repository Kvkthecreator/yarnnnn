"""The settle verb gate (ADR-457 D3 onto D4; ADR-460 §8 step 2).

Run: python3 test_settle_verb.py   (NOT pytest — check()-gates print ✗ but
pytest would PASS them; this file's exit code is the signal.)

What it protects:
  1. The placement ladder — all four rungs + collision (spec §5). Pure, no LLM.
  2. The division of labour: the posture carries NO placement/citation/embed
     mechanics. Don't give the model a lever the kernel should hold.
  3. Settle is NOT a primitive (the never-ambient ratchet).
  4. The write carries revision_kind='derivation' + the honest citation.
  5. It meters with slug="settle" + session_id — falsifier 2's instrument.

Spec: docs/analysis/settle-verb-spec-2026-07-16.md
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.settle import (  # noqa: E402
    _SETTLE_POSTURE,
    compose_settle_path,
    extract_title,
    resolve_topic_folder,
    slugify,
    strip_fence,
    transcript_for_settle,
)

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"  {'✓' if cond else '✗'} {label}")


def run() -> bool:
    print("\n── 1. the title + slug (deterministic, kernel-owned) ──")
    _check("a `# Title` line is the title", extract_title("# Pricing model\n\nbody") == "Pricing model")
    _check("no heading → the first non-empty line", extract_title("Pricing model\nbody") == "Pricing model")
    _check("empty note → a fallback, never a crash", extract_title("") == "Untitled note")
    _check("slugify kebab-cases", slugify("Pricing Model: the Three Axes") == "pricing-model-the-three-axes")
    _check("slugify never returns empty", slugify("!!!") == "note")

    print("\n── 2. the placement ladder (spec §5 — no LLM, ever) ──")
    # Rung 1 — a bound lane files beside the thing it is about.
    _check(
        "rung 1: a BOUND lane → the artifact's folder",
        resolve_topic_folder("Anything", artifact_path="/workspace/operation/pricing/deck.html") == "pricing",
    )
    # Rung 2 — same logic for a derive lane.
    _check(
        "rung 2: a DERIVE lane → the source's folder",
        resolve_topic_folder("Anything", derive_source="/workspace/operation/hiring/notes.md") == "hiring",
    )
    _check(
        "rung 1 beats rung 2 when both are present",
        resolve_topic_folder(
            "X",
            artifact_path="/workspace/operation/pricing/d.html",
            derive_source="/workspace/operation/hiring/n.md",
        ) == "pricing",
    )
    # Rung 3 — EXACT match only. A near-match that mis-files thinking is worse
    # than the fallback: the fallback is visibly un-filed, a mis-file is
    # invisibly wrong.
    _check(
        "rung 3: an EXACT existing peer folder matches",
        resolve_topic_folder("Pricing and the meter", existing_folders=["pricing", "hiring"]) == "pricing",
    )
    _check(
        "rung 3 is case-insensitive",
        resolve_topic_folder("PRICING notes", existing_folders=["pricing"]) == "pricing",
    )
    _check(
        "rung 3 does NOT fuzzy-match (prices ≠ pricing → fallback)",
        resolve_topic_folder("Prices went up", existing_folders=["pricing"]) is None,
    )
    _check(
        "rung 3 never invents a folder that doesn't exist",
        resolve_topic_folder("Pricing model", existing_folders=[]) is None,
    )
    # Rung 4 — the fallback.
    _check("rung 4: no signal → None (the Documents root)", resolve_topic_folder("Some thought") is None)
    # A bound path OUTSIDE operation/ has no topic folder to borrow.
    _check(
        "a binding outside operation/ → falls through, never a bogus topic",
        resolve_topic_folder("X", artifact_path="/workspace/system/_recurrences.yaml") is None,
    )
    # operation/file.md (no topic dir) must not yield a topic.
    _check(
        "a binding directly in operation/ (no topic dir) → no topic",
        resolve_topic_folder("X", artifact_path="/workspace/operation/loose.md") is None,
    )

    print("\n── 3. the path (ADR-457 D4 convention) ──")
    _check(
        "with a topic → operation/{topic}/{date}-{slug}.md",
        compose_settle_path("Pricing model", "pricing", today="2026-07-16")
        == "/workspace/operation/pricing/2026-07-16-pricing-model.md",
    )
    _check(
        "without a topic → the Documents root (D4's fallback)",
        compose_settle_path("Pricing model", None, today="2026-07-16")
        == "/workspace/operation/2026-07-16-pricing-model.md",
    )

    print("\n── 4. the division of labour: the model distills, the kernel places ──")
    # The posture must carry NO mechanic the kernel owns. If any of these leak
    # in, the model gets a lever it should not hold (spec §4).
    for banned, why in [
        ("operation/", "the path convention (the kernel places)"),
        ("derived_from", "the citation (the kernel writes the edge)"),
        ("WriteFile", "a file verb (a settle turn has NO tools)"),
        ("embed", "the embed decision (the kernel embeds)"),
    ]:
        _check(
            f"the posture does NOT carry {why}",
            banned.lower() not in _SETTLE_POSTURE.lower(),
        )
    _check(
        "the posture DOES carry the never-invent bar",
        "NEVER invent specifics" in _SETTLE_POSTURE,
    )
    _check(
        "the posture DOES demand honesty about an inconclusive conversation",
        "no conclusion" in _SETTLE_POSTURE and "SAY SO" in _SETTLE_POSTURE,
    )
    _check(
        "the posture distinguishes settle from summary",
        "not a summary" in _SETTLE_POSTURE.lower(),
    )

    print("\n── 5. settle is a GESTURE, not a primitive (the never-ambient ratchet) ──")
    # A primitive is a capability an LLM may invoke. In any registry, a model
    # could settle its own conversation unasked — the ambient behavior the
    # whole discourse refuses.
    reg = (Path(__file__).parent / "services" / "primitives" / "registry.py").read_text()
    _check(
        "Settle appears in NO primitive registry",
        not re.search(r"[\"']Settle[\"']", reg),
    )
    routes = (Path(__file__).parent / "routes" / "lanes.py").read_text()
    _check(
        "settle is a route on the member's own lane",
        '@router.post("/lanes/{lane_id}/settle")' in routes,
    )
    _check(
        "the settle turn passes NO tools (it returns content, not tool calls)",
        "tools=" not in (Path(__file__).parent / "services" / "settle.py").read_text(),
    )

    print("\n── 6. the write: cite + kind + embed + meter ──")
    src = (Path(__file__).parent / "services" / "settle.py").read_text()
    _check(
        "the revision is a DERIVATION (ADR-423)",
        'revision_kind="derivation"' in src,
    )
    _check(
        "it attributes as the member's embodiment (ADR-411 D4)",
        "lane_caller_identity(auth.user_id, model)" in src,
    )
    _check(
        "derived_from carries the lane's BINDINGS (real paths — ADR-448)",
        "derived_from=edges or None" in src,
    )
    # The conversation rides the revision MESSAGE — probed 2026-07-16 and
    # corrected. write_revision's `metadata=` writes workspace_files.metadata
    # (the FILE row), which the NEXT revision overwrites: this settle's
    # provenance would vanish on the first edit of the note.
    # workspace_file_versions has NO metadata column; `message` is the
    # permanent per-revision record.
    _check(
        "the lane id rides the revision MESSAGE (immutable, survives later edits)",
        "(session {lane_id})" in src,
    )
    _check(
        "…and NOT write_revision(metadata=) — that writes the mutable FILE row",
        "metadata={" not in src,
    )
    _check(
        "it EMBEDS (bird 3 — the retrieval fix dies without this)",
        "_embed_workspace_file" in src,
    )
    _check(
        "an embed failure never loses the note (written first, embedded after)",
        src.index("write_revision(") < src.index("_embed_workspace_file"),
    )
    _check(
        "it meters with slug='settle' (falsifier 2 keys on this)",
        'slug="settle"' in src,
    )
    _check(
        "…and carries W0's session_id join key",
        "session_id=lane_id,     # ← W0's join key" in src,
    )
    _check(
        "it NEVER overwrites (two settles are two acts)",
        "_unique_path" in src,
    )

    print("\n── 7. transport hygiene ──")
    _check(
        "a whole-note fence is stripped (the model wrapped it despite the contract)",
        strip_fence("```markdown\n# T\n\nbody\n```") == "# T\n\nbody",
    )
    _check(
        "an INNER code fence is content and survives",
        "```py" in strip_fence("# T\n\n```py\nx=1\n```\n\ntail"),
    )
    _check(
        "the transcript renders both roles",
        transcript_for_settle([{"role": "user", "content": "q"},
                               {"role": "assistant", "content": "a"}])
        == "Member: q\n\nAssistant: a",
    )
    _check(
        "empty messages are dropped, not rendered as blanks",
        transcript_for_settle([{"role": "user", "content": ""},
                               {"role": "assistant", "content": "a"}]) == "Assistant: a",
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
