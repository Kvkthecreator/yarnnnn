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

echo "Canonical project documents (READ on demand, not upfront):"
echo "- docs/architecture/FOUNDATIONS.md — project philosophy, axioms, north star"
echo "- docs/NARRATIVE.md — product narrative and positioning"
echo "- docs/ESSENCE.md — core identity and design principles"
echo "- docs/README.md — project overview"
echo "- api/prompts/CHANGELOG.md — prompt version history"
echo "- docs/adr/ — architectural decisions (search before proposing changes)"
echo "- CLAUDE.md — development guidelines (already loaded)"
echo ""
echo "Before responding to the first message:"
echo "1. Review commits above for recent work direction"
echo "2. If the user's request touches architecture/philosophy, read the relevant doc FIRST"
echo "3. If referencing specific features or files, read them before responding"
echo "4. Check in-progress work above for continuity with prior session"