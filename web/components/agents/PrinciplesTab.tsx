'use client';

/**
 * PrinciplesTab — Thinking Partner detail Principles tab.
 *
 * Lifted from web/components/agents/reviewer/PrinciplesPane.tsx by
 * ADR-241 D2. Refactored to use WorkspaceFileView (universal kernel
 * component) by the chat-page refactor — same look-and-feel as the
 * other TP tabs (Identity / Mandate / Autonomy / Memory).
 */

import { Scale } from 'lucide-react';
import { WorkspaceFileView } from '@/components/shared/WorkspaceFileView';
import { useTP } from '@/contexts/TPContext';

export function PrinciplesTab() {
  const { sendMessage } = useTP();
  return (
    <WorkspaceFileView
      path="/workspace/review/principles.md"
      title="Principles"
      icon={Scale}
      tagline="The judgment framework TP applies to verdicts. Operator-authored; revision history preserved per ADR-209."
      editPrompt="I want to evolve my Reviewer's principles. Walk me through the current declaration and help me decide what to change."
      onEdit={(prompt) => sendMessage(prompt)}
      emptyBody={
        <p className="text-center text-xs">
          No principles declared yet. The Reviewer applies these to every proposal —
          declaring them sharpens what gets approved vs rejected.
        </p>
      }
    />
  );
}
