"""
Context Inference — ADR-144: Inference-First Shared Context
                   ADR-162: Gap detection on inference output

Single inference function for workspace shared context. Reads any combination
of sources (text, documents, URLs, platform content) and produces rich markdown
for IDENTITY.md. (ADR-432 D1c: the BRAND.md target was retired.)

Replaces enrich_context() from ADR-138/140 onboarding flow.

ADR-162 adds `detect_inference_gaps()` — a pure-Python function (no LLM) that
inspects inference output for missing-but-load-bearing fields and returns a
structured gap report. TP uses the report to issue at most one targeted
Clarify per inference cycle. Deterministic by design — no shadow LLM calls,
preserves single-intelligence-layer (ADR-156).
"""

import json
import logging
import re
from typing import Any, Literal, Optional

logger = logging.getLogger(__name__)

INFERENCE_MODEL = "claude-sonnet-4-6"


IDENTITY_SYSTEM = """You are updating a user's workspace identity file (IDENTITY.md).
Read all provided sources carefully. Produce a rich markdown identity document.

OUTPUT FORMAT (use exactly this structure):
# Identity

## Who
[Name], [Role] at [Company]
[Industry/space]. [2-3 sentence context summary of who this person is and what they work on.]

## Domains of Attention
- [Domain 1]: [why this matters to them]
- [Domain 2]: [why this matters to them]

## Work Patterns
- [Pattern 1]: [cadence, what it involves]
- [Pattern 2]: [cadence, what it involves]

## Timezone
[Inferred or stated, e.g., "US Pacific (UTC-8)"]

RULES:
- Extract REAL names, companies, industries from their materials — never fabricate
- Domains = areas of sustained attention (2-5)
- Work patterns = recurring rhythms you can identify (1-5)
- If something isn't mentioned, omit that section entirely
- Be specific — use their actual context, not generic labels
- If existing content is provided, MERGE: preserve information from both old and new sources"""

# ADR-432 D1c: BRAND_SYSTEM removed — Brand retired; this workflow authors IDENTITY.md only.


async def author_identity_merge(
    target: Literal["identity"],
    text: str = "",
    document_contents: Optional[list] = None,
    url_contents: Optional[list] = None,
    existing_content: str = "",
) -> str:
    """Merge new operator input into the IDENTITY.md file content (ADR-324).

    The focused LLM merge step: read-set (text + doc contents + URLs + existing)
    → IDENTITY_SYSTEM prompt → merged markdown. Renamed from
    `infer_shared_context` (ADR-324 — honest name; it authors the operator's
    identity, it does not "infer context"). Used by `author_identity`
    (the full workflow), the MCP path, and the eval harness. Returns merged
    markdown content for the target workspace file.

    ADR-432 D1c: the `brand` target is retired — this now authors identity only.

    Args:
        target: "identity"
        text: Direct text from user (chat message, description)
        document_contents: [{filename, content}] from uploaded documents
        url_contents: [{url, content}] from web search/fetch
        existing_content: Current file content (for merge, not overwrite)

    Returns:
        Markdown string for IDENTITY.md or BRAND.md, with an inference-meta
        HTML comment appended at the bottom (ADR-162 Sub-phase D).
    """
    from services.anthropic import chat_completion

    # Assemble source material
    parts = []
    source_summary = {
        "has_text": bool(text.strip()),
        "doc_count": 0,
        "doc_filenames": [],
        "url_count": 0,
        "urls": [],
    }
    if text.strip():
        parts.append(f"User says:\n{text.strip()}")
    if document_contents:
        for doc in (document_contents or [])[:5]:
            name = doc.get("filename", "document")
            content = doc.get("content", "")[:5000]
            if content:
                parts.append(f"--- Document: {name} ---\n{content}")
                source_summary["doc_count"] += 1
                source_summary["doc_filenames"].append(name)
    if url_contents:
        for item in (url_contents or [])[:3]:
            url = item.get("url", "")
            content = item.get("content", "")[:3000]
            if content:
                parts.append(f"--- URL: {url} ---\n{content}")
                source_summary["url_count"] += 1
                source_summary["urls"].append(url)
    if not parts:
        logger.warning("[INFERENCE] No source material provided")
        return existing_content or ""

    # Include existing content for merge
    if existing_content and existing_content.strip():
        parts.append(f"--- Existing {target.upper()}.md (merge with this) ---\n{existing_content.strip()}")

    source_material = "\n\n".join(parts)
    system = IDENTITY_SYSTEM  # ADR-432 D1c: identity-only (brand retired)

    try:
        from services.anthropic import chat_completion_with_usage
        result_text, usage = await chat_completion_with_usage(
            messages=[{"role": "user", "content": f"Update the {target} file from these sources:\n\n{source_material}"}],
            system=system,
            model=INFERENCE_MODEL,
            max_tokens=2048,
        )
        result = result_text.strip()
        if result:
            logger.info(f"[INFERENCE] Generated {target} ({len(result)} chars)")
            gap_report = detect_inference_gaps(target=target, inferred_content=result)
            result = _append_inference_meta(result, target, source_summary, gap_report=gap_report)
            return result, usage
    except Exception as e:
        logger.error(f"[INFERENCE] Failed for {target}: {e}")

    return existing_content or "", {}


