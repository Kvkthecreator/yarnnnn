'use client';

/**
 * ADR-039: Unified Context Surface
 *
 * Single page for all context sources following Finder/Explorer mental model.
 * Combines platforms, documents, and user-stated facts into one view.
 *
 * Sources:
 * - Platforms: Connected integrations (Slack, Gmail, Notion)
 * - Documents: Uploaded files (PDF, DOCX, TXT, MD)
 * - Facts: User-stated preferences and information
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Loader2,
  Upload,
  Plus,
  Search,
  Link2,
  FileText,
  MessageSquare,
  Layers,
  RefreshCw,
  CheckCircle2,
  Clock,
  XCircle,
  Slack,
  Mail,
  FileCode,
  Calendar,
  Edit2,
  Trash2,
  ExternalLink,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import type { Document } from '@/types';
import type { PlatformSummary } from '@/components/ui/PlatformCard';

// =============================================================================
// Types
// =============================================================================

type SourceFilter = 'all' | 'platforms' | 'documents' | 'facts';

interface UserFact {
  id: string;
  content: string;
  tags: string[];
  importance: number;
  source_type: string;
  created_at: string;
}

// =============================================================================
// Platform Icons
// =============================================================================

const PLATFORM_ICONS: Record<string, React.ReactNode> = {
  slack: <Slack className="w-5 h-5" />,
  gmail: <Mail className="w-5 h-5" />,
  notion: <FileCode className="w-5 h-5" />,
  google: <Calendar className="w-5 h-5" />,
  calendar: <Calendar className="w-5 h-5" />,
};

const PLATFORM_COLORS: Record<string, { bg: string; text: string }> = {
  slack: { bg: 'bg-purple-100 dark:bg-purple-900/30', text: 'text-purple-600 dark:text-purple-400' },
  gmail: { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-600 dark:text-red-400' },
  notion: { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-700 dark:text-gray-300' },
  google: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-600 dark:text-blue-400' },
  calendar: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-600 dark:text-blue-400' },
};

// =============================================================================
// Main Component
// =============================================================================

export default function ContextPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Determine initial filter from URL
  const sourceParam = searchParams.get('source');
  const initialFilter: SourceFilter =
    sourceParam === 'platforms' ? 'platforms' :
    sourceParam === 'documents' ? 'documents' :
    sourceParam === 'facts' ? 'facts' :
    'all';

  // State
  const [filter, setFilter] = useState<SourceFilter>(initialFilter);
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Data state
  const [platforms, setPlatforms] = useState<PlatformSummary[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [facts, setFacts] = useState<UserFact[]>([]);
  const [uploading, setUploading] = useState(false);

  // Fact editing
  const [editingFactId, setEditingFactId] = useState<string | null>(null);
  const [editingFactContent, setEditingFactContent] = useState('');
  const [addingFact, setAddingFact] = useState(false);
  const [newFactContent, setNewFactContent] = useState('');

  // =============================================================================
  // Data Loading
  // =============================================================================

  const loadData = useCallback(async (showRefresh = false) => {
    try {
      if (showRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      // Load all data in parallel
      const [platformsResult, docsResult, factsResult] = await Promise.all([
        api.integrations.getSummary().catch(() => ({ platforms: [] })),
        api.documents.list().catch(() => ({ documents: [] })),
        api.userMemories.list().catch(() => []),
      ]);

      setPlatforms(platformsResult.platforms);
      setDocuments(docsResult.documents);
      setFacts(factsResult);
    } catch (err) {
      console.error('Failed to load context data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // =============================================================================
  // Handlers
  // =============================================================================

  const handleFilterChange = (newFilter: SourceFilter) => {
    setFilter(newFilter);
    // Update URL without full navigation
    const params = new URLSearchParams();
    if (newFilter !== 'all') {
      params.set('source', newFilter);
    }
    if (searchQuery) {
      params.set('search', searchQuery);
    }
    const newUrl = params.toString() ? `/context?${params}` : '/context';
    router.replace(newUrl, { scroll: false });
  };

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    // Update URL with search
    const params = new URLSearchParams();
    if (filter !== 'all') {
      params.set('source', filter);
    }
    if (query) {
      params.set('search', query);
    }
    const newUrl = params.toString() ? `/context?${params}` : '/context';
    router.replace(newUrl, { scroll: false });
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await api.documents.upload(file);
      await loadData(true);
    } catch (err) {
      console.error('Failed to upload document:', err);
      alert('Failed to upload. Please try again.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleConnectPlatform = async (provider: string) => {
    try {
      const result = await api.integrations.getAuthorizationUrl(provider);
      window.location.href = result.authorization_url;
    } catch (err) {
      console.error(`Failed to initiate ${provider} OAuth:`, err);
    }
  };

  const handleAddFact = async () => {
    if (!newFactContent.trim()) return;

    try {
      await api.userMemories.create({
        content: newFactContent.trim(),
        tags: ['user-stated'],
        source_type: 'user_stated',
      });
      setNewFactContent('');
      setAddingFact(false);
      await loadData(true);
    } catch (err) {
      console.error('Failed to add fact:', err);
    }
  };

  const handleEditFact = async (factId: string) => {
    if (!editingFactContent.trim()) return;

    try {
      await api.memories.update(factId, { content: editingFactContent.trim() });
      setEditingFactId(null);
      setEditingFactContent('');
      await loadData(true);
    } catch (err) {
      console.error('Failed to update fact:', err);
    }
  };

  const handleDeleteFact = async (factId: string) => {
    if (!confirm('Delete this fact?')) return;

    try {
      await api.memories.delete(factId);
      await loadData(true);
    } catch (err) {
      console.error('Failed to delete fact:', err);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!confirm('Delete this document?')) return;

    try {
      await api.documents.delete(docId);
      await loadData(true);
    } catch (err) {
      console.error('Failed to delete document:', err);
    }
  };

  // =============================================================================
  // Filtering
  // =============================================================================

  const filteredPlatforms = platforms.filter((p) => {
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        p.provider.toLowerCase().includes(q) ||
        (p.workspace_name?.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const filteredDocuments = documents.filter((d) => {
    if (searchQuery) {
      return d.filename.toLowerCase().includes(searchQuery.toLowerCase());
    }
    return true;
  });

  const filteredFacts = facts.filter((f) => {
    if (searchQuery) {
      return f.content.toLowerCase().includes(searchQuery.toLowerCase());
    }
    return true;
  });

  // Counts for sidebar
  const counts = {
    all: platforms.length + documents.length + facts.length,
    platforms: platforms.length,
    documents: documents.length,
    facts: facts.length,
  };

  const isEmpty = counts.all === 0;

  // =============================================================================
  // Render
  // =============================================================================

  return (
    <div className="h-full flex">
      {/* Sidebar */}
      <aside className="w-56 border-r border-border bg-muted/30 flex flex-col shrink-0">
        {/* Sources */}
        <div className="p-4 flex-1">
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Sources
          </h2>
          <nav className="space-y-1">
            <SidebarItem
              icon={<Layers className="w-4 h-4" />}
              label="All"
              count={counts.all}
              active={filter === 'all'}
              onClick={() => handleFilterChange('all')}
            />
            <SidebarItem
              icon={<Link2 className="w-4 h-4" />}
              label="Platforms"
              count={counts.platforms}
              active={filter === 'platforms'}
              onClick={() => handleFilterChange('platforms')}
            />
            <SidebarItem
              icon={<FileText className="w-4 h-4" />}
              label="Documents"
              count={counts.documents}
              active={filter === 'documents'}
              onClick={() => handleFilterChange('documents')}
            />
            <SidebarItem
              icon={<MessageSquare className="w-4 h-4" />}
              label="Facts"
              count={counts.facts}
              active={filter === 'facts'}
              onClick={() => handleFilterChange('facts')}
            />
          </nav>
        </div>

        {/* Quick Actions */}
        <div className="p-4 border-t border-border space-y-2">
          <button
            onClick={() => handleConnectPlatform('slack')}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left rounded-md hover:bg-muted transition-colors"
          >
            <Link2 className="w-4 h-4 text-muted-foreground" />
            <span>Connect Platform</span>
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left rounded-md hover:bg-muted transition-colors disabled:opacity-50"
          >
            {uploading ? (
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            ) : (
              <Upload className="w-4 h-4 text-muted-foreground" />
            )}
            <span>Upload Document</span>
          </button>
          <button
            onClick={() => setAddingFact(true)}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left rounded-md hover:bg-muted transition-colors"
          >
            <Plus className="w-4 h-4 text-muted-foreground" />
            <span>Add Fact</span>
          </button>
        </div>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleUpload}
          className="hidden"
          accept=".pdf,.doc,.docx,.txt,.md"
        />
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {/* Header */}
        <div className="sticky top-0 bg-background border-b border-border px-6 py-4 z-10">
          <div className="flex items-center justify-between gap-4">
            <h1 className="text-xl font-semibold">
              {filter === 'all' ? 'All Context' :
               filter === 'platforms' ? 'Platforms' :
               filter === 'documents' ? 'Documents' :
               'Facts'}
            </h1>
            <div className="flex items-center gap-3">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search..."
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-9 pr-4 py-2 w-64 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>
              {/* Refresh */}
              <button
                onClick={() => loadData(true)}
                disabled={refreshing}
                className="p-2 rounded-md hover:bg-muted transition-colors disabled:opacity-50"
              >
                <RefreshCw className={cn('w-4 h-4', refreshing && 'animate-spin')} />
              </button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
            </div>
          ) : isEmpty ? (
            <EmptyState
              onConnectPlatform={() => handleConnectPlatform('slack')}
              onUploadDocument={() => fileInputRef.current?.click()}
              onAddFact={() => setAddingFact(true)}
            />
          ) : (
            <div className="space-y-8">
              {/* Platforms Section */}
              {(filter === 'all' || filter === 'platforms') && filteredPlatforms.length > 0 && (
                <section>
                  {filter === 'all' && (
                    <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-4">
                      Platforms
                    </h2>
                  )}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredPlatforms.map((platform) => (
                      <PlatformSourceCard
                        key={platform.provider}
                        platform={platform}
                        onClick={() => router.push(`/context?source=${platform.provider}`)}
                      />
                    ))}
                    {/* Add Platform Card */}
                    <AddSourceCard
                      type="platform"
                      onClick={() => handleConnectPlatform('slack')}
                    />
                  </div>
                </section>
              )}

              {/* Show add platform when in platforms filter with no connected platforms */}
              {filter === 'platforms' && filteredPlatforms.length === 0 && (
                <section>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    <AddSourceCard
                      type="platform"
                      onClick={() => handleConnectPlatform('slack')}
                    />
                  </div>
                </section>
              )}

              {/* Documents Section */}
              {(filter === 'all' || filter === 'documents') && (filteredDocuments.length > 0 || filter === 'documents') && (
                <section>
                  {filter === 'all' && (
                    <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-4">
                      Documents
                    </h2>
                  )}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredDocuments.map((doc) => (
                      <DocumentSourceCard
                        key={doc.id}
                        document={doc}
                        onClick={() => router.push(`/docs/${doc.id}`)}
                        onDelete={() => handleDeleteDocument(doc.id)}
                      />
                    ))}
                    {/* Add Document Card */}
                    <AddSourceCard
                      type="document"
                      onClick={() => fileInputRef.current?.click()}
                    />
                  </div>
                </section>
              )}

              {/* Facts Section */}
              {(filter === 'all' || filter === 'facts') && (filteredFacts.length > 0 || filter === 'facts' || addingFact) && (
                <section>
                  {filter === 'all' && (
                    <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-4">
                      Facts
                    </h2>
                  )}
                  <div className="space-y-3">
                    {/* Add new fact form */}
                    {addingFact && (
                      <div className="p-4 border border-primary/30 rounded-lg bg-primary/5">
                        <textarea
                          value={newFactContent}
                          onChange={(e) => setNewFactContent(e.target.value)}
                          placeholder="Tell TP something about yourself or your work..."
                          className="w-full p-3 text-sm border border-border rounded-md bg-background resize-none focus:outline-none focus:ring-2 focus:ring-primary/20"
                          rows={3}
                          autoFocus
                        />
                        <div className="flex justify-end gap-2 mt-3">
                          <button
                            onClick={() => {
                              setAddingFact(false);
                              setNewFactContent('');
                            }}
                            className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={handleAddFact}
                            disabled={!newFactContent.trim()}
                            className="px-4 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
                          >
                            Save
                          </button>
                        </div>
                      </div>
                    )}

                    {filteredFacts.map((fact) => (
                      <FactSourceCard
                        key={fact.id}
                        fact={fact}
                        isEditing={editingFactId === fact.id}
                        editContent={editingFactContent}
                        onEditStart={() => {
                          setEditingFactId(fact.id);
                          setEditingFactContent(fact.content);
                        }}
                        onEditChange={setEditingFactContent}
                        onEditSave={() => handleEditFact(fact.id)}
                        onEditCancel={() => {
                          setEditingFactId(null);
                          setEditingFactContent('');
                        }}
                        onDelete={() => handleDeleteFact(fact.id)}
                      />
                    ))}

                    {/* Add fact prompt when no facts and not adding */}
                    {filteredFacts.length === 0 && !addingFact && (
                      <button
                        onClick={() => setAddingFact(true)}
                        className="w-full p-4 border border-dashed border-border rounded-lg text-center text-sm text-muted-foreground hover:border-primary/50 hover:text-foreground transition-colors"
                      >
                        <Plus className="w-5 h-5 mx-auto mb-2" />
                        Add your first fact
                      </button>
                    )}
                  </div>
                </section>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

// =============================================================================
// Sub-Components
// =============================================================================

function SidebarItem({
  icon,
  label,
  count,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center justify-between px-3 py-2 text-sm rounded-md transition-colors',
        active
          ? 'bg-primary/10 text-primary font-medium'
          : 'text-foreground hover:bg-muted'
      )}
    >
      <span className="flex items-center gap-2">
        {icon}
        {label}
      </span>
      <span className="text-xs text-muted-foreground">{count}</span>
    </button>
  );
}

