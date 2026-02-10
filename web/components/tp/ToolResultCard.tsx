'use client';

/**
 * ADR-037: Chat-First Surface
 * ToolResultCard - Claude Code-style inline tool result display
 *
 * Maps primitives to visual representations:
 * - Read: Entity card with key fields
 * - Write: Confirmation with preview
 * - Edit: Change summary (before → after)
 * - List: Compact entity list
 * - Search: Results with match info
 * - Execute: Action result card
 * - Todo: Progress indicator
 * - Respond/Clarify: Handled separately in chat
 */

import { CheckCircle2, XCircle, FileText, Plus, Pencil, List, Search, Play, ListTodo } from 'lucide-react';
import { TPToolResult } from '@/types/desk';
import { cn } from '@/lib/utils';

interface ToolResultCardProps {
  result: TPToolResult;
  compact?: boolean;
}

const PRIMITIVE_ICONS: Record<string, React.ElementType> = {
  Read: FileText,
  Write: Plus,
  Edit: Pencil,
  List: List,
  Search: Search,
  Execute: Play,
  Todo: ListTodo,
};

/**
 * Render entity preview based on YARNNN entity type
 */
function renderEntityPreview(entity: Record<string, unknown>, entityType?: string): React.ReactNode {
  switch (entityType) {
    case 'deliverable': {
      const schedule = entity.schedule as Record<string, unknown> | undefined;
      const frequency = schedule?.frequency as string;
      return (
        <div className="space-y-1">
          <div className="font-medium">{String(entity.title || 'Untitled')}</div>
          <div className="flex gap-2 text-xs">
            {entity.status && (
              <span className={cn(
                "px-1.5 py-0.5 rounded",
                entity.status === 'active' ? "bg-green-500/10 text-green-600" :
                entity.status === 'paused' ? "bg-yellow-500/10 text-yellow-600" :
                "bg-muted text-muted-foreground"
              )}>
                {String(entity.status)}
              </span>
            )}
            {frequency && (
              <span className="text-muted-foreground">{frequency}</span>
            )}
          </div>
        </div>
      );
    }

    case 'memory': {
      const content = String(entity.content || '');
      const tags = entity.tags as string[] | undefined;
      return (
        <div className="space-y-1">
          <div className="text-sm line-clamp-2">{content}</div>
          {tags && tags.length > 0 && (
            <div className="flex gap-1 flex-wrap">
              {tags.slice(0, 3).map((tag, i) => (
                <span key={i} className="px-1.5 py-0.5 text-xs bg-muted rounded">{tag}</span>
              ))}
            </div>
          )}
        </div>
      );
    }

    case 'platform': {
      return (
        <div className="space-y-1">
          <div className="font-medium capitalize">{String(entity.provider || 'Platform')}</div>
          {entity.status && (
            <span className={cn(
              "text-xs px-1.5 py-0.5 rounded",
              entity.status === 'connected' ? "bg-green-500/10 text-green-600" : "bg-muted"
            )}>
              {String(entity.status)}
            </span>
          )}
        </div>
      );
    }

    case 'work': {
      return (
        <div className="space-y-1">
          <div className="text-sm">{String(entity.description || 'Work task')}</div>
          {entity.status && (
            <span className="text-xs text-muted-foreground">{String(entity.status)}</span>
          )}
        </div>
      );
    }

    default: {
      // Generic fallback
      return (
        <div className="space-y-1">
          {entity.title && <div className="font-medium">{String(entity.title)}</div>}
          {entity.name && <div className="font-medium">{String(entity.name)}</div>}
          {entity.content && <div className="text-sm line-clamp-2">{String(entity.content)}</div>}
          {entity.status && (
            <div className="text-xs text-muted-foreground">
              Status: <span className="text-foreground">{String(entity.status)}</span>
            </div>
          )}
        </div>
      );
    }
  }
}

