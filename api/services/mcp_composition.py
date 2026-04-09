"""
MCP Composition Layer — ADR-169

Thin composition module for the three MCP tools (work_on_this, pull_context,
remember_this). Each tool is an intent-shaped wrapper over existing primitives
from the ADR-168 matrix (QueryKnowledge, ReadFile, UpdateContext).

Design invariants:
    1. No new primitives — this module is composition over execute_primitive()
    2. Zero YARNNN-internal LLM calls on the serving path (except rare Haiku
       fallback in classify_memory_target for workspace-level enum ambiguity)
    3. Two-branch classifier in remember_this: workspace-level vs operational-feedback
    4. Every write carries ADR-162 provenance (source: mcp:<client_name>)
    5. Ambiguity is a first-class return shape, not an error

Canonical product framing:
    docs/features/mcp/README.md and sibling docs (tool-contracts.md,
    workflows.md, architecture.md) — this module is their implementation.

Primitive naming (ADR-168 Commit 4):
    File-layer primitives: ReadFile, WriteFile, SearchFiles, ListFiles.
    Semantic-query primitive: QueryKnowledge (unchanged, distinct mental model).
    Context-mutation primitive: UpdateContext (unchanged).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Domain keyword hints for subject/content classification
# =============================================================================
# The directory_registry does not ship domain-level keyword metadata, so we
# maintain a minimal dict here for MCP classification. Keys match the canonical
# domain keys in api/services/directory_registry.py (context type only).
#
# This is intentionally small — the classifier's job is not exhaustive entity
# recognition, just a confident first-pass routing hint. When keywords miss,
# the tool returns the structured ambiguous shape and the LLM asks the user.
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "competitors": [
        "competitor", "competition", "rival", "compete", "market share",
        "positioning", "pricing model", "product roadmap",
    ],
    "market": [
        "market", "segment", "industry", "trend", "tam", "sam",
        "buyer", "adoption", "category",
    ],
    "relationships": [
        "contact", "relationship", "partner", "customer", "client",
        "introduction", "intro", "warm intro", "connection",
    ],
    "projects": [
        "project", "initiative", "milestone", "roadmap item", "sprint",
        "deliverable", "deadline",
    ],
    "content_research": [
        "draft", "outline", "research note", "article", "post",
        "blog", "essay", "content piece",
    ],
    "signals": [
        "signal", "observation", "heard that", "noticed", "flag",
        "incident", "event",
    ],
}

# User-facing domain aliases (what LLMs might pass) → registry keys
DOMAIN_ALIASES: dict[str, str] = {
    "content": "content_research",
    "competitor": "competitors",
    "contact": "relationships",
    "contacts": "relationships",
    "project": "projects",
    "market_research": "market",
}


# =============================================================================
# Public composition functions
# =============================================================================


async def compose_subject_context(
    auth: Any,
    context: str,
    subject_hint: Optional[str] = None,
) -> dict:
    """
    Drive work_on_this.

    Resolves a subject from subject_hint or context, then composes a curated
    starting bundle (entity profile, recent signals, prior decisions, related
    tasks). If the subject cannot be resolved, falls through to
    compose_active_candidates for the ambiguous return shape.
    """
    from services.primitives.registry import execute_primitive

    # --- Resolve subject ---
    subject = (subject_hint or "").strip() or _extract_subject_from_context(context)
    if not subject:
        # Cold start — no subject resolvable, fall through to candidates
        return await compose_active_candidates(auth)

    # --- Identify domain from subject + context text ---
    domain = _classify_domain(f"{subject} {context}")

    # --- Pull via QueryKnowledge (semantic ranked search) ---
    qk_result = await execute_primitive(auth, "QueryKnowledge", {
        "query": subject,
        "domain": domain,  # None is fine — searches all context/
        "limit": 8,
    })

    results = qk_result.get("results") or []
    if not results:
        # Subject named but no context found — return thin success with
        # explicit empty bundle so the LLM can tell the user YARNNN doesn't
        # know about this yet
        return {
            "success": True,
            "subject": subject,
            "primed_context": {
                "entity": None,
                "recent_signals": [],
                "prior_decisions": [],
                "related_tasks": [],
            },
            "citations": [],
            "explanation": (
                f"YARNNN has no accumulated context about '{subject}' yet. "
                "Consider creating a tracking task for this subject."
            ),
            "pull_context_hint": f"Call pull_context('{subject}') if you need to double-check.",
        }

    # --- Classify results into bundle buckets ---
    entity_row = None
    signals: list[dict] = []
    decisions: list[dict] = []

    for r in results:
        path = r.get("path", "")
        excerpt = _short_excerpt(r.get("content_preview") or r.get("summary") or "")
        item = {
            "path": path,
            "excerpt": excerpt,
            "updated_at": r.get("updated_at"),
            "source_tag": _extract_provenance_tag(r.get("content_preview") or ""),
        }
        lower_path = path.lower()
        if entity_row is None and ("profile.md" in lower_path or lower_path.endswith(f"/{_slugify(subject)}/profile.md")):
            entity_row = item
        elif "signals.md" in lower_path or "/signals/" in lower_path:
            signals.append(item)
        elif "decisions.md" in lower_path or "/memory/notes.md" in lower_path or "/workspace/memory/" in lower_path:
            decisions.append(item)
        else:
            # General context hit — bucket as a signal by default
            signals.append(item)

    # --- Related tasks (thin direct SQL; no task-listing primitive at MCP scope) ---
    related_tasks = _list_related_tasks(auth, domain or "context")

    # --- Citations: flat list of all paths used ---
    citations: list[str] = []
    if entity_row:
        citations.append(entity_row["path"])
    citations.extend(s["path"] for s in signals[:5])
    citations.extend(d["path"] for d in decisions[:2])

    return {
        "success": True,
        "subject": subject,
        "primed_context": {
            "entity": entity_row,
            "recent_signals": signals[:5],
            "prior_decisions": decisions[:2],
            "related_tasks": related_tasks,
        },
        "citations": citations,
        "pull_context_hint": (
            f"Call pull_context('{subject}') if you need deeper material during the conversation."
        ),
    }


async def compose_active_candidates(auth: Any) -> dict:
    """
    Drive the work_on_this ambiguity fallback.

    Queries workspace state for currently-active subjects (active tasks, recent
    signal activity, draft outputs) and returns them as candidates for the LLM
    to surface to the user. Ranked by freshness + priority (overdue first).
    """
    candidates: list[dict] = []

    # --- Active tasks (direct SQL; same shape as working_memory._get_active_tasks_sync) ---
    try:
        result = (
            auth.client.table("tasks")
            .select("slug, title, mode, schedule, status, next_run_at, last_run_at, essential")
            .eq("user_id", auth.user_id)
            .eq("status", "active")
            .order("next_run_at", desc=False, nullsfirst=False)
            .limit(5)
            .execute()
        )
        for t in (result.data or []):
            reason_bits = []
            if t.get("schedule"):
                reason_bits.append(str(t["schedule"]))
            if t.get("next_run_at"):
                reason_bits.append(f"next {_short_date(t['next_run_at'])}")
            candidates.append({
                "subject": t.get("title") or t.get("slug"),
                "reason": " · ".join(reason_bits) or "active task",
                "path": f"/tasks/{t.get('slug')}/",
                "kind": "task",
            })
    except Exception as e:
        logger.warning(f"[MCP_COMPOSITION] active tasks query failed: {e}")

    # --- Recently-updated entity files under /workspace/context/ ---
    try:
        seven_days_ago = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        # Reach back ~7 days via a broad query and rely on ordering
        result = (
            auth.client.table("workspace_files")
            .select("path, updated_at, summary")
            .eq("user_id", auth.user_id)
            .like("path", "/workspace/context/%")
            .order("updated_at", desc=True)
            .limit(10)
            .execute()
        )
        seen_entities: set[str] = set()
        for row in (result.data or []):
            path = row.get("path", "")
            # Extract entity segment: /workspace/context/{domain}/{entity}/...
            parts = path.split("/")
            if len(parts) >= 5:
                domain = parts[3]
                entity = parts[4]
                key = f"{domain}/{entity}"
                if key in seen_entities or entity.startswith("_"):
                    continue
                seen_entities.add(key)
                candidates.append({
                    "subject": entity.replace("-", " ").replace("_", " ").title(),
                    "reason": f"recent activity in {domain}",
                    "path": f"/workspace/context/{domain}/{entity}/",
                    "kind": "entity",
                })
                if len(seen_entities) >= 3:
                    break
    except Exception as e:
        logger.warning(f"[MCP_COMPOSITION] recent entity query failed: {e}")

    # --- Truncate to 5 candidates max ---
    candidates = candidates[:5]

    if not candidates:
        # Totally empty workspace — honest signal
        return {
            "success": True,
            "ambiguous": {
                "candidates": [],
                "clarification": (
                    "Your YARNNN workspace doesn't have any active tasks or recent "
                    "activity yet. Tell the user what they'd like to work on, or "
                    "suggest they start by describing their current work."
                ),
            },
        }

    return {
        "success": True,
        "ambiguous": {
            "candidates": candidates,
            "clarification": "Several active subjects in your workspace. Which one?",
        },
    }


# =============================================================================
# classify_memory_target — two-branch classifier for remember_this
# =============================================================================


def classify_memory_target(
    content: str,
    about: Optional[str],
    agents_by_slug: Optional[dict[str, dict]] = None,
    tasks_by_slug: Optional[dict[str, dict]] = None,
) -> dict:
    """
    Classify remember_this content into an UpdateContext target.

    Returns one of three shapes:

        # Confident routing — caller proceeds with UpdateContext dispatch
        {"target": "memory" | "identity" | "brand" | "agent" | "task",
         "slug": <optional, for agent/task>,
         "confidence": "high" | "medium"}

        # Ambiguous operational-feedback — caller returns ambiguous shape
        # to the LLM with the candidates list
        {"ambiguous": True,
         "candidates": [{"target": "agent:<slug>", "reason": "..."}, ...]}

    Two-branch logic:
        1. Workspace-level (identity/brand/memory) — small mutually exclusive
           enum; defaults safely to memory on ambiguity
        2. Operational feedback (agent/task) — requires confident slug match
           or returns ambiguous for LLM-mediated disambiguation

    agents_by_slug and tasks_by_slug are optional in-memory dicts for slug
    matching; if omitted, the classifier falls back to "memory" on any
    feedback-shaped content (safer default than wrong slug routing).
    """
    content_lower = content.lower().strip()
    about_lower = (about or "").lower().strip()

    # --- Workspace-level branch ---
    if _is_identity_claim(content_lower, about_lower):
        return {"target": "identity", "confidence": "high"}
    if _is_brand_preference(content_lower, about_lower):
        return {"target": "brand", "confidence": "high"}

    # --- Operational feedback branch ---
    feedback_flavor = _feedback_flavor(content_lower, about_lower)
    if feedback_flavor in ("agent", "task"):
        slug_pool = agents_by_slug if feedback_flavor == "agent" else tasks_by_slug
        if not slug_pool:
            # No slug pool provided — fall through to general memory as the
            # safest default. Wrong routing is worse than no routing.
            return {"target": "memory", "confidence": "medium", "note": "feedback_unrouted"}

        matches = _match_slugs(content_lower + " " + about_lower, slug_pool)
        if len(matches) == 1:
            return {
                "target": feedback_flavor,
                "slug": matches[0],
                "confidence": "high",
            }
        if len(matches) > 1:
            return {
                "ambiguous": True,
                "candidates": [
                    {
                        "target": f"{feedback_flavor}:{slug}",
                        "reason": f"{feedback_flavor} '{slug}' matches content",
                    }
                    for slug in matches
                ],
            }
        # Zero matches — treat as mis-categorized, fall through to memory
        return {"target": "memory", "confidence": "medium", "note": "feedback_unrouted"}

    # --- Default: general memory ---
    return {"target": "memory", "confidence": "high"}


# =============================================================================
# Helpers
# =============================================================================


def derive_client_name(request_context: Any) -> str:
    """
    Derive the MCP client name for provenance stamping.

    Known clients map to short identifiers; unknown clients return 'unknown'.
    Sources in preference order:
        1. OAuth client_id if present on the request context
        2. User-Agent header substring match
        3. Fallback to 'unknown'

    Values: claude.ai, chatgpt, claude_desktop, gemini, cursor, unknown
    """
    if request_context is None:
        return "unknown"

    # Try OAuth client id
    client_id = getattr(request_context, "client_id", None)
    if client_id:
        normalized = _normalize_client_id(client_id)
        if normalized:
            return normalized

    # Try User-Agent from the request headers
    headers = getattr(request_context, "headers", None) or {}
    ua = headers.get("user-agent") or headers.get("User-Agent") or ""
    normalized = _normalize_client_id(ua)
    if normalized:
        return normalized

    return "unknown"


def stamp_provenance(
    content: str,
    client_name: str,
    user_context: Optional[str] = None,
) -> str:
    """
    Prepend an ADR-162 source-provenance HTML comment to content.

    Format:
        <!-- source: mcp:<client> | date: YYYY-MM-DD | user_context: "..." -->
        <original content>
    """
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    uc = (user_context or "")[:100].replace('"', "'")
    comment = f'<!-- source: mcp:{client_name} | date: {date} | user_context: "{uc}" -->'
    return f"{comment}\n{content}"


def extract_domain_from_path(path: str) -> Optional[str]:
    """
    Extract the domain key from a /workspace/context/{domain}/... path.
    Returns None if the path is not under /workspace/context/.
    """
    if not path or not path.startswith("/workspace/context/"):
        return None
    parts = path.split("/")
    if len(parts) >= 4:
        return parts[3]
    return None


def _extract_provenance_tag(content: Optional[str]) -> Optional[str]:
    """
    Extract the `source: <tag>` field from the first ADR-162 HTML comment
    at the start of a file's content. Returns None if no tag is found.
    """
    if not content:
        return None
    # Match an HTML comment on the first or second line
    lines = content.strip().split("\n", 2)
    for line in lines[:2]:
        m = re.search(r"source:\s*([^\s|]+)", line)
        if m:
            return m.group(1).strip()
    return None


def _extract_subject_from_context(context: str) -> str:
    """
    Best-effort extraction of a subject noun phrase from the free-form
    context blob the LLM passed. Deterministic, zero-LLM — when this fails
    the caller falls through to compose_active_candidates.

    Heuristics:
        1. Look for capitalized multi-word sequences (e.g., "Acme Corp")
        2. Look for quoted strings
        3. Return empty string on miss
    """
    if not context:
        return ""
    # Capitalized sequence of 1-3 words
    m = re.search(r"\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\b", context)
    if m:
        return m.group(1).strip()
    # Quoted
    m = re.search(r"[\"']([^\"']{2,40})[\"']", context)
    if m:
        return m.group(1).strip()
    return ""


def _classify_domain(text: str) -> Optional[str]:
    """
    Match text against DOMAIN_KEYWORDS and return the best-scoring domain key.
    Returns None if no domain scores > 0.
    """
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[domain] = score
    if not scores:
        return None
    return max(scores.items(), key=lambda kv: kv[1])[0]


def _is_identity_claim(content_lower: str, about_lower: str) -> bool:
    """User-role / company / work-context claim."""
    identity_markers = [
        "i'm ", "i am ", "my role", "my company", "my title",
        "my team", "i work at", "i work on", "i lead", "i manage",
        "my background", "my experience", "my focus",
    ]
    if about_lower in ("identity", "my role", "me", "who i am"):
        return True
    return any(marker in content_lower for marker in identity_markers)


def _is_brand_preference(content_lower: str, about_lower: str) -> bool:
    """Voice / tone / style / visual preference."""
    brand_markers = [
        "my brand", "my voice", "my tone", "my style", "my aesthetic",
        "use active voice", "always use", "we write in", "our voice is",
        "avoid jargon", "no em-dashes", "our look",
    ]
    if about_lower in ("brand", "voice", "tone", "style"):
        return True
    return any(marker in content_lower for marker in brand_markers)


def _feedback_flavor(content_lower: str, about_lower: str) -> Optional[str]:
    """
    Detect whether the content is operational feedback about an agent or task.
    Returns 'agent', 'task', or None.

    Uses regex patterns that allow one or two adjective-like words between
    the determiner and the agent/task noun (e.g., "the research agent",
    "the weekly digest").
    """
    # agent-shaped: "the/my/this/that [adj]* agent|researcher|analyst|writer|monitor|briefer"
    agent_pattern = (
        r"\b(?:the|my|this|that)\s+(?:\w+\s+){0,2}"
        r"(?:agent|researcher|analyst|writer|monitor|briefer|drafter|scout|planner)\b"
    )
    # task-shaped: "the/my/this/that [adj]* task|brief|report|digest|deliverable|output|update"
    task_pattern = (
        r"\b(?:the|my|this|that)\s+(?:\w+\s+){0,2}"
        r"(?:task|brief|report|digest|deliverable|output|update|summary|recap)\b"
    )
    if re.search(agent_pattern, content_lower) or "agent" in about_lower:
        return "agent"
    if re.search(task_pattern, content_lower) or "task" in about_lower:
        return "task"
    return None


def _match_slugs(text: str, slug_pool: dict[str, dict]) -> list[str]:
    """
    Return the list of slugs from slug_pool whose slug substring appears
    in text. Uses word-boundary matching where possible.
    """
    matches = []
    for slug in slug_pool.keys():
        slug_variants = {slug, slug.replace("-", " "), slug.replace("_", " ")}
        for variant in slug_variants:
            if variant and variant in text:
                matches.append(slug)
                break
    return matches


def _list_related_tasks(auth: Any, domain: str) -> list[dict]:
    """
    Return a thin list of tasks touching the given domain. Direct SQL query
    — there is no task-listing primitive at MCP scope.
    """
    try:
        result = (
            auth.client.table("tasks")
            .select("slug, title, schedule, next_run_at")
            .eq("user_id", auth.user_id)
            .eq("status", "active")
            .limit(5)
            .execute()
        )
        # TODO: filter by context_reads when that metadata is easily queryable
        # For now, return all active tasks — small set on typical workspaces
        return [
            {
                "slug": t.get("slug"),
                "title": t.get("title") or t.get("slug"),
                "next_run": _short_date(t.get("next_run_at")),
            }
            for t in (result.data or [])
        ]
    except Exception as e:
        logger.warning(f"[MCP_COMPOSITION] related tasks query failed: {e}")
        return []


def _short_excerpt(text: str, limit: int = 400) -> str:
    """Trim text to a reasonable excerpt length."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _short_date(iso_str: Optional[str]) -> str:
    """Format an ISO timestamp as a short relative-ish date. Empty if None."""
    if not iso_str:
        return ""
    try:
        return iso_str.split("T")[0]
    except Exception:
        return iso_str


def _slugify(text: str) -> str:
    """Simple slug derivation for entity path matching."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _normalize_client_id(raw: str) -> Optional[str]:
    """
    Map an OAuth client id or User-Agent string to one of the known
    short identifiers for provenance stamps.
    """
    if not raw:
        return None
    low = raw.lower()
    if "claude.ai" in low or "claude-ai" in low or "anthropic" in low and "desktop" not in low:
        return "claude.ai"
    if "claude" in low and "desktop" in low:
        return "claude_desktop"
    if "claude" in low and "code" in low:
        return "claude_code"
    if "chatgpt" in low or "openai" in low:
        return "chatgpt"
    if "gemini" in low or "google" in low:
        return "gemini"
    if "cursor" in low:
        return "cursor"
    return None
