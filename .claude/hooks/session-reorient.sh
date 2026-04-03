#!/bin/bash
# Session start hook: front-load context so new/compacted sessions hit the ground running

echo "SESSION ORIENTATION (auto-injected via hook):"
echo ""

echo "Recent commits:"
git -C "$CLAUDE_PROJECT_DIR" log --oneline -10 2>/dev/null || echo "(git log unavailable)"
echo ""

# Show in-progress work (unstaged/staged changes)
STATUS=$(git -C "$CLAUDE_PROJECT_DIR" status --short 2>/dev/null)
if [ -n "$STATUS" ]; then
  echo "In-progress work (uncommitted changes):"
  echo "$STATUS"
  echo ""
fi

# Show what changed in staged/unstaged files (compact diff stat)
DIFF_STAT=$(git -C "$CLAUDE_PROJECT_DIR" diff --stat HEAD 2>/dev/null)
if [ -n "$DIFF_STAT" ]; then
  echo "Change summary:"
  echo "$DIFF_STAT"
  echo ""
fi

# Current branch
BRANCH=$(git -C "$CLAUDE_PROJECT_DIR" branch --show-current 2>/dev/null)
echo "Current branch: $BRANCH"
echo ""

echo "=== DOCUMENTATION DIRECTION (2026-03-29) ==="
echo ""
echo "SERVICE-MODEL.md is the SINGLE canonical service description."
echo "  → docs/architecture/SERVICE-MODEL.md — entities, execution, services, primitives, perception"
echo "  → All other architecture docs are deep-dives linked FROM service model, not standalone"
echo "  → Stale docs (primitives.md, agents.md, context-pipeline.md) are now redirects"
echo ""
echo "Terminology:"
echo "  → 'process' = multi-step agent sequence (user-facing AND data model field)"
echo "  → 'pipeline' = internal execution engine only (task_pipeline.py, log prefixes)"
echo "  → ADRs 120-137 = SUPERSEDED (project/PM layer deleted by ADR-138)"
echo ""
echo "When writing docs or code, prefer linking to SERVICE-MODEL.md over duplicating context."
echo ""

echo "Canonical project documents (READ on demand, not upfront):"
echo "- docs/architecture/SERVICE-MODEL.md — HOW THE SYSTEM WORKS (start here)"
echo "- docs/architecture/FOUNDATIONS.md — project philosophy, axioms, north star"
echo "- docs/NARRATIVE.md — product narrative and positioning"
echo "- docs/ESSENCE.md — core identity and design principles"
echo "- docs/README.md — project overview and quick links"
echo "- api/prompts/CHANGELOG.md — prompt version history"
echo "- docs/adr/ — architectural decisions (search before proposing changes)"
echo "- CLAUDE.md — development guidelines (already loaded)"
echo ""
echo "=== CONTENT OPS ==="
echo ""
echo "Single source of truth: content/OPS.md (consolidated 2026-03-16)"
echo "  → Voice/brand: content/VOICE_AND_BRAND.md (three voices: Kevin, YARNNN brand, YARNNN ads)"
echo "  → Strategy: content/STRATEGY.md (readability rules, hub-and-spoke, GEO)"
echo "  → Blog posts: content/posts/*.md (frontmatter + markdown, status: published|draft)"
echo ""
echo "Content workflow (NO separate md files per platform):"
echo "  1. Draft blog post in content/posts/{slug}.md (set status: draft)"
echo "  2. Set status: published → git commit + push → Vercel auto-deploys to yarnnn.com/blog"
echo "  3. Cross-post via Claude in Chrome (same session):"
echo "     - LinkedIn company page (200-400 word condensed version)"
echo "     - X/Twitter (<280 char thesis + blog URL)"
echo "     - X Article (3-7 days later, full cross-post)"
echo "     - Medium (import from blog URL, set canonical)"
echo "     - Reddit (Kevin posts manually, Claude drafts)"
echo "  4. Blog first, always. LinkedIn + X tweet same day. X Article + Medium following week."
echo ""

echo "Before responding to the first message:"
echo "1. Review commits above for recent work direction"
echo "2. If the user's request touches architecture/philosophy, read the relevant doc FIRST"
echo "3. If referencing specific features or files, read them before responding"
echo "4. Check in-progress work above for continuity with prior session"
echo "5. If the user asks about content/posting, read content/OPS.md before proceeding"