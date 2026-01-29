"""
Anthropic client for Claude API calls

ADR-007: Tool infrastructure for agent authority
"""

import os
from typing import AsyncGenerator, Optional, Any
from dataclasses import dataclass
from anthropic import AsyncAnthropic


@dataclass
class ToolUseBlock:
    """Represents a tool use request from Claude."""
    id: str
    name: str
    input: dict


@dataclass
class ChatResponse:
    """Structured response from chat completion with tools."""
    content: list[Any]  # Can include text blocks and tool_use blocks
    stop_reason: str  # "end_turn", "tool_use", "max_tokens"
    text: str  # Concatenated text content
    tool_uses: list[ToolUseBlock]  # Extracted tool use blocks


def get_anthropic_client() -> AsyncAnthropic:
    """Get Anthropic client with API key from environment."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set")
    return AsyncAnthropic(api_key=api_key)


def _parse_response(response) -> ChatResponse:
    """Parse Anthropic response into structured ChatResponse."""
    text_parts = []
    tool_uses = []

    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_uses.append(ToolUseBlock(
                id=block.id,
                name=block.name,
                input=block.input
            ))

    return ChatResponse(
        content=response.content,
        stop_reason=response.stop_reason,
        text="".join(text_parts),
        tool_uses=tool_uses,
    )


async def chat_completion(
    messages: list[dict],
    system: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
) -> str:
    """
    Non-streaming chat completion (legacy, no tools).

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


async def chat_completion_with_tools(
    messages: list[dict],
    system: str,
    tools: list[dict],
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
    tool_choice: Optional[dict] = None,
) -> ChatResponse:
    """
    Chat completion with tool use support (ADR-007).

    Args:
        messages: List of {"role": "user"|"assistant", "content": str|list}
        system: System prompt
        tools: List of tool definitions
        model: Model ID
        max_tokens: Maximum response tokens
        tool_choice: Optional tool choice config {"type": "auto"|"any"|"tool", "name": "..."}

    Returns:
        ChatResponse with text, stop_reason, and tool_uses
    """
    client = get_anthropic_client()

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
        "tools": tools,
    }

    if tool_choice:
        kwargs["tool_choice"] = tool_choice

    response = await client.messages.create(**kwargs)
    return _parse_response(response)


async def chat_completion_stream(
    messages: list[dict],
    system: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
) -> AsyncGenerator[str, None]:
    """
    Streaming chat completion (no tools).

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
