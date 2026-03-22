"""
Semantic Command Matching (ADR-040)

Provides semantic command detection using embeddings as a fallback to pattern matching.
This enables natural language command activation even when exact patterns don't match.

Architecture:
- Command descriptions are embedded once (cached at module level)
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
# Command Descriptions for Semantic Matching
# =============================================================================
# These descriptions are designed to capture the semantic intent of each command,
# including variations and synonyms that might not appear in trigger_patterns.

COMMAND_DESCRIPTIONS = {
    # =========================================================================
    # Agent Creation Commands
    # =========================================================================
    "create": """
        Create a new recurring agent. Set up an agent to do work automatically.
        Make an agent, build an agent, new agent, start something recurring.
        I want to automate, help me set up something that runs regularly.
    """,

    "summary": """
        Create a work summary agent that synthesizes activity across platforms.
        Weekly or daily progress updates, status reports, board updates, investor updates.
        Summarize my work, progress report, stakeholder update, team update.
        Share progress with the team, send updates to my manager, board report.
    """,

    "recap": """
        Create a platform recap agent to catch up on everything in a connected platform.
        Slack recap, Notion summary, channel summary.
        Catch me up on Slack, what happened in Notion.
        Daily recap, weekly digest, platform summary, catch up on messages.
    """,

    "research": """
        Set up proactive insights that watch your platforms and surface what matters.
        Deep research, competitive intelligence, trend monitoring, emerging themes.
        Watch my platforms, surface insights, investigate trends, what should I know.
        Monitor competitors, track industry developments, research this topic.
    """,

    # =========================================================================
    # Capability Commands
    # =========================================================================
    "search": """
        Search across connected platforms to find specific information.
        Find in Slack, look up in Notion, find messages.
        Search my platforms, look for, find that conversation, where did I see.
        Platform search, content search, find across my tools.
    """,

    "sync": """
        Refresh platform data to pull the latest from connected tools.
        Sync my Slack, update Notion data, resync platforms.
        Pull latest data, get fresh data, update my platforms, resync.
    """,

    "memory": """
        Save a preference, fact, or instruction to persistent memory.
        Remember that, save to memory, note that, keep in mind.
        Store this preference, remember my settings, save this fact.
        I prefer, my preference is, always do, never do.
    """,

    "web": """
        Search the web for current information, news, or research.
        Web search, Google, look up online, current events, latest news.
        What's happening with, search the internet, find online.
        Competitor research, industry news, technical docs, current trends.
    """,
}


# =============================================================================
# Embedding Cache
# =============================================================================

_command_embeddings: dict[str, list[float]] = {}
_embeddings_initialized = False


async def _initialize_command_embeddings():
    """Initialize command embeddings cache (called once on first use)."""
    global _command_embeddings, _embeddings_initialized

    if _embeddings_initialized:
        return

    logger.info("Initializing command embeddings cache...")

    # Get all descriptions
    command_names = list(COMMAND_DESCRIPTIONS.keys())
    descriptions = [COMMAND_DESCRIPTIONS[name] for name in command_names]

    # Batch embed all descriptions
    embeddings = await get_embeddings_batch(descriptions)

    # Cache results
    for command_name, embedding in zip(command_names, embeddings):
        _command_embeddings[command_name] = embedding

    _embeddings_initialized = True
    logger.info(f"Command embeddings cache initialized with {len(_command_embeddings)} commands")


async def get_command_embeddings() -> dict[str, list[float]]:
    """Get cached command embeddings (initializes on first call)."""
    if not _embeddings_initialized:
        await _initialize_command_embeddings()
    return _command_embeddings


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


async def detect_command_semantic(
    user_message: str,
    threshold: float = SEMANTIC_THRESHOLD
) -> tuple[Optional[str], float]:
    """
    Detect command using semantic similarity.

    Args:
        user_message: The user's message to analyze
        threshold: Minimum similarity score to consider a match

    Returns:
        Tuple of (command_name or None, confidence score)
        - If confidence >= threshold, command_name is the best match
        - If confidence < threshold, command_name is None
    """
    # Get message embedding
    message_embedding = await get_embedding(user_message)

    # Get command embeddings (cached)
    cmd_embeddings = await get_command_embeddings()

    # Find best match
    best_command: Optional[str] = None
    best_score: float = 0.0

    for command_name, command_embedding in cmd_embeddings.items():
        score = cosine_similarity(message_embedding, command_embedding)
        if score > best_score:
            best_score = score
            best_command = command_name

    # Return match only if above threshold
    if best_score >= threshold:
        logger.debug(f"Semantic command match: '{best_command}' with confidence {best_score:.3f}")
        return (best_command, best_score)

    logger.debug(f"No semantic command match (best was '{best_command}' at {best_score:.3f})")
    return (None, best_score)