export function ToolResultCard({ result, compact = false }: ToolResultCardProps) {
  const { toolName, success, data } = result;

  // Skip Respond/Clarify - these are handled as chat messages
  if (toolName === 'Respond' || toolName === 'Clarify') {
    return null;
  }

  const Icon = PRIMITIVE_ICONS[toolName] || FileText;
  const StatusIcon = success ? CheckCircle2 : XCircle;

  // Extract display data based on primitive type
  const displayData = getDisplayData(toolName, data);

  if (compact) {
    return (
      <div className={cn(
        "inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs",
        success ? "bg-muted text-muted-foreground" : "bg-destructive/10 text-destructive"
      )}>
        <Icon className="w-3 h-3" />
        <span>{toolName}</span>
        <StatusIcon className="w-3 h-3" />
      </div>
    );
  }

  return (
    <div className={cn(
      "rounded-lg border text-sm overflow-hidden",
      success ? "border-border bg-muted/30" : "border-destructive/50 bg-destructive/5"
    )}>
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border/50 bg-muted/20">
        <Icon className="w-4 h-4 text-muted-foreground" />
        <span className="font-medium">{toolName}</span>
        <StatusIcon className={cn(
          "w-4 h-4 ml-auto",
          success ? "text-green-500" : "text-destructive"
        )} />
      </div>

      {/* Body */}
      <div className="px-3 py-2">
        {displayData.content}
      </div>
    </div>
  );
}

/**
 * Extract display-friendly data from tool result
 *
 * YARNNN Entity Types:
 * - deliverable: title, status, schedule (frequency), recipient_context
 * - memory: content, tags, importance
 * - platform: provider, status
 * - document: filename, content_type
 * - work: description, status
 */
