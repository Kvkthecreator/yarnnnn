"""
Derive recipes — the kernel registry behind the "Learn from" verb (ADR-450).

KERNEL-INTERNAL, code-seeded data (the STUDIO_LAYOUTS / APPS-table precedent):
versioned here, refined by yarnnn, never written to workspace substrate, never
operator-editable. NOT to be confused with workspace-authored skills/scaffolds
(a separate, deferred, user-owned concept — ADR-450 D1).

A recipe is the constraint prose that turns the generic derive capability
(ADR-448: read a source, author cited meaning-files) into a repeatable,
quality-bounded act for one named TARGET. The ecosystem's lesson (ADR-450 §1):
this layer is SKILL.md-grade instructions on the ordinary agent loop — never
an engine. The lane executes; the recipe constrains.

Consumption: a lane may carry a derive binding {derive_recipe, derive_source}
(routes/lanes.py, the ADR-440 binding pattern); every turn composes
``build_derive_section`` into the lane conventions (lane_runner).

MANAGEMENT DISCIPLINE: ``instructions`` strings are LLM-facing content — every
edit gets an api/prompts/CHANGELOG.md entry (prompt change protocol), and each
recipe earns a Hat-B eval probe as it matures.
"""

from __future__ import annotations

from typing import Optional

#: The registry (ADR-450 D2). slug → {label, description, accepts, target,
#: instructions}. v1 sources are workspace files ("file"); repo/webpage legs
#: arrive as data + intake writers, not new mechanisms (D4).
DERIVE_RECIPES: dict[str, dict] = {
    "context-brief": {
        "label": "Context brief",
        "description": "A reusable understanding of the source — what it is, what matters, what's open.",
        "accepts": ["file"],
        "target": "One markdown brief in a meaning-folder, citing the source.",
        "instructions": """Produce a CONTEXT BRIEF — a derived understanding the workspace can
reuse, not a copy of the source (the raw is already retained; your job is the
understanding).

Steps:
1. Read the source fully before writing anything.
2. Write ONE markdown file into the meaning-folder that fits the topic (an
   existing peer folder if one matches; otherwise a sensibly named new one, or
   the Documents home). Name it after the subject, not the source file.
3. Shape: a one-paragraph "What this is" · key facts and figures (verbatim
   where precision matters) · the entities/people/systems involved · decisions
   or claims the source makes · open questions / gaps you noticed.

Quality bar:
- Under ~150 lines. Selective beats complete — drop what a reader wouldn't act on.
- Every load-bearing claim traceable to the source; never invent specifics.
- Write for a colleague who will NOT read the source.

Anti-patterns: wholesale copying; summarizing the document's structure instead
of its content ("section 2 discusses…"); vague abstraction with no facts.""",
    },
    "design-system": {
        "label": "Design system",
        "description": "A design-system folder (tokens-first CSS + manifest) Studio artifacts can wear.",
        "accepts": ["file"],
        "target": "A meaning-folder satisfying the ADR-449 contract: _design.yaml (name + ordered css) + the css files it lists.",
        "instructions": """Produce a DESIGN SYSTEM — a meaning-folder that satisfies the workspace
design-system contract, so Studio artifacts can wear it and the workspace can
track what depends on it.

The contract (must hold exactly):
- A folder (e.g. 'design-system/' or a name the member prefers) containing
  `_design.yaml` with `name:` (display name) and `css:` (an ORDERED list of
  folder-relative css files — list ONLY files you actually created).
- The css files themselves, tokens FIRST: a custom-properties block (:root
  color / type-scale / spacing / radius / shadow variables), then component
  rules built on those variables.

Steps:
1. Read the source and EXTRACT evidence: explicit tokens (css variables,
   tailwind config values, brand-guideline values), recurring colors, type
   choices, spacing rhythms. Note each value's origin.
2. Write the token css first, then a small rules layer, then `_design.yaml`.
3. Re-read `_design.yaml` and verify every listed file exists and the order
   is tokens-before-rules.

Quality bar:
- Every value evidenced in the source — never invent brand values; if the
  source is thin, produce fewer tokens and say so in the lane, don't pad.
- Lean: tokens + reusable component rules only.

Anti-patterns: dumping entire stylesheets verbatim (derive, don't mirror);
page-specific selectors (#hero-2024) in a system meant to be reusable;
inventing a palette the source doesn't show; a manifest listing files you
didn't write.""",
    },
    "deck": {
        "label": "Deck",
        "description": "A slide deck where every slide earns its claim from the source.",
        "accepts": ["file"],
        "target": "A deck artifact — slides grounded in the source, titles as claims, evidence cited.",
        "instructions": """Produce a DECK — a slide narrative a teammate could present, derived
from the source. (Studio flow: the deck is the bound artifact; the authoring
posture owns the slide/block format — these are the CONTENT constraints.)

Steps:
1. Read the source fully; list the 5–10 claims it actually supports.
2. Shape the narrative: title slide (the thesis) · the claims, one per slide ·
   a closing slide (so-what / next steps).
3. Each slide: the TITLE is the claim (a sentence someone could disagree
   with, never a topic word); the body is the evidence — figures, quotes,
   comparisons from the source.

Quality bar:
- Every slide's claim traceable to the source; where you extrapolate, mark
  the slide "(inferred)".
- 6–12 slides. A slide that carries no evidence gets cut, not padded.
- Prefer the source's own numbers and phrases over paraphrase mush.

Anti-patterns: topic-word titles ("Market", "Team"); wall-of-text slides;
agenda/divider filler; claims the source never makes; burying the thesis
past slide one.""",
    },
    "prd": {
        "label": "Product description (PRD)",
        "description": "A grounded product-requirements document derived from the source.",
        "accepts": ["file"],
        "target": "One PRD markdown file with the conventional sections, grounded in the source, inferences marked.",
        "instructions": """Produce a PRD — a product-requirements document a teammate (or another
AI) could act on, derived from the source.

Steps:
1. Read the source fully; separate what it STATES from what you INFER.
2. Write ONE markdown file into the product's meaning-folder (create one if
   none fits), named for the product/feature.
3. Sections, in order: Problem · Users · Goals · Non-goals · Requirements
   (functional, then non-functional) · Success metrics · Open questions.

Quality bar:
- Grounded: every requirement traceable to the source; where you infer,
  mark it "(inferred)" so readers can challenge it.
- Non-goals and Open questions are mandatory — an empty one means you
  haven't thought about scope; say what the source leaves undecided.
- Requirements are testable statements, not themes.

Anti-patterns: solution language in the Problem section; requirements the
source never supports; omitting Open questions to look complete.""",
    },
}


