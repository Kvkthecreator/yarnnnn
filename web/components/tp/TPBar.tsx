'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * TPBar - Floating thinking partner input bar
 *
 * Design: Floating pill that hovers above content
 * - Desktop: Centered with max-width, lifted with shadow
 * - Mobile: Collapsed FAB that expands on tap
 */

import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, MessageCircle, X } from 'lucide-react';
import { useDesk } from '@/contexts/DeskContext';
import { useTP } from '@/contexts/TPContext';
import { TPMessages } from './TPMessages';

export function TPBar() {
  const { surface } = useDesk();
  const { messages, sendMessage, isLoading, clearMessages } = useTP();
  const [input, setInput] = useState('');
  const [mobileExpanded, setMobileExpanded] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Handle form submit
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    handleSend(input);
  };

  // Send message
  const handleSend = async (content: string) => {
    setInput('');
    await sendMessage(content, { surface });
  };

  // Focus input when expanded on mobile
  useEffect(() => {
    if (mobileExpanded) {
      inputRef.current?.focus();
    }
  }, [mobileExpanded]);

  return (
    <>
      {/* Mobile FAB - visible only on small screens when collapsed */}
      <button
        onClick={() => setMobileExpanded(true)}
        className={`
          fixed bottom-6 right-6 z-50
          w-14 h-14 rounded-full
          bg-primary text-primary-foreground
          shadow-lg shadow-primary/25
          flex items-center justify-center
          transition-all duration-200
          hover:scale-105 active:scale-95
          md:hidden
          ${mobileExpanded ? 'scale-0 opacity-0' : 'scale-100 opacity-100'}
        `}
        aria-label="Ask TP"
      >
        <MessageCircle className="w-6 h-6" />
      </button>

      {/* Floating input bar */}
      <div
        className={`
          shrink-0 bg-transparent
          transition-all duration-200
          ${mobileExpanded ? 'fixed inset-x-0 bottom-0 z-50 bg-background/80 backdrop-blur-sm md:relative md:bg-transparent md:backdrop-blur-none' : 'hidden md:block'}
        `}
      >
        {/* Messages area - positioned above the input */}
        {messages.length > 0 && (
          <div className="max-w-2xl mx-auto px-4">
            <TPMessages messages={messages} onDismiss={clearMessages} />
          </div>
        )}

        {/* Input container */}
        <div className="p-4 pb-6 md:pb-4">
          <div className="max-w-2xl mx-auto">
            <form onSubmit={handleSubmit}>
              <div className="relative flex items-center gap-2">
                {/* Close button on mobile */}
                {mobileExpanded && (
                  <button
                    type="button"
                    onClick={() => setMobileExpanded(false)}
                    className="md:hidden p-2 text-muted-foreground hover:text-foreground"
                    aria-label="Close"
                  >
                    <X className="w-5 h-5" />
                  </button>
                )}

                {/* Input field */}
                <div className="flex-1 relative">
                  <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={isLoading}
                    placeholder="Ask anything..."
                    className="
                      w-full px-5 py-3 pr-14
                      border border-border rounded-full
                      text-sm bg-background
                      shadow-lg shadow-black/5
                      focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary
                      disabled:opacity-50
                    "
                  />

                  {/* Send button */}
                  <button
                    type="submit"
                    disabled={isLoading || !input.trim()}
                    className="
                      absolute right-2 top-1/2 -translate-y-1/2
                      p-2.5 rounded-full
                      bg-primary text-primary-foreground
                      disabled:opacity-50
                      hover:bg-primary/90 transition-colors
                    "
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
          </div>
        </div>
      </div>

      {/* Mobile backdrop */}
      {mobileExpanded && (
        <div
          className="fixed inset-0 z-40 bg-black/20 md:hidden"
          onClick={() => setMobileExpanded(false)}
        />
      )}
    </>
  );
}
