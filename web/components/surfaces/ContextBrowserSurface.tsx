'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * ADR-034: Context v2 - Domain-based context scoping
 *
 * ContextBrowserSurface - Browse memories/context across all domains
 *
 * Tab-based layout:
 * - "Personal" tab: User-scoped memories (default domain)
 * - Domain tabs: Browse any domain's scoped memories
 *
 * Features:
 * - Domain selector dropdown to browse any domain's context
 * - Search filtering across content and tags
 * - Tags displayed inline on each memory card
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Loader2,
  Plus,
  Edit,
  Trash2,
  User,
  Layers,
  Search,
  X,
  ChevronDown,
  Check,
  Hash,
  Mail,
  FileText,
} from 'lucide-react';
import { PlatformFilter, type PlatformFilterValue } from '@/components/ui/PlatformFilter';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { useTP } from '@/contexts/TPContext';
import { useActiveDomain } from '@/hooks/useActiveDomain';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import type { Memory, ContextDomainSummary } from '@/types';

interface ContextBrowserSurfaceProps {
  scope: 'user' | 'deliverable' | 'domain';
  scopeId?: string;
}

// Source badge for imported memories - shows platform provenance
function SourceBadge({ memory }: { memory: Memory }) {
  // Only show for imported memories with source_ref
  if (memory.source_type !== 'import' || !memory.source_ref?.platform) {
    return null;
  }

  const { platform, resource_name } = memory.source_ref;

  const platformConfig: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
    slack: {
      icon: <Hash className="w-2.5 h-2.5" />,
      color: 'bg-[#4A154B]/10 text-[#4A154B] dark:bg-[#4A154B]/20 dark:text-[#E01E5A]',
      label: resource_name || 'Slack',
    },
    notion: {
      icon: <FileText className="w-2.5 h-2.5" />,
      color: 'bg-black/5 text-black dark:bg-white/10 dark:text-white',
      label: resource_name || 'Notion',
    },
    gmail: {
      icon: <Mail className="w-2.5 h-2.5" />,
      color: 'bg-red-500/10 text-red-600 dark:text-red-400',
      label: resource_name || 'Gmail',
    },
  };

  const config = platformConfig[platform];
  if (!config) return null;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] rounded',
        config.color
      )}
      title={`Imported from ${platform}: ${resource_name || 'unknown'}`}
    >
      {config.icon}
      <span className="max-w-[80px] truncate">{config.label}</span>
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

// Memory list component
function MemoryList({
  memories,
  emptyMessage,
  onEdit,
  onDelete,
  deletingId,
}: {
  memories: Memory[];
  emptyMessage: string;
  onEdit: (memoryId: string) => void;
  onDelete: (memoryId: string) => void;
  deletingId: string | null;
}) {
  if (memories.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8">
        {emptyMessage}
      </p>
    );
  }

  return (
    <div className="space-y-2">
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
  );
}

