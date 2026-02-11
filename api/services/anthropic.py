"""
Anthropic client for Claude API calls

ADR-007: Tool infrastructure for agent authority
"""

import os
import logging
from typing import AsyncGenerator, Optional, Any
from dataclasses import dataclass
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)


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


def _truncate_tool_result(result: dict, max_items: int = 5, max_content_len: int = 200) -> str:
    """
    Truncate tool result to prevent context overflow.

    ADR-043: Keep tool results concise for conversation history.
    Large results (like List with 20+ items) can cause prompt overflow.

    Args:
        result: Tool result dict
        max_items: Max items to include in lists
        max_content_len: Max length for content strings

    Returns:
        JSON string of truncated result
    """
    import json

    def truncate_value(v, depth=0):
        if depth > 3:
            return "..."
        if isinstance(v, str):
            if len(v) > max_content_len:
                return v[:max_content_len] + "..."
            return v
        elif isinstance(v, list):
            if len(v) > max_items:
                truncated = [truncate_value(item, depth + 1) for item in v[:max_items]]
                truncated.append(f"... and {len(v) - max_items} more")
                return truncated
            return [truncate_value(item, depth + 1) for item in v]
        elif isinstance(v, dict):
            return {k: truncate_value(val, depth + 1) for k, val in v.items()}
        else:
            return v

    truncated = truncate_value(result)
    return json.dumps(truncated)


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


@dataclass
class StreamEvent:
    """Event from streaming chat with tools."""
    type: str  # "text", "tool_use", "tool_result", "done"
    content: Any  # text chunk, tool use block, tool result, or None


async def chat_completion_stream_with_tools(
    messages: list[dict],
    system: str,
    tools: list[dict],
    tool_executor: Any,  # Callable[[str, dict], Awaitable[dict]]
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
    max_tool_rounds: int = 5,
    tool_choice: Optional[dict] = None,
) -> AsyncGenerator[StreamEvent, None]:
    """
    Streaming chat completion with tool support.

    Yields StreamEvents for:
    - text: Text chunks as they arrive
    - tool_use: When Claude wants to use a tool (before execution)
    - tool_result: After tool execution completes
    - done: When conversation is complete

    Args:
        messages: List of conversation messages
        system: System prompt
        tools: List of tool definitions
        tool_executor: Async function(tool_name, tool_input) -> result dict
        model: Model ID
        max_tokens: Maximum response tokens
        max_tool_rounds: Maximum tool use cycles
        tool_choice: Optional tool choice config {"type": "auto"|"any"|"tool", "name": "..."}

    Yields:
        StreamEvent objects
    """
    client = get_anthropic_client()
    working_messages = list(messages)

    for round_num in range(max_tool_rounds):
        # Accumulate the full response for this round
        full_response = None

        # Build kwargs for the stream call
        stream_kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": working_messages,
            "tools": tools,
        }
        # Only use tool_choice on first round to force initial tool use
        # After that, let model decide (it might want to respond after action)
        if tool_choice and round_num == 0:
            stream_kwargs["tool_choice"] = tool_choice

        async with client.messages.stream(**stream_kwargs) as stream:
            # Stream text as it arrives
            async for text in stream.text_stream:
                yield StreamEvent(type="text", content=text)

            # Get final response to check for tool use
            full_response = await stream.get_final_message()

        # Check if we need to handle tool use
        if full_response.stop_reason == "tool_use":
            # Extract tool use blocks
            tool_uses = []
            text_content = []

            for block in full_response.content:
                if block.type == "tool_use":
                    tool_uses.append(block)
                elif block.type == "text":
                    text_content.append({"type": "text", "text": block.text})

            # Add assistant message with tool use to history
            assistant_content = text_content + [
                {
                    "type": "tool_use",
                    "id": t.id,
                    "name": t.name,
                    "input": t.input
                }
                for t in tool_uses
            ]
            working_messages.append({
                "role": "assistant",
                "content": assistant_content
            })

            # Execute each tool and yield events
            tool_results = []
            for tool_use in tool_uses:
                logger.info(f"[ANTHROPIC] Executing tool: {tool_use.name} with input: {str(tool_use.input)[:200]}")
                # Signal that tool is being used
                yield StreamEvent(
                    type="tool_use",
                    content={
                        "id": tool_use.id,
                        "name": tool_use.name,
                        "input": tool_use.input
                    }
                )

                # Execute the tool
                result = await tool_executor(tool_use.name, tool_use.input)
                msg = f"[ANTHROPIC] Tool {tool_use.name} result: ui_action={result.get('ui_action')}, success={result.get('success')}"
                print(msg, flush=True)
                logger.info(msg)

                # Signal tool result
                yield StreamEvent(
                    type="tool_result",
                    content={
                        "tool_use_id": tool_use.id,
                        "name": tool_use.name,
                        "result": result
                    }
                )

                # Truncate large results to prevent context overflow
                # ADR-043: Keep tool results concise for conversation history
                truncated_result = _truncate_tool_result(result)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": truncated_result
                })

            # Add tool results to messages
            working_messages.append({
                "role": "user",
                "content": tool_results
            })

            # Continue to next round (will stream Claude's response to tool results)
            continue

        else:
            # No tool use, we're done
            yield StreamEvent(type="done", content=None)
            return

    # Reached max rounds
    yield StreamEvent(type="done", content=None)
