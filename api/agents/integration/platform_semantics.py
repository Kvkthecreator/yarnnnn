"""
Platform Semantic Extraction - ADR-031 Phase 1

Extracts platform-specific signals that inform "what's worth saying",
not just "how to say it".

This module provides:
1. Signal extraction from raw platform data
2. Semantic classification (hot threads, unanswered questions, etc.)
3. Metadata enrichment for ephemeral context storage

Per ADR-031: "Platforms inform reasoning, not just formatting"
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SlackSemanticSignals:
    """
    Semantic signals extracted from Slack messages.
    These identify what's important, not just what was said.
    """
    # Thread engagement
    thread_reply_count: int = 0
    unique_participants: list[str] = None
    is_hot_thread: bool = False  # High engagement (>5 replies or >3 reactions)

    # Question detection
    has_question: bool = False
    is_unanswered: bool = False  # Question with no reply
    is_stalled: bool = False     # Question with no reply after 24h

    # Urgency markers
    mentions_deadline: bool = False
    mentions_blocker: bool = False
    has_action_request: bool = False
    is_urgent: bool = False      # Contains urgent keywords

    # Engagement metrics
    reaction_count: int = 0
    reaction_types: list[str] = None
    has_eyes: bool = False       # 👀 reaction (watching)
    has_check: bool = False      # ✅ reaction (done/approved)

    # Message characteristics
    is_decision: bool = False    # Contains decision markers
    is_announcement: bool = False
    has_link: bool = False
    has_code: bool = False

    def __post_init__(self):
        if self.unique_participants is None:
            self.unique_participants = []
        if self.reaction_types is None:
            self.reaction_types = []

    def to_dict(self) -> dict:
        return {
            "thread_reply_count": self.thread_reply_count,
            "unique_participants": self.unique_participants,
            "is_hot_thread": self.is_hot_thread,
            "has_question": self.has_question,
            "is_unanswered": self.is_unanswered,
            "is_stalled": self.is_stalled,
            "mentions_deadline": self.mentions_deadline,
            "mentions_blocker": self.mentions_blocker,
            "has_action_request": self.has_action_request,
            "is_urgent": self.is_urgent,
            "reaction_count": self.reaction_count,
            "reaction_types": self.reaction_types,
            "has_eyes": self.has_eyes,
            "has_check": self.has_check,
            "is_decision": self.is_decision,
            "is_announcement": self.is_announcement,
            "has_link": self.has_link,
            "has_code": self.has_code,
        }

    @property
    def importance_score(self) -> float:
        """Calculate importance score (0-1) based on signals."""
        score = 0.3  # Base score

        # Engagement boosts
        if self.is_hot_thread:
            score += 0.2
        if self.reaction_count > 0:
            score += min(0.1, self.reaction_count * 0.02)

        # Urgency boosts
        if self.is_urgent or self.mentions_blocker:
            score += 0.3
        if self.mentions_deadline:
            score += 0.2
        if self.has_action_request:
            score += 0.1

        # Unanswered questions are important
        if self.is_unanswered:
            score += 0.2
        if self.is_stalled:
            score += 0.3

        # Decision/announcement markers
        if self.is_decision:
            score += 0.2
        if self.is_announcement:
            score += 0.1

        return min(1.0, score)


# =============================================================================
# Pattern Detection
# =============================================================================

# Question patterns
QUESTION_PATTERNS = [
    r'\?$',                          # Ends with ?
    r'^(who|what|when|where|why|how|can|could|would|should|is|are|do|does)\s',
    r'anyone know',
    r'any thoughts',
    r'what do you think',
    r'any idea',
    r'can someone',
    r'could someone',
]

# Urgency patterns
URGENCY_PATTERNS = [
    r'\burgent\b',
    r'\basap\b',
    r'\beod\b',                      # End of day
    r'\bcritical\b',
    r'\bblocker\b',
    r'\bblocked\b',
    r'\bblocking\b',
    r'need.*immediately',
    r'need.*today',
    r'🚨',
    r'⚠️',
    r'🔴',
]

# Deadline patterns
DEADLINE_PATTERNS = [
    r'\bby\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
    r'\bby\s+\d{1,2}[:/]\d{2}\b',    # by 5:00
    r'\bdue\s+(date|by|on)\b',
    r'\bdeadline\b',
    r'\bend of (day|week|month)\b',
    r'\bbefore\s+(the\s+)?meeting\b',
]

# Action request patterns
ACTION_PATTERNS = [
    r'^(please|can you|could you|would you)\s',
    r'\blet me know\b',
    r'\bget back to me\b',
    r'\bneed you to\b',
    r'\baction item\b',
    r'\btodo\b',
    r'\bfollow up\b',
    r'@\w+.*\?',                     # @mention with question
]

# Decision patterns
DECISION_PATTERNS = [
    r'\bdecided\b',
    r'\bdecision\b',
    r'\bwe.*(going|will)\s+(to\s+)?(go with|use|proceed)\b',
    r'\blet\'s (go with|use|proceed)\b',
    r'\bfinal(ized|izing)?\b',
    r'\bapproved\b',
    r'\bconfirmed\b',
    r'✅.*decision',
]

# Announcement patterns
ANNOUNCEMENT_PATTERNS = [
    r'^(heads up|fyi|announcement|update|news)\b',
    r'^📢',
    r'^🎉',
    r'\bexcited to (announce|share)\b',
    r'\bplease note\b',
]

# Blocker patterns
BLOCKER_PATTERNS = [
    r'\bblocker\b',
    r'\bblocked\b',
    r'\bblocking\b',
    r'\bcan\'t proceed\b',
    r'\bwaiting on\b',
    r'\bdepends on\b',
    r'\bneed.*before\b',
]


def _matches_patterns(text: str, patterns: list[str]) -> bool:
    """Check if text matches any of the patterns."""
    text_lower = text.lower()
    for pattern in patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


# =============================================================================
# Slack Semantic Extraction
# =============================================================================

def extract_slack_message_signals(
    message: dict,
    thread_replies: Optional[list[dict]] = None,
    now: Optional[datetime] = None,
) -> SlackSemanticSignals:
    """
    Extract semantic signals from a single Slack message.

    Args:
        message: Raw Slack message dict
        thread_replies: Optional list of reply messages (for thread analysis)
        now: Current time (for staleness detection)

    Returns:
        SlackSemanticSignals with detected patterns
    """
    if now is None:
        now = datetime.now(timezone.utc)

    signals = SlackSemanticSignals()
    text = message.get("text", "")

    # Thread engagement
    signals.thread_reply_count = message.get("reply_count", 0)
    if thread_replies:
        signals.thread_reply_count = len(thread_replies)
        users = {r.get("user") for r in thread_replies if r.get("user")}
        users.add(message.get("user"))
        signals.unique_participants = list(users - {None})

    # Hot thread detection
    signals.is_hot_thread = (
        signals.thread_reply_count >= 5 or
        len(signals.unique_participants) >= 3
    )

    # Question detection
    signals.has_question = _matches_patterns(text, QUESTION_PATTERNS)

    if signals.has_question:
        # Check if unanswered
        signals.is_unanswered = signals.thread_reply_count == 0

        # Check if stalled (question posted >24h ago with no replies)
        if signals.is_unanswered:
            try:
                msg_ts = datetime.fromtimestamp(float(message.get("ts", 0)), tz=timezone.utc)
                age = now - msg_ts
                signals.is_stalled = age > timedelta(hours=24)
            except (ValueError, TypeError):
                pass

    # Urgency detection
    signals.is_urgent = _matches_patterns(text, URGENCY_PATTERNS)
    signals.mentions_deadline = _matches_patterns(text, DEADLINE_PATTERNS)
    signals.has_action_request = _matches_patterns(text, ACTION_PATTERNS)
    signals.mentions_blocker = _matches_patterns(text, BLOCKER_PATTERNS)

    # Reaction analysis
    reactions = message.get("reactions", [])
    signals.reaction_count = sum(r.get("count", 0) for r in reactions)
    signals.reaction_types = [r.get("name", "") for r in reactions]
    signals.has_eyes = any("eyes" in r.get("name", "") for r in reactions)
    signals.has_check = any(
        r.get("name", "") in ("white_check_mark", "heavy_check_mark", "ballot_box_with_check", "+1", "thumbsup")
        for r in reactions
    )

    # Boost hot thread if high reactions
    if signals.reaction_count >= 3:
        signals.is_hot_thread = True

    # Content classification
    signals.is_decision = _matches_patterns(text, DECISION_PATTERNS)
    signals.is_announcement = _matches_patterns(text, ANNOUNCEMENT_PATTERNS)
    signals.has_link = "http" in text or "<http" in text
    signals.has_code = "```" in text or "`" in text

    return signals


def extract_slack_channel_signals(
    messages: list[dict],
    now: Optional[datetime] = None,
) -> dict:
    """
    Extract aggregate signals from a Slack channel's messages.

    Returns:
        Dict with:
        - hot_threads: List of thread parent messages with high engagement
        - unanswered_questions: Messages with questions but no replies
        - stalled_threads: Questions waiting >24h for response
        - action_items: Messages with action requests
        - decisions: Messages containing decisions
        - urgent_messages: Messages with urgency markers
    """
    if now is None:
        now = datetime.now(timezone.utc)

    result = {
        "hot_threads": [],
        "unanswered_questions": [],
        "stalled_threads": [],
        "action_items": [],
        "decisions": [],
        "urgent_messages": [],
        "announcements": [],
    }

    # Group messages by thread
    threads = {}  # thread_ts -> list of messages
    standalone = []

    for msg in messages:
        thread_ts = msg.get("thread_ts")
        msg_ts = msg.get("ts")

        if thread_ts:
            if thread_ts not in threads:
                threads[thread_ts] = []
            threads[thread_ts].append(msg)
        else:
            standalone.append(msg)

    # Analyze thread parents
    for msg in standalone:
        msg_ts = msg.get("ts")
        thread_replies = threads.get(msg_ts, [])

        signals = extract_slack_message_signals(msg, thread_replies, now)

        msg_with_signals = {
            **msg,
            "_signals": signals.to_dict(),
            "_importance": signals.importance_score,
        }

        if signals.is_hot_thread:
            result["hot_threads"].append(msg_with_signals)

        if signals.is_unanswered:
            result["unanswered_questions"].append(msg_with_signals)

        if signals.is_stalled:
            result["stalled_threads"].append(msg_with_signals)

        if signals.has_action_request:
            result["action_items"].append(msg_with_signals)

        if signals.is_decision:
            result["decisions"].append(msg_with_signals)

        if signals.is_urgent or signals.mentions_blocker:
            result["urgent_messages"].append(msg_with_signals)

        if signals.is_announcement:
            result["announcements"].append(msg_with_signals)

    # Sort by importance
    for key in result:
        result[key].sort(key=lambda x: x.get("_importance", 0), reverse=True)

    return result


# =============================================================================
# Gmail Semantic Extraction
# =============================================================================

@dataclass
class GmailSemanticSignals:
    """Semantic signals from Gmail messages."""
    has_question: bool = False
    has_action_request: bool = False
    mentions_deadline: bool = False
    is_urgent: bool = False
    is_reply: bool = False
    thread_length: int = 1
    has_attachment: bool = False
    is_from_external: bool = False

    def to_dict(self) -> dict:
        return {
            "has_question": self.has_question,
            "has_action_request": self.has_action_request,
            "mentions_deadline": self.mentions_deadline,
            "is_urgent": self.is_urgent,
            "is_reply": self.is_reply,
            "thread_length": self.thread_length,
            "has_attachment": self.has_attachment,
            "is_from_external": self.is_from_external,
        }

    @property
    def importance_score(self) -> float:
        score = 0.3
        if self.is_urgent:
            score += 0.3
        if self.mentions_deadline:
            score += 0.2
        if self.has_action_request:
            score += 0.1
        if self.has_question and not self.is_reply:
            score += 0.1
        if self.is_from_external:
            score += 0.1
        return min(1.0, score)


def extract_gmail_message_signals(
    message: dict,
    user_email: Optional[str] = None,
) -> GmailSemanticSignals:
    """Extract semantic signals from a Gmail message."""
    signals = GmailSemanticSignals()

    headers = message.get("headers", {})
    body = message.get("body", message.get("snippet", ""))
    subject = headers.get("Subject", headers.get("subject", ""))

    full_text = f"{subject}\n{body}"

    # Pattern detection
    signals.has_question = _matches_patterns(full_text, QUESTION_PATTERNS)
    signals.has_action_request = _matches_patterns(full_text, ACTION_PATTERNS)
    signals.mentions_deadline = _matches_patterns(full_text, DEADLINE_PATTERNS)
    signals.is_urgent = _matches_patterns(full_text, URGENCY_PATTERNS)

    # Reply detection
    signals.is_reply = subject.lower().startswith("re:")

    # Attachment detection
    signals.has_attachment = bool(message.get("attachments") or message.get("parts"))

    # External sender detection
    if user_email:
        from_addr = headers.get("From", headers.get("from", ""))
        user_domain = user_email.split("@")[-1] if "@" in user_email else ""
        if user_domain and user_domain not in from_addr:
            signals.is_from_external = True

    return signals


# =============================================================================
# Notion Semantic Extraction
# =============================================================================

@dataclass
class NotionSemanticSignals:
    """Semantic signals from Notion pages."""
    has_unresolved_comments: bool = False
    has_todos: bool = False
    incomplete_todos: int = 0
    recently_edited: bool = False
    has_mentions: bool = False
    word_count: int = 0

    def to_dict(self) -> dict:
        return {
            "has_unresolved_comments": self.has_unresolved_comments,
            "has_todos": self.has_todos,
            "incomplete_todos": self.incomplete_todos,
            "recently_edited": self.recently_edited,
            "has_mentions": self.has_mentions,
            "word_count": self.word_count,
        }


def extract_notion_page_signals(
    page_content: dict,
    now: Optional[datetime] = None,
) -> NotionSemanticSignals:
    """Extract semantic signals from a Notion page."""
    if now is None:
        now = datetime.now(timezone.utc)

    signals = NotionSemanticSignals()

    content = page_content.get("content", "")
    signals.word_count = len(content.split())

    # Check for todos (common patterns)
    signals.has_todos = "[ ]" in content or "[x]" in content or "☐" in content
    signals.incomplete_todos = content.count("[ ]") + content.count("☐")

    # Check for mentions
    signals.has_mentions = "@" in content

    # Check if recently edited (within 24h)
    last_edited = page_content.get("last_edited")
    if last_edited:
        try:
            if isinstance(last_edited, str):
                edited_dt = datetime.fromisoformat(last_edited.replace("Z", "+00:00"))
            else:
                edited_dt = last_edited
            signals.recently_edited = (now - edited_dt) < timedelta(hours=24)
        except (ValueError, TypeError):
            pass

    return signals
