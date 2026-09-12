#!/bin/bash
# SessionStart hook: git orientation + the open-items file. DYNAMIC STATE ONLY —
# doctrine lives in CLAUDE.md (already loaded); do not re-echo it here.

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

echo "Current branch: $(git -C "$CLAUDE_PROJECT_DIR" branch --show-current 2>/dev/null)"
echo ""

# docs/SESSION-HANDOFF.md holds OPEN items only (CLAUDE.md §Hooks). Delete an
# item in the commit that closes it. Warn when it starts turning into a journal.
HANDOFF="$CLAUDE_PROJECT_DIR/docs/SESSION-HANDOFF.md"
if [ -f "$HANDOFF" ]; then
  LINES=$(wc -l < "$HANDOFF" | tr -d ' ')
  echo "=== OPEN ITEMS (READ FIRST): docs/SESSION-HANDOFF.md — $LINES lines ==="
  if [ "$LINES" -gt 120 ]; then
    echo "  WARNING: over 120 lines. It holds open items only — move narrative to the ADR, the evaluation record, or memory."
  fi
  echo ""
fi