def list_recipes() -> list[dict]:
    """The chooser payload (served on the lane capability envelope — D5)."""
    return [
        {
            "slug": slug,
            "label": r["label"],
            "description": r["description"],
            "accepts": r["accepts"],
        }
        for slug, r in DERIVE_RECIPES.items()
    ]


def get_recipe(slug: str) -> Optional[dict]:
    return DERIVE_RECIPES.get((slug or "").strip())


def build_derive_section(
    recipe_slug: str,
    source_path: str,
    artifact_path: Optional[str] = None,
) -> str:
    """The derive-bound lane's posture overlay (ADR-450 D3 + ADR-452 D3) — pure.

    Recipe instructions + the source + the two mechanics every recipe shares:
    read the projection for binary raws, and cite via derived_from (the
    ADR-448 edge — how the workspace knows what was made from what).

    ``artifact_path`` (ADR-452 D3 — the studio mode): when the lane is ALSO
    artifact-bound, a target-override block redirects the recipe's
    file-creation mechanics to the bound artifact; the content constraints
    and citation discipline stand unchanged.
    """
    recipe = get_recipe(recipe_slug)
    if not recipe:
        return ""
    src = (
        source_path
        if source_path.startswith("/workspace/")
        else "/workspace/" + (source_path or "").lstrip("/")
    )
    target_line = recipe["target"]
    override = ""
    if artifact_path:
        target_line = f"the bound artifact at {artifact_path}"
        override = f"""
TARGET OVERRIDE (studio flow): your target is the bound artifact at
{artifact_path} — author the derived content THERE, in the artifact's format
(the authoring posture above owns the grammar: blocks, slides, layout). Any
instruction below about creating a separate markdown file is superseded by
this; the content constraints, quality bar, and citation discipline stand.
"""
    return f"""## Learn from (this lane's job)
This lane exists to derive from ONE source:
  SOURCE: {src}
  TARGET: {target_line}

Mechanics (apply to every step below):
- If the source is a binary raw (its content is a one-line caption with an
  attachment), read its co-located text projection instead: the sibling file
  ending `.extracted.md`.
- Every file you author from the source MUST pass
  derived_from=["{src}"] on the write — that edge is how the workspace
  shows what was made from what. Cite additional files you read the same way.
- The source is retained and immutable — never edit it; derive beside it.
{override}
{recipe['instructions']}

When done, tell the member what you created (paths) and what you could NOT
evidence from the source."""