async def author_identity(
    client: Any,
    user_id: str,
    target: Literal["identity"],
    text: str = "",
    document_ids: Optional[list] = None,
    url_contents: Optional[list] = None,
    authored_by: str = "operator",
) -> dict:
    """Full IDENTITY.md authoring workflow (ADR-324 — relocated from the
    dissolved InferContext primitive's handler).

    Reads the existing file, merges new input via `author_identity_merge`,
    records the cost ledger, writes the result via UserMemory (→ write_revision,
    authored_by=operator by default), and runs deterministic gap detection.

    Called by the MCP `dispatch_remember_this` identity path and the eval
    harness. The chat surface does NOT call this — post-ADR-324 the chat LLM
    authors identity inline via WriteFile (no focused sub-prompt).

    ADR-432 D1c: the `brand` target is retired — this authors identity only.

    Returns the same shape the old handle_infer_context returned:
        {success, target, filename, content, gaps, message} | {success: False, error, message}
    """
    from services.workspace import UserMemory
    from services.workspace_paths import PERSONA_IDENTITY_PATH

    if target != "identity":
        return {"success": False, "error": "invalid_target", "message": "target must be 'identity'"}
    if not text or not text.strip():
        return {"success": False, "error": "empty_text", "message": "text is required"}

    filename = PERSONA_IDENTITY_PATH

    try:
        um = UserMemory(client, user_id)
        existing = await um.read(filename)

        document_contents = []
        if document_ids:
            document_contents = await read_uploaded_documents(client, user_id, document_ids)

        new_content, usage = await author_identity_merge(
            target=target,
            text=text,
            document_contents=document_contents,
            url_contents=url_contents or [],
            existing_content=existing or "",
        )

        # ADR-291: unified cost ledger.
        if usage.get("input_tokens") or usage.get("output_tokens"):
            try:
                from services.telemetry import record_execution_event
                from services.supabase import get_service_client
                record_execution_event(
                    get_service_client(),
                    user_id=user_id,
                    # ADR-373/445: operator-initiated authoring — the acting
                    # principal is the caller themselves. Stamped so the draw
                    # lands in spend_by_principal rather than the NULL bucket.
                    principal_id=user_id,
                    slug=f"author-identity:{target}",
                    mode="judgment",
                    trigger_type="addressed",
                    status="success",
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                    cache_read_tokens=usage.get("cache_read_input_tokens", 0) or 0,
                    cache_create_tokens=usage.get("cache_creation_input_tokens", 0) or 0,
                    model=INFERENCE_MODEL,
                )
            except Exception as e:
                logger.warning(f"[AUTHOR_IDENTITY] cost ledger record failed: {e}")

        if not new_content or not new_content.strip():
            return {"success": False, "error": "merge_empty", "message": "Merge produced no content — provide more detail"}

        ok = await um.write(
            filename, new_content,
            summary=f"{target.capitalize()} updated via merge",
            authored_by=authored_by,
            message=f"author {target}",
        )
        if not ok:
            return {"success": False, "error": "write_failed", "message": f"Failed to write {filename}"}

        gap_report = detect_inference_gaps(target=target, inferred_content=new_content)
        return {
            "success": True,
            "target": target,
            "filename": filename,
            "content": new_content,
            "gaps": gap_report,
            "message": f"Updated {filename} successfully",
        }
    except Exception as e:
        logger.error(f"[AUTHOR_IDENTITY] failed for {target}: {e}")
        return {"success": False, "error": "author_failed", "message": str(e)}


