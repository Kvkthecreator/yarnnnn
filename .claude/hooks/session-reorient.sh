#!/bin/bash
# Session start hook: inject recent commit history and orientation reminders

echo "SESSION ORIENTATION (auto-injected via hook):"
echo ""
echo "Recent commits:"
git -C "$CLAUDE_PROJECT_DIR" log --oneline -10 2>/dev/null || echo "(git log unavailable)"
echo ""
echo "Before responding to the first message:"
echo "1. Review the commits above to understand recent work direction"
echo "2. CLAUDE.md and auto-memory are already loaded — consult them for project philosophy and architecture"
echo "3. If the user references specific files or features, read them before responding"
echo "4. Check for any in-progress work (unstaged changes, open TODOs) that may need continuity"