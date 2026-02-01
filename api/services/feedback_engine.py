"""
Feedback Engine Service

ADR-018: Recurring Deliverables Product Pivot

Computes edit metrics between draft and final content:
- Edit distance score (0.0 = no edits, 1.0 = complete rewrite)
- Edit categories (additions, deletions, restructures, rewrites)
- Structured diff for review

The feedback engine is core to the product's learning loop.
"""

import re
import difflib
from typing import Optional


def compute_edit_metrics(draft: str, final: str) -> dict:
    """
    Compute comprehensive edit metrics between draft and final content.

    Args:
        draft: Original draft content produced by YARNNN
        final: Final content after user edits

    Returns:
        Dict with:
        - diff: Structured diff representation
        - categories: Categorized edits (additions, deletions, etc.)
        - distance_score: 0.0-1.0 edit distance score
    """
    if not draft or not final:
        return {
            "diff": None,
            "categories": {},
            "distance_score": 0.0 if draft == final else 1.0,
        }

    # Compute basic diff
    diff = compute_diff(draft, final)

    # Categorize edits
    categories = categorize_edits(draft, final, diff)

    # Compute distance score
    distance_score = compute_distance_score(draft, final)

    return {
        "diff": diff,
        "categories": categories,
        "distance_score": distance_score,
    }


def compute_diff(draft: str, final: str) -> list[dict]:
    """
    Compute a structured diff between draft and final.

    Returns a list of change operations with context.
    """
    draft_lines = draft.splitlines(keepends=True)
    final_lines = final.splitlines(keepends=True)

    differ = difflib.unified_diff(
        draft_lines,
        final_lines,
        fromfile="draft",
        tofile="final",
        lineterm="",
    )

    changes = []
    current_chunk = None

    for line in differ:
        if line.startswith("@@"):
            # New chunk
            if current_chunk:
                changes.append(current_chunk)
            current_chunk = {
                "header": line.strip(),
                "removals": [],
                "additions": [],
            }
        elif line.startswith("-") and not line.startswith("---"):
            if current_chunk:
                current_chunk["removals"].append(line[1:].strip())
        elif line.startswith("+") and not line.startswith("+++"):
            if current_chunk:
                current_chunk["additions"].append(line[1:].strip())

    if current_chunk:
        changes.append(current_chunk)

    return changes


def categorize_edits(draft: str, final: str, diff: list[dict]) -> dict:
    """
    Categorize edits into semantic categories.

    Categories:
    - additions: Content user added that wasn't in draft
    - deletions: Content user removed from draft
    - restructures: Sections that were moved/reordered
    - rewrites: Content that was rephrased (same meaning, different words)
    """
    categories = {
        "additions": [],
        "deletions": [],
        "restructures": [],
        "rewrites": [],
    }

    # Extract pure additions and deletions
    for chunk in diff:
        removals = chunk.get("removals", [])
        additions = chunk.get("additions", [])

        # Check for rewrites (similar content with different wording)
        matched_removals = set()
        matched_additions = set()

        for i, removal in enumerate(removals):
            for j, addition in enumerate(additions):
                if j not in matched_additions:
                    similarity = compute_similarity(removal, addition)
                    if similarity > 0.5:
                        # This is a rewrite, not a pure deletion/addition
                        categories["rewrites"].append({
                            "original": removal[:100],
                            "revised": addition[:100],
                            "similarity": round(similarity, 2),
                        })
                        matched_removals.add(i)
                        matched_additions.add(j)
                        break

        # Unmatched removals are true deletions
        for i, removal in enumerate(removals):
            if i not in matched_removals and removal.strip():
                categories["deletions"].append(summarize_content(removal))

        # Unmatched additions are true additions
        for j, addition in enumerate(additions):
            if j not in matched_additions and addition.strip():
                categories["additions"].append(summarize_content(addition))

    # Detect restructures by comparing section order
    draft_sections = extract_sections(draft)
    final_sections = extract_sections(final)

    if draft_sections and final_sections:
        restructures = detect_restructures(draft_sections, final_sections)
        categories["restructures"] = restructures

    # Limit each category to top items
    for key in categories:
        if isinstance(categories[key], list) and len(categories[key]) > 5:
            categories[key] = categories[key][:5]

    return categories