def _append_inference_meta(
    content: str,
    target: str,
    source_summary: dict,
    gap_report: Optional[dict] = None,
) -> str:
    """Append an inference-meta HTML comment to the end of inference output.

    ADR-162 Sub-phase D + ADR-209 Phase 4: Source-summary + gap provenance.
    Frontend parses this to show "Last updated from: 2 documents + 1 URL"
    captions on the Context surface, and "Missing: company name" gap banners.

    Two concerns carried in this comment:
      - `target` — which inferred domain (identity / brand / …)
      - `sources` — what external material the inference consumed
      - `gaps` — optional structured gap report (high/medium/low severity)

    Authorship + timestamp are NOT in this comment. Those live in the
    Authored Substrate revision chain (ADR-209) — every write to IDENTITY.md
    / BRAND.md / similar inferred files lands a revision with an `authored_by`
    trailer (`yarnnn:<model>` for inference, `operator` for direct edits) and
    a `created_at`. The frontend reads age from the revision chain now, not
    from `inferred_at` in this comment. Duplicating timestamp here would
    conflict with substrate-as-source-of-truth per FOUNDATIONS v6.1 Axiom 1.

    The comment is JSON-shaped inside an HTML comment so it survives markdown
    rendering and is easy to parse on the frontend.
    """
    # Strip any prior inference-meta comment so we don't accumulate them
    content = re.sub(
        r"\n*<!--\s*inference-meta:.*?-->\s*$",
        "",
        content,
        flags=re.DOTALL,
    ).rstrip()

    meta = {
        "target": target,
        "sources": {
            "from_chat": source_summary.get("has_text", False),
            "documents": source_summary.get("doc_filenames", []),
            "urls": source_summary.get("urls", []),
        },
    }
    if gap_report is not None:
        # Keep only the fields the frontend needs — drop `single_most_important_gap`
        # since it's derivable from `gaps` at render time, keeping the embedded
        # JSON lean.
        meta["gaps"] = {
            "richness": gap_report.get("richness"),
            "items": gap_report.get("gaps", []),
        }
    comment = f"\n\n<!-- inference-meta: {json.dumps(meta, separators=(',', ':'))} -->"
    return content + comment


async def read_uploaded_documents(
    client: Any,
    user_id: str,
    document_ids: list,
) -> list:
    """Read content from uploaded documents.

    ADR-249: reads from /workspace/uploads/*.md workspace files.
    document_ids are treated as workspace file paths (e.g.
    '/workspace/uploads/acme-brief.md') or path slugs to match.
    Falls back to searching by partial path match when no exact hit.

    Returns [{filename, content}] for inference input.
    """
    docs = []
    for doc_ref in (document_ids or [])[:5]:
        try:
            doc_ref = str(doc_ref)
            # Normalise: treat as path if it starts with '/', else match by slug
            if doc_ref.startswith("/workspace/uploads/"):
                path_filter = doc_ref
                result = client.table("workspace_files").select(
                    "path, content"
                ).eq("user_id", user_id).eq("path", path_filter).execute()
            else:
                # Match by partial path (slug or filename fragment)
                result = client.table("workspace_files").select(
                    "path, content"
                ).eq("user_id", user_id).like(
                    "path", f"/workspace/uploads/%{doc_ref}%"
                ).limit(1).execute()

            rows = result.data or []
            if not rows:
                continue

            row = rows[0]
            content = row.get("content", "") or ""
            # Strip YAML frontmatter block for cleaner inference input
            if content.startswith("---"):
                parts = content.split("---", 2)
                content = parts[2].strip() if len(parts) >= 3 else content

            # Extract filename from frontmatter or path
            filename = row["path"].rsplit("/", 1)[-1].removesuffix(".md")
            for line in (row.get("content", "") or "").split("\n"):
                if line.startswith("original_filename:"):
                    filename = line.split(":", 1)[1].strip()
                    break

            if content:
                docs.append({"filename": filename, "content": content})
        except Exception as e:
            logger.warning(f"[INFERENCE] Failed to read doc {doc_ref}: {e}")

    return docs


