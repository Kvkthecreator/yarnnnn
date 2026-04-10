"""Inference Evaluation Harness — ADR-162 Sub-phase C.

Runs all fixtures in api/eval/inference_fixtures/ through infer_shared_context()
and scores each output against the fixture's `expected` block.

Usage (from api/ directory):
    python -m eval.run_inference_eval
    python -m eval.run_inference_eval --verbose
    python -m eval.run_inference_eval --fixture 02_solo_founder_with_url

Cost: ~$0.02 per fixture × 10 fixtures = ~$0.20-0.50 per full run.
This is a developer tool — manual discipline, not CI-gated in v1.

When prompts in api/services/context_inference.py change, run this harness
to detect regressions before merging the change. Aggregate score should
trend up or stay flat across prompt iterations, never down.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import Any


# =============================================================================
# Scoring axes
# =============================================================================

def _score_entity_recall(output: str, must_contain: list[str]) -> tuple[float, list[str]]:
    """Fraction of required entities found in output (case-insensitive substring)."""
    if not must_contain:
        return 1.0, []
    output_lower = output.lower()
    found = [e for e in must_contain if e.lower() in output_lower]
    missed = [e for e in must_contain if e.lower() not in output_lower]
    return len(found) / len(must_contain), missed


def _score_section_completeness(output: str, must_have_sections: list[str]) -> tuple[float, list[str]]:
    """Fraction of required sections present as markdown headers (## Heading)."""
    if not must_have_sections:
        return 1.0, []
    found = []
    missed = []
    for section in must_have_sections:
        # Match `## Section` or `### Section` (any header level)
        pattern = re.compile(rf"^#{{1,6}}\s+{re.escape(section)}\s*$", re.MULTILINE | re.IGNORECASE)
        if pattern.search(output):
            found.append(section)
        else:
            missed.append(section)
    return len(found) / len(must_have_sections), missed


def _score_anti_fabrication(output: str, must_not_fabricate: list[str]) -> tuple[float, list[str]]:
    """1.0 if no must_not_fabricate term is in output (case-insensitive).

    Note: this uses a soft heuristic. The fabrication checks are descriptive
    ("competitor names not in source"), so we look for *concrete substrings*
    that the LLM might invent. The fixture author should write specific test
    strings (e.g., "Acme Competitor Inc") if they want strict checking.
    """
    if not must_not_fabricate:
        return 1.0, []
    output_lower = output.lower()
    violations = []
    for term in must_not_fabricate:
        # Only check if the term looks like a concrete proper noun, not a description
        # Heuristic: if the term has 3+ words and contains lowercase, treat as a description
        # and skip strict checking. Otherwise check substring.
        is_description = len(term.split()) >= 3 and any(c.islower() for c in term)
        if is_description:
            continue
        if term.lower() in output_lower:
            violations.append(term)
    if not must_not_fabricate or all(
        len(t.split()) >= 3 and any(c.islower() for c in t) for t in must_not_fabricate
    ):
        return 1.0, []
    checkable = [t for t in must_not_fabricate if not (len(t.split()) >= 3 and any(c.islower() for c in t))]
    if not checkable:
        return 1.0, []
    return (len(checkable) - len(violations)) / len(checkable), violations


def _score_length(output: str, min_words: int, max_words: int) -> tuple[float, str]:
    """1.0 if word count is within range, otherwise scaled penalty."""
    word_count = len(output.split())
    if min_words <= word_count <= max_words:
        return 1.0, f"{word_count} words"
    if word_count < min_words:
        # Linear penalty toward 0 as count → 0
        ratio = word_count / max(min_words, 1)
        return max(0.0, ratio), f"{word_count} words (below min {min_words})"
    # Above max — gentler penalty
    overshoot = word_count - max_words
    ratio = max(0.0, 1.0 - (overshoot / max(max_words, 1)))
    return ratio, f"{word_count} words (above max {max_words})"


def _score_richness(output: str, expected: str) -> tuple[float, str]:
    """Heuristic richness classification: empty / sparse / rich.

    Empty: < 30 words or no headers
    Sparse: 30-100 words OR 1-2 sections
    Rich: 100+ words AND 3+ sections
    """
    word_count = len(output.split())
    section_count = len(re.findall(r"^#{1,6}\s+\S", output, re.MULTILINE))

    if word_count < 30 or section_count == 0:
        actual = "empty"
    elif word_count < 100 or section_count < 3:
        actual = "sparse"
    else:
        actual = "rich"

    matched = actual == expected
    return (1.0 if matched else 0.0), f"actual={actual} expected={expected}"


def score_against_expected(output: str, expected: dict) -> dict:
    """Compute all scoring axes and aggregate. Returns a structured score dict."""
    entity_score, missed_entities = _score_entity_recall(
        output, expected.get("must_contain_entities", [])
    )
    section_score, missed_sections = _score_section_completeness(
        output, expected.get("must_have_sections", [])
    )
    fabrication_score, violations = _score_anti_fabrication(
        output, expected.get("must_not_fabricate", [])
    )
    length_score, length_detail = _score_length(
        output,
        expected.get("min_word_count", 0),
        expected.get("max_word_count", 10000),
    )
    richness_score, richness_detail = _score_richness(
        output, expected.get("expected_richness", "rich")
    )

    # Weighted average — entity recall and sections matter most
    aggregate = (
        entity_score * 0.30
        + section_score * 0.25
        + fabrication_score * 0.15
        + length_score * 0.10
        + richness_score * 0.20
    )

    return {
        "aggregate": round(aggregate, 3),
        "entity_recall": {
            "score": round(entity_score, 3),
            "missed": missed_entities,
        },
        "section_completeness": {
            "score": round(section_score, 3),
            "missed": missed_sections,
        },
        "anti_fabrication": {
            "score": round(fabrication_score, 3),
            "violations": violations,
        },
        "length": {
            "score": round(length_score, 3),
            "detail": length_detail,
        },
        "richness": {
            "score": round(richness_score, 3),
            "detail": richness_detail,
        },
    }


# =============================================================================
# Runner
# =============================================================================

async def run_fixture(fixture_path: Path, verbose: bool = False) -> dict:
    """Run one fixture through inference and score the result."""
    fixture = json.loads(fixture_path.read_text())

    # Lazy import — keeps the module loadable for unit tests of the scorer
    from services.context_inference import infer_shared_context

    output, _usage = await infer_shared_context(
        target=fixture["target"],
        text=fixture["inputs"].get("text", ""),
        document_contents=fixture["inputs"].get("document_contents", []),
        url_contents=fixture["inputs"].get("url_contents", []),
        existing_content=fixture["inputs"].get("existing_content", ""),
    )

    score = score_against_expected(output, fixture["expected"])

    return {
        "fixture": fixture_path.name,
        "name": fixture["name"],
        "target": fixture["target"],
        "score": score,
        "output_preview": output[:500] if not verbose else output,
        "output_length_chars": len(output),
    }


def _format_result_line(result: dict) -> str:
    """One-line summary for terminal output."""
    fixture = result["fixture"].replace(".json", "")
    target = result["target"]
    score = result["score"]["aggregate"]
    bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
    return f"  {fixture:<35} {target:<10} {bar} {score:.2f}"


def _print_summary(results: list[dict]) -> None:
    """Print aggregate stats across all fixtures."""
    if not results:
        print("\n  (no fixtures run)\n")
        return

    print("\n=== Per-Fixture Results ===\n")
    for r in results:
        print(_format_result_line(r))

    aggregate = sum(r["score"]["aggregate"] for r in results) / len(results)
    entity_avg = sum(r["score"]["entity_recall"]["score"] for r in results) / len(results)
    section_avg = sum(r["score"]["section_completeness"]["score"] for r in results) / len(results)
    fabrication_avg = sum(r["score"]["anti_fabrication"]["score"] for r in results) / len(results)
    length_avg = sum(r["score"]["length"]["score"] for r in results) / len(results)
    richness_avg = sum(r["score"]["richness"]["score"] for r in results) / len(results)

    print(f"\n=== Aggregate ({len(results)} fixtures) ===")
    print(f"  Mean aggregate score:    {aggregate:.3f}")
    print(f"  Mean entity recall:      {entity_avg:.3f}")
    print(f"  Mean section coverage:   {section_avg:.3f}")
    print(f"  Mean anti-fabrication:   {fabrication_avg:.3f}")
    print(f"  Mean length adherence:   {length_avg:.3f}")
    print(f"  Mean richness accuracy:  {richness_avg:.3f}")
    print()

    # Failures (any fixture below 0.6)
    failures = [r for r in results if r["score"]["aggregate"] < 0.6]
    if failures:
        print(f"\n⚠  {len(failures)} fixture(s) scored below 0.6:")
        for f in failures:
            print(f"  - {f['fixture']}: {f['score']['aggregate']}")
            if f['score']['entity_recall']['missed']:
                print(f"      missed entities: {f['score']['entity_recall']['missed']}")
            if f['score']['section_completeness']['missed']:
                print(f"      missed sections: {f['score']['section_completeness']['missed']}")
        print()


async def main(fixture_filter: str | None = None, verbose: bool = False) -> int:
    """Run all fixtures (or one matching `fixture_filter`). Returns exit code."""
    fixture_dir = Path(__file__).parent / "inference_fixtures"
    fixtures = sorted(fixture_dir.glob("*.json"))

    if fixture_filter:
        fixtures = [f for f in fixtures if fixture_filter in f.name]
        if not fixtures:
            print(f"No fixtures matched filter: {fixture_filter}", file=sys.stderr)
            return 1

    print(f"=== Inference Evaluation ({len(fixtures)} fixtures) ===\n")

    results = []
    for fixture_path in fixtures:
        print(f"  Running {fixture_path.name}...", end=" ", flush=True)
        try:
            result = await run_fixture(fixture_path, verbose=verbose)
            results.append(result)
            print(f"done ({result['score']['aggregate']:.2f})")
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()

    _print_summary(results)

    if verbose:
        print("\n=== Verbose: Outputs ===\n")
        for r in results:
            print(f"--- {r['fixture']} ({r['target']}) ---")
            print(r["output_preview"])
            print()

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Inference evaluation harness (ADR-162)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print full inference outputs")
    parser.add_argument("--fixture", "-f", type=str, help="Filter to fixtures matching this string")
    args = parser.parse_args()

    sys.exit(asyncio.run(main(fixture_filter=args.fixture, verbose=args.verbose)))
