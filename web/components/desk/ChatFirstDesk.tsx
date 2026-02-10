'use client';

/**
 * ADR-037: Chat-First Surface Architecture
 *
 * Chat-first desk layout - TP is the primary interface
 *
 * Layout:
 * - Mobile: TP full screen
 * - Desktop: TP takes 60%+ of screen, surfaces as needed
 *
 * This inverts the traditional desk layout where surfaces were primary
 * and TP was a side drawer.
 */

import { useState, useRef, useEffect } from 'react';
import {
  MessageCircle,
  CheckCircle2,
  Circle,
  Loader2,
  Send,
  MapPin,
  Layers,
  User,
  ChevronRight,
  X,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { useActiveDomain } from '@/hooks/useActiveDomain';
import { Todo } from '@/types/desk';
import { cn } from '@/lib/utils';
import { getTPStateIndicators } from '@/lib/tp-chips';
import { getEntityName } from '@/lib/entity-cache';
import { SkillPicker } from '@/components/tp/SkillPicker';
import { SurfaceRouter } from './SurfaceRouter';
import { AttentionBanner } from './AttentionBanner';

export function ChatFirstDesk() {
  const {
    todos,
    messages,
    activeSkill,
    sendMessage,
    isLoading,
    status,
    pendingClarification,
    respondToClarification,
  } = useTP();
  const { surface, attention } = useDesk();
  const { domain, isLoading: domainLoading } = useActiveDomain();

  const [input, setInput] = useState('');
  const [skillPickerOpen, setSkillPickerOpen] = useState(false);
  const [surfacePanelOpen, setSurfacePanelOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Detect skill picker trigger
  const skillQuery = input.startsWith('/') ? input.slice(1).split(' ')[0] : null;

  useEffect(() => {
    if (skillQuery !== null && !input.includes(' ')) {
      setSkillPickerOpen(true);
    } else {
      setSkillPickerOpen(false);
    }
  }, [skillQuery, input]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    sendMessage(input, { surface });
    setInput('');
  };

  const handleSkillSelect = (command: string) => {
    setInput(command + ' ');
    setSkillPickerOpen(false);
    inputRef.current?.focus();
  };

  const handleOptionClick = (option: string) => {
    respondToClarification(option);
  };

  // Get context indicators
  const indicators = getTPStateIndicators(surface);
  const deliverableId = indicators.deliverable.id;
  const cachedDeliverableName = deliverableId ? getEntityName(deliverableId) : undefined;
  const surfaceLabel = cachedDeliverableName || indicators.surface.label;

  const formatSkillName = (skill: string) => {
    return skill
      .split('-')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getTitle = () => {
    if (activeSkill) return formatSkillName(activeSkill);
    return 'Thinking Partner';
  };

  // Check if there's a non-idle surface to show
  const hasActiveSurface = surface.type !== 'idle';

  return (
    <div className="h-full flex">
      {/* Main Chat Area - Primary */}
      <div className="flex-1 flex flex-col bg-background min-w-0">
        {/* Attention Banner - ADR-037: surfaces attention items */}
        {attention.length > 0 && (
          <AttentionBanner />
        )}

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
          <div className="flex items-center gap-2">
            <MessageCircle className="w-5 h-5 text-primary" />
            <span className="font-medium">{getTitle()}</span>
            {isLoading && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
          </div>

          {/* Surface toggle - only show if there's an active surface */}
          {hasActiveSurface && (
            <button
              onClick={() => setSurfacePanelOpen(!surfacePanelOpen)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-muted hover:bg-muted/80 transition-colors"
            >
              <span className="truncate max-w-[120px]">{surfaceLabel}</span>
              <ChevronRight className={cn(
                'w-4 h-4 transition-transform',
                surfacePanelOpen && 'rotate-90'
              )} />
            </button>
          )}
        </div>

        {/* Context indicators */}
        <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-muted/30 text-xs">
          <span className="text-muted-foreground/60">Context:</span>
          <div className="flex items-center gap-1 text-muted-foreground">
            <MapPin className="w-3 h-3" />
            <span className="truncate max-w-[100px]">{surfaceLabel}</span>
          </div>
          <span className="text-muted-foreground/40">·</span>
          <div className="flex items-center gap-1">
            {domainLoading ? (
              <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
            ) : domain ? (
              <>
                <Layers className="w-3 h-3 text-primary" />
                <span className="text-primary truncate max-w-[80px]" title={domain.name}>
                  {domain.name}
                </span>
              </>
            ) : (
              <>
                <User className="w-3 h-3 text-muted-foreground" />
                <span className="text-muted-foreground">All Context</span>
              </>
            )}
          </div>
        </div>

        {/* Todos (when active) */}
        {todos.length > 0 && (
          <div className="px-4 py-3 border-b border-border bg-muted/20 shrink-0">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-muted-foreground">Progress</span>
              <span className="text-xs text-muted-foreground">
                {todos.filter((t) => t.status === 'completed').length}/{todos.length}
              </span>
            </div>
            <div className="space-y-1.5 max-h-28 overflow-y-auto">
              {todos.map((todo, i) => (
                <TodoItem key={i} todo={todo} />
              ))}
            </div>
          </div>
        )}

        {/* Messages - Primary content area */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.length === 0 && !isLoading && (
            <div className="text-center py-12">
              <MessageCircle className="w-12 h-12 text-muted-foreground/20 mx-auto mb-3" />
              <h2 className="text-lg font-medium mb-2">Welcome to yarnnn</h2>
              <p className="text-sm text-muted-foreground max-w-md mx-auto mb-4">
                I&apos;m your Thinking Partner. Tell me what recurring work you need help with,
                or type <code className="bg-muted px-1.5 py-0.5 rounded text-xs">/</code> to see available skills.
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                <button
                  onClick={() => setInput('/create ')}
                  className="px-3 py-1.5 text-sm rounded-full bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                >
                  Create a deliverable
                </button>
                <button
                  onClick={() => setInput('What can you help me with?')}
                  className="px-3 py-1.5 text-sm rounded-full bg-muted hover:bg-muted/80 transition-colors"
                >
                  What can you do?
                </button>
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                'text-sm rounded-lg p-3 max-w-2xl',
                msg.role === 'user' ? 'bg-primary/10 ml-auto' : 'bg-muted'
              )}
            >
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide block mb-1">
                {msg.role === 'user' ? 'You' : 'TP'}
              </span>
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          ))}

          {/* Status indicators */}
          {status.type === 'thinking' && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Thinking...</span>
            </div>
          )}
          {status.type === 'tool' && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>{status.toolName}...</span>
            </div>
          )}
          {status.type === 'streaming' && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Typing...</span>
            </div>
          )}

          {/* Clarification options */}
          {status.type === 'clarify' && pendingClarification?.options && (
            <div className="space-y-2 bg-muted rounded-lg p-3 max-w-2xl">
              <p className="text-sm">{pendingClarification.question}</p>
              <div className="flex flex-wrap gap-2">
                {pendingClarification.options.map((option, i) => (
                  <button
                    key={i}
                    onClick={() => handleOptionClick(option)}
                    className="px-3 py-1.5 text-sm rounded-full bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-border shrink-0">
          <div className="relative max-w-2xl mx-auto">
            <SkillPicker
              query={skillQuery ?? ''}
              onSelect={handleSkillSelect}
              onClose={() => setSkillPickerOpen(false)}
              isOpen={skillPickerOpen}
            />
            <form onSubmit={handleSubmit} className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isLoading}
                placeholder={
                  status.type === 'clarify' ? 'Type your answer...' : 'Ask anything or type /...'
                }
                className="flex-1 px-4 py-3 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className="px-4 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                aria-label="Send"
              >
                <Send className="w-5 h-5" />
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Surface Panel - Secondary, slides in when needed */}
      {hasActiveSurface && (
        <div
          className={cn(
            'hidden md:block border-l border-border bg-background transition-all duration-300',
            surfacePanelOpen ? 'w-[480px]' : 'w-0 overflow-hidden'
          )}
        >
          {surfacePanelOpen && (
            <div className="h-full flex flex-col">
              <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <span className="font-medium text-sm truncate">{surfaceLabel}</span>
                <button
                  onClick={() => setSurfacePanelOpen(false)}
                  className="p-1.5 hover:bg-muted rounded-md transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="flex-1 overflow-hidden">
                <SurfaceRouter surface={surface} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TodoItem({ todo }: { todo: Todo }) {
  return (
    <div className="flex items-center gap-2">
      {todo.status === 'completed' ? (
        <CheckCircle2 className="w-3.5 h-3.5 text-green-600 shrink-0" />
      ) : todo.status === 'in_progress' ? (
        <Loader2 className="w-3.5 h-3.5 text-primary animate-spin shrink-0" />
      ) : (
        <Circle className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
      )}
      <span
        className={cn(
          'text-xs',
          todo.status === 'completed' && 'text-muted-foreground line-through',
          todo.status === 'in_progress' && 'text-foreground font-medium'
        )}
      >
        {todo.status === 'in_progress' ? todo.activeForm || todo.content : todo.content}
      </span>
    </div>
  );
}