# =============================================================================
# ADR-162: Deterministic Gap Detection
# =============================================================================
#
# Pure Python. Zero LLM cost. Examines inference output for missing-but-load-
# bearing fields and returns a structured gap report. TP reads the report and
# issues at most one targeted Clarify per inference cycle.
#
# Gap heuristics are stable patterns that match against the rendered markdown.
# False negatives (missed gaps) are recoverable in subsequent inference cycles.
# False positives (gaps that aren't really gaps) are mitigated by careful
# heuristic design — when in doubt, downgrade severity rather than nag the user.

# Words that indicate a role/profession is mentioned in the Who block
_ROLE_KEYWORDS = {
    "founder", "co-founder", "cofounder", "ceo", "cto", "coo", "cfo", "vp",
    "engineer", "engineering", "developer", "designer", "consultant", "advisor",
    "operator", "manager", "director", "lead", "head of", "president",
    "principal", "owner", "fractional", "freelancer", "freelance", "contractor",
    "researcher", "analyst", "writer", "creator", "creative", "artist",
    "investor", "partner", "associate", "specialist", "strategist", "architect",
    "scientist", "teacher", "professor", "instructor", "coach",
}

# Words that indicate an industry/space is mentioned anywhere in the output
_INDUSTRY_KEYWORDS = {
    "industry", "market", "sector", "space", "vertical", "category",
    "saas", "fintech", "biotech", "edtech", "climate", "ai", "ml", "data",
    "infrastructure", "platform", "tools", "tooling", "consulting",
    "healthcare", "education", "media", "gaming", "ecommerce", "marketplace",
    "developer tools", "design tools", "productivity", "analytics", "security",
}


def _extract_section(content: str, section_name: str) -> str:
    """Return the body of a markdown section by header name (case-insensitive).

    Matches `## Section Name` or `### Section Name`. Returns content from after
    the header to the next header at any level (or end of file). Empty string
    if section not found.
    """
    pattern = re.compile(
        rf"^#{{1,6}}\s+{re.escape(section_name)}\s*$"
        rf"(?P<body>[\s\S]*?)"
        rf"(?=^#{{1,6}}\s|\Z)",
        re.MULTILINE | re.IGNORECASE,
    )
    match = pattern.search(content)
    if not match:
        return ""
    return match.group("body").strip()


def _count_bullets(section_body: str) -> int:
    """Count markdown bullet points (lines starting with `- ` or `* `)."""
    return len(re.findall(r"^[-*]\s+\S", section_body, re.MULTILINE))


