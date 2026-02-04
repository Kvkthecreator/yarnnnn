'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * TPBar - Status hub and input for Thinking Partner
 *
 * Design: Claude Code-style bottom bar with:
 * - State indicators above input (surface, context, deliverable)
 * - Status area for thinking/streaming/clarify states
 * - Input field with send button
 * - History toggle for recent messages
 */

import { useState, useRef, useEffect } from 'react';
import {
  Send,
  Loader2,
  MessageCircle,
  X,
  ChevronDown,
  ChevronUp,
  LayoutDashboard,
  Calendar,
  Briefcase,
  Brain,
  FileText,
  Folder,
  FileCheck,
  MapPin,
} from 'lucide-react';
import { useDesk } from '@/contexts/DeskContext';
import { useTP, TPStatus } from '@/contexts/TPContext';
import { cn } from '@/lib/utils';
import { getTPStateIndicators } from '@/lib/tp-chips';
import { getEntityName } from '@/lib/entity-cache';

// Human-readable tool names - conversational tone
const TOOL_LABELS: Record<string, string> = {
  respond: 'Composing response...',
  clarify: 'Need to ask you something...',
  list_memories: 'Pulling up your memories...',
  list_projects: 'Loading your projects...',
  list_deliverables: 'Checking your deliverables...',
  list_work: 'Looking at your work...',
  get_deliverable: 'Opening that deliverable...',
  get_work: 'Fetching work details...',
  create_project: 'Setting up the project...',
  create_memory: 'Remembering this...',
  create_work: 'Kicking off the work...',
  create_deliverable: 'Creating your deliverable...',
  run_deliverable: 'Generating the deliverable...',
  update_deliverable: 'Updating deliverable...',
  update_work: 'Updating work...',
  delete_memory: 'Removing from memory...',
  rename_project: 'Renaming project...',
  update_project: 'Updating project...',
};

function getToolLabel(toolName: string): string {
  return TOOL_LABELS[toolName] || `Running ${toolName}...`;
}

// Icon component mapping
const SURFACE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  LayoutDashboard,
  Calendar,
  Briefcase,
  Brain,
  FileText,
  Folder,
  FileCheck,
};

