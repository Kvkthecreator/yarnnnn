'use client';

/**
 * Chat Page — Dedicated full-page TP chat surface + onboarding home.
 *
 * SURFACE-ARCHITECTURE.md v3: Unscoped TP for strategic direction,
 * cross-cutting questions, workspace management, and task creation.
 *
 * This is also the ONBOARDING surface. New users (post-signup) land here.
 * When there's no chat history, ContextSetup renders as a full-page overlay
 * centered above ChatPanel's input bar. ContextSetup gets max-w-xl of real
 * estate — not constrained to ChatPanel's internal message area.
 * After first interaction, the overlay disappears and it's normal chat.
 */

import { useEffect, useMemo } from 'react';
import { Globe, Upload, ListChecks, Settings2 } from 'lucide-react';
import { ChatPanel } from '@/components/tp/ChatPanel';
import { ContextSetup } from '@/components/tp/ContextSetup';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import { useTP } from '@/contexts/TPContext';

export default function ChatPage() {
  const { messages, sendMessage, isLoading, loadScopedHistory } = useTP();
  const hasMessages = messages.length > 0 || isLoading;

  // Load global session history — ensures we're on global scope
  // (user may have navigated here from /agents which set agent scope)
  useEffect(() => {
    loadScopedHistory();
  }, [loadScopedHistory]);

  // Plus menu actions — workspace-level
  const plusMenuActions: PlusMenuAction[] = useMemo(() => [
    { id: 'create-task', label: 'Create a task', icon: ListChecks, verb: 'prompt' as const, onSelect: () => sendMessage('I want to create a task. What do you suggest based on my context?') },
    { id: 'update-context', label: 'Update my context', icon: Settings2, verb: 'prompt' as const, onSelect: () => {} },
    { id: 'web-search', label: 'Web search', icon: Globe, verb: 'prompt' as const, onSelect: () => {} },
    { id: 'upload-file', label: 'Upload file', icon: Upload, verb: 'attach' as const, onSelect: () => {} },
  ], [sendMessage]);

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto w-full relative">
      {/* ChatPanel always renders — handles messages + input bar */}
      <ChatPanel
        surfaceOverride={{ type: 'chat' }}
        plusMenuActions={plusMenuActions}
        placeholder={hasMessages ? 'Ask anything or type / ...' : 'Or just type here...'}
        showCommandPicker={true}
      />

      {/* Onboarding overlay — renders OVER ChatPanel's empty message area */}
      {/* Positioned to fill the space above the input bar */}
      {!hasMessages && (
        <div className="absolute inset-0 bottom-[72px] flex items-center justify-center px-6 py-8 bg-background z-10">
          <div className="w-full max-w-xl">
            <ContextSetup
              onSubmit={(msg) => sendMessage(msg)}
              showSkipOptions
              onSkipAction={(msg) => sendMessage(msg)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