function EmptyState({
  onConnectPlatform,
  onUploadDocument,
  onAddFact,
}: {
  onConnectPlatform: () => void;
  onUploadDocument: () => void;
  onAddFact: () => void;
}) {
  return (
    <div className="max-w-2xl mx-auto text-center py-16">
      <Layers className="w-16 h-16 mx-auto mb-6 text-muted-foreground/50" />
      <h2 className="text-xl font-semibold mb-3">Your context is empty</h2>
      <p className="text-muted-foreground mb-8">
        TP works best when it knows about your work.
        Add context from any of these sources:
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <button
          onClick={onConnectPlatform}
          className="p-6 border border-border rounded-lg hover:border-primary/50 hover:bg-muted/50 transition-all text-left"
        >
          <Link2 className="w-8 h-8 mb-3 text-primary" />
          <h3 className="font-medium mb-1">Connect</h3>
          <p className="text-sm text-muted-foreground">
            Slack, Gmail, Notion, Calendar
          </p>
        </button>

        <button
          onClick={onUploadDocument}
          className="p-6 border border-border rounded-lg hover:border-primary/50 hover:bg-muted/50 transition-all text-left"
        >
          <FileText className="w-8 h-8 mb-3 text-primary" />
          <h3 className="font-medium mb-1">Upload</h3>
          <p className="text-sm text-muted-foreground">
            PDFs, docs, notes
          </p>
        </button>

        <button
          onClick={onAddFact}
          className="p-6 border border-border rounded-lg hover:border-primary/50 hover:bg-muted/50 transition-all text-left"
        >
          <MessageSquare className="w-8 h-8 mb-3 text-primary" />
          <h3 className="font-medium mb-1">Tell TP</h3>
          <p className="text-sm text-muted-foreground">
            Directly in chat
          </p>
        </button>
      </div>

      <p className="text-sm text-muted-foreground mt-8">
        All three are equally valid — pick what fits your work.
      </p>
    </div>
  );
}