def _detect_identity_gaps(content: str) -> list[dict]:
    """Identify missing-but-load-bearing fields in an IDENTITY.md inference.

    Returns a list of gap dicts ordered by severity (high → low).
    Each gap is one of the documented heuristics in ADR-162.
    """
    gaps: list[dict] = []
    content_lower = content.lower()

    who_block = _extract_section(content, "Who")
    domains_block = _extract_section(content, "Domains of Attention")
    work_patterns_block = _extract_section(content, "Work Patterns")

    # Gap: company name (high severity)
    # Heuristic: the Who block has the user's role but no capitalized company-like noun.
    # We look for any sequence of 2+ capitalized words OR a single capitalized word
    # that isn't a sentence-start. This is intentionally loose — false positives are
    # tolerable, false negatives (missing real companies) are worse.
    has_company = False
    if who_block:
        # Strip the user's name (typically first capitalized noun) and look for OTHER
        # capitalized nouns
        candidates = re.findall(r"\b[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)?", who_block)
        # Common false positives: "I", "AI", "US", "EU", etc. Filter very short ones.
        meaningful = [c for c in candidates if len(c) >= 4 and c not in {"This", "That", "What", "When", "Where", "Their", "These", "Those"}]
        # Need at least 2 meaningful capitalized nouns (one is the user's name, one is the company)
        # OR a single one PLUS a "founder/CEO at X" pattern
        has_at_pattern = bool(re.search(r"\b(?:at|of|founder of|ceo of|cto of)\s+[A-Z]", who_block, re.IGNORECASE))
        has_company = len(meaningful) >= 2 or has_at_pattern

    if not has_company:
        gaps.append({
            "field": "company_name",
            "severity": "high",
            "suggested_question": "What company or project are you building?",
            "options": ["I'll tell you the name", "I'm independent — no company"],
        })

    # Gap: role (medium severity)
    # Use word-boundary regex — substring match would catch "founder" inside
    # "foundering" or "ai" inside "domains of attention".
    has_role = any(
        re.search(rf"\b{re.escape(kw)}\b", content_lower)
        for kw in _ROLE_KEYWORDS
    )
    if not has_role:
        gaps.append({
            "field": "role",
            "severity": "medium",
            "suggested_question": "What's your role?",
            "options": ["Founder / CEO", "Engineer / Technical", "Designer / Creative", "Operator / Business", "Other"],
        })

    # Gap: domain count (high severity)
    domain_bullets = _count_bullets(domains_block)
    if domain_bullets < 2:
        gaps.append({
            "field": "domain_count",
            "severity": "high",
            "suggested_question": "What are 2-3 areas you spend most of your work attention on?",
            "options": [],
        })

    # Gap: work patterns (medium severity)
    if not work_patterns_block or _count_bullets(work_patterns_block) == 0:
        gaps.append({
            "field": "work_patterns",
            "severity": "medium",
            "suggested_question": "What recurring rhythms do you have? (e.g., weekly investor updates, daily standup)",
            "options": [],
        })

    # Gap: industry (low severity)
    # Word-boundary match — short keywords like "ai" or "ml" must not match
    # substrings inside other words ("domains of attention", "html").
    has_industry = any(
        re.search(rf"\b{re.escape(kw)}\b", content_lower)
        for kw in _INDUSTRY_KEYWORDS
    )
    if not has_industry:
        gaps.append({
            "field": "industry",
            "severity": "low",
            "suggested_question": "What industry or space are you in?",
            "options": [],
        })

    return gaps


# ADR-432 D1c: _detect_brand_gaps removed — Brand retired.


def _classify_richness(content: str) -> str:
    """Classify inference output as empty/sparse/rich.

    Same heuristic as the eval harness scorer — kept consistent so the harness
    and the runtime detector agree.
    """
    word_count = len(content.split())
    section_count = len(re.findall(r"^#{1,6}\s+\S", content, re.MULTILINE))

    if word_count < 30 or section_count == 0:
        return "empty"
    if word_count < 100 or section_count < 3:
        return "sparse"
    return "rich"


def detect_inference_gaps(
    target: Literal["identity"],
    inferred_content: str,
) -> dict:
    """Identify missing-but-load-bearing fields in an inference output.

    ADR-162 Sub-phase A. Pure Python. Zero LLM cost. Deterministic.
    ADR-432 D1c: identity-only (brand retired).

    Args:
        target: "identity"
        inferred_content: The markdown content produced by infer_shared_context()

    Returns:
        {
            "richness": "empty" | "sparse" | "rich",
            "gaps": [list of gap dicts ordered by severity],
            "single_most_important_gap": {gap dict} | None,
        }

    The single_most_important_gap is the highest-severity gap, with ties broken
    by which gap most blocks downstream scaffolding. TP should issue at most one
    Clarify per inference cycle, and only when severity is "high".
    """
    if not inferred_content or not inferred_content.strip():
        return {
            "richness": "empty",
            "gaps": [],
            "single_most_important_gap": None,
        }

    richness = _classify_richness(inferred_content)

    if target == "identity":
        gaps = _detect_identity_gaps(inferred_content)
    else:
        gaps = []

    # Sort by severity (high → medium → low) and pick the most important high-severity one
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    gaps.sort(key=lambda g: severity_rank.get(g["severity"], 3))

    single_most_important = None
    if gaps and gaps[0]["severity"] == "high":
        single_most_important = gaps[0]

    return {
        "richness": richness,
        "gaps": gaps,
        "single_most_important_gap": single_most_important,
    }
