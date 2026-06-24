#!/bin/bash
# Session start hook: git orientation only.
# Static doctrine (docs map, content ops, conventions) lives in CLAUDE.md, which is
# already loaded — don't re-echo it here. Keep this to dynamic state git can't load.

echo "SESSION ORIENTATION (auto-injected via hook):"
echo ""

echo "Recent commits:"
git -C "$CLAUDE_PROJECT_DIR" log --oneline -10 2>/dev/null || echo "(git log unavailable)"
echo ""

STATUS=$(git -C "$CLAUDE_PROJECT_DIR" status --short 2>/dev/null)
if [ -n "$STATUS" ]; then
  echo "In-progress work (uncommitted changes):"
  echo "$STATUS"
  echo ""
fi

BRANCH=$(git -C "$CLAUDE_PROJECT_DIR" branch --show-current 2>/dev/null)
echo "Current branch: $BRANCH"
echo ""

# Session handoff file — surfaces an explicit handoff left by the previous session.
# Delete docs/SESSION-HANDOFF.md after absorbing it to silence this banner.
if [ -f "$CLAUDE_PROJECT_DIR/docs/SESSION-HANDOFF.md" ]; then
  echo "=== ACTIVE SESSION HANDOFF (READ FIRST): docs/SESSION-HANDOFF.md ==="
  echo "Read it before responding; delete it in the commit that absorbs it."
  echo ""
fi