function PlatformSourceCard({
  platform,
  onClick,
}: {
  platform: PlatformSummary;
  onClick: () => void;
}) {
  const colors = PLATFORM_COLORS[platform.provider] || { bg: 'bg-muted', text: 'text-foreground' };
  const icon = PLATFORM_ICONS[platform.provider] || <Link2 className="w-5 h-5" />;

  return (
    <button
      onClick={onClick}
      className="p-4 border border-border rounded-lg hover:border-primary/50 hover:shadow-sm transition-all text-left"
    >
      <div className="flex items-start justify-between mb-3">
        <div className={cn('p-2 rounded-lg', colors.bg, colors.text)}>
          {icon}
        </div>
        {platform.status === 'active' ? (
          <CheckCircle2 className="w-4 h-4 text-green-500" />
        ) : platform.status === 'error' ? (
          <XCircle className="w-4 h-4 text-red-500" />
        ) : (
          <Clock className="w-4 h-4 text-amber-500" />
        )}
      </div>
      <h3 className="font-medium capitalize">{platform.provider}</h3>
      {platform.workspace_name && (
        <p className="text-xs text-muted-foreground truncate">{platform.workspace_name}</p>
      )}
      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
        <span>{platform.resource_count} {platform.resource_type}</span>
        {platform.activity_7d > 0 && (
          <span>{platform.activity_7d} items (7d)</span>
        )}
      </div>
    </button>
  );
}

