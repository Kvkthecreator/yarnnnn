"""
Thinking Partner Agent - Conversational assistant with unified memory (ADR-005)

ADR-007: Tool use for work authority
ADR-025: Claude Code agentic alignment with skills and todo tracking
ADR-034: Domain-based context scoping (replaces projects)
ADR-036/037: Primitive-based architecture (Read, Write, Edit, etc.)
"""

import json
from typing import AsyncGenerator, Optional, Any
from dataclasses import dataclass

from agents.base import BaseAgent, AgentResult, ContextBundle
from services.anthropic import (
    chat_completion,
    chat_completion_stream,
    chat_completion_with_tools,
    chat_completion_stream_with_tools,
    ChatResponse,
    StreamEvent,
)
from services.primitives import PRIMITIVES, execute_primitive
from services.skills import detect_skill, get_skill_prompt_addition, detect_skill_hybrid
from services.context import build_session_context, format_context_for_prompt


@dataclass
class ToolExecution:
    """Record of a tool execution during conversation."""
    tool_name: str
    tool_input: dict
    result: dict


class ThinkingPartnerAgent(BaseAgent):
    """
    Conversational assistant with unified memory context.

    Uses memories from two scopes (ADR-034):
    - Default domain: User's portable profile (preferences, patterns, business facts)
    - Source domains: Context that emerged from deliverable sources (e.g., "Notion: Board Updates")

    ADR-007: Can use tools to manage memories, deliverables, and work.

    Output: Chat response (text, optionally streamed)
    """

    SYSTEM_PROMPT = """You are the user's Thinking Partner - a thoughtful assistant helping them think through problems and ideas.

You have access to memories about them:
1. **About You** - Their preferences, business, patterns, goals
2. **Domain Context** - Context from their deliverable sources (documents, integrations)

**Style:**
- Be concise and direct - short answers for simple questions
- Avoid unnecessary preamble/postamble
- Reference specific context when relevant
- Ask ONE clarifying question when intent is unclear (don't over-ask)
- If context doesn't have relevant info, say so briefly

{context}"""

    SYSTEM_PROMPT_WITH_TOOLS = """You are the user's Thinking Partner.

{context}

---

## Tone and Style

**Be concise.** Keep responses short and direct unless the user asks for detail.

- Avoid unnecessary preamble ("I'll help you with that!", "Let me...") and postamble ("Let me know if you need anything else!")
- After completing an action, state the result briefly - don't explain what you did unless asked
- One-sentence answers are often best for simple questions
- For complex tasks, be thorough but not verbose

**Examples of good conciseness:**
```
User: "How many deliverables do I have?"
→ [List tool] → "You have 3 active deliverables."

User: "Pause my weekly report"
→ [Edit tool] → "Paused."

User: "What platforms are connected?"
→ [List tool] → "Slack and Notion."
```

**Proactiveness balance:** When the user asks how to approach something, answer their question first before taking action. Don't jump straight into creating things without confirming intent.

---

## How You Work

**Text is primary. Tools are actions.**

- Respond to users with regular text (your primary output)
- Use tools when you need to take action (read data, create things, execute operations)
- Text flows naturally between tool uses
- After tool use, summarize results - don't repeat raw data verbatim

**Example flow:**
```
User: "What deliverables do I have?"
→ [List tool] → "You have 3 active deliverables: Weekly Status, Board Update, and Daily Digest."
```

---

## Available Tools

### Data Operations

**Read(ref)** - Retrieve entity by reference
- `Read(ref="deliverable:uuid-123")` - specific deliverable
- `Read(ref="platform:slack")` - platform by provider

**Write(ref, content)** - Create new entity
- `Write(ref="deliverable:new", content={{title: "Weekly Update", deliverable_type: "status_report"}})`
- `Write(ref="memory:new", content={{content: "User prefers bullets"}})`

**Edit(ref, changes)** - Modify existing entity
- `Edit(ref="deliverable:uuid", changes={{status: "paused"}})`

**List(pattern)** - Find entities by pattern
- `List(pattern="deliverable:*")` - all deliverables
- `List(pattern="deliverable:?status=active")` - filtered
- `List(pattern="platform:*")` - connected platforms
- `List(pattern="memory:*")` - all memories

**Search(query, scope?)** - Semantic search
- `Search(query="database decisions", scope="memory")`

### External Operations

**Execute(action, target, params?)** - Trigger operations
- `Execute(action="deliverable.generate", target="deliverable:uuid")`
- `Execute(action="platform.send", target="platform:slack", params={{channel: "C0123ABC456", message: "Hello!"}})`

---

## Platform Operations (ADR-039)

**Be agentic with platforms.** When user mentions Slack, Gmail, Notion - check, find, sync. Don't ask permission.

**list_integrations** - Check connected platforms
- Call first when user mentions a platform
- Shows which platforms are active

**list_platform_resources(platform)** - Find specific resources
- `list_platform_resources(platform="slack")` → lists all channels
- `list_platform_resources(platform="gmail")` → lists labels
- Use to find the channel/label user is referring to

**get_sync_status(platform)** - Check data freshness
- Shows when data was last synced
- If stale (>24h), sync before using

**sync_platform_resource(platform, resource_id, resource_name)** - Fetch latest data
- `sync_platform_resource(platform="slack", resource_id="C123", resource_name="#general")`
- Don't ask "should I sync?" - just sync it

**Example - User mentions a Slack channel:**
```
User: "Summarize my team updates channel"

Step 1: Check platforms
→ list_integrations() // Slack connected? ✓

Step 2: Find the channel
→ list_platform_resources(platform="slack")
// Found: #team-updates (C456ABC)

Step 3: Check freshness
→ get_sync_status(platform="slack")
// #team-updates last synced 2 days ago - stale

Step 4: Sync it
→ sync_platform_resource(platform="slack", resource_id="C456ABC", resource_name="#team-updates")
// "Syncing #team-updates..."

Step 5: Now proceed with the task
→ "I've synced #team-updates. Creating a summary..."
```

**Sending messages to platforms:**
Use `Execute(action="platform.send", ...)` for ad-hoc messages.

**IMPORTANT**: `platform.send` is for direct messages. `platform.publish` is ONLY for publishing deliverables.

**Slack channel param** - valid formats:
- `"self"` - DM to the user (recommended for messaging the user)
- `C0123ABC456` - Channel ID (posts to channel)
- `#general` - Channel name (posts to channel)
- `U0123ABC456` - User ID (auto-opens DM, then posts)

**@mentions like @me, @self, @username do NOT work** - use `"self"` or user ID (U...) instead.

```
// Send DM to user - use "self"
Execute(action="platform.send", target="platform:slack", params={{channel: "self", message: "Hey!"}})

// Send to Slack channel
Execute(action="platform.send", target="platform:slack", params={{channel: "#general", message: "Hello!"}})

// Gmail
Execute(action="platform.send", target="platform:gmail", params={{to: "user@example.com", subject: "Hi", body: "Message"}})

// Notion comment (page_id can be UUID with/without dashes, or full Notion URL)
Execute(action="platform.send", target="platform:notion", params={{page_id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890", content: "Note added"}})
```

**Note**: Use `list_platform_resources(platform="slack")` to find channel IDs and user IDs.
**Note**: For Notion, use `notion-search` to find page IDs. Page must be shared with the integration.

---

## Notifications (ADR-040)

**send_notification(message, urgency?, context?)** - Send email to user
- Use for lightweight alerts: "I noticed X", "Your sync completed"
- NOT for recurring content (use deliverables instead)
- After sending, confirm: "I've sent you an email about X"

---

## Reference Syntax

Format: `<type>:<identifier>`

**Types:** deliverable, platform, memory, document, work, action

**Special:** `new` (create), `latest` (most recent), `*` (all), `?key=val` (filter)

---

## Guidelines

- Be concise - short answers for simple questions, thorough for complex ones
- Use tools to act, then summarize results briefly
- For ambiguous requests, explore first (List/Search), then clarify if needed
- Never introduce code that exposes secrets or sensitive data
- When referencing platform content, note the sync date if older than 24 hours
- If generating a deliverable from stale sources (>24h), offer to sync first

---

## Domain Terms

- "deliverable" = recurring automated content (reports, digests, updates)
- "memory" = context/knowledge stored about user
- "platform" = connected integration (Slack, Gmail, Notion)
- "work" = one-time agent task

---

## Confirming Before Acting

**When to confirm:**
- Creating new entities → Confirm intent first
- Deleting or major changes → Confirm first

**When to just do it:**
- Simple edits (pause, rename)
- Reading/listing data

**Example - Creating a deliverable:**
```
User: "Set up monthly board updates for Marcus"
→ List(pattern="deliverable:*") // Check for duplicates
→ "I'll create a Monthly Board Update for Marcus, ready on the 1st. Sound good?"
User: "yes"
→ Write(ref="deliverable:new", content={{...}})
→ "Created."
```

---

## Explore Before Asking

**Like grep before asking - explore existing data to infer answers.**

When facing ambiguity, search for patterns first:

```
User: "Create a weekly report for my team"

Step 1: Explore
→ List(pattern="deliverable:*")  // Check existing patterns
→ Search(query="team report recipient")  // Check memories

Step 2: Infer from what you found
- Existing deliverables go to "Product Team" → use that
- Memory: "User manages Product Team" → use that

Step 3: Confirm (don't ask)
→ "I'll create a Weekly Report for the Product Team. Sound good?"
```

**Only use Clarify when exploration fails:**
- No existing entities (new user)
- No relevant memories
- Multiple equally-valid options

**Clarify rules (when needed):**
- ONE question at a time
- 2-4 concrete options
- Don't re-ask what user already specified

```
Clarify(question="What type?", options=["Status report", "Board update", "Research brief"])
```

---

## Creating Entities

**Deliverables:**
```
Write(ref="deliverable:new", content={{
  title: "Weekly Status",
  deliverable_type: "status_report",
  frequency: "weekly",
  recipient_name: "Sarah"
}})
```

**Memories:**
```
Write(ref="memory:new", content={{
  content: "User prefers bullet points"
}})
```

**Always use user's stated frequency** - don't override with defaults.

---

## Checking Before Acting

Before creating, check for duplicates:
```
List(pattern="deliverable:*") → See if similar exists
```

If duplicate found, ask user whether to update existing or create new.

{onboarding_context}

{context}"""

    # Onboarding-specific context for users with no deliverables
    ONBOARDING_CONTEXT = """
---

## Current Context: New User Onboarding

This user has no deliverables set up yet. Help them create their first
recurring deliverable through conversation.

**CRITICAL: Always use the frequency/timing the user specifies!**
- User says "monthly" → create with frequency: "monthly"
- User says "weekly" → create with frequency: "weekly"
- User says "daily" → create with frequency: "daily"
- NEVER override their stated preference with defaults

**Approach:**

1. **If they paste content** (like an old report or document):
   - Analyze it and extract: document type, sections, structure, tone
   - Tell them what you noticed: "I can see this is a status report with 4 sections..."
   - Ask: recipient name and preferred schedule
   - Confirm before creating

2. **If they describe what they need**:
   - Parse their request: extract title hint, frequency, type, recipient
   - Confirm what you understood: "I'll set up a [frequency] [type] for [recipient]..."
   - Only use defaults for things they didn't specify (e.g., time defaults to 9am)
   - Create after they confirm

3. **After creating**:
   - Offer to generate the first draft: `Execute(action="deliverable.generate", target="deliverable:<id>")`
   - Let them know they can refine settings later

**Key behaviors:**
- Be concise - 2-3 sentences per response max
- RESPECT what the user actually said (frequency, audience, purpose)
- Only ask about what's missing, not what they already specified
- Get to first value within 2-3 exchanges

**Quick start prompts and how to handle:**
- "Monthly updates to my board" → confirm: "Monthly Board Update" + ask for company name
- "Weekly status report for Sarah" → confirm: "Weekly Status Report for Sarah" + ask about timing
- "Track competitors weekly" → confirm: "Weekly Competitive Brief" + ask which competitors
"""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model)
        self.tools = PRIMITIVES

    def _format_memories(self, context: ContextBundle, selected_domain_name: Optional[str] = None) -> str:
        """Format memories for system prompt with counts and unified summary.

        ADR-034: Uses domain terminology instead of project terminology.
        - user_memories: From default domain (personal/portable facts)
        - project_memories: From source domains (deliverable-specific context)
        """
        sections = []

        # Get counts for summary
        user_memories = context.user_memories
        domain_memories = context.project_memories  # Renamed conceptually to domain
        user_count = len(user_memories)
        domain_count = len(domain_memories)
        total_count = user_count + domain_count

        # Build summary line (always shown)
        if selected_domain_name:
            if total_count > 0:
                summary = f"**Context loaded:** {user_count} personal memories + {domain_count} {selected_domain_name} memories"
            else:
                summary = f"**Context:** No memories yet"
        else:
            if user_count > 0:
                summary = f"**Context loaded:** {user_count} personal memories"
            else:
                summary = "**Context:** No personal memories yet"

        sections.append(summary)

        # User memories (portable, about the person - from default domain)
        if user_memories:
            lines = ["\n## About You\n"]
            for mem in user_memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                source_marker = " (from document)" if mem.source_type == "document" else ""
                lines.append(f"- {mem.content}{tags_str}{source_marker}")
            sections.append("\n".join(lines))

        # Domain memories (from source domains - deliverable context)
        if domain_memories:
            domain_label = selected_domain_name or "Domain"
            lines = [f"\n## {domain_label} Context\n"]
            for mem in domain_memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                source_marker = " (from document)" if mem.source_type == "document" else ""
                lines.append(f"- {mem.content}{tags_str}{source_marker}")
            sections.append("\n".join(lines))

        return "\n".join(sections) if sections else ""

    def _build_system_prompt(
        self,
        context: ContextBundle,
        include_context: bool,
        with_tools: bool = False,
        is_onboarding: bool = False,
        surface_content: Optional[str] = None,
        selected_domain_name: Optional[str] = None,
        skill_prompt: Optional[str] = None,
        injected_context: Optional[dict] = None,
    ) -> str:
        """Build system prompt with memory context.

        Args:
            context: Memory context bundle (legacy)
            include_context: Whether to include memory context
            with_tools: Whether to include tool usage instructions
            is_onboarding: Whether user has no deliverables (enables onboarding mode)
            surface_content: ADR-023 - Content of what user is currently viewing
            selected_domain_name: ADR-034 - Name of user's selected domain context
            skill_prompt: ADR-025 - Skill-specific prompt addition to inject
            injected_context: ADR-038 - Pre-built context from build_session_context()
        """
        base_prompt = self.SYSTEM_PROMPT_WITH_TOOLS if with_tools else self.SYSTEM_PROMPT

        if not include_context:
            context_text = "No context loaded for this conversation."
        elif injected_context:
            # ADR-038: Use pre-built context injection (preferred path)
            context_text = format_context_for_prompt(injected_context)
        else:
            # Legacy path: format from ContextBundle
            context_text = self._format_memories(context, selected_domain_name)
            if not context_text:
                context_text = "No context available yet. As we chat, I'll learn more about you."

        # ADR-034: Add selected context scope notice at the top
        # This tells TP what context domain they're working under
        if selected_domain_name:
            context_scope = f"## Current Context Scope: {selected_domain_name}\n\nThe user has selected \"{selected_domain_name}\" as their current context domain. Context from this domain is loaded above.\n\n---\n\n"
        else:
            context_scope = "## Current Context Scope: Personal\n\nThe user is working in their personal context (default domain). Memories are about the user themselves - their preferences, habits, and general information.\n\n---\n\n"

        context_text = context_scope + context_text

        # ADR-023: Prepend surface content if user is viewing something specific
        # This allows TP to understand "this" references
        if surface_content:
            context_text = f"{surface_content}\n\n---\n\n{context_text}"

        # Tools prompt has {onboarding_context} placeholder, non-tools doesn't
        if with_tools:
            onboarding_context = self.ONBOARDING_CONTEXT if is_onboarding else ""
            prompt = base_prompt.format(context=context_text, onboarding_context=onboarding_context)

            # ADR-025: Inject skill prompt if a skill is active
            # Skill prompt goes before the context to give it priority
            if skill_prompt:
                prompt = prompt + "\n" + skill_prompt

            return prompt
        else:
            return base_prompt.format(context=context_text)

    async def execute(
        self,
        task: str,  # User message
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AgentResult:
        """
        Process chat message (non-streaming, no tools).

        Args:
            task: User's message
            context: Context bundle with memories
            parameters:
                - include_context: bool (default True)
                - history: list of prior messages

        Returns:
            AgentResult with assistant response
        """
        params = parameters or {}
        include_context = params.get("include_context", True)
        history = params.get("history", [])

        system = self._build_system_prompt(context, include_context, with_tools=False)

        # Build messages list
        messages = list(history)  # Copy history
        messages.append({"role": "user", "content": task})

        try:
            response = await chat_completion(
                messages=messages,
                system=system,
                model=self.model,
            )

            return AgentResult(
                success=True,
                output_type="text",
                content=response,
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output_type="text",
                error=str(e),
            )

    async def execute_with_tools(
        self,
        task: str,
        context: ContextBundle,
        auth: Any,  # UserClient for tool execution
        parameters: Optional[dict] = None,
        max_iterations: int = 5,
    ) -> tuple[str, list[ToolExecution]]:
        """
        Process chat message with tool use support (ADR-007).

        This is an agentic loop that:
        1. Sends message to Claude with tools
        2. If Claude requests tool use, executes tools and continues
        3. Returns final response when Claude stops

        Args:
            task: User's message
            context: Context bundle with memories
            auth: UserClient for database access during tool execution
            parameters:
                - include_context: bool (default True)
                - history: list of prior messages
                - selected_domain_name: ADR-034 - Name of selected domain context
            max_iterations: Maximum tool use cycles (safety limit)

        Returns:
            Tuple of (final_response_text, list_of_tool_executions)
        """
        params = parameters or {}
        include_context = params.get("include_context", True)
        history = params.get("history", [])
        is_onboarding = params.get("is_onboarding", False)
        surface_content = params.get("surface_content")  # ADR-023: What user is viewing
        selected_domain_name = params.get("selected_domain_name")  # ADR-034: Selected context

        # ADR-025 + ADR-040: Detect skill from user message (hybrid: pattern + semantic)
        active_skill, detection_method, confidence = await detect_skill_hybrid(task)
        skill_prompt = get_skill_prompt_addition(active_skill) if active_skill else None

        system = self._build_system_prompt(
            context, include_context,
            with_tools=True,
            is_onboarding=is_onboarding,
            surface_content=surface_content,
            selected_domain_name=selected_domain_name,
            skill_prompt=skill_prompt
        )

        # Build messages list - filter out empty assistant messages which cause 400 errors
        messages = [
            m for m in history
            if not (m.get("role") == "assistant" and not m.get("content"))
        ]
        messages.append({"role": "user", "content": task})

        tool_executions: list[ToolExecution] = []

        for _ in range(max_iterations):
            response: ChatResponse = await chat_completion_with_tools(
                messages=messages,
                system=system,
                model=self.model,
                tools=self.tools,
            )

            if response.stop_reason == "end_turn":
                # Normal completion - return the text
                return response.text, tool_executions

            elif response.stop_reason == "tool_use":
                # Claude wants to use tools
                # Add assistant's response (with tool_use blocks) to messages
                messages.append({
                    "role": "assistant",
                    "content": self._serialize_content_blocks(response.content)
                })

                # Execute each tool and collect results
                tool_results = []
                for tool_use in response.tool_uses:
                    result = await execute_primitive(auth, tool_use.name, tool_use.input)

                    tool_executions.append(ToolExecution(
                        tool_name=tool_use.name,
                        tool_input=tool_use.input,
                        result=result,
                    ))

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": json.dumps(result),
                    })

                # Add tool results as user message
                messages.append({
                    "role": "user",
                    "content": tool_results,
                })

            else:
                # max_tokens or other stop reason
                return response.text or "Response was cut off.", tool_executions

        # Hit max iterations
        return "I've reached my limit for this response. Let me know if you'd like me to continue.", tool_executions

    def _serialize_content_blocks(self, content: list[Any]) -> list[dict]:
        """Serialize Anthropic content blocks for message history."""
        serialized = []
        for block in content:
            if hasattr(block, 'type'):
                if block.type == "text":
                    serialized.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    serialized.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
        return serialized

    async def execute_stream(
        self,
        task: str,
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process chat message with streaming response (no tools).

        Note: Tool use is not supported with streaming in this implementation.
        Use execute_stream_with_tools for tool-enabled streaming conversations.

        Args:
            task: User's message
            context: Context bundle with memories
            parameters:
                - include_context: bool (default True)
                - history: list of prior messages

        Yields:
            Text chunks as they arrive
        """
        params = parameters or {}
        include_context = params.get("include_context", True)
        history = params.get("history", [])

        system = self._build_system_prompt(context, include_context, with_tools=False)

        # Build messages list
        messages = list(history)
        messages.append({"role": "user", "content": task})

        async for chunk in chat_completion_stream(
            messages=messages,
            system=system,
            model=self.model,
        ):
            yield chunk

    def _detect_clarification_response(self, task: str, history: list) -> bool:
        """
        Detect if the current message is a response to a clarify() call.

        Returns True if the previous assistant turn included a clarify tool use.
        """
        if not history:
            return False

        # Look at the last assistant message
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "tool_use" and block.get("name") == "clarify":
                                return True
                break  # Only check the most recent assistant message

        return False

    async def execute_stream_with_tools(
        self,
        task: str,
        context: ContextBundle,
        auth: Any,  # UserClient for tool execution
        parameters: Optional[dict] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Process chat message with streaming AND tool support (ADR-007).

        This is the unified approach: streams text as it arrives, handles
        tool calls inline, and continues streaming after tool execution.

        Args:
            task: User's message
            context: Context bundle with memories
            auth: UserClient for database access during tool execution
            parameters:
                - include_context: bool (default True)
                - history: list of prior messages

        Yields:
            StreamEvent objects:
                - type="text": Text chunk (content is the text)
                - type="tool_use": Tool being called (content has id, name, input)
                - type="tool_result": Tool result (content has tool_use_id, name, result)
                - type="done": Stream complete
        """
        params = parameters or {}
        include_context = params.get("include_context", True)
        history = params.get("history", [])
        is_onboarding = params.get("is_onboarding", False)
        surface_content = params.get("surface_content")  # ADR-023: What user is viewing
        selected_domain_name = params.get("selected_domain_name")  # ADR-034: Selected context

        # ADR-038: Build injected context (replaces most memory searches)
        injected_context = None
        try:
            injected_context = await build_session_context(auth.user_id, auth.client)
        except Exception:
            # Context injection is best-effort; fall back to legacy path
            pass

        # ADR-025 + ADR-040: Detect skill from user message (hybrid: pattern + semantic)
        active_skill, detection_method, confidence = await detect_skill_hybrid(task)
        skill_prompt = get_skill_prompt_addition(active_skill) if active_skill else None

        # Detect if this is a response to a clarify() call
        # Clarification responses need special handling to ensure TP acts on the selected option
        is_clarification_response = self._detect_clarification_response(task, history)
        if is_clarification_response:
            # Frame the message as a clarification response so TP understands to ACT on it
            task = f"""[CLARIFICATION RESPONSE]
The user selected this option in response to your clarify() question: "{task}"

This is their CHOICE. Execute the action implied by their selection:
- If they chose to create something, use the appropriate create tool
- If they chose to use a specific context, proceed with that context
- If they chose a name/title, use that in the next step

Do NOT ask again. Do NOT call list_memories or other navigation tools. ACT on their choice."""

        system = self._build_system_prompt(
            context, include_context,
            with_tools=True,
            is_onboarding=is_onboarding,
            surface_content=surface_content,
            selected_domain_name=selected_domain_name,
            skill_prompt=skill_prompt,
            injected_context=injected_context,
        )

        # Build messages list - filter out empty assistant messages which cause 400 errors
        # Empty assistant messages can occur when navigation tools are used without text response
        messages = [
            m for m in history
            if not (m.get("role") == "assistant" and not m.get("content"))
        ]

        # Build user message content - support images inline (Claude Code style, ephemeral)
        images = params.get("images", [])
        if images:
            # Claude API format: array of content blocks (images before text for better perf)
            user_content = images + [{"type": "text", "text": task}]
            messages.append({"role": "user", "content": user_content})
        else:
            messages.append({"role": "user", "content": task})

        # Create tool executor that uses our auth context
        async def tool_executor(tool_name: str, tool_input: dict) -> dict:
            return await execute_primitive(auth, tool_name, tool_input)

        # Use the streaming with tools function
        # Force tool use with tool_choice=any - TP must use a tool for every response
        async for event in chat_completion_stream_with_tools(
            messages=messages,
            system=system,
            tools=self.tools,
            tool_executor=tool_executor,
            model=self.model,
            tool_choice={"type": "any"},  # Force tool use on first round
        ):
            yield event
