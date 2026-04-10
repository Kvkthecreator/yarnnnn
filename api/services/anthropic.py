from __future__ import annotations
"""
Anthropic client for Claude API calls

ADR-007: Tool infrastructure for agent authority
"""

import os
import logging
from typing import AsyncGenerator, Optional, Any, Union
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
    usage: Optional[dict] = None  # ADR-101: {input_tokens, output_tokens}


def get_anthropic_client() -> AsyncAnthropic:
    """Get Anthropic client with API key from environment."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY must be set")
    return AsyncAnthropic(api_key=api_key)


def _truncate_tool_result(result: dict, max_items: int = 5, max_content_len: int = 200, max_depth: int = 3) -> str:
    """
    Truncate tool result to prevent context overflow.

    ADR-043: Keep tool results concise for conversation history.
    Large results (like List with 20+ items) can cause prompt overflow.
    When truncation occurs, adds _truncated metadata so the model knows
    results were clipped and can advise the user to narrow their query.

    Args:
        result: Tool result dict
        max_items: Max items to include in lists
        max_content_len: Max length for content strings
        max_depth: Maximum nesting depth before collapsing to "..."
                   Platform tools need depth>=5: result→result→channels→[item]→field

    Returns:
        JSON string of truncated result
    """
    import json

    truncation_info = {}  # tracks {total: N, shown: M} for the first truncated list

    def truncate_value(v, depth=0):
        if depth > max_depth:
            return "..."
        if isinstance(v, str):
            if len(v) > max_content_len:
                return v[:max_content_len] + "..."
            return v
        elif isinstance(v, list):
            if len(v) > max_items:
                if not truncation_info:
                    truncation_info["total"] = len(v)
                    truncation_info["shown"] = max_items
                truncated = [truncate_value(item, depth + 1) for item in v[:max_items]]
                truncated.append(f"... and {len(v) - max_items} more")
                return truncated
            return [truncate_value(item, depth + 1) for item in v]
        elif isinstance(v, dict):
            return {k: truncate_value(val, depth + 1) for k, val in v.items()}
        else:
            return v

    truncated = truncate_value(result)

    if truncation_info:
        # Add structured truncation metadata so the model knows results were clipped
        if isinstance(truncated, dict):
            truncated["_truncated"] = True
            truncated["_truncation_note"] = (
                f"Showing {truncation_info['shown']} of {truncation_info['total']} results. "
                f"Use a more specific query to narrow results."
            )

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

    # ADR-101: Extract token usage from response (including cache metrics)
    usage = None
    if hasattr(response, 'usage') and response.usage:
        cache_creation = getattr(response.usage, 'cache_creation_input_tokens', 0) or 0
        cache_read = getattr(response.usage, 'cache_read_input_tokens', 0) or 0
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cache_creation_input_tokens": cache_creation,
            "cache_read_input_tokens": cache_read,
        }
        # Log cache efficiency for observability
        total_input = response.usage.input_tokens + cache_creation + cache_read
        if total_input > 0:
            cache_pct = round(cache_read / total_input * 100) if cache_read else 0
            logger.info(
                f"[TOKENS] in={response.usage.input_tokens} out={response.usage.output_tokens} "
                f"cache_create={cache_creation} cache_read={cache_read} "
                f"cache_hit={cache_pct}% model={getattr(response, 'model', '?')}"
            )

    return ChatResponse(
        content=response.content,
        stop_reason=response.stop_reason,
        text="".join(text_parts),
        tool_uses=tool_uses,
        usage=usage,
    )


def _prepare_system(system: str | list[dict]) -> list[dict]:
    """Normalize system prompt to content blocks for prompt caching.

    Accepts either a plain string (wrapped as a single text block)
    or a list of content blocks (passed through). Callers that want
    prompt caching should pass a list with cache_control on static blocks.
    """
    if isinstance(system, str):
        return [{"type": "text", "text": system}]
    return system


async def chat_completion(
    messages: list[dict],
    system: str | list[dict],
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
) -> str:
    """
    Non-streaming chat completion (legacy, no tools).

    Args:
        messages: List of {"role": "user"|"assistant", "content": str}
        system: System prompt (string or content blocks with cache_control)
        model: Model ID
        max_tokens: Maximum response tokens

    Returns:
        Assistant response text
    """
    client = get_anthropic_client()

    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=_prepare_system(system),
        messages=messages,
        extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
    )

    return response.content[0].text


async def chat_completion_with_usage(
    messages: list[dict],
    system: str | list[dict],
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
) -> tuple[str, dict]:
    """Non-streaming chat completion returning (text, usage).

    ADR-171: Use this instead of chat_completion() when the caller needs to
    record token spend to token_usage. Usage dict has input_tokens + output_tokens.
    """
    client = get_anthropic_client()

    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=_prepare_system(system),
        messages=messages,
        extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
    )

    usage = {}
    if response.usage:
        usage = {
            "input_tokens": getattr(response.usage, "input_tokens", 0),
            "output_tokens": getattr(response.usage, "output_tokens", 0),
        }
    return response.content[0].text, usage


async def chat_completion_with_tools(
    messages: list[dict],
    system: str | list[dict],
    tools: list[dict],
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
    tool_choice: Optional[dict] = None,
) -> ChatResponse:
    """
    Chat completion with tool use support (ADR-007).

    Args:
        messages: List of {"role": "user"|"assistant", "content": str|list}
        system: System prompt (string or content blocks with cache_control)
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
        "system": _prepare_system(system),
        "messages": messages,
        "tools": tools,
        "extra_headers": {"anthropic-beta": "prompt-caching-2024-07-31"},
    }

    if tool_choice:
        kwargs["tool_choice"] = tool_choice

    response = await client.messages.create(**kwargs)
    return _parse_response(response)