function DocumentSourceCard({
  document,
  onClick,
  onDelete,
}: {
  document: Document;
  onClick: () => void;
  onDelete: () => void;
}) {
  const getStatusIcon = () => {
    switch (document.processing_status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'processing':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-amber-500" />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="group p-4 border border-border rounded-lg hover:border-primary/50 hover:shadow-sm transition-all">
      <div className="flex items-start justify-between mb-3">
        <div className="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
          <FileText className="w-5 h-5" />
        </div>
        <div className="flex items-center gap-1">
          {getStatusIcon()}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1 opacity-0 group-hover:opacity-100 hover:bg-muted rounded transition-all"
          >
            <Trash2 className="w-3.5 h-3.5 text-muted-foreground hover:text-destructive" />
          </button>
        </div>
      </div>
      <button onClick={onClick} className="text-left w-full">
        <h3 className="font-medium truncate">{document.filename}</h3>
        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
          <span>{document.file_type.toUpperCase()}</span>
          <span>·</span>
          <span>{formatFileSize(document.file_size)}</span>
          {document.page_count && (
            <>
              <span>·</span>
              <span>{document.page_count} pages</span>
            </>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          {formatDistanceToNow(new Date(document.created_at), { addSuffix: true })}
        </p>
      </button>
    </div>
  );
}

function FactSourceCard({
  fact,
  isEditing,
  editContent,
  onEditStart,
  onEditChange,
  onEditSave,
  onEditCancel,
  onDelete,
}: {
  fact: UserFact;
  isEditing: boolean;
  editContent: string;
  onEditStart: () => void;
  onEditChange: (content: string) => void;
  onEditSave: () => void;
  onEditCancel: () => void;
  onDelete: () => void;
}) {
  if (isEditing) {
    return (
      <div className="p-4 border border-primary/30 rounded-lg bg-primary/5">
        <textarea
          value={editContent}
          onChange={(e) => onEditChange(e.target.value)}
          className="w-full p-3 text-sm border border-border rounded-md bg-background resize-none focus:outline-none focus:ring-2 focus:ring-primary/20"
          rows={3}
          autoFocus
        />
        <div className="flex justify-end gap-2 mt-3">
          <button
            onClick={onEditCancel}
            className="px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            Cancel
          </button>
          <button
            onClick={onEditSave}
            disabled={!editContent.trim()}
            className="px-4 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
          >
            Save
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="group p-4 border border-border rounded-lg hover:border-primary/50 transition-all">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <p className="text-sm">&quot;{fact.content}&quot;</p>
          <div className="flex items-center gap-2 mt-2">
            {fact.tags.map((tag) => (
              <span
                key={tag}
                className="px-2 py-0.5 text-xs bg-muted rounded-full text-muted-foreground"
              >
                {tag}
              </span>
            ))}
            <span className="text-xs text-muted-foreground">
              {formatDistanceToNow(new Date(fact.created_at), { addSuffix: true })}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={onEditStart}
            className="p-1.5 hover:bg-muted rounded transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5 text-muted-foreground" />
          </button>
          <button
            onClick={onDelete}
            className="p-1.5 hover:bg-muted rounded transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5 text-muted-foreground hover:text-destructive" />
          </button>
        </div>
      </div>
    </div>
  );
}

function AddSourceCard({
  type,
  onClick,
}: {
  type: 'platform' | 'document';
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="p-4 border border-dashed border-border rounded-lg hover:border-primary/50 hover:bg-muted/50 transition-all flex flex-col items-center justify-center min-h-[120px] text-center"
    >
      <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center mb-2">
        <Plus className="w-5 h-5 text-muted-foreground" />
      </div>
      <p className="text-sm font-medium text-muted-foreground">
        {type === 'platform' ? 'Connect Platform' : 'Upload Document'}
      </p>
    </button>
  );
}
