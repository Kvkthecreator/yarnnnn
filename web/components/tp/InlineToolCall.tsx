'use client';

/**
 * ADR-042: Streaming Process Visibility
 * Inline tool call display - shows tool execution as it happens
 *
 * States:
 * - pending: Tool is executing (spinner)
 * - success: Tool completed successfully (checkmark)
 * - failed: Tool failed (X, auto-expand to show error)
 */

import { useState } from 'react';
import {
  Loader2,
  CheckCircle2,
  XCircle,
  ChevronRight,
  FileText,
  Plus,
  Pencil,
  List,
  Search,
  Play,
  ListTodo,
  Eye,
} from 'lucide-react';
import { MessageBlock } from '@/types/desk';
import { cn, getToolDisplayMessage } from '@/lib/utils';

interface InlineToolCallProps {
  block: Extract<MessageBlock, { type: 'tool_call' }>;
}

const TOOL_ICONS: Record<string, React.ElementType> = {
  // Legacy primitive tools
  Read: Eye,
  Write: Plus,
  Edit: Pencil,
  List: List,
  Search: Search,
  Execute: Play,
  Todo: ListTodo,
  Respond: FileText,
  Clarify: FileText,
  // ADR-039: Platform operation tools
  list_integrations: Eye,
  list_platform_resources: List,
  sync_platform_resource: Play,
  get_sync_status: Eye,
  // Work tools
  create_work: Plus,
  list_work: List,
  get_work: Eye,
  update_work: Pencil,
  delete_work: FileText,
  // Memory tools
  list_memories: List,
  create_memory: Plus,
  update_memory: Pencil,
  delete_memory: FileText,
  // Deliverable tools
  list_deliverables: List,
  get_deliverable: Eye,
  create_deliverable: Plus,
  update_deliverable: Pencil,
  run_deliverable: Play,
  // Todo tracking
  todo_write: ListTodo,
};

export function InlineToolCall({ block }: InlineToolCallProps) {
  const [expanded, setExpanded] = useState(block.status === 'failed');

  const Icon = TOOL_ICONS[block.tool] || FileText;
  // ADR-039: Use descriptive display message
  const displayMessage = getToolDisplayMessage(block.tool, block.input);

  // Skip Respond/Clarify - these are handled as chat messages
  if (block.tool === 'Respond' || block.tool === 'Clarify' || block.tool === 'respond' || block.tool === 'clarify') {
    return null;
  }

  // Skip todo_write - this is shown separately in the work panel
  if (block.tool === 'todo_write') {
    return null;
  }

  return (
    <div className={cn(
      'rounded-lg border text-sm overflow-hidden my-1.5 transition-all',
      block.status === 'pending' && 'border-primary/30 bg-primary/5',
      block.status === 'success' && 'border-border bg-muted/30',
      block.status === 'failed' && 'border-destructive/50 bg-destructive/5'
    )}>
      {/* Header - always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-muted/50 transition-colors text-left"
      >
        <ChevronRight className={cn(
          'w-3 h-3 text-muted-foreground transition-transform shrink-0',
          expanded && 'rotate-90'
        )} />

        <Icon className="w-4 h-4 text-muted-foreground shrink-0" />

        {/* ADR-039: Show descriptive message instead of raw tool name */}
        <span className="font-medium">{displayMessage}</span>

        {/* Status indicator */}
        <div className="shrink-0 ml-auto">
          {block.status === 'pending' && (
            <Loader2 className="w-4 h-4 animate-spin text-primary" />
          )}
          {block.status === 'success' && (
            <CheckCircle2 className="w-4 h-4 text-green-500" />
          )}
          {block.status === 'failed' && (
            <XCircle className="w-4 h-4 text-destructive" />
          )}
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-3 py-2 border-t border-border/50 bg-muted/20 text-xs space-y-2">
          {/* Input */}
          {block.input && Object.keys(block.input).length > 0 && (
            <div>
              <div className="text-muted-foreground mb-1">Input:</div>
              <pre className="bg-background/50 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
                {JSON.stringify(block.input, null, 2)}
              </pre>
            </div>
          )}

          {/* Result */}
          {block.result && (
            <div>
              <div className="text-muted-foreground mb-1">Result:</div>
              {block.result.data?.error ? (
                <div className="text-destructive">{String(block.result.data.error)}</div>
              ) : block.result.data?.message ? (
                <div>{String(block.result.data.message)}</div>
              ) : (
                <pre className="bg-background/50 rounded p-2 overflow-x-auto whitespace-pre-wrap break-all max-h-40 overflow-y-auto">
                  {JSON.stringify(block.result.data, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Thinking indicator block
 */
export function ThinkingBlock({ content }: { content: string }) {
  return (
    <div className="flex items-start gap-2 text-sm text-muted-foreground italic my-1.5 px-1">
      <Loader2 className="w-4 h-4 animate-spin shrink-0 mt-0.5" />
      <span>{content || 'Thinking...'}</span>
    </div>
  );
}

/**
 * Render all blocks in a message
 */
export function MessageBlocks({ blocks }: { blocks: MessageBlock[] }) {
  return (
    <div className="space-y-1">
      {blocks.map((block, i) => {
        switch (block.type) {
          case 'text':
            return block.content ? (
              <p key={i} className="whitespace-pre-wrap">{block.content}</p>
            ) : null;
          case 'thinking':
            return <ThinkingBlock key={i} content={block.content} />;
          case 'tool_call':
            return <InlineToolCall key={i} block={block} />;
          case 'clarify':
            // Clarify is handled separately in the chat UI
            return null;
          default:
            return null;
        }
      })}
    </div>
  );
}
