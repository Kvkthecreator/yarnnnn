# ADR-040: Semantic Skill Matching

> **Status**: Proposed
> **Created**: 2026-02-10
> **Priority**: P1 (Low effort, immediate value)
> **Related**: ADR-025 (Claude Code Agentic Alignment), ADR-038 (Claude Code Architecture Mapping)
> **Effort**: 2-3 days development

---

## Context

ADR-038 identified semantic skill matching as an enhancement opportunity. The current skill detection system uses simple substring pattern matching, which works well for explicit triggers but misses semantically equivalent requests.

### Current State

**Pattern-based detection** (`detect_skill()` in `services/skills.py`):
```python
def detect_skill(user_message: str) -> Optional[str]:
    # 1. Explicit slash command: /board-update → 100% accurate
    # 2. Substring patterns: "board update" in message → 100% for patterns
    for pattern in skill_def.get("trigger_patterns", []):
        if pattern in message_lower:
            return skill_name
```

**What works:**
- `/board-update` → Always detected
- "Create a board update" → Detected (contains "board update")
- "I need a weekly report" → Detected (contains "weekly report")

**What fails (~20-40% miss rate):**
- "Send monthly updates to my investors" → Not detected (different phrasing)
- "Set up investor communications" → Not detected
- "Create a quarterly report for the board" → Not detected
- "All hands summary" → Not in meeting-summary patterns

### Why This Matters

Users express intent naturally. Forcing exact phrasing creates friction. The gap between user intent and skill detection reduces TP effectiveness.

### Infrastructure Already Exists

YARNNN already has:
- **Embedding service**: `services/embeddings.py` with OpenAI text-embedding-3-small
- **Batch API**: Efficient embedding generation
- **Vector math**: 1536-dimensional vectors, cosine similarity ready
- **LLM extraction**: Memory extraction patterns we can adapt

---

## Decision

Implement **hybrid skill detection** that tries pattern matching first (fast, precise), then falls back to semantic matching (slower, higher recall).

### Detection Flow

```
User Message
    ↓
Pattern Match (existing detect_skill)
    ├── Match found → Return skill (fast path)
    └── No match → Continue
    ↓
Semantic Match (new detect_skill_semantic)
    ├── Embed message
    ├── Compare to skill embeddings
    ├── Above threshold? → Return skill
    └── Below threshold → No skill detected
```

### Why Hybrid?

| Approach | Speed | Precision | Recall |
|----------|-------|-----------|--------|
| Pattern only | Fast (<1ms) | 100% | ~70% |
| Semantic only | Slow (~300ms) | ~95% | ~95% |
| **Hybrid** | Fast (pattern) or slow (fallback) | ~98% | ~90% |

Pattern matching handles 70-80% of cases instantly. Semantic fallback catches the rest without degrading the common case.

---

## Specification

### 1. Skill Descriptions for Embeddings

Add natural language descriptions to each skill for semantic matching:

```python
SKILL_DESCRIPTIONS = {
    "board-update": """
        Create recurring board update deliverables for investors and board members.
        Monthly or quarterly updates with company metrics, progress, challenges, and asks.
        Investor communications, board reports, investor updates.
    """,

    "status-report": """
        Set up recurring status reports for managers, teams, or stakeholders.
        Weekly or daily progress updates, wins, blockers, alignment.
        Progress reports, team updates, status summaries.
    """,

    "research-brief": """
        Create competitive intelligence or market research briefs.
        Track competitors, market trends, technology developments.
        Competitor analysis, market research, competitive intel.
    """,

    "stakeholder-update": """
        Send regular updates to clients, external partners, or stakeholders.
        Project updates, client communications, partner reports.
    """,

    "meeting-summary": """
        Generate recurring meeting summaries from conversations.
        Standup notes, one-on-one summaries, team meeting recaps.
        Meeting notes, action items, discussion summaries.
    """,

    "newsletter-section": """
        Create recurring sections for newsletters or company digests.
        Founder letters, weekly digests, product updates, company news.
    """,

    "changelog": """
        Generate product release notes or changelog entries.
        New features, bug fixes, improvements, version updates.
        Release notes, what's new, product releases.
    """,

    "one-on-one-prep": """
        Prepare for recurring one-on-one meetings.
        Direct report conversations, skip-level meetings, mentee sessions.
        1:1 prep, meeting preparation, discussion points.
    """,

    "client-proposal": """
        Create proposal templates for client engagements.
        Service offerings, scope of work, project proposals.
        SOW, engagement proposals, client pitches.
    """,

    "performance-review": """
        Generate self-assessment documents for performance reviews.
        Quarterly retrospectives, annual evaluations, self-assessments.
        Review prep, accomplishments summary.
    """,
}
```

### 2. Embedding Cache

Pre-compute skill embeddings at startup (or lazy-load on first use):

```python
# services/skill_embeddings.py

import numpy as np
from services.embeddings import get_embedding

_SKILL_EMBEDDINGS: dict[str, list[float]] = {}

async def get_skill_embeddings() -> dict[str, list[float]]:
    """Get or compute skill embeddings (cached)."""
    global _SKILL_EMBEDDINGS

    if not _SKILL_EMBEDDINGS:
        for skill_name, description in SKILL_DESCRIPTIONS.items():
            _SKILL_EMBEDDINGS[skill_name] = await get_embedding(description)

    return _SKILL_EMBEDDINGS

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_np = np.array(a)
    b_np = np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))
```

