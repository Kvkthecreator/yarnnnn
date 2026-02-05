'use client';

/**
 * ADR-025 Addendum: TP as Persistent Drawer (Model B)
 *
 * TPDrawer - Right-side collapsible drawer for TP conversation
 *
 * Desktop (≥768px): 360px right panel, collapsible
 * Mobile (<768px): Full-screen overlay when expanded, FAB when collapsed
 *
 * Features:
 * - Full message history
 * - Inline todo progress when TP is working
 * - Input field with skill picker
 * - Context indicators (surface, project)
 */

import { useState, useRef, useEffect } from 'react';
import {
  X,
  MessageCircle,
  CheckCircle2,
  Circle,
  Loader2,
  Send,
  ChevronLeft,
  MapPin,
  FolderOpen,
  User,
} from 'lucide-react';
import { useTP } from '@/contexts/TPContext';
import { useDesk } from '@/contexts/DeskContext';
import { useProjects } from '@/hooks/useProjects';
import { Todo } from '@/types/desk';
import { cn } from '@/lib/utils';
import { getTPStateIndicators } from '@/lib/tp-chips';
import { getEntityName } from '@/lib/entity-cache';
import { SkillPicker } from './SkillPicker';

export function TPDrawer() {
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
  const { surface, selectedProject, setSelectedProject } = useDesk();
  const { projects } = useProjects();

  const [expanded, setExpanded] = useState(true);
  const [input, setInput] = useState('');
  const [skillPickerOpen, setSkillPickerOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (expanded) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, status, expanded]);

  // Focus input when drawer expands
  useEffect(() => {
    if (expanded) {
      inputRef.current?.focus();
    }
  }, [expanded]);

  // Auto-expand when TP has todos (multi-step work)
  useEffect(() => {
    if (todos.length > 0 && !expanded) {
      setExpanded(true);
    }
  }, [todos.length, expanded]);

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

    // Auto-expand drawer when sending message
    if (!expanded) {
      setExpanded(true);
    }

    sendMessage(input, {
      surface,
      projectId: selectedProject?.id,
    });
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

  // Format skill name for display
  const formatSkillName = (skill: string) => {
    return skill
      .split('-')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Get drawer title
  const getTitle = () => {
    if (activeSkill) return formatSkillName(activeSkill);
    return 'Thinking Partner';
  };

  // Mobile FAB (shown when collapsed on mobile)
  const MobileFAB = () => (
    <button
      onClick={() => setExpanded(true)}
      className={cn(
        'fixed bottom-6 right-6 z-50',
        'w-14 h-14 rounded-full',
        'bg-primary text-primary-foreground',
        'shadow-lg shadow-primary/25',
        'flex items-center justify-center',
        'transition-all duration-200',
        'hover:scale-105 active:scale-95',
        'md:hidden',
        expanded ? 'scale-0 opacity-0 pointer-events-none' : 'scale-100 opacity-100'
      )}
      aria-label="Open TP chat"
    >
      {isLoading ? (
        <Loader2 className="w-6 h-6 animate-spin" />
      ) : todos.length > 0 ? (
        <span className="relative">
          <MessageCircle className="w-6 h-6" />
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-amber-500 rounded-full text-[10px] flex items-center justify-center">
            {todos.filter((t) => t.status !== 'completed').length}
          </span>
        </span>
      ) : (
        <MessageCircle className="w-6 h-6" />
      )}
    </button>
  );

  // Desktop collapsed tab (shown when collapsed on desktop)
  const DesktopTab = () => (
    <button
      onClick={() => setExpanded(true)}
      className={cn(
        'hidden md:flex',
        'fixed right-0 top-1/2 -translate-y-1/2 z-40',
        'flex-col items-center gap-2 px-2 py-4',
        'bg-background border border-r-0 border-border rounded-l-lg shadow-md',
        'hover:bg-muted transition-colors',
        expanded ? 'translate-x-full opacity-0 pointer-events-none' : 'translate-x-0 opacity-100'
      )}
      aria-label="Open TP drawer"
    >
      <ChevronLeft className="w-4 h-4" />
      {isLoading && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
      {todos.length > 0 && !isLoading && (
        <span className="w-5 h-5 bg-amber-500 rounded-full text-[10px] text-white flex items-center justify-center">
          {todos.filter((t) => t.status !== 'completed').length}
        </span>
      )}
      <span className="text-xs [writing-mode:vertical-lr] rotate-180">TP</span>
    </button>
  );

  // Main drawer content
  const DrawerContent = () => (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <MessageCircle className="w-4 h-4 text-primary" />
          <span className="font-medium text-sm">{getTitle()}</span>
          {isLoading && <Loader2 className="w-4 h-4 animate-spin text-primary" />}
        </div>
        <button
          onClick={() => setExpanded(false)}
          className="p-1.5 hover:bg-muted rounded-md transition-colors"
          aria-label="Collapse drawer"
        >
          <X className="w-4 h-4" />
        </button>
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
          {selectedProject ? (
            <FolderOpen className="w-3 h-3 text-primary" />
          ) : (
            <User className="w-3 h-3 text-muted-foreground" />
          )}
          <select
            value={selectedProject?.id || ''}
            onChange={(e) => {
              const projectId = e.target.value;
              if (!projectId) {
                setSelectedProject(null);
              } else {
                const project = projects.find((p) => p.id === projectId);
                if (project) {
                  setSelectedProject({ id: project.id, name: project.name });
                }
              }
            }}
            className={cn(
              'bg-transparent border-none cursor-pointer text-xs',
              'focus:outline-none focus:ring-0',
              selectedProject ? 'text-primary' : 'text-muted-foreground'
            )}
          >
            <option value="">Personal</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
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

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 && !isLoading && (
          <div className="text-center py-8">
            <MessageCircle className="w-10 h-10 text-muted-foreground/20 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">
              Ask anything or type <code className="bg-muted px-1 rounded">/</code> for skills
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              'text-sm rounded-lg p-2.5',
              msg.role === 'user' ? 'bg-primary/10 ml-6' : 'bg-muted mr-6'
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
          <div className="space-y-2 bg-muted rounded-lg p-3">
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
      <div className="p-3 border-t border-border shrink-0">
        <div className="relative">
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
              className="flex-1 px-3 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-3 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              aria-label="Send"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile FAB */}
      <MobileFAB />

      {/* Desktop collapsed tab */}
      <DesktopTab />

      {/* Mobile: Full-screen overlay */}
      <div
        className={cn(
          'md:hidden fixed inset-0 z-50 bg-background',
          'transition-transform duration-300 ease-out',
          expanded ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        <DrawerContent />
      </div>

      {/* Desktop: Right panel */}
      <div
        className={cn(
          'hidden md:block',
          'h-full border-l border-border',
          'transition-all duration-300 ease-out',
          expanded ? 'w-[360px]' : 'w-0 overflow-hidden'
        )}
      >
        {expanded && <DrawerContent />}
      </div>
    </>
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