async def chat_completion_stream(
    messages: list[dict],
    system: str | list[dict],
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
) -> AsyncGenerator[str, None]:
    """
    Streaming chat completion (no tools).

    Args:
        messages: List of {"role": "user"|"assistant", "content": str}
        system: System prompt (string or content blocks with cache_control)
        model: Model ID
        max_tokens: Maximum response tokens

    Yields:
        Text chunks as they arrive
    """
    client = get_anthropic_client()

    async with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=_prepare_system(system),
        messages=messages,
        extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
    ) as stream:
        async for text in stream.text_stream:
            yield text


def _microcompact_tool_history(messages: list[dict], keep_recent: int = 3) -> None:
    """Clear old tool results from message history to prevent geometric growth.

    CC-style microcompact: replaces tool_result content older than the last N
    results with a stub. The model retains tool_use_id linkage but doesn't
    re-process full content on subsequent rounds.

    Mutates messages in place.
    """
    positions = []  # (msg_idx, block_idx)
    for i, msg in enumerate(messages):
        if msg.get("role") != "user" or not isinstance(msg.get("content"), list):
            continue
        for j, block in enumerate(msg["content"]):
            if isinstance(block, dict) and block.get("type") == "tool_result":
                positions.append((i, j))

    to_clear = positions[:-keep_recent] if len(positions) > keep_recent else []
    for msg_idx, block_idx in to_clear:
        block = messages[msg_idx]["content"][block_idx]
        if block.get("content") != "[Prior tool result cleared]":
            block["content"] = "[Prior tool result cleared]"


@dataclass
class StreamEvent:
    """Event from streaming chat with tools."""
    type: str  # "text", "tool_use", "tool_result", "usage", "done"
    content: Any  # text chunk, tool use block, tool result, usage dict, or None