def compute_distance_score(draft: str, final: str) -> float:
    """
    Compute normalized edit distance score.

    0.0 = no edits (identical)
    1.0 = complete rewrite (no overlap)
    """
    if not draft and not final:
        return 0.0
    if not draft or not final:
        return 1.0

    # Use SequenceMatcher ratio
    ratio = difflib.SequenceMatcher(None, draft, final).ratio()

    # Convert similarity to distance
    distance = 1.0 - ratio

    return round(distance, 3)


def compute_similarity(text1: str, text2: str) -> float:
    """
    Compute similarity between two text strings.
    """
    if not text1 or not text2:
        return 0.0

    # Normalize texts
    t1 = normalize_text(text1)
    t2 = normalize_text(text2)

    return difflib.SequenceMatcher(None, t1, t2).ratio()


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.
    """
    # Lowercase and remove extra whitespace
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def summarize_content(content: str, max_length: int = 100) -> str:
    """
    Summarize content to a short description.
    """
    content = content.strip()
    if len(content) <= max_length:
        return content

    # Try to break at a word boundary
    truncated = content[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.7:
        truncated = truncated[:last_space]

    return truncated + "..."


def extract_sections(text: str) -> list[str]:
    """
    Extract section headers from text.

    Looks for markdown headers or numbered sections.
    """
    sections = []

    # Markdown headers
    for match in re.finditer(r"^#+\s+(.+)$", text, re.MULTILINE):
        sections.append(match.group(1).strip())

    # Numbered sections (1. Section, 2. Section)
    for match in re.finditer(r"^\d+\.\s+(.+)$", text, re.MULTILINE):
        sections.append(match.group(1).strip())

    # Bold section headers (**Section**)
    for match in re.finditer(r"\*\*([^*]+)\*\*", text):
        header = match.group(1).strip()
        if len(header) < 50:  # Likely a header, not emphasized text
            sections.append(header)

    return sections


def detect_restructures(draft_sections: list[str], final_sections: list[str]) -> list[dict]:
    """
    Detect sections that were moved or reordered.
    """
    restructures = []

    # Find sections present in both but in different positions
    for i, section in enumerate(draft_sections):
        if section in final_sections:
            final_pos = final_sections.index(section)
            if final_pos != i:
                restructures.append({
                    "section": section,
                    "moved_from": i + 1,
                    "moved_to": final_pos + 1,
                })

    return restructures


def create_feedback_memory(
    categories: dict,
    distance_score: float,
    feedback_notes: Optional[str] = None,
) -> str:
    """
    Create a memory-formatted string from feedback data.

    This is what gets stored as a memory for future synthesis context.
    """
    lines = ["[DELIVERABLE FEEDBACK]"]

    if distance_score < 0.1:
        lines.append("User approved with minimal edits - current approach is working well.")
    elif distance_score < 0.3:
        lines.append("User made moderate edits. Key patterns:")
    else:
        lines.append("User made significant edits. Important feedback:")

    if categories.get("additions"):
        lines.append(f"  - Added: {', '.join(categories['additions'][:3])}")
        lines.append("    → Include similar content in future versions")

    if categories.get("deletions"):
        lines.append(f"  - Removed: {', '.join(categories['deletions'][:3])}")
        lines.append("    → Avoid including similar content")

    if categories.get("rewrites"):
        for rewrite in categories["rewrites"][:2]:
            lines.append(f"  - Rephrased: '{rewrite['original']}' → '{rewrite['revised']}'")

    if categories.get("restructures"):
        for restructure in categories["restructures"][:2]:
            lines.append(f"  - Moved '{restructure['section']}' to position {restructure['moved_to']}")

    if feedback_notes:
        lines.append(f"  - User note: {feedback_notes}")

    return "\n".join(lines)
