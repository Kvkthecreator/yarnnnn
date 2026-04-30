'use client';

/**
 * SubstrateTab — thin wrapper for rendering a workspace substrate file
 * in the Thinking Partner detail view (ADR-241 + ADR-236 Round 5+).
 *
 * Previously had its own fetch loop; now delegates to WorkspaceFileView
 * (universal kernel component) per the chat-page refactor that established
 * WorkspaceFileView as the single file-rendering contract.
 *
 * Props are 1:1 with WorkspaceFileView's interface so callers (MandateTab,
 * AutonomyTab) don't need to change.
 */

import { useTP } from '@/contexts/TPContext';
import { WorkspaceFileView, type WorkspaceFileViewProps } from '@/components/shared/WorkspaceFileView';

export interface SubstrateTabProps
  extends Omit<WorkspaceFileViewProps, 'onEdit'> {
  editPrompt: string;
}

export function SubstrateTab({
  editPrompt,
  ...rest
}: SubstrateTabProps) {
  const { sendMessage } = useTP();
  return (
    <WorkspaceFileView
      {...rest}
      editPrompt={editPrompt}
      onEdit={(prompt) => sendMessage(prompt)}
    />
  );
}
