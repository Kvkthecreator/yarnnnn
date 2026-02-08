"""
MCP Client Manager.

Manages MCP server connections via stdio subprocess transport.
This is the standard pattern used by Claude Desktop.

Official MCP servers are Node.js packages spawned via npx:
- @modelcontextprotocol/server-slack
- @notionhq/notion-mcp-server

Tokens are passed via environment variables to the subprocess.
"""

import os
import logging
import asyncio
from typing import Optional, Any
from contextlib import AsyncExitStack

from .types import IntegrationProvider, ExportResult, ExportStatus

logger = logging.getLogger(__name__)

# MCP SDK imports - may not be available in all environments
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("[MCP] mcp package not installed. Integration features disabled.")


# Server command configurations
SERVER_COMMANDS: dict[str, list[str]] = {
    "slack": ["npx", "-y", "@modelcontextprotocol/server-slack"],
    "notion": ["npx", "-y", "@notionhq/notion-mcp-server", "--transport", "stdio"],
    # ADR-029: Gmail MCP server (shinzo-labs)
    "gmail": ["npx", "-y", "@shinzolabs/gmail-mcp"],
}

# Environment variable mappings per provider
SERVER_ENV_KEYS: dict[str, list[str]] = {
    "slack": ["SLACK_BOT_TOKEN", "SLACK_TEAM_ID"],
    "notion": ["NOTION_TOKEN"],  # Official Notion MCP server uses NOTION_TOKEN
    # ADR-029: Gmail requires OAuth credentials + refresh token
    "gmail": ["CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN"],
}


