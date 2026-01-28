"""
Anthropic client for Claude API calls
"""

import os
from typing import AsyncGenerator, Optional
from anthropic import AsyncAnthropic


def get_anthropic_client() -> AsyncAnthropic:
    """Get Anthropic client with API key from environment."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set")
    return AsyncAnthropic(api_key=api_key)


async def chat_completion(
    messages: list[dict],
    system: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
) -> str:
    """
    Non-streaming chat completion.

    Args:
        messages: List of {"role": "user"|"assistant", "content": str}
        system: System prompt
        model: Model ID
        max_tokens: Maximum response tokens

    Returns:
        Assistant response text
    """
    client = get_anthropic_client()

    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )

    return response.content[0].text


async def chat_completion_stream(
    messages: list[dict],
    system: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
) -> AsyncGenerator[str, None]:
    """
    Streaming chat completion.

    Args:
        messages: List of {"role": "user"|"assistant", "content": str}
        system: System prompt
        model: Model ID
        max_tokens: Maximum response tokens

    Yields:
        Text chunks as they arrive
    """
    client = get_anthropic_client()

    async with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text
