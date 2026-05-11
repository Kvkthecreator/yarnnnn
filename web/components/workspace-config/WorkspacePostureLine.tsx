'use client';

/**
 * WorkspacePostureLine — single line under PageHeader on /workspace.
 *
 * Per ADR-266 D2. Resets operator expectation: this page describes what's
 * set; the chat changes it. No inline forms expected. One sentence,
 * always present.
 */

export function WorkspacePostureLine() {
  return (
    <p className="text-xs text-muted-foreground">
      Your workspace's standing configuration. Read here, edit by chatting with YARNNN.
    </p>
  );
}
