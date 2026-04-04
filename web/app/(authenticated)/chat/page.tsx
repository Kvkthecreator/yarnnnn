'use client';

/**
 * Chat Page — Dedicated full-page TP chat surface + onboarding home.
 *
 * SURFACE-ARCHITECTURE.md v3: Unscoped TP for strategic direction,
 * cross-cutting questions, workspace management, and task creation.
 *
 * This is also the ONBOARDING surface. New users (post-signup) land here.
 * When there's no chat history, ContextSetup renders as the cold-start
 * experience — URLs, files, and notes that bootstrap workspace identity.
 * After first interaction, the page is a normal full-page chat.
 */

import { useMemo } from 'react';
import { MessageCircle, Globe, Upload, ListChecks, Settings2 } from 'lucide-react';
import { ChatPanel } from '@/components/tp/ChatPanel';
import { ContextSetup } from '@/components/tp/ContextSetup';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import { useTP } from '@/contexts/TPContext';

export default function ChatPage() {
  const { messages, sendMessage } = useTP();
  const hasMessages = messages.length > 0;

  // Plus menu actions — workspace-level
  const plusMenuActions: PlusMenuAction[] = useMemo(() => [
    { id: 'create-task', label: 'Create a task', icon: ListChecks, verb: 'prompt' as const, onSelect: () => sendMessage('I want to create a task. What do you suggest based on my context?') },
    { id: 'update-context', label: 'Update my context', icon: Settings2, verb: 'prompt' as const, onSelect: () => {} },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt' as const, onSelect: () => {} },
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach' as const, onSelect: () => {} },
  ], [sendMessage]);

  // Cold-start: ContextSetup with full onboarding (URLs, files, notes)
  // After first message: no empty state — chat takes over
  const emptyState = !hasMessages ? (
    <div className="flex flex-col items-center justify-center h-full px-4 py-8">
      <ContextSetup
        onSubmit={(msg) => sendMessage(msg)}
        showSkipOptions
        onSkipAction={(msg) => sendMessage(msg)}
      />
    </div>
  ) : undefined;

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto w-full">
      <ChatPanel
        surfaceOverride={{ type: 'chat' }}
        plusMenuActions={plusMenuActions}
        placeholder="Ask anything or type / ..."
        showCommandPicker={true}
        emptyState={emptyState}
      />
    </div>
  );
}
