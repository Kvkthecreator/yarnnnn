'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * ADR-034: Context v2 - Domain-based context scoping
 *
 * ContextBrowserSurface - Browse memories/context with source-first design
 *
 * Source-first layout (ADR-034 refactor):
 * - All memories displayed in a single view
 * - Grouped by platform source (Slack, Gmail, Notion, Manual)
 * - Domain filter only shown when multiple non-default domains exist
 *
 * Features:
 * - Search filtering across content and tags
 * - Platform grouping for easy navigation
 * - Tags displayed inline on each memory card
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Loader2,
  Plus,
  Edit,
  Trash2,
  Search,
  X,
  Hash,
  Mail,
  FileText,
  PenLine,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { useTP } from '@/contexts/TPContext';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import type { Memory, ContextDomainSummary } from '@/types';

interface ContextBrowserSurfaceProps {
  scope?: 'user' | 'deliverable' | 'domain';
  scopeId?: string;
}

// Platform source type for grouping
type PlatformSource = 'slack' | 'notion' | 'gmail' | 'manual';

// Platform configuration for display
const PLATFORM_CONFIG: Record<PlatformSource, {
  icon: React.ReactNode;
  label: string;
  color: string;
  bgColor: string;
}> = {
  slack: {
    icon: <Hash className="w-4 h-4" />,
    label: 'Slack',
    color: 'text-[#4A154B] dark:text-[#E01E5A]',
    bgColor: 'bg-[#4A154B]/10 dark:bg-[#4A154B]/20',
  },
  notion: {
    icon: <FileText className="w-4 h-4" />,
    label: 'Notion',
    color: 'text-black dark:text-white',
    bgColor: 'bg-black/5 dark:bg-white/10',
  },
  gmail: {
    icon: <Mail className="w-4 h-4" />,
    label: 'Gmail',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-500/10',
  },
  manual: {
    icon: <PenLine className="w-4 h-4" />,
    label: 'Added manually',
    color: 'text-muted-foreground',
    bgColor: 'bg-muted/50',
  },
};

// Get platform source from a memory
function getMemorySource(memory: Memory): PlatformSource {
  if (memory.source_type === 'import' && memory.source_ref?.platform) {
    const platform = memory.source_ref.platform as string;
    if (platform === 'slack' || platform === 'notion' || platform === 'gmail') {
      return platform;
    }
  }
  return 'manual';
}

// Source badge for imported memories - shows resource name
function SourceBadge({ memory }: { memory: Memory }) {
  // Only show resource name for imported memories
  if (memory.source_type !== 'import' || !memory.source_ref?.resource_name) {
    return null;
  }

  return (
    <span
      className="text-[10px] text-muted-foreground/70"
      title={memory.source_ref.resource_name}
    >
      from {memory.source_ref.resource_name}
    </span>
  );
}

