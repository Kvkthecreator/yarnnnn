'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * TPBar - Floating thinking partner input bar
 */

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, X } from 'lucide-react';
import { useDesk } from '@/contexts/DeskContext';
import { useTP } from '@/contexts/TPContext';
import { getChipsForSurface } from '@/lib/tp-chips';
import { TPChips } from './TPChips';
import { TPMessages } from './TPMessages';

export function TPBar() {
  const { surface, setSurface } = useDesk();
  const { messages, sendMessage, isLoading, clearMessages } = useTP();
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const chips = getChipsForSurface(surface);

  // Handle chip click - either send immediately or populate input
  const handleChipClick = (prompt: string) => {
    // For short prompts, send directly
    if (prompt.length < 50) {
      handleSend(prompt);
    } else {
      setInput(prompt);
      inputRef.current?.focus();
    }
  };

  // Handle form submit
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    handleSend(input);
  };

  // Send message
  const handleSend = async (content: string) => {
    setInput('');

    const results = await sendMessage(content, { surface });

    // If any tool result has a ui_action to open a surface, it's handled by TPContext
    // which calls onSurfaceChange
  };

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <div className="shrink-0 border-t border-border bg-background">
      {/* Messages area */}
      {messages.length > 0 && (
        <TPMessages messages={messages} onDismiss={clearMessages} />
      )}

      {/* Input area */}
      <div className="p-4">
        <form onSubmit={handleSubmit}>
          <div className="flex items-center gap-2">
            {/* Chips - hidden on small screens when there are messages */}
            <div className={`hidden sm:flex ${messages.length > 0 ? 'sm:hidden md:flex' : ''}`}>
              <TPChips chips={chips} onSelect={handleChipClick} disabled={isLoading} />
            </div>

            {/* Input */}
            <div className="flex-1 relative">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isLoading}
                placeholder="Ask anything..."
                className="w-full px-4 py-2.5 pr-12 border border-border rounded-full text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary disabled:opacity-50"
              />

              {/* Send button inside input */}
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 p-2 bg-primary text-primary-foreground rounded-full disabled:opacity-50 hover:bg-primary/90 transition-colors"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
        </form>

        {/* Mobile chips - show below input */}
        <div className="sm:hidden mt-3 flex gap-2 overflow-x-auto scrollbar-hide">
          <TPChips chips={chips} onSelect={handleChipClick} disabled={isLoading} />
        </div>
      </div>
    </div>
  );
}
