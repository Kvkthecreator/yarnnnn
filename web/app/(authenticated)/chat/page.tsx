'use client';

/**
 * Chat Page — Dedicated full-page TP chat surface.
 *
 * SURFACE-ARCHITECTURE.md v3: Unscoped TP for strategic direction,
 * cross-cutting questions, workspace management, and task creation.
 * This is the action surface — where the user directs their workforce.
 */

import { useState, useMemo } from 'react';
import { MessageCircle, Globe, Upload, ListChecks, Settings2 } from 'lucide-react';
import { ChatPanel } from '@/components/tp/ChatPanel';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import { useTP } from '@/contexts/TPContext';

// Cold-start suggestion chips
const SUGGESTIONS = [
  'Tell me about my work and who I serve',
  'Set up competitive intelligence tracking',
  'Create a weekly Slack recap',
];

function ChatEmptyState({ onSuggestion }: { onSuggestion: (text: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-12">
      <MessageCircle className="w-10 h-10 text-muted-foreground/15 mb-4" />
      <h2 className="text-lg font-medium mb-1">What would you like to work on?</h2>
      <p className="text-sm text-muted-foreground mb-6 text-center max-w-md">
        Create tasks, update your workspace, or ask about your agents.
      </p>
      <div className="flex flex-wrap gap-2 justify-center max-w-lg">
        {SUGGESTIONS.map(s => (
          <button
            key={s}
            onClick={() => onSuggestion(s)}
            className="px-3 py-1.5 text-sm rounded-full border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const { messages, sendMessage } = useTP();
  const hasMessages = messages.length > 0;

  const handleSuggestion = (text: string) => {
    sendMessage(text);
  };

  // Plus menu actions need onSelect callbacks
  const plusMenuActions: PlusMenuAction[] = useMemo(() => [
    {
      id: 'create-task',
      label: 'Create a task',
      icon: ListChecks,
      verb: 'prompt' as const,
      onSelect: () => { /* ChatPanel handles via verb */ },
    },
    {
      id: 'update-context',
      label: 'Update my context',
      icon: Settings2,
      verb: 'prompt' as const,
      onSelect: () => { /* ChatPanel handles via verb */ },
    },
    {
      id: 'web-search',
      label: 'Web search',
      icon: Globe,
      verb: 'prompt' as const,
      onSelect: () => { /* ChatPanel handles via verb */ },
    },
    {
      id: 'upload-file',
      label: 'Upload file',
      icon: Upload,
      verb: 'attach' as const,
      onSelect: () => { /* ChatPanel handles file upload */ },
    },
  ], []);

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto w-full">
      <ChatPanel
        surfaceOverride={{ type: 'chat' }}
        plusMenuActions={plusMenuActions}
        placeholder="Ask anything or type / ..."
        showCommandPicker={true}
        emptyState={
          !hasMessages ? <ChatEmptyState onSuggestion={handleSuggestion} /> : undefined
        }
      />
    </div>
  );
}
