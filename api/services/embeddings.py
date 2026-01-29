"""
Embedding Service

Generates vector embeddings for semantic search using OpenAI's API.
Used by the unified memory architecture (ADR-005).
"""

import os
from typing import Optional
from openai import AsyncOpenAI

# Initialize client
_client: Optional[AsyncOpenAI] = None


def get_client() -> AsyncOpenAI:
    """Get or create OpenAI client."""
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return _client


async def get_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    """
    Generate embedding vector for text.

    Args:
        text: Text to embed (will be truncated if too long)
        model: OpenAI embedding model

    Returns:
        List of floats (1536 dimensions for text-embedding-3-small)
    """
    client = get_client()

    # Truncate to ~8000 tokens worth of text (rough estimate)
    truncated = text[:32000] if len(text) > 32000 else text

    response = await client.embeddings.create(
        model=model,
        input=truncated,
        dimensions=1536  # Fixed dimension for our schema
    )

    return response.data[0].embedding


async def get_embeddings_batch(texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
    """
    Generate embeddings for multiple texts in a single API call.

    Args:
        texts: List of texts to embed
        model: OpenAI embedding model

    Returns:
        List of embedding vectors (same order as input)
    """
    if not texts:
        return []

    client = get_client()

    # Truncate each text
    truncated = [t[:32000] if len(t) > 32000 else t for t in texts]

    response = await client.embeddings.create(
        model=model,
        input=truncated,
        dimensions=1536
    )

    # Return in original order
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