// Memory card component for consistent rendering
function MemoryCard({
  memory,
  onEdit,
  onDelete,
  isDeleting,
}: {
  memory: Memory;
  onEdit: () => void;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  return (
    <div className="group p-3 border border-border rounded-lg bg-background hover:border-border/80 transition-colors">
      {/* Content */}
      <p className="text-sm leading-relaxed whitespace-pre-wrap">{memory.content}</p>

      {/* Footer: source + tags + meta + actions */}
      <div className="mt-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0 flex-1 flex-wrap">
          {/* Source badge (for imports) */}
          <SourceBadge memory={memory} />

          {/* Tags (all of them) */}
          {memory.tags && memory.tags.length > 0 && (
            <div className="flex items-center gap-1 flex-wrap">
              {memory.tags.map((tag, i) => (
                <span
                  key={i}
                  className="px-1.5 py-0.5 text-[10px] rounded bg-muted text-muted-foreground"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Timestamp */}
          <span className="text-[10px] text-muted-foreground/60 shrink-0">
            {formatDistanceToNow(new Date(memory.created_at), { addSuffix: true })}
          </span>
        </div>

        {/* Actions - visible on hover */}
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          <button
            onClick={onEdit}
            className="p-1 hover:bg-muted rounded"
            title="Edit"
          >
            <Edit className="w-3 h-3 text-muted-foreground" />
          </button>
          <button
            onClick={onDelete}
            disabled={isDeleting}
            className="p-1 hover:bg-muted rounded"
            title="Delete"
          >
            {isDeleting ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Trash2 className="w-3 h-3 text-muted-foreground hover:text-red-500" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// Collapsible platform group component
function PlatformGroup({
  platform,
  memories,
  onEdit,
  onDelete,
  deletingId,
  defaultExpanded = true,
}: {
  platform: PlatformSource;
  memories: Memory[];
  onEdit: (memoryId: string) => void;
  onDelete: (memoryId: string) => void;
  deletingId: string | null;
  defaultExpanded?: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const config = PLATFORM_CONFIG[platform];

  if (memories.length === 0) return null;

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      {/* Group header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'w-full flex items-center gap-2 px-3 py-2 text-sm font-medium',
          'hover:bg-muted/50 transition-colors',
          config.bgColor
        )}
      >
        {isExpanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
        )}
        <span className={config.color}>{config.icon}</span>
        <span>{config.label}</span>
        <span className="text-xs text-muted-foreground ml-auto">
          {memories.length}
        </span>
      </button>

      {/* Memory cards */}
      {isExpanded && (
        <div className="p-2 space-y-2 bg-background">
          {memories.map((memory) => (
            <MemoryCard
              key={memory.id}
              memory={memory}
              onEdit={() => onEdit(memory.id)}
              onDelete={() => onDelete(memory.id)}
              isDeleting={deletingId === memory.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}


export function ContextBrowserSurface({ scope, scopeId }: ContextBrowserSurfaceProps) {
  const { setSurface } = useDesk();
  const { sendMessage } = useTP();

  const [loading, setLoading] = useState(true);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Domain state (only used when multiple non-default domains exist)
  const [domains, setDomains] = useState<ContextDomainSummary[]>([]);
  const [selectedDomainId, setSelectedDomainId] = useState<string | null>(null);

  // Load all memories (user + domain memories combined)
  const loadMemories = useCallback(async () => {
    setLoading(true);
    try {
      // Load user memories (personal/default domain)
      const userMemories = await api.userMemories.list();

      // Load domains to check if we need domain filtering
      const domainsResult = await api.domains.list();
      setDomains(domainsResult.domains);

      // Combine all memories - user memories are the primary source
      // Domain-scoped memories would come from specific domain if selected
      let allMemories = [...userMemories];

      // If a specific domain is selected, load its memories too
      if (selectedDomainId) {
        const domainMemories = await api.domains.memories.list(selectedDomainId);
        // Merge, avoiding duplicates by id
        const existingIds = new Set(allMemories.map(m => m.id));
        domainMemories.forEach(m => {
          if (!existingIds.has(m.id)) {
            allMemories.push(m);
          }
        });
      }

      setMemories(allMemories);
    } catch (err) {
      console.error('Failed to load memories:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedDomainId]);

  useEffect(() => {
    loadMemories();
  }, [loadMemories]);

  // Filter memories by search query
  const filteredMemories = useMemo(() => {
    if (!searchQuery.trim()) return memories;

    const query = searchQuery.toLowerCase();
    return memories.filter(
      (m) =>
        m.content.toLowerCase().includes(query) ||
        m.tags?.some((t) => t.toLowerCase().includes(query)) ||
        m.source_ref?.resource_name?.toLowerCase().includes(query)
    );
  }, [memories, searchQuery]);

  // Group memories by platform source
  const groupedMemories = useMemo(() => {
    const groups: Record<PlatformSource, Memory[]> = {
      slack: [],
      notion: [],
      gmail: [],
      manual: [],
    };

    filteredMemories.forEach((memory) => {
      const source = getMemorySource(memory);
      groups[source].push(memory);
    });

    return groups;
  }, [filteredMemories]);

  // Calculate counts per platform
  const platformCounts = useMemo(() => {
    return {
      slack: groupedMemories.slack.length,
      notion: groupedMemories.notion.length,
      gmail: groupedMemories.gmail.length,
      manual: groupedMemories.manual.length,
    };
  }, [groupedMemories]);

  // Determine platform order (non-empty first, manual last)
  const platformOrder = useMemo(() => {
    const order: PlatformSource[] = [];
    if (platformCounts.slack > 0) order.push('slack');
    if (platformCounts.notion > 0) order.push('notion');
    if (platformCounts.gmail > 0) order.push('gmail');
    if (platformCounts.manual > 0) order.push('manual');
    return order;
  }, [platformCounts]);

  const handleEdit = (memoryId: string) => {
    setSurface({ type: 'context-editor', memoryId });
  };

  const handleDelete = async (memoryId: string) => {
    if (!confirm('Are you sure you want to delete this memory?')) return;

    setDeleting(memoryId);
    try {
      await api.memories.delete(memoryId);
      setMemories((prev) => prev.filter((m) => m.id !== memoryId));
    } catch (err) {
      console.error('Failed to delete memory:', err);
      alert('Failed to delete memory');
    } finally {
      setDeleting(null);
    }
  };

  const totalCount = memories.length;
  const filteredCount = filteredMemories.length;
  const nonDefaultDomains = domains.filter((d) => !d.is_default);

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-6 py-6">
        {/* Header with search */}
        <div className="flex items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-medium">Context</h1>
            {!loading && totalCount > 0 && (
              <span className="text-sm text-muted-foreground">
                {filteredCount === totalCount ? totalCount : `${filteredCount} of ${totalCount}`}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 flex-1 max-w-sm">
            {/* Search input */}
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search memories..."
                className="w-full pl-8 pr-8 py-1.5 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-primary/30"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 hover:bg-muted rounded"
                >
                  <X className="w-3 h-3 text-muted-foreground" />
                </button>
              )}
            </div>
            <button
              onClick={() => sendMessage("I'd like to add something to my memory")}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted shrink-0"
            >
              <Plus className="w-3.5 h-3.5" />
              Add
            </button>
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : totalCount === 0 ? (
          <div className="text-center py-12 border border-dashed border-border rounded-lg">
            <PenLine className="w-8 h-8 mx-auto text-muted-foreground/50 mb-2" />
            <p className="text-muted-foreground mb-2">No memories yet</p>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Tell TP things you want it to remember — your preferences, company info,
              writing style, or any context that helps it understand you better.
            </p>
          </div>
        ) : filteredMemories.length === 0 ? (
          <div className="text-center py-12 border border-dashed border-border rounded-lg">
            <Search className="w-8 h-8 mx-auto text-muted-foreground/50 mb-2" />
            <p className="text-muted-foreground">No memories match your search</p>
          </div>
        ) : (
          <div className="space-y-4">
            {platformOrder.map((platform) => (
              <PlatformGroup
                key={platform}
                platform={platform}
                memories={groupedMemories[platform]}
                onEdit={handleEdit}
                onDelete={handleDelete}
                deletingId={deleting}
              />
            ))}
          </div>
        )}

        {/* Footer */}
        {!loading && totalCount > 0 && (
          <p className="mt-6 text-xs text-muted-foreground text-center">
            TP uses your context to personalize responses
          </p>
        )}
      </div>
    </div>
  );
}