### 3. Semantic Detection Function

```python
# services/skills.py (additions)

SEMANTIC_THRESHOLD = 0.72  # Tuned via testing

async def detect_skill_semantic(user_message: str) -> tuple[Optional[str], float]:
    """
    Semantic skill detection using embeddings.

    Returns: (skill_name or None, confidence score)
    """
    # Get message embedding
    message_embedding = await get_embedding(user_message)

    # Get skill embeddings (cached)
    skill_embeddings = await get_skill_embeddings()

    # Find best match
    best_skill = None
    best_score = 0.0

    for skill_name, skill_embedding in skill_embeddings.items():
        score = cosine_similarity(message_embedding, skill_embedding)
        if score > best_score:
            best_score = score
            best_skill = skill_name

    # Return if above threshold
    if best_score >= SEMANTIC_THRESHOLD:
        return (best_skill, best_score)

    return (None, best_score)
```

### 4. Hybrid Detection

```python
# services/skills.py (modified detect_skill)

async def detect_skill_hybrid(user_message: str) -> tuple[Optional[str], str, float]:
    """
    Hybrid skill detection: pattern first, semantic fallback.

    Returns: (skill_name, method, confidence)
        - method: "pattern" | "semantic" | "none"
        - confidence: 1.0 for pattern, 0.0-1.0 for semantic
    """
    # Fast path: pattern matching
    pattern_match = detect_skill(user_message)
    if pattern_match:
        return (pattern_match, "pattern", 1.0)

    # Fallback: semantic matching
    semantic_match, confidence = await detect_skill_semantic(user_message)
    if semantic_match:
        return (semantic_match, "semantic", confidence)

    return (None, "none", 0.0)
```

### 5. Integration with TP

```python
# agents/thinking_partner.py (modified)

# In execute_stream_with_tools() around line 895:
# Replace:
#   active_skill = detect_skill(task)
# With:
active_skill, detection_method, confidence = await detect_skill_hybrid(task)

# Optional: Log detection method for debugging
if active_skill:
    logger.info(f"Skill detected: {active_skill} via {detection_method} (confidence: {confidence:.2f})")
```

---

## Implementation Plan

### Phase 1: Core Implementation (1 day)

1. Add `SKILL_DESCRIPTIONS` to `services/skills.py`
2. Create `services/skill_embeddings.py` with:
   - Embedding cache
   - Cosine similarity function
   - `detect_skill_semantic()` function
3. Add `detect_skill_hybrid()` to `services/skills.py`

### Phase 2: Integration (0.5 day)

1. Update `ThinkingPartnerAgent.execute_with_tools()` to use hybrid detection
2. Update `ThinkingPartnerAgent.execute_stream_with_tools()` to use hybrid detection
3. Add logging for detection method tracking

### Phase 3: Testing & Tuning (1-1.5 days)

1. Create test set: 50+ natural language variations
2. Measure accuracy across all 10 skills
3. Tune `SEMANTIC_THRESHOLD` (test 0.65, 0.70, 0.72, 0.75, 0.80)
4. Validate no regressions in pattern matching

---

## Test Cases

### Should Match (Semantic)

| User Message | Expected Skill | Why Semantic Needed |
|--------------|----------------|---------------------|
| "Send monthly updates to my investors" | board-update | Phrasing differs |
| "Set up investor communications" | board-update | Synonym |
| "Create a quarterly report for the board" | board-update | Board implied |
| "All hands meeting notes" | meeting-summary | Synonym for meeting |
| "Competitive landscape analysis" | research-brief | Synonym |
| "Share progress with the team weekly" | status-report | Phrasing differs |
| "Prepare for my 1-1 with Sarah" | one-on-one-prep | Natural language |
| "Write up what we shipped this sprint" | changelog | Informal phrasing |

### Should NOT Match

| User Message | Why No Skill |
|--------------|--------------|
| "What's the weather?" | Unrelated |
| "Show my memories" | Navigation, not skill |
| "Tell me about board games" | "Board" is false positive risk |
| "Update my profile" | Different kind of update |

---

## Consequences

### Positive

1. **Better user experience** — Natural language works
2. **Higher skill activation** — 15-25% more requests trigger skills
3. **No UX changes** — Invisible improvement
4. **Low risk** — Pattern matching still handles most cases

### Negative

1. **Latency on fallback** — +200-300ms for semantic path
2. **API cost** — ~$0.0003 per embedding (negligible)
3. **Tuning required** — Threshold needs calibration

### Risks

1. **False positives** — "Update my resume" matching stakeholder-update
   - Mitigation: High threshold (0.72+), pattern matching first

2. **Embedding model changes** — OpenAI updates break cache
   - Mitigation: Re-embed on startup, version in cache key

---

## Open Questions

1. **Threshold value** — Start with 0.72, tune based on testing
2. **Multi-skill detection** — Defer to future ADR (not MVP)
3. **User feedback** — Could show "Did you mean /board-update?" (defer)

---

## References

- [ADR-025: Claude Code Agentic Alignment](./ADR-025-claude-code-agentic-alignment.md)
- [ADR-038: Claude Code Architecture Mapping](./ADR-038-claude-code-architecture-mapping.md)
- `services/skills.py` — Current skill system
- `services/embeddings.py` — Embedding infrastructure

---

*This ADR proposes semantic skill matching as a low-effort enhancement to improve natural language skill detection.*
