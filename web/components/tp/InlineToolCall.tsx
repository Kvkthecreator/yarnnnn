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
import Link from 'next/link';
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
  Bell,
  Globe,
  Bookmark,
  Monitor,
  Sparkles,
  FolderSearch,
  Brain,
  ArrowRight,
} from 'lucide-react';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { NotificationCard } from '@/components/tp/NotificationCard';
import { SystemCard } from '@/components/tp/SystemCard';
import { MessageBlock } from '@/types/desk';
import { cn, getToolDisplayMessage } from '@/lib/utils';
import { stripSnapshotMeta, stripOnboardingMeta } from '@/lib/snapshot-meta';

interface InlineToolCallProps {
  block: Extract<MessageBlock, { type: 'tool_call' }>;
}

const TOOL_ICONS: Record<string, React.ElementType> = {
  // Entity layer (ADR-168 Commit 4: renamed from Read/List/Search/Edit)
  LookupEntity: Eye,
  ListEntities: List,
  SearchEntities: Search,
  EditEntity: Pencil,
  Todo: ListTodo,
  Respond: FileText,
  Clarify: FileText,
  // Agent lifecycle (ADR-156, ADR-235 D2: lifecycle-only — no chat 'create')
  ManageAgent: Sparkles,
  // Recurrence lifecycle (ADR-235 D1.c: replaces UpdateContext(target='recurrence'))
  ManageRecurrence: Play,
  // Domain management (ADR-155)
  ManageDomains: Sparkles,
  // Inference-merged writes (ADR-235 D1.a: replaces UpdateContext(target='identity'|'brand'|'workspace'))
  InferContext: Bookmark,
  InferWorkspace: Sparkles,
  // FireInvocation (ADR-231 D5: manual fire, replaces ManageTask(action='trigger'))
  FireInvocation: Play,
  // ADR-235: legacy entries — UpdateContext + ManageTask retained for historical
  // run logs (tool_history snapshots in archived sessions). Live runtime no
  // longer dispatches these names.
  UpdateContext: Bookmark,
  ManageTask: Play,
  GetSystemState: Monitor,
  WebSearch: Globe,
  web_search: Globe,
  // Platform tools
  list_integrations: Eye,
  list_platform_resources: List,
  sync_platform_resource: Play,
  get_sync_status: Eye,
  // File layer (ADR-106, ADR-168 Commit 4: renamed from ReadWorkspace/etc.)
  ReadFile: Eye,
  WriteFile: Plus,
  SearchFiles: FolderSearch,
  QueryKnowledge: Brain,
  ListFiles: List,
  DiscoverAgents: Search,
  ReadAgentFile: Eye,
  // Notification
  send_notification: Bell,
  todo_write: ListTodo,
};

interface InlineToolCallOptions {
  /**
   * If true, renders as Claude Code-style single line: [Using X...] done
   * If false, renders as expandable card (legacy)
   */
  compact?: boolean;
}

export function InlineToolCall({ block, compact = true }: InlineToolCallProps & InlineToolCallOptions) {
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

  // Claude Code-style compact display with expandable details
  if (compact) {
    const isRunning = block.status === 'pending';
    const errorMsg = block.result?.data?.error as string | undefined;
    // ADR-144: Navigation link from ui_action
    const navAction = block.result?.uiAction?.type === 'NAVIGATE' ? block.result.uiAction.data : null;
    const navUrl = navAction?.url as string | undefined;
    const navLabel = navAction?.label as string | undefined;

    // Show details by default for completed calls
    const hasInput = block.input && Object.keys(block.input).length > 0;
    const hasResult = block.result?.data && Object.keys(block.result.data).length > 0;
    const hasDetails = hasInput || hasResult;

    return (
      <div className="my-0.5">
        <button
          onClick={() => hasDetails && setExpanded(!expanded)}
          className={cn(
            'inline-flex items-center gap-1.5 text-xs font-mono py-0.5',
            hasDetails && 'cursor-pointer hover:text-foreground',
            isRunning && 'text-muted-foreground',
            block.status === 'success' && 'text-muted-foreground',
            block.status === 'failed' && 'text-destructive'
          )}
        >
          {hasDetails && (
            <ChevronRight className={cn('w-3 h-3 text-muted-foreground/40 transition-transform', expanded && 'rotate-90')} />
          )}
          {isRunning && (
            <>
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Using {displayMessage}...</span>
            </>
          )}
          {block.status === 'success' && (
            <>
              <span>Using {displayMessage}...</span>
              <CheckCircle2 className="w-3 h-3 text-green-500" />
              <span className="text-green-600">done</span>
            </>
          )}
          {block.status === 'failed' && (
            <>
              <span>Using {displayMessage}...</span>
              <XCircle className="w-3 h-3" />
              <span>{errorMsg ? `failed: ${errorMsg.slice(0, 40)}${errorMsg.length > 40 ? '...' : ''}` : 'failed'}</span>
            </>
          )}
        </button>

        {/* Expanded details */}
        {expanded && hasDetails && (
          <div className="ml-4 mt-1 mb-2 text-[11px] font-mono space-y-1.5 border-l-2 border-border/40 pl-3">
            {hasInput && (
              <pre className="text-muted-foreground/70 whitespace-pre-wrap break-all max-h-48 overflow-y-auto">
                {JSON.stringify(block.input, null, 2)}
              </pre>
            )}
            {hasResult && block.result?.data?.message ? (
              <p className="text-muted-foreground/50">→ {String(block.result.data.message)}</p>
            ) : null}
            {hasResult && block.result?.data?.error ? (
              <p className="text-destructive/70">→ {String(block.result.data.error)}</p>
            ) : null}
          </div>
        )}

        {block.status === 'success' && navUrl && (
          <Link
            href={navUrl}
            className="inline-flex items-center gap-1 text-[10px] text-primary hover:text-primary/80 font-medium mt-0.5 ml-1"
          >
            {navLabel || 'View'} <ArrowRight className="w-2.5 h-2.5" />
          </Link>
        )}
      </div>
    );
  }

  // Legacy expandable card display
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
 *
 * @param compact - If true, tool calls render as Claude Code-style single line indicators
 */
export function MessageBlocks({ blocks, compact = true }: { blocks: MessageBlock[]; compact?: boolean }) {
  return (
    <div className="space-y-1">
      {blocks.map((block, i) => {
        switch (block.type) {
          case 'text': {
            // ADR-215 Phase 6: strip snapshot marker; ADR-190: strip retired
            // onboarding marker from historical messages (display hygiene).
            const stripped = stripOnboardingMeta(stripSnapshotMeta(block.content));
            return stripped ? (
              <MarkdownRenderer key={i} content={stripped} compact />
            ) : null;
          }
          case 'thinking':
            return <ThinkingBlock key={i} content={block.content} />;
          case 'tool_call':
            return <InlineToolCall key={i} block={block} compact={compact} />;
          case 'clarify':
            // Clarify is handled separately in the chat UI
            return null;
          case 'notification':
            return <NotificationCard key={i} title={block.title} description={block.description} toolName={block.toolName} />;
          case 'system_card':
            return <SystemCard key={i} card_type={block.card_type} data={block.data} />;
          default:
            return null;
        }
      })}
    </div>
  );
}