export function TPBar() {
  const { surface } = useDesk();
  const {
    sendMessage,
    isLoading,
    status,
    pendingClarification,
    respondToClarification,
    clearClarification,
    messages,
  } = useTP();
  const [input, setInput] = useState('');
  const [mobileExpanded, setMobileExpanded] = useState(false);
  const [historyExpanded, setHistoryExpanded] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const statusRef = useRef<HTMLDivElement>(null);

  // Get state indicators from current surface
  const indicators = getTPStateIndicators(surface);
  const SurfaceIcon = SURFACE_ICONS[indicators.surface.icon] || LayoutDashboard;

  // Get dynamic entity names from cache (if available)
  const deliverableId = indicators.deliverable.id;
  const cachedDeliverableName = deliverableId ? getEntityName(deliverableId) : undefined;

  // Use cached name if available, otherwise fall back to generic label
  const surfaceLabel = cachedDeliverableName || indicators.surface.label;
  const contextLabel = cachedDeliverableName
    ? `${cachedDeliverableName} context`
    : indicators.context.label;

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

  // Handle clarification option click
  const handleOptionClick = (option: string) => {
    respondToClarification(option);
  };

  // Focus input when expanded on mobile
  useEffect(() => {
    if (mobileExpanded) {
      inputRef.current?.focus();
    }
  }, [mobileExpanded]);

  // Render status content based on current state
  const renderStatus = (currentStatus: TPStatus) => {
    switch (currentStatus.type) {
      case 'idle':
        return null;

      case 'thinking':
        return (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">Thinking...</span>
          </div>
        );

      case 'tool':
        return (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">{getToolLabel(currentStatus.toolName)}</span>
          </div>
        );

      case 'streaming':
        return <div className="text-sm text-foreground">{currentStatus.content}</div>;

      case 'clarify':
        return (
          <div className="space-y-2">
            <p className="text-sm text-foreground">{currentStatus.question}</p>
            {currentStatus.options && currentStatus.options.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {currentStatus.options.map((option, i) => (
                  <button
                    key={i}
                    onClick={() => handleOptionClick(option)}
                    className="px-3 py-1.5 text-sm rounded-full bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                  >
                    {option}
                  </button>
                ))}
              </div>
            )}
          </div>
        );

      case 'complete':
        if (!currentStatus.message) return null;
        return <div className="text-sm text-foreground">{currentStatus.message}</div>;

      default:
        return null;
    }
  };

  const hasStatus = status.type !== 'idle';
  const recentMessages = messages.slice(-3);

  return (
    <>
      {/* Mobile FAB - visible only on small screens when collapsed */}
      <button
        onClick={() => setMobileExpanded(true)}
        className={cn(
          'fixed bottom-6 right-6 z-50',
          'w-14 h-14 rounded-full',
          'bg-primary text-primary-foreground',
          'shadow-lg shadow-primary/25',
          'flex items-center justify-center',
          'transition-all duration-200',
          'hover:scale-105 active:scale-95',
          'md:hidden',
          mobileExpanded ? 'scale-0 opacity-0' : 'scale-100 opacity-100'
        )}
        aria-label="Ask TP"
      >
        <MessageCircle className="w-6 h-6" />
      </button>

      {/* Main TP Bar */}
      <div
        className={cn(
          'shrink-0 bg-background',
          'transition-all duration-200',
          mobileExpanded
            ? 'fixed inset-x-0 bottom-0 z-50 bg-background md:relative'
            : 'hidden md:block'
        )}
      >
        <div className="max-w-2xl mx-auto px-4">
          {/* History toggle (when there are messages) */}
          {messages.length > 0 && !hasStatus && (
            <button
              onClick={() => setHistoryExpanded(!historyExpanded)}
              className="w-full flex items-center justify-center gap-1 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {historyExpanded ? (
                <>
                  <ChevronDown className="w-3 h-3" />
                  Hide history
                </>
              ) : (
                <>
                  <ChevronUp className="w-3 h-3" />
                  {messages.length} message{messages.length !== 1 ? 's' : ''}
                </>
              )}
            </button>
          )}

          {/* Message history (collapsed by default) */}
          {historyExpanded && !hasStatus && (
            <div className="mb-2 p-3 rounded-lg bg-muted/50 max-h-48 overflow-y-auto">
              {recentMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={cn(
                    'text-sm py-1',
                    msg.role === 'user' ? 'text-muted-foreground' : 'text-foreground'
                  )}
                >
                  <span className="font-medium">{msg.role === 'user' ? 'You: ' : 'TP: '}</span>
                  {msg.content.slice(0, 150)}
                  {msg.content.length > 150 && '...'}
                </div>
              ))}
            </div>
          )}

          {/* Status area - prominent when visible for user assurance */}
          {hasStatus && (
            <div
              ref={statusRef}
              className="mb-2 p-3 rounded-lg bg-muted border border-border shadow-md animate-in fade-in slide-in-from-bottom-2 duration-200"
            >
              {renderStatus(status)}
            </div>
          )}
        </div>

        {/* Input container with integrated state indicators */}
        <div className="p-4 pb-3 md:pb-3">
          <div className="max-w-2xl mx-auto">
            {/* Close button on mobile - outside the input group */}
            {mobileExpanded && (
              <div className="flex justify-end mb-2 md:hidden">
                <button
                  type="button"
                  onClick={() => setMobileExpanded(false)}
                  className="p-2 text-muted-foreground hover:text-foreground"
                  aria-label="Close"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            )}

            {/* Input group - input + indicators as unified component */}
            <div className="border border-border rounded-2xl bg-background shadow-sm overflow-hidden">
              <form onSubmit={handleSubmit}>
                <div className="relative flex items-center">
                  {/* Input field */}
                  <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    disabled={isLoading}
                    placeholder={
                      status.type === 'clarify' ? 'Type your answer...' : 'Ask anything...'
                    }
                    className={cn(
                      'w-full px-4 py-3 pr-12',
                      'text-sm bg-transparent',
                      'border-0',
                      'focus:outline-none focus:ring-0',
                      'disabled:opacity-50'
                    )}
                  />

                  {/* Send button */}
                  <button
                    type="submit"
                    disabled={isLoading || !input.trim()}
                    className={cn(
                      'absolute right-2 top-1/2 -translate-y-1/2',
                      'p-2 rounded-full',
                      'text-muted-foreground',
                      'disabled:opacity-30',
                      'hover:text-foreground hover:bg-muted transition-colors',
                      input.trim() && !isLoading && 'text-primary hover:text-primary'
                    )}
                  >
                    {isLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </form>

              {/* State indicators - inside the input container, subtle divider */}
              <div className="flex items-center gap-2 px-4 py-1.5 border-t border-border/50 bg-muted/30">
                {/* Label */}
                <span className="shrink-0 text-[11px] text-muted-foreground/60">TP sees:</span>

                {/* Surface indicator */}
                <div className="shrink-0 flex items-center gap-1 text-[11px] text-muted-foreground">
                  <MapPin className="w-3 h-3 opacity-60" />
                  <span className="truncate max-w-[100px]">{surfaceLabel}</span>
                </div>

                <span className="text-muted-foreground/40 text-[10px]">·</span>

                {/* Context indicator */}
                <div className="shrink-0 flex items-center gap-1 text-[11px] text-muted-foreground">
                  <Brain className="w-3 h-3 opacity-60" />
                  <span className="truncate max-w-[120px]">{contextLabel}</span>
                </div>

                {/* Deliverable indicator (only show if active) */}
                {indicators.deliverable.active && (
                  <>
                    <span className="text-muted-foreground/40 text-[10px]">·</span>
                    <div className="shrink-0 flex items-center gap-1 text-[11px] text-primary/60">
                      <Calendar className="w-3 h-3" />
                      <span>Active</span>
                    </div>
                  </>
                )}
              </div>
            </div>
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