async def chat_completion_stream_with_tools(
    messages: list[dict],
    system: str | list[dict],
    tools: list[dict],
    tool_executor: Any,  # Callable[[str, dict], Awaitable[dict]]
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
    max_tool_rounds: int = 15,  # Safety net only; model should decide when done
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

    # Track cumulative token usage across all rounds
    total_input_tokens = 0
    total_output_tokens = 0

    for round_num in range(max_tool_rounds):
        # Microcompact: clear old tool results to prevent geometric context growth.
        # Keeps the N most recent tool results, replaces older ones with stubs.
        if round_num >= 2:
            _microcompact_tool_history(working_messages, keep_recent=3)

        # Accumulate the full response for this round
        full_response = None

        # Build kwargs for the stream call
        system_blocks = _prepare_system(system)
        stream_kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_blocks,
            "messages": working_messages,
            "tools": tools,
            "extra_headers": {"anthropic-beta": "prompt-caching-2024-07-31"},
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

        # Track token usage from this round (including cache metrics)
        if hasattr(full_response, 'usage') and full_response.usage:
            total_input_tokens += full_response.usage.input_tokens
            total_output_tokens += full_response.usage.output_tokens
            cache_creation = getattr(full_response.usage, 'cache_creation_input_tokens', 0) or 0
            cache_read = getattr(full_response.usage, 'cache_read_input_tokens', 0) or 0
            # Log cache efficiency per round
            total_in = full_response.usage.input_tokens + cache_creation + cache_read
            cache_pct = round(cache_read / total_in * 100) if total_in and cache_read else 0
            logger.info(
                f"[TOKENS] stream round={round_num} in={full_response.usage.input_tokens} "
                f"out={full_response.usage.output_tokens} cache_create={cache_creation} "
                f"cache_read={cache_read} cache_hit={cache_pct}%"
            )
            # Emit usage event after each round
            yield StreamEvent(
                type="usage",
                content={
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                    "total_tokens": total_input_tokens + total_output_tokens,
                    "cache_creation_input_tokens": cache_creation,
                    "cache_read_input_tokens": cache_read,
                }
            )

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
                # Per-tool limits:
                # - platform_*: high limits (TP needs full channel/message lists)
                # - WebSearch: preserve snippet content (already capped at 500 chars
                #   per result in the primitive; default 200 would double-truncate)
                # - everything else: default 200 chars (entity lookups, system state)
                if tool_use.name.startswith("platform_"):
                    truncated_result = _truncate_tool_result(
                        result, max_items=100, max_content_len=1000, max_depth=6
                    )
                elif tool_use.name == "WebSearch":
                    truncated_result = _truncate_tool_result(
                        result, max_items=10, max_content_len=500, max_depth=4
                    )
                else:
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

    # Reached max rounds - generate a final text response
    # This prevents silent failure when tools are exhausted
    logger.warning(f"[ANTHROPIC] Reached max_tool_rounds ({max_tool_rounds}), generating summary")

    # Make one final call without tools to force a text response
    try:
        # Append summary instruction to the system blocks
        summary_blocks = _prepare_system(system) + [
            {"type": "text", "text": "\n\n[SYSTEM: You've used several tools. Now provide a brief summary response to the user based on what you found. Do not request any more tools.]"}
        ]
        final_response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=summary_blocks,
            messages=working_messages,
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
            # No tools - force text response
        )

        if final_response.content:
            for block in final_response.content:
                if block.type == "text":
                    yield StreamEvent(type="text", content=block.text)

        # Track final usage
        if hasattr(final_response, 'usage') and final_response.usage:
            total_input_tokens += final_response.usage.input_tokens
            total_output_tokens += final_response.usage.output_tokens
            yield StreamEvent(
                type="usage",
                content={
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                    "total_tokens": total_input_tokens + total_output_tokens,
                }
            )
    except Exception as e:
        logger.error(f"[ANTHROPIC] Failed to generate final response: {e}")
        yield StreamEvent(type="text", content="I've gathered some information but encountered a limit. Let me know if you'd like me to continue.")

    yield StreamEvent(type="done", content=None)