// Domain selector dropdown component (ADR-034: Context v2)
function DomainSelector({
  domains,
  selectedDomainId,
  onSelect,
  isLoading,
}: {
  domains: ContextDomainSummary[];
  selectedDomainId: string | null;
  onSelect: (domainId: string | null) => void;
  isLoading: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter to non-default domains only
  const nonDefaultDomains = domains.filter((d) => !d.is_default);
  const selectedDomain = domains.find((d) => d.id === selectedDomainId);
  const buttonLabel = selectedDomain?.name || 'Select domain...';

  if (nonDefaultDomains.length === 0 && !isLoading) {
    return null; // Don't show selector if no non-default domains
  }

  return (
    <div ref={dropdownRef} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className={cn(
          'inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
          selectedDomainId
            ? 'border-primary text-foreground'
            : 'border-transparent text-muted-foreground hover:text-foreground'
        )}
      >
        <Layers className="w-3.5 h-3.5" />
        <span className="max-w-[120px] truncate">{buttonLabel}</span>
        <ChevronDown className={cn('w-3.5 h-3.5 transition-transform', isOpen && 'rotate-180')} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-56 bg-background border border-border rounded-md shadow-lg z-50 py-1 max-h-64 overflow-auto">
          {isLoading ? (
            <div className="px-3 py-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
              Loading...
            </div>
          ) : nonDefaultDomains.length === 0 ? (
            <div className="px-3 py-2 text-sm text-muted-foreground">
              No domains yet
            </div>
          ) : (
            nonDefaultDomains.map((domain) => (
              <button
                key={domain.id}
                onClick={() => {
                  onSelect(domain.id);
                  setIsOpen(false);
                }}
                className={cn(
                  'w-full px-3 py-2 text-sm text-left hover:bg-muted flex items-center justify-between gap-2',
                  selectedDomainId === domain.id && 'bg-muted/50'
                )}
              >
                <div className="flex flex-col min-w-0">
                  <span className="truncate">{domain.name}</span>
                  <span className="text-[10px] text-muted-foreground">
                    {domain.memory_count} memories
                  </span>
                </div>
                {selectedDomainId === domain.id && (
                  <Check className="w-3.5 h-3.5 text-primary shrink-0" />
                )}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export function ContextBrowserSurface({ scope, scopeId }: ContextBrowserSurfaceProps) {
  const { setSurface } = useDesk();
  const { sendMessage } = useTP();
  const { domain: activeDomain } = useActiveDomain();

  const [loading, setLoading] = useState(true);
  const [userMemories, setUserMemories] = useState<Memory[]>([]);
  const [scopedMemories, setScopedMemories] = useState<Memory[]>([]);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'personal' | 'scoped'>('personal');
  const [searchQuery, setSearchQuery] = useState('');
  const [platformFilter, setPlatformFilter] = useState<PlatformFilterValue>('all');

  // ADR-034: Domain selector state
  const [domains, setDomains] = useState<ContextDomainSummary[]>([]);
  const [loadingDomains, setLoadingDomains] = useState(false);
  const [selectedDomainId, setSelectedDomainId] = useState<string | null>(
    scope === 'domain' ? (scopeId ?? null) : null
  );
  const [selectedDomainName, setSelectedDomainName] = useState<string>('Domain');

  const loadedRef = useRef<string | null>(null);

  // Load user's domains for the selector
  useEffect(() => {
    async function loadDomains() {
      setLoadingDomains(true);
      try {
        const result = await api.domains.list();
        setDomains(result.domains);

        // If we have an initial scopeId, find its name
        if (scopeId && scope === 'domain') {
          const found = result.domains.find((d) => d.id === scopeId);
          if (found) {
            setSelectedDomainName(found.name);
          }
        }
      } catch (err) {
        console.error('Failed to load domains:', err);
      } finally {
        setLoadingDomains(false);
      }
    }
    loadDomains();
  }, [scope, scopeId]);

  // Auto-select domain from active context
  useEffect(() => {
    if (activeDomain && !selectedDomainId && scope !== 'domain') {
      setSelectedDomainId(activeDomain.id);
      setSelectedDomainName(activeDomain.name);
    }
  }, [activeDomain, selectedDomainId, scope]);

  // Load memories based on scope
  const loadMemories = useCallback(async () => {
    const loadKey = `${scope}:${selectedDomainId || scopeId || 'none'}`;

    // Skip if we've already loaded this exact combination
    if (loadedRef.current === loadKey && (userMemories.length > 0 || scopedMemories.length > 0)) {
      return;
    }

    setLoading(true);
    try {
      // Always load user memories for personal context
      const userData = await api.userMemories.list();
      setUserMemories(userData);

      // Load scoped memories based on selected domain
      if (selectedDomainId) {
        const domainData = await api.domains.memories.list(selectedDomainId);
        setScopedMemories(domainData);

        // Update domain name
        const found = domains.find((d) => d.id === selectedDomainId);
        if (found) {
          setSelectedDomainName(found.name);
        }
      } else if (scope === 'deliverable' && scopeId) {
        // Deliverable scope: get deliverable's domain
        const domainResult = await api.domains.getActive(scopeId);
        if (domainResult.domain) {
          const domainData = await api.domains.memories.list(domainResult.domain.id);
          setScopedMemories(domainData);
          setSelectedDomainId(domainResult.domain.id);
          setSelectedDomainName(domainResult.domain.name);
        } else {
          setScopedMemories([]);
        }
      } else {
        setScopedMemories([]);
      }

      loadedRef.current = loadKey;
    } catch (err) {
      console.error('Failed to load memories:', err);
    } finally {
      setLoading(false);
    }
  }, [scope, scopeId, selectedDomainId, domains, userMemories.length, scopedMemories.length]);

  useEffect(() => {
    loadMemories();
  }, [loadMemories]);

  // Handle domain selection change
  const handleDomainSelect = useCallback((domainId: string | null) => {
    setSelectedDomainId(domainId);
    loadedRef.current = null; // Force reload
    if (domainId) {
      setActiveTab('scoped');
    }
  }, []);

  // Filter memories by search query and platform
  const filterMemories = useCallback(
    (memories: Memory[]) => {
      let filtered = memories;

      // Platform filter (ADR-033 Phase 3)
      if (platformFilter !== 'all') {
        // Filter by specific platform
        filtered = filtered.filter(
          (m) => m.source_type === 'import' && m.source_ref?.platform === platformFilter
        );
      }

      // Search query filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        filtered = filtered.filter(
          (m) =>
            m.content.toLowerCase().includes(query) ||
            m.tags?.some((t) => t.toLowerCase().includes(query)) ||
            m.source_ref?.resource_name?.toLowerCase().includes(query)
        );
      }

      return filtered;
    },
    [searchQuery, platformFilter]
  );

  // Calculate platform counts for filter (ADR-033 Phase 3)
  const getPlatformCounts = useCallback((memories: Memory[]) => {
    const counts: Partial<Record<PlatformFilterValue, number>> = { all: memories.length };
    memories.forEach((m) => {
      if (m.source_type === 'import' && m.source_ref?.platform) {
        const platform = m.source_ref.platform as PlatformFilterValue;
        counts[platform] = (counts[platform] || 0) + 1;
      }
    });
    return counts;
  }, []);

  const filteredUserMemories = useMemo(
    () => filterMemories(userMemories),
    [filterMemories, userMemories]
  );
  const filteredScopedMemories = useMemo(
    () => filterMemories(scopedMemories),
    [filterMemories, scopedMemories]
  );

  const handleEdit = (memoryId: string) => {
    setSurface({ type: 'context-editor', memoryId });
  };

  const handleDelete = async (memoryId: string) => {
    if (!confirm('Are you sure you want to delete this memory?')) return;

    setDeleting(memoryId);
    try {
      await api.memories.delete(memoryId);
      // Remove from appropriate list
      setUserMemories((prev) => prev.filter((m) => m.id !== memoryId));
      setScopedMemories((prev) => prev.filter((m) => m.id !== memoryId));
    } catch (err) {
      console.error('Failed to delete memory:', err);
      alert('Failed to delete memory');
    } finally {
      setDeleting(null);
    }
  };

  const totalCount = userMemories.length + scopedMemories.length;
  const activeMemories = activeTab === 'personal' ? filteredUserMemories : filteredScopedMemories;
  const currentMemories = activeTab === 'personal' ? userMemories : scopedMemories;
  const platformCounts = useMemo(() => getPlatformCounts(currentMemories), [getPlatformCounts, currentMemories]);
  const hasImports = (platformCounts.slack || 0) > 0 || (platformCounts.notion || 0) > 0 || (platformCounts.gmail || 0) > 0;

  // Determine which platforms are available for filtering
  const availablePlatforms = useMemo(() => {
    const platforms: PlatformFilterValue[] = ['all'];
    if (platformCounts.slack) platforms.push('slack');
    if (platformCounts.notion) platforms.push('notion');
    if (platformCounts.gmail) platforms.push('gmail');
    return platforms;
  }, [platformCounts]);

  // Determine if we show domain tab (when a domain is selected or we have scope context)
  const nonDefaultDomains = domains.filter((d) => !d.is_default);
  const showDomainTab = selectedDomainId !== null || (scope !== 'user' && scopeId) || nonDefaultDomains.length > 0;

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-6 py-6">
        {/* Header with search */}
        <div className="flex items-center justify-between gap-4 mb-4">
          <h1 className="text-lg font-medium shrink-0">Context</h1>
          <div className="flex items-center gap-2 flex-1 max-w-sm">
            {/* Search input */}
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search..."
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

        {/* Tabs with domain selector */}
        <div className="flex gap-1 mb-4 border-b border-border">
          {/* Personal tab */}
          <button
            onClick={() => setActiveTab('personal')}
            className={cn(
              'px-3 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === 'personal'
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            <User className="w-3.5 h-3.5 inline mr-1.5" />
            Personal
            <span className="ml-1.5 text-xs text-muted-foreground">
              {filteredUserMemories.length}
            </span>
          </button>

          {/* Domain selector dropdown (ADR-034: Context v2) */}
          {showDomainTab && (
            <DomainSelector
              domains={domains}
              selectedDomainId={selectedDomainId}
              onSelect={handleDomainSelect}
              isLoading={loadingDomains}
            />
          )}

          {/* Show memory count when domain is selected */}
          {showDomainTab && activeTab === 'scoped' && selectedDomainId && (
            <span className="self-center text-xs text-muted-foreground ml-0.5">
              {filteredScopedMemories.length}
            </span>
          )}
        </div>

        {/* Platform filter - ADR-033 Phase 3 */}
        {!loading && hasImports && (
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xs text-muted-foreground">Platform:</span>
            <PlatformFilter
              value={platformFilter}
              onChange={setPlatformFilter}
              availablePlatforms={availablePlatforms}
              counts={platformCounts}
            />
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : activeTab === 'scoped' && !selectedDomainId ? (
          <div className="text-center py-12 border border-dashed border-border rounded-lg">
            <Layers className="w-8 h-8 mx-auto text-muted-foreground/50 mb-2" />
            <p className="text-muted-foreground mb-1">Select a domain</p>
            <p className="text-sm text-muted-foreground/70">
              Choose a domain from the dropdown to browse its context
            </p>
          </div>
        ) : activeMemories.length === 0 && totalCount === 0 ? (
          <div className="text-center py-12 border border-dashed border-border rounded-lg">
            <p className="text-muted-foreground mb-2">No memories yet</p>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Tell TP things you want it to remember — your preferences, company info,
              writing style, or any context that helps it understand you better.
            </p>
          </div>
        ) : (
          <MemoryList
            memories={activeMemories}
            emptyMessage={
              searchQuery
                ? 'No memories match your search'
                : platformFilter !== 'all'
                  ? `No ${platformFilter} context found`
                  : activeTab === 'personal'
                    ? 'No personal context yet. Share things TP should always know about you.'
                    : `No context in ${selectedDomainName} yet.`
            }
            onEdit={handleEdit}
            onDelete={handleDelete}
            deletingId={deleting}
          />
        )}

        {/* Footer */}
        {!loading && totalCount > 0 && (
          <p className="mt-6 text-xs text-muted-foreground text-center">
            {totalCount} total memories • TP uses your context to personalize responses
          </p>
        )}
      </div>
    </div>
  );
}
