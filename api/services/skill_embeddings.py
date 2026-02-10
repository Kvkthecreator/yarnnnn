"""
Semantic Skill Matching (ADR-040)

Provides semantic skill detection using embeddings as a fallback to pattern matching.
This enables natural language skill activation even when exact patterns don't match.

Architecture:
- Skill descriptions are embedded once (cached at module level)
- User messages are embedded on-demand
- Cosine similarity determines best match
- Threshold controls precision/recall tradeoff
"""

import logging
import math
from typing import Optional

from services.embeddings import get_embedding, get_embeddings_batch

logger = logging.getLogger(__name__)


# =============================================================================
# Skill Descriptions for Semantic Matching
# =============================================================================
# These descriptions are designed to capture the semantic intent of each skill,
# including variations and synonyms that might not appear in trigger_patterns.

SKILL_DESCRIPTIONS = {
    "board-update": """
        Create recurring board update deliverables for investors and board members.
        Monthly or quarterly updates with company metrics, progress, challenges, and asks.
        Investor communications, board reports, investor updates, VC updates.
        Send updates to the board, share progress with investors.
    """,

    "status-report": """
        Set up recurring status reports for managers, teams, or stakeholders.
        Weekly or daily progress updates, wins, blockers, alignment.
        Progress reports, team updates, status summaries, weekly standups.
        Share progress with the team, send updates to my manager.
    """,

    "research-brief": """
        Create competitive intelligence or market research briefs.
        Track competitors, market trends, technology developments.
        Competitor analysis, market research, competitive intel, industry tracking.
        Monitor competitors, track what rivals are doing, competitive landscape.
    """,

    "stakeholder-update": """
        Send regular updates to clients, external partners, or stakeholders.
        Project updates, client communications, partner reports.
        Keep clients informed, update external stakeholders, partner communications.
    """,

    "meeting-summary": """
        Generate recurring meeting summaries from conversations.
        Standup notes, one-on-one summaries, team meeting recaps.
        Meeting notes, action items, discussion summaries.
        All hands summary, team sync notes, weekly meeting recap.
    """,

    "newsletter-section": """
        Create recurring sections for newsletters or company digests.
        Founder letters, weekly digests, product updates, company news.
        Write newsletter content, company update emails, founder memo.
    """,

    "changelog": """
        Generate product release notes or changelog entries.
        New features, bug fixes, improvements, version updates.
        Release notes, what's new, product releases, shipped features.
        Document what we shipped, write up the sprint, version update.
    """,

    "one-on-one-prep": """
        Prepare for recurring one-on-one meetings.
        Direct report conversations, skip-level meetings, mentee sessions.
        1:1 prep, meeting preparation, discussion points.
        Prepare for my meeting with, get ready for 1-1.
    """,

    "client-proposal": """
        Create proposal templates for client engagements.
        Service offerings, scope of work, project proposals.
        SOW, engagement proposals, client pitches, project bids.
        Write a proposal for, pitch deck for client.
    """,

    "performance-review": """
        Generate self-assessment documents for performance reviews.
        Quarterly retrospectives, annual evaluations, self-assessments.
        Review prep, accomplishments summary, career reflection.
        Write my self-review, prepare for annual review.
    """,
}


# =============================================================================
# Embedding Cache
# =============================================================================

_skill_embeddings: dict[str, list[float]] = {}
_embeddings_initialized = False


async def _initialize_skill_embeddings():
    """Initialize skill embeddings cache (called once on first use)."""
    global _skill_embeddings, _embeddings_initialized

    if _embeddings_initialized:
        return

    logger.info("Initializing skill embeddings cache...")

    # Get all descriptions
    skill_names = list(SKILL_DESCRIPTIONS.keys())
    descriptions = [SKILL_DESCRIPTIONS[name] for name in skill_names]

    # Batch embed all descriptions
    embeddings = await get_embeddings_batch(descriptions)

    # Cache results
    for skill_name, embedding in zip(skill_names, embeddings):
        _skill_embeddings[skill_name] = embedding

    _embeddings_initialized = True
    logger.info(f"Skill embeddings cache initialized with {len(_skill_embeddings)} skills")


async def get_skill_embeddings() -> dict[str, list[float]]:
    """Get cached skill embeddings (initializes on first call)."""
    if not _embeddings_initialized:
        await _initialize_skill_embeddings()
    return _skill_embeddings


# =============================================================================
# Similarity Computation
# =============================================================================

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    Returns a value between -1 and 1, where 1 means identical direction.

    Uses pure Python to avoid numpy dependency.
    """
    if len(a) != len(b):
        return 0.0

    # Compute dot product
    dot_product = sum(x * y for x, y in zip(a, b))

    # Compute norms
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


# =============================================================================
# Semantic Detection
# =============================================================================

# Threshold tuned for precision/recall balance
# Higher = fewer false positives, lower = more matches
SEMANTIC_THRESHOLD = 0.72


async def detect_skill_semantic(
    user_message: str,
    threshold: float = SEMANTIC_THRESHOLD
) -> tuple[Optional[str], float]:
    """
    Detect skill using semantic similarity.

    Args:
        user_message: The user's message to analyze
        threshold: Minimum similarity score to consider a match

    Returns:
        Tuple of (skill_name or None, confidence score)
        - If confidence >= threshold, skill_name is the best match
        - If confidence < threshold, skill_name is None
    """
    # Get message embedding
    message_embedding = await get_embedding(user_message)

    # Get skill embeddings (cached)
    skill_embeddings = await get_skill_embeddings()

    # Find best match
    best_skill: Optional[str] = None
    best_score: float = 0.0

    for skill_name, skill_embedding in skill_embeddings.items():
        score = cosine_similarity(message_embedding, skill_embedding)
        if score > best_score:
            best_score = score
            best_skill = skill_name

    # Return match only if above threshold
    if best_score >= threshold:
        logger.debug(f"Semantic skill match: '{best_skill}' with confidence {best_score:.3f}")
        return (best_skill, best_score)

    logger.debug(f"No semantic skill match (best was '{best_skill}' at {best_score:.3f})")
    return (None, best_score)
