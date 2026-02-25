"""
Integration Readers - DEPRECATED.

This module previously contained direct API clients (SlackReader, NotionReader).
All read operations now use platform-specific Direct API clients:
- Slack: integrations/core/slack_client.py
- Notion: integrations/core/notion_client.py
- Gmail/Calendar: integrations/core/google_client.py
"""

__all__ = []