class MCPClientManager:
    """
    Manages MCP server connections via stdio subprocess transport.

    Each user+provider combination gets its own subprocess and session.
    Sessions are created on-demand and can be explicitly closed.

    Usage:
        manager = MCPClientManager()

        # Export to Slack
        result = await manager.export_to_slack(
            user_id="user-123",
            channel="#general",
            content="Hello from YARNNN!",
            bot_token="xoxb-...",
            team_id="T..."
        )

        # Clean up when done
        await manager.close_all()
    """

    def __init__(self):
        """Initialize the MCP client manager."""
        self._sessions: dict[str, "ClientSession"] = {}
        self._exit_stacks: dict[str, AsyncExitStack] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, key: str) -> asyncio.Lock:
        """Get or create a lock for a session key."""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    def _parse_mcp_result(self, result: Any) -> Any:
        """
        Parse MCP CallToolResult into usable data.

        MCP SDK returns CallToolResult objects with a content attribute.
        The content is typically a list of TextContent items with JSON strings.
        """
        import json

        # Already a dict or list - return as-is
        if isinstance(result, (dict, list)):
            return result

        # MCP CallToolResult - extract content
        if hasattr(result, "content"):
            for content_item in result.content:
                if hasattr(content_item, "text"):
                    try:
                        return json.loads(content_item.text)
                    except (json.JSONDecodeError, TypeError):
                        # Return raw text if not JSON
                        return content_item.text

        # Fallback - return as-is
        return result

    async def get_session(
        self,
        user_id: str,
        provider: str,
        env: dict[str, str]
    ) -> "ClientSession":
        """
        Get or create an MCP client session for user+provider.

        Args:
            user_id: User identifier
            provider: Integration provider (slack, notion)
            env: Environment variables for the subprocess (tokens)

        Returns:
            Active ClientSession

        Raises:
            ValueError: If provider is unknown or MCP not available
            RuntimeError: If session creation fails
        """
        if not MCP_AVAILABLE:
            raise RuntimeError("MCP package not installed. Run: pip install mcp")

        key = f"{user_id}:{provider}"

        # Use lock to prevent race conditions when creating sessions
        async with self._get_lock(key):
            if key in self._sessions:
                return self._sessions[key]

            # Get server command
            cmd = SERVER_COMMANDS.get(provider)
            if not cmd:
                raise ValueError(f"Unknown provider: {provider}")

            # Validate required env vars
            required_keys = SERVER_ENV_KEYS.get(provider, [])
            missing = [k for k in required_keys if k not in env]
            if missing:
                raise ValueError(f"Missing required env vars for {provider}: {missing}")

            logger.info(f"[MCP] Creating session for {key}")

            try:
                server_params = StdioServerParameters(
                    command=cmd[0],
                    args=cmd[1:],
                    env={**os.environ, **env}  # Inherit base env + add tokens
                )

                exit_stack = AsyncExitStack()
                self._exit_stacks[key] = exit_stack

                stdio_transport = await exit_stack.enter_async_context(
                    stdio_client(server_params)
                )
                session = await exit_stack.enter_async_context(
                    ClientSession(stdio_transport[0], stdio_transport[1])
                )
                await session.initialize()

                # Debug: list available tools
                try:
                    tools_result = await session.list_tools()
                    tool_names = [t.name for t in tools_result.tools] if tools_result.tools else []
                    logger.info(f"[MCP] Available tools for {provider}: {tool_names}")
                except Exception as e:
                    logger.warning(f"[MCP] Could not list tools for {provider}: {e}")

                self._sessions[key] = session
                logger.info(f"[MCP] Session created for {key}")

                return session

            except Exception as e:
                logger.error(f"[MCP] Failed to create session for {key}: {e}")
                # Clean up on failure
                if key in self._exit_stacks:
                    try:
                        await self._exit_stacks[key].aclose()
                    except Exception:
                        pass
                    del self._exit_stacks[key]
                raise RuntimeError(f"Failed to create MCP session: {e}") from e

    async def call_tool(
        self,
        user_id: str,
        provider: str,
        tool_name: str,
        arguments: dict[str, Any],
        env: dict[str, str]
    ) -> Any:
        """
        Call a tool on an MCP server.

        Args:
            user_id: User identifier
            provider: Integration provider
            tool_name: Name of the tool to call
            arguments: Tool arguments
            env: Environment variables (tokens)

        Returns:
            Tool result
        """
        session = await self.get_session(user_id, provider, env)
        result = await session.call_tool(tool_name, arguments)
        return result

    async def export_to_slack(
        self,
        user_id: str,
        channel: str,
        content: str,
        bot_token: str,
        team_id: str
    ) -> ExportResult:
        """
        Export content to Slack via MCP.

        Args:
            user_id: User identifier
            channel: Slack channel (ID or name with #)
            content: Message content (markdown)
            bot_token: Slack bot token (xoxb-...)
            team_id: Slack team/workspace ID

        Returns:
            ExportResult with status and message details
        """
        try:
            result = await self.call_tool(
                user_id=user_id,
                provider="slack",
                tool_name="slack_post_message",
                arguments={"channel": channel, "text": content},
                env={
                    "SLACK_BOT_TOKEN": bot_token,
                    "SLACK_TEAM_ID": team_id
                }
            )

            # Parse result - actual structure depends on MCP server
            return ExportResult(
                status=ExportStatus.SUCCESS,
                external_id=result.get("ts") if isinstance(result, dict) else None,
                metadata={"result": result}
            )

        except Exception as e:
            logger.error(f"[MCP] Slack export failed: {e}")
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=str(e)
            )

    async def export_to_notion(
        self,
        user_id: str,
        parent_id: str,
        title: str,
        content: str,
        auth_token: str
    ) -> ExportResult:
        """
        Export content to Notion via MCP.

        Args:
            user_id: User identifier
            parent_id: Parent page or database ID
            title: Page title
            content: Page content (markdown)
            auth_token: Notion integration token

        Returns:
            ExportResult with status and page details
        """
        try:
            result = await self.call_tool(
                user_id=user_id,
                provider="notion",
                tool_name="notion-create-pages",  # Official tool uses hyphenated names
                arguments={
                    "parent_id": parent_id,
                    "title": title,
                    "content": content
                },
                env={"NOTION_TOKEN": auth_token}
            )

            # Parse result
            page_id = result.get("id") if isinstance(result, dict) else None
            page_url = result.get("url") if isinstance(result, dict) else None

            return ExportResult(
                status=ExportStatus.SUCCESS,
                external_id=page_id,
                external_url=page_url,
                metadata={"result": result}
            )

        except Exception as e:
            logger.error(f"[MCP] Notion export failed: {e}")
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=str(e)
            )

    # =========================================================================
    # Slack Read Operations (via MCP)
    # =========================================================================

    async def list_slack_channels(
        self,
        user_id: str,
        bot_token: str,
        team_id: str
    ) -> list[dict[str, Any]]:
        """
        List Slack channels via MCP.

        Returns list of channel objects with id, name, is_private, etc.
        """
        try:
            result = await self.call_tool(
                user_id=user_id,
                provider="slack",
                tool_name="slack_list_channels",
                arguments={},
                env={
                    "SLACK_BOT_TOKEN": bot_token,
                    "SLACK_TEAM_ID": team_id
                }
            )
            # Parse MCP result - CallToolResult has content attribute
            parsed = self._parse_mcp_result(result)
            if isinstance(parsed, dict) and "channels" in parsed:
                return parsed["channels"]
            elif isinstance(parsed, list):
                return parsed
            else:
                logger.warning(f"[MCP] Unexpected channels result format: {type(parsed)}, raw: {parsed}")
                return []
        except Exception as e:
            logger.error(f"[MCP] Failed to list Slack channels: {e}")
            raise

    async def join_slack_channel(
        self,
        user_id: str,
        channel_id: str,
        bot_token: str,
        team_id: str
    ) -> bool:
        """
        Join a Slack channel (for public channels).

        This allows the bot to read messages from channels it hasn't been
        explicitly invited to. Only works for public channels.

        Uses Slack API directly since the MCP server doesn't have a join tool.

        Returns True if successful or already in channel.
        """
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://slack.com/api/conversations.join",
                    headers={
                        "Authorization": f"Bearer {bot_token}",
                        "Content-Type": "application/json"
                    },
                    json={"channel": channel_id}
                )
                result = response.json()

                if result.get("ok"):
                    logger.info(f"[SLACK] Bot joined channel {channel_id}")
                    return True

                error = result.get("error", "")
                # Already in channel is fine
                if error in ("already_in_channel",):
                    logger.info(f"[SLACK] Bot already in channel {channel_id}")
                    return True
                # Private channels can't be auto-joined
                if error in ("method_not_supported_for_channel_type", "channel_not_found"):
                    logger.warning(f"[SLACK] Cannot auto-join channel {channel_id}: {error} (may be private)")
                    return False

                logger.warning(f"[SLACK] Failed to join channel: {error}")
                return False

        except Exception as e:
            logger.warning(f"[SLACK] Could not join channel {channel_id}: {e}")
            return False

    async def get_slack_channel_history(
        self,
        user_id: str,
        channel_id: str,
        bot_token: str,
        team_id: str,
        limit: int = 100,
        auto_join: bool = True
    ) -> list[dict[str, Any]]:
        """
        Get Slack channel message history via MCP.

        Args:
            auto_join: If True, attempt to join public channels automatically
                      when "not_in_channel" error is received

        Returns list of message objects.
        """
        async def _fetch_history() -> tuple[list[dict], str | None]:
            """Fetch history, returning (messages, error_code)."""
            result = await self.call_tool(
                user_id=user_id,
                provider="slack",
                tool_name="slack_get_channel_history",
                arguments={"channel_id": channel_id, "limit": limit},
                env={
                    "SLACK_BOT_TOKEN": bot_token,
                    "SLACK_TEAM_ID": team_id
                }
            )
            parsed = self._parse_mcp_result(result)

            if isinstance(parsed, dict):
                # Check for error response first
                if "error" in parsed:
                    return [], parsed["error"]
                if "messages" in parsed:
                    return parsed["messages"], None
                if "history" in parsed:
                    return parsed["history"], None
                logger.warning(f"[MCP] History dict missing 'messages' key. Keys: {list(parsed.keys())}")
                return [], None
            elif isinstance(parsed, list):
                return parsed, None
            else:
                logger.warning(f"[MCP] Unexpected history result format: {type(parsed)}")
                return [], None

        try:
            messages, error = await _fetch_history()

            # Handle "not_in_channel" error with auto-join
            if error == "not_in_channel" and auto_join:
                logger.info(f"[MCP] Bot not in channel {channel_id}, attempting auto-join...")
                joined = await self.join_slack_channel(
                    user_id=user_id,
                    channel_id=channel_id,
                    bot_token=bot_token,
                    team_id=team_id
                )
                if joined:
                    logger.info(f"[MCP] Auto-join successful, retrying history fetch...")
                    messages, error = await _fetch_history()
                    if error:
                        logger.error(f"[MCP] Slack API error after join: {error}")
                else:
                    logger.warning(f"[MCP] Could not auto-join channel {channel_id} (may be private)")
            elif error:
                logger.error(f"[MCP] Slack API error: {error}")

            return messages

        except Exception as e:
            logger.error(f"[MCP] Failed to get Slack history: {e}")
            raise

    # =========================================================================
    # Notion Read Operations (via MCP)
    # =========================================================================

    async def search_notion_pages(
        self,
        user_id: str,
        auth_token: str,
        query: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        Search/list Notion pages via MCP.

        Returns list of page objects with id, title, url, etc.
        """
        try:
            arguments = {}
            if query:
                arguments["query"] = query

            result = await self.call_tool(
                user_id=user_id,
                provider="notion",
                tool_name="notion-search",  # Official tool uses hyphenated names
                arguments=arguments,
                env={"NOTION_TOKEN": auth_token}
            )
            parsed = self._parse_mcp_result(result)
            if isinstance(parsed, dict) and "results" in parsed:
                return parsed["results"]
            elif isinstance(parsed, list):
                return parsed
            else:
                logger.warning(f"[MCP] Unexpected search result format: {type(parsed)}")
                return []
        except Exception as e:
            logger.error(f"[MCP] Failed to search Notion pages: {e}")
            raise

    async def get_notion_page_content(
        self,
        user_id: str,
        page_id: str,
        auth_token: str
    ) -> dict[str, Any]:
        """
        Get Notion page content via MCP.

        Returns page object with content blocks.
        """
        try:
            result = await self.call_tool(
                user_id=user_id,
                provider="notion",
                tool_name="notion-fetch",  # Official tool uses hyphenated names
                arguments={"page_id": page_id},
                env={"NOTION_TOKEN": auth_token}
            )
            parsed = self._parse_mcp_result(result)
            return parsed if isinstance(parsed, dict) else {"content": str(parsed)}
        except Exception as e:
            logger.error(f"[MCP] Failed to get Notion page: {e}")
            raise

    # =========================================================================
    # Gmail Read Operations (via MCP) - ADR-029
    # =========================================================================

    async def list_gmail_labels(
        self,
        user_id: str,
        client_id: str,
        client_secret: str,
        refresh_token: str
    ) -> list[dict[str, Any]]:
        """
        List Gmail labels (folders) via MCP.

        ADR-030: Used for landscape discovery.

        Returns list of label objects with id, name, type, etc.
        """
        try:
            result = await self.call_tool(
                user_id=user_id,
                provider="gmail",
                tool_name="list_labels",
                arguments={},
                env={
                    "CLIENT_ID": client_id,
                    "CLIENT_SECRET": client_secret,
                    "REFRESH_TOKEN": refresh_token
                }
            )
            parsed = self._parse_mcp_result(result)
            if isinstance(parsed, dict) and "labels" in parsed:
                return parsed["labels"]
            elif isinstance(parsed, list):
                return parsed
            else:
                logger.warning(f"[MCP] Unexpected Gmail labels result format: {type(parsed)}")
                return []
        except Exception as e:
            logger.error(f"[MCP] Failed to list Gmail labels: {e}")
            raise

    async def list_gmail_messages(
        self,
        user_id: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        query: Optional[str] = None,
        max_results: int = 20
    ) -> list[dict[str, Any]]:
        """
        List Gmail messages via MCP.

        Args:
            user_id: User identifier
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            refresh_token: User's refresh token
            query: Gmail search query (e.g., "is:unread", "from:sarah@company.com")
            max_results: Maximum messages to return

        Returns list of message objects with id, threadId, snippet, etc.
        """
        try:
            arguments = {"maxResults": max_results}
            if query:
                arguments["query"] = query

            result = await self.call_tool(
                user_id=user_id,
                provider="gmail",
                tool_name="gmail_list_messages",
                arguments=arguments,
                env={
                    "CLIENT_ID": client_id,
                    "CLIENT_SECRET": client_secret,
                    "REFRESH_TOKEN": refresh_token
                }
            )
            parsed = self._parse_mcp_result(result)
            if isinstance(parsed, dict) and "messages" in parsed:
                return parsed["messages"]
            elif isinstance(parsed, list):
                return parsed
            else:
                logger.warning(f"[MCP] Unexpected Gmail list result format: {type(parsed)}")
                return []
        except Exception as e:
            logger.error(f"[MCP] Failed to list Gmail messages: {e}")
            raise

    async def get_gmail_message(
        self,
        user_id: str,
        message_id: str,
        client_id: str,
        client_secret: str,
        refresh_token: str
    ) -> dict[str, Any]:
        """
        Get a specific Gmail message via MCP.

        Returns full message object with headers, body, attachments info.
        """
        try:
            result = await self.call_tool(
                user_id=user_id,
                provider="gmail",
                tool_name="gmail_get_message",
                arguments={"messageId": message_id},
                env={
                    "CLIENT_ID": client_id,
                    "CLIENT_SECRET": client_secret,
                    "REFRESH_TOKEN": refresh_token
                }
            )
            parsed = self._parse_mcp_result(result)
            return parsed if isinstance(parsed, dict) else {"content": str(parsed)}
        except Exception as e:
            logger.error(f"[MCP] Failed to get Gmail message: {e}")
            raise

    async def get_gmail_thread(
        self,
        user_id: str,
        thread_id: str,
        client_id: str,
        client_secret: str,
        refresh_token: str
    ) -> dict[str, Any]:
        """
        Get a Gmail thread (conversation) via MCP.

        Returns thread object with all messages in the conversation.
        """
        try:
            result = await self.call_tool(
                user_id=user_id,
                provider="gmail",
                tool_name="gmail_get_thread",
                arguments={"threadId": thread_id},
                env={
                    "CLIENT_ID": client_id,
                    "CLIENT_SECRET": client_secret,
                    "REFRESH_TOKEN": refresh_token
                }
            )
            parsed = self._parse_mcp_result(result)
            return parsed if isinstance(parsed, dict) else {"content": str(parsed)}
        except Exception as e:
            logger.error(f"[MCP] Failed to get Gmail thread: {e}")
            raise

    async def send_gmail_message(
        self,
        user_id: str,
        to: str,
        subject: str,
        body: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        cc: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> ExportResult:
        """
        Send a Gmail message via MCP.

        Args:
            user_id: User identifier
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text or HTML)
            client_id: Google OAuth client ID
            client_secret: Google OAuth client secret
            refresh_token: User's refresh token
            cc: Optional CC recipients
            thread_id: Optional thread ID for replies

        Returns:
            ExportResult with message ID and status
        """
        try:
            arguments = {
                "to": to,
                "subject": subject,
                "body": body
            }
            if cc:
                arguments["cc"] = cc
            if thread_id:
                arguments["threadId"] = thread_id

            result = await self.call_tool(
                user_id=user_id,
                provider="gmail",
                tool_name="gmail_send_message",
                arguments=arguments,
                env={
                    "CLIENT_ID": client_id,
                    "CLIENT_SECRET": client_secret,
                    "REFRESH_TOKEN": refresh_token
                }
            )

            message_id = result.get("id") if isinstance(result, dict) else None

            return ExportResult(
                status=ExportStatus.SUCCESS,
                external_id=message_id,
                metadata={"result": result}
            )

        except Exception as e:
            logger.error(f"[MCP] Gmail send failed: {e}")
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=str(e)
            )

    async def create_gmail_draft(
        self,
        user_id: str,
        to: str,
        subject: str,
        body: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        cc: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> ExportResult:
        """
        Create a Gmail draft via MCP.

        Useful for deliverables that need user review before sending.
        """
        try:
            arguments = {
                "to": to,
                "subject": subject,
                "body": body
            }
            if cc:
                arguments["cc"] = cc
            if thread_id:
                arguments["threadId"] = thread_id

            result = await self.call_tool(
                user_id=user_id,
                provider="gmail",
                tool_name="gmail_create_draft",
                arguments=arguments,
                env={
                    "CLIENT_ID": client_id,
                    "CLIENT_SECRET": client_secret,
                    "REFRESH_TOKEN": refresh_token
                }
            )

            draft_id = result.get("id") if isinstance(result, dict) else None

            return ExportResult(
                status=ExportStatus.SUCCESS,
                external_id=draft_id,
                metadata={"result": result, "is_draft": True}
            )

        except Exception as e:
            logger.error(f"[MCP] Gmail draft creation failed: {e}")
            return ExportResult(
                status=ExportStatus.FAILED,
                error_message=str(e)
            )

    # =========================================================================
    # Tool Discovery
    # =========================================================================

    async def list_tools(
        self,
        user_id: str,
        provider: str,
        env: dict[str, str]
    ) -> list[dict[str, Any]]:
        """
        List available tools from an MCP server.

        Useful for discovering what operations are available.
        """
        session = await self.get_session(user_id, provider, env)
        tools = await session.list_tools()
        return [
            {"name": t.name, "description": t.description}
            for t in tools.tools
        ]

    async def close_session(self, user_id: str, provider: str):
        """
        Close a specific session.

        Args:
            user_id: User identifier
            provider: Integration provider
        """
        key = f"{user_id}:{provider}"
        async with self._get_lock(key):
            if key in self._exit_stacks:
                logger.info(f"[MCP] Closing session for {key}")
                try:
                    await self._exit_stacks[key].aclose()
                except Exception as e:
                    logger.warning(f"[MCP] Error closing session {key}: {e}")
                del self._exit_stacks[key]
                del self._sessions[key]

    async def close_all(self):
        """Close all active sessions."""
        keys = list(self._exit_stacks.keys())
        for key in keys:
            try:
                await self._exit_stacks[key].aclose()
            except Exception as e:
                logger.warning(f"[MCP] Error closing session {key}: {e}")
        self._sessions.clear()
        self._exit_stacks.clear()
        logger.info(f"[MCP] Closed {len(keys)} sessions")


# Singleton instance
_mcp_manager: Optional[MCPClientManager] = None


def get_mcp_manager() -> MCPClientManager:
    """Get the global MCPClientManager instance."""
    global _mcp_manager
    if _mcp_manager is None:
        _mcp_manager = MCPClientManager()
    return _mcp_manager