function getDisplayData(toolName: string, data?: Record<string, unknown>): { content: React.ReactNode } {
  if (!data) {
    return { content: <span className="text-muted-foreground">No data</span> };
  }

  switch (toolName) {
    case 'Read': {
      // Entity read - show key fields based on entity type
      // Backend returns {success, data: <entity>, entity_type, message}
      const entity = data.data as Record<string, unknown> | undefined;
      const entityType = data.entity_type as string;

      if (entity) {
        return {
          content: renderEntityPreview(entity, entityType),
        };
      }
      return { content: <span className="text-muted-foreground">{data.message as string || 'Entity read'}</span> };
    }

    case 'Write': {
      // Entity created - show confirmation
      // Backend returns {success, data: <entity>, entity_type, message}
      const created = data.data as Record<string, unknown> | undefined;
      const entityType = data.entity_type as string || 'entity';
      return {
        content: (
          <div className="space-y-1">
            <div className="text-green-600 dark:text-green-400">
              Created {entityType}
            </div>
            {created?.title && <div className="text-xs">{String(created.title)}</div>}
            {created?.id && (
              <div className="text-xs text-muted-foreground font-mono">
                {String(created.id).slice(0, 8)}...
              </div>
            )}
          </div>
        ),
      };
    }

    case 'Edit': {
      // Entity edited - show changes
      // Backend returns {success, data, changes_applied: ["field1", "field2"], message}
      const changesApplied = data.changes_applied as string[] | undefined;
      const entity = data.data as Record<string, unknown> | undefined;
      const entityType = data.entity_type as string;

      if (changesApplied && changesApplied.length > 0 && entity) {
        return {
          content: (
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">
                Updated {entityType || 'entity'}
              </div>
              {changesApplied.filter(f => f !== 'updated_at').map((field) => (
                <div key={field} className="text-xs">
                  <span className="text-muted-foreground">{field}:</span>{' '}
                  <span className="text-green-600 dark:text-green-400">
                    {String(entity[field] ?? '(set)')}
                  </span>
                </div>
              ))}
            </div>
          ),
        };
      }
      return { content: <span className="text-muted-foreground">{data.message as string || 'Entity updated'}</span> };
    }

    case 'List': {
      // Entity list - show compact grid with entity-type awareness
      // Backend returns {success, items: [...], count, entity_type}
      const entities = (data.items || data.entities) as Array<Record<string, unknown>> | undefined;
      const entityType = data.entity_type as string;
      const count = data.count as number || entities?.length || 0;

      if (entities && entities.length > 0) {
        return {
          content: (
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground">
                {count} {entityType || 'result'}{count !== 1 ? 's' : ''}
              </div>
              <div className="space-y-1">
                {entities.slice(0, 4).map((e, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    {/* Deliverable-specific display */}
                    {entityType === 'deliverable' && (
                      <>
                        <span className={cn(
                          "w-2 h-2 rounded-full",
                          e.status === 'active' ? "bg-green-500" :
                          e.status === 'paused' ? "bg-yellow-500" : "bg-muted"
                        )} />
                        <span className="font-medium">{String(e.title)}</span>
                        {(e.schedule as Record<string, unknown>)?.frequency && (
                          <span className="text-muted-foreground">
                            ({String((e.schedule as Record<string, unknown>).frequency)})
                          </span>
                        )}
                      </>
                    )}
                    {/* Platform-specific display */}
                    {entityType === 'platform' && (
                      <>
                        <span className={cn(
                          "w-2 h-2 rounded-full",
                          e.status === 'connected' ? "bg-green-500" : "bg-muted"
                        )} />
                        <span className="font-medium capitalize">{String(e.provider)}</span>
                      </>
                    )}
                    {/* Memory-specific display */}
                    {entityType === 'memory' && (
                      <span className="line-clamp-1">{String(e.content).slice(0, 60)}...</span>
                    )}
                    {/* Generic fallback */}
                    {!['deliverable', 'platform', 'memory'].includes(entityType || '') && (
                      <span>{String(e.title || e.name || e.content?.toString().slice(0, 40) || `Item ${i + 1}`)}</span>
                    )}
                  </div>
                ))}
                {entities.length > 4 && (
                  <div className="text-xs text-muted-foreground pl-4">
                    +{entities.length - 4} more
                  </div>
                )}
              </div>
            </div>
          ),
        };
      }
      return { content: <span className="text-muted-foreground">{count} {entityType || 'entities'}</span> };
    }

    case 'Search': {
      // Search results
      const results = data.results as Array<Record<string, unknown>> | undefined;
      const query = data.query as string;
      if (results && results.length > 0) {
        return {
          content: (
            <div className="space-y-1">
              {query && <div className="text-xs text-muted-foreground">Query: "{query}"</div>}
              <div className="text-xs">{results.length} match{results.length !== 1 ? 'es' : ''}</div>
            </div>
          ),
        };
      }
      return { content: <span className="text-muted-foreground">No results</span> };
    }

    case 'Execute': {
      // Action execution
      const action = data.action as string;
      const message = data.message as string;
      return {
        content: (
          <div className="space-y-1">
            {action && <div className="font-mono text-xs">{action}</div>}
            {message && <div className="text-xs text-muted-foreground">{message}</div>}
          </div>
        ),
      };
    }

    case 'Todo': {
      // Todo update - show progress
      const todos = data.todos as Array<{ content: string; status: string }> | undefined;
      if (todos) {
        const completed = todos.filter(t => t.status === 'completed').length;
        const total = todos.length;
        return {
          content: (
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all"
                    style={{ width: `${(completed / total) * 100}%` }}
                  />
                </div>
                <span className="text-xs text-muted-foreground">{completed}/{total}</span>
              </div>
            </div>
          ),
        };
      }
      return { content: <span className="text-muted-foreground">Todos updated</span> };
    }

    default:
      // Generic fallback
      if (data.message) {
        return { content: <span>{String(data.message)}</span> };
      }
      return { content: <span className="text-muted-foreground">Action completed</span> };
  }
}

/**
 * Render multiple tool results inline
 */
export function ToolResultList({ results, compact = true }: { results: TPToolResult[]; compact?: boolean }) {
  // Filter out Respond/Clarify which are handled as chat
  const displayable = results.filter(r => r.toolName !== 'Respond' && r.toolName !== 'Clarify');

  if (displayable.length === 0) return null;

  if (compact) {
    return (
      <div className="flex flex-wrap gap-1.5 mt-2">
        {displayable.map((result, i) => (
          <ToolResultCard key={i} result={result} compact />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-2 mt-2">
      {displayable.map((result, i) => (
        <ToolResultCard key={i} result={result} />
      ))}
    </div>
  );
}
