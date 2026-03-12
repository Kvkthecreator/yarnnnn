'use client';

/**
 * ADR-063: Context Page — Four-Layer Model
 *
 * Layer 3: Context — What's in the user's platforms right now
 *
 * Sections:
 * - Platforms: Connected integrations (Slack, Gmail, Notion, Calendar)
 * - Documents: Uploaded files (PDF, DOC, TXT, MD)
 * - Knowledge: Agent-produced artifacts in /knowledge/ filesystem
 *
 * Data lives in: platform_connections, platform_content, filesystem_documents, workspace_files(/knowledge/)
 * Written by: OAuth flow, platform_worker sync, document upload
 * Read by: TP via Search tool, agent pipeline via TP execution mode
 *
 * Note: Profile, Styles, and Entries moved to /memory (Memory layer)
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Loader2,
  Upload,
  RefreshCw,
  FileText,
  Slack,
  Mail,
  FileCode,
  Calendar,
  Layers,
  ChevronRight,
  CheckCircle2,
  XCircle,
  FolderOpen,
  FolderTree,
  ArrowLeft,
  Plus,
  X,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import type { Document, KnowledgeFile, KnowledgeFileDetail, KnowledgeContentClass, KnowledgeVersion } from '@/types';
import type { PlatformSummary } from '@/components/ui/PlatformCard';
import ReactMarkdown from 'react-markdown';

// =============================================================================
// Types
// =============================================================================

type Section = 'platforms' | 'documents' | 'knowledge';
const VALID_SECTIONS: readonly Section[] = ['platforms', 'documents', 'knowledge'] as const;

function normalizeSection(value: string | null): Section {
  return VALID_SECTIONS.includes(value as Section) ? (value as Section) : 'knowledge';
}

const VALID_KNOWLEDGE_CLASSES: readonly KnowledgeContentClass[] = [
  'digests',
  'analyses',
  'briefs',
  'research',
  'insights',
] as const;

function normalizeKnowledgeClass(value: string | null): KnowledgeContentClass | undefined {
  return VALID_KNOWLEDGE_CLASSES.includes(value as KnowledgeContentClass)
    ? (value as KnowledgeContentClass)
    : undefined;
}

// =============================================================================
// Platform Configuration
// =============================================================================

const PLATFORM_CONFIG: Record<string, {
  label: string;
  icon: React.ReactNode;
  colors: { bg: string; text: string };
}> = {
  slack: {
    label: 'Slack',
    icon: <Slack className="w-4 h-4" />,
    colors: { bg: 'bg-purple-100 dark:bg-purple-900/30', text: 'text-purple-600 dark:text-purple-400' },
  },
  gmail: {
    label: 'Email',
    icon: <Mail className="w-4 h-4" />,
    colors: { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-600 dark:text-red-400' },
  },
  notion: {
    label: 'Notion',
    icon: <FileCode className="w-4 h-4" />,
    colors: { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-700 dark:text-gray-300' },
  },
  calendar: {
    label: 'Calendar',
    icon: <Calendar className="w-4 h-4" />,
    colors: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-600 dark:text-blue-400' },
  },
};

const ALL_PLATFORMS = ['slack', 'gmail', 'notion', 'calendar'] as const;

// =============================================================================
// Section Navigation
// =============================================================================

const SECTIONS: { id: Section; label: string; icon: React.ReactNode }[] = [
  { id: 'knowledge', label: 'Knowledge', icon: <FolderTree className="w-4 h-4" /> },
  { id: 'platforms', label: 'Platforms', icon: <Layers className="w-4 h-4" /> },
  { id: 'documents', label: 'Documents', icon: <FolderOpen className="w-4 h-4" /> },
];

// =============================================================================
// Platforms Section
// =============================================================================

interface PlatformsSectionProps {
  platforms: PlatformSummary[];
  loading: boolean;
  onNavigate: (platform: string) => void;
}

function PlatformsSection({ platforms, loading, onNavigate }: PlatformsSectionProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const platformMap: Record<string, PlatformSummary | undefined> = {};
  for (const p of platforms) {
    platformMap[p.provider] = p;
  }

  const connectedCount = ALL_PLATFORMS.filter((p) => platformMap[p]?.status === 'active').length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Connected Platforms</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            {connectedCount === 0
              ? 'Connect platforms to sync your context.'
              : `${connectedCount} of ${ALL_PLATFORMS.length} connected`}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {ALL_PLATFORMS.map((platformKey) => {
          const config = PLATFORM_CONFIG[platformKey];
          const summary = platformMap[platformKey];
          const isConnected = summary?.status === 'active';
          const navTarget = platformKey;

          return (
            <button
              key={platformKey}
              onClick={() => onNavigate(navTarget)}
              className={cn(
                "rounded-lg border p-4 text-left transition-colors",
                isConnected
                  ? "bg-card border-border hover:border-primary/50"
                  : "bg-muted/30 border-border border-dashed hover:border-muted-foreground/40"
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "p-2 rounded-lg",
                    isConnected ? config.colors.bg : "bg-muted",
                    isConnected ? config.colors.text : "text-muted-foreground"
                  )}>
                    {config.icon}
                  </div>
                  <div>
                    <span className={cn("font-medium text-sm", isConnected ? "text-foreground" : "text-muted-foreground")}>
                      {config.label}
                    </span>
                    {isConnected && summary?.workspace_name && (
                      <p className="text-xs text-muted-foreground truncate max-w-[140px]">
                        {summary.workspace_name}
                      </p>
                    )}
                    {!isConnected && (
                      <p className="text-xs text-muted-foreground/60">Not connected</p>
                    )}
                  </div>
                </div>
                {isConnected ? (
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <span className="text-xs text-primary font-medium">Connect →</span>
                )}
              </div>

              {isConnected && summary && (
                <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-green-500" />
                    Connected
                  </span>
                  {summary.resource_count > 0 && (
                    <span>{summary.resource_count} {summary.resource_type || 'sources'}</span>
                  )}
                  {summary.activity_7d > 0 && (
                    <span>{summary.activity_7d} items (7d)</span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// =============================================================================
// Documents Section
// =============================================================================

interface DocumentsSectionProps {
  documents: Document[];
  loading: boolean;
  onUpload: () => void;
}

function DocumentsSection({ documents, loading, onUpload }: DocumentsSectionProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Uploaded Documents</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            PDFs, docs, and notes you've uploaded for TP to reference.
          </p>
        </div>
        <button
          onClick={onUpload}
          className="flex items-center gap-1.5 text-sm text-primary hover:text-primary/80"
        >
          <Upload className="w-4 h-4" />
          Upload
        </button>
      </div>

      {documents.length === 0 ? (
        <div className="bg-muted/50 rounded-lg p-6 text-center">
          <FileText className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
          <p className="text-muted-foreground mb-4">
            No documents uploaded yet. Upload PDFs, docs, or notes to add context.
          </p>
          <button
            onClick={onUpload}
            className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium"
          >
            Upload Document
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="bg-card rounded-lg border border-border p-4 flex items-center gap-3"
            >
              <FileText className="w-8 h-8 text-primary" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-foreground truncate">{doc.filename}</p>
                <p className="text-xs text-muted-foreground">
                  {doc.file_type?.toUpperCase()} · {formatDistanceToNow(new Date(doc.created_at), { addSuffix: true })}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {doc.processing_status === 'completed' && (
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                )}
                {doc.processing_status === 'processing' && (
                  <Loader2 className="w-4 h-4 animate-spin text-primary" />
                )}
                {doc.processing_status === 'failed' && (
                  <XCircle className="w-4 h-4 text-red-500" />
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Knowledge Section
// =============================================================================

const KNOWLEDGE_CLASS_LABELS: Record<KnowledgeContentClass, string> = {
  digests: 'Digests',
  analyses: 'Analyses',
  briefs: 'Briefs',
  research: 'Research',
  insights: 'Insights',
};

interface KnowledgeSectionProps {
  files: KnowledgeFile[];
  loading: boolean;
  activeClass?: KnowledgeContentClass;
  classCounts: Record<string, number>;
  onClassChange: (contentClass?: KnowledgeContentClass) => void;
  onFileCreated: () => void;
}

function KnowledgeSection({
  files,
  loading,
  activeClass,
  classCounts,
  onClassChange,
  onFileCreated,
}: KnowledgeSectionProps) {
  const [selectedFile, setSelectedFile] = useState<KnowledgeFileDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [versions, setVersions] = useState<KnowledgeVersion[]>([]);
  const [canonicalPath, setCanonicalPath] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [createTitle, setCreateTitle] = useState('');
  const [createClass, setCreateClass] = useState<string>('research');
  const [createContent, setCreateContent] = useState('');
  const [createSaving, setCreateSaving] = useState(false);

  const handleFileClick = async (file: KnowledgeFile) => {
    setDetailLoading(true);
    setCanonicalPath(file.path);
    try {
      const [detail, versionsResult] = await Promise.all([
        api.knowledge.readFile(file.path),
        api.knowledge.listVersions(file.path).catch(() => ({ versions: [], total: 0, canonical_path: file.path })),
      ]);
      setSelectedFile(detail);
      setVersions(versionsResult.versions || []);
    } catch (err) {
      console.error('Failed to read knowledge file:', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleVersionClick = async (versionPath: string) => {
    setDetailLoading(true);
    try {
      const detail = await api.knowledge.readFile(versionPath);
      setSelectedFile(detail);
    } catch (err) {
      console.error('Failed to read version:', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!createTitle.trim() || !createContent.trim()) return;
    setCreateSaving(true);
    try {
      await api.knowledge.createFile({
        title: createTitle.trim(),
        content: createContent.trim(),
        content_class: createClass,
      });
      setShowCreate(false);
      setCreateTitle('');
      setCreateContent('');
      setCreateClass('research');
      onFileCreated();
    } catch (err) {
      console.error('Failed to create knowledge file:', err);
    } finally {
      setCreateSaving(false);
    }
  };

  // Detail view
  if (selectedFile) {
    const detailClass = (selectedFile.content_class in KNOWLEDGE_CLASS_LABELS
      ? selectedFile.content_class
      : 'analyses') as KnowledgeContentClass;
    const detailMeta = (selectedFile.metadata || {}) as Record<string, unknown>;

    return (
      <div className="space-y-4">
        <button
          onClick={() => setSelectedFile(null)}
          className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to files
        </button>

        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h2 className="text-lg font-semibold text-foreground">{selectedFile.name}</h2>
            <span className="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary">
              {KNOWLEDGE_CLASS_LABELS[detailClass]}
            </span>
            {typeof detailMeta.source === 'string' && (
              <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                {detailMeta.source === 'user_upload' ? 'User' : detailMeta.source}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="truncate">{selectedFile.path}</span>
            {selectedFile.updated_at && (
              <span className="shrink-0">
                {formatDistanceToNow(new Date(selectedFile.updated_at), { addSuffix: true })}
              </span>
            )}
          </div>
        </div>

        <div className="bg-card rounded-lg border border-border p-5">
          {selectedFile.path.endsWith('.md') ? (
            <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:mt-4 prose-headings:mb-2 prose-p:my-2 prose-ul:my-2 prose-li:my-0">
              <ReactMarkdown>{selectedFile.content}</ReactMarkdown>
            </div>
          ) : (
            <pre className="text-sm whitespace-pre-wrap break-words text-foreground">
              {selectedFile.content}
            </pre>
          )}
        </div>

        {/* Version history — ADR-107 Phase 2 */}
        {versions.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-sm font-medium text-muted-foreground">
              Version History ({versions.length})
            </h3>
            {versions.map((v) => {
              const isViewing = selectedFile.path === v.path;
              return (
                <button
                  key={v.path}
                  onClick={() => !isViewing && handleVersionClick(v.path)}
                  disabled={isViewing}
                  className={cn(
                    "w-full text-left rounded-lg border p-3 text-sm transition-colors",
                    isViewing
                      ? "bg-primary/5 border-primary/30 cursor-default"
                      : "bg-card border-border hover:border-primary/50"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-foreground">
                      v{v.version}
                      {isViewing && <span className="text-xs text-muted-foreground ml-2">(viewing)</span>}
                    </span>
                    {v.updated_at && (
                      <span className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(v.updated_at), { addSuffix: true })}
                      </span>
                    )}
                  </div>
                  {v.summary && (
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-1">{v.summary}</p>
                  )}
                </button>
              );
            })}
            {canonicalPath && selectedFile.path !== canonicalPath && (
              <button
                onClick={() => handleVersionClick(canonicalPath)}
                className="text-xs text-primary hover:text-primary/80"
              >
                Back to current version
              </button>
            )}
          </div>
        )}
      </div>
    );
  }

  // Loading detail
  if (detailLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const totalFiles = Object.values(classCounts).reduce((sum, count) => sum + count, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Knowledge Files</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Agent outputs and user notes organized by content class.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-1.5 text-sm text-primary hover:text-primary/80"
        >
          <Plus className="w-4 h-4" />
          Add File
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="bg-card rounded-lg border border-border p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-foreground">New Knowledge File</h3>
            <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Title"
              value={createTitle}
              onChange={(e) => setCreateTitle(e.target.value)}
              className="flex-1 px-3 py-1.5 text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
            />
            <select
              value={createClass}
              onChange={(e) => setCreateClass(e.target.value)}
              className="px-3 py-1.5 text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {VALID_KNOWLEDGE_CLASSES.map((cls) => (
                <option key={cls} value={cls}>{KNOWLEDGE_CLASS_LABELS[cls]}</option>
              ))}
            </select>
          </div>
          <textarea
            placeholder="Content (markdown supported)"
            value={createContent}
            onChange={(e) => setCreateContent(e.target.value)}
            rows={6}
            className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-1 focus:ring-primary resize-y"
          />
          <div className="flex justify-end">
            <button
              onClick={handleCreate}
              disabled={createSaving || !createTitle.trim() || !createContent.trim()}
              className="px-4 py-1.5 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {createSaving ? 'Saving...' : 'Create'}
            </button>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => onClassChange(undefined)}
          className={cn(
            "px-2.5 py-1 text-xs rounded-full border transition-colors",
            !activeClass
              ? "bg-primary text-primary-foreground border-primary"
              : "border-border hover:bg-muted"
          )}
        >
          All ({totalFiles})
        </button>
        {VALID_KNOWLEDGE_CLASSES.map((contentClass) => (
          <button
            key={contentClass}
            onClick={() => onClassChange(contentClass)}
            className={cn(
              "px-2.5 py-1 text-xs rounded-full border transition-colors",
              activeClass === contentClass
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border hover:bg-muted"
            )}
          >
            {KNOWLEDGE_CLASS_LABELS[contentClass]} ({classCounts[contentClass] || 0})
          </button>
        ))}
      </div>

      {files.length === 0 ? (
        <div className="bg-muted/50 rounded-lg p-6 text-center">
          <FolderTree className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
          <p className="text-muted-foreground mb-4">
            {activeClass
              ? `No ${KNOWLEDGE_CLASS_LABELS[activeClass].toLowerCase()} files yet.`
              : 'No knowledge files yet. Create one or run an agent to get started.'}
          </p>
          {!showCreate && (
            <button
              onClick={() => setShowCreate(true)}
              className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium"
            >
              Create File
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {files.map((file) => {
            const metadata = (file.metadata || {}) as Record<string, unknown>;
            const contentClass = (file.content_class in KNOWLEDGE_CLASS_LABELS
              ? file.content_class
              : 'analyses') as KnowledgeContentClass;

            return (
              <button
                key={file.path}
                onClick={() => handleFileClick(file)}
                className="w-full text-left bg-card rounded-lg border border-border p-4 hover:border-primary/50 transition-colors"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <p className="font-medium text-foreground truncate">{file.name}</p>
                      <span className="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                        {KNOWLEDGE_CLASS_LABELS[contentClass]}
                      </span>
                      {typeof metadata.agent_type === 'string' && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                          {metadata.agent_type}
                        </span>
                      )}
                    </div>
                    {file.summary && (
                      <p className="text-sm text-muted-foreground line-clamp-2">{file.summary}</p>
                    )}
                    <p className="text-xs text-muted-foreground mt-1 truncate">{file.path}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {file.updated_at && (
                      <span className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(file.updated_at), { addSuffix: true })}
                      </span>
                    )}
                    <ChevronRight className="w-4 h-4 text-muted-foreground" />
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export default function ContextPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const sectionParam = normalizeSection(searchParams.get('section'));
  const knowledgeClassParam = normalizeKnowledgeClass(searchParams.get('class'));
  const [activeSection, setActiveSection] = useState<Section>(sectionParam);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [platforms, setPlatforms] = useState<PlatformSummary[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [knowledgeFiles, setKnowledgeFiles] = useState<KnowledgeFile[]>([]);
  const [knowledgeClassCounts, setKnowledgeClassCounts] = useState<Record<string, number>>({});

  const loadData = useCallback(async () => {
    try {
      const [platformsResult, documentsResult, knowledgeResult, knowledgeSummary] = await Promise.all([
        api.integrations.getSummary().catch(() => ({ platforms: [] })),
        api.documents.list().catch(() => ({ documents: [] })),
        api.knowledge.listFiles({
          content_class: knowledgeClassParam,
          limit: 60,
        }).catch(() => ({ files: [] })),
        api.knowledge.summary().catch(() => ({ classes: [] })),
      ]);

      setPlatforms(platformsResult?.platforms || []);
      setDocuments(documentsResult?.documents || []);
      setKnowledgeFiles(knowledgeResult?.files || []);

      const nextCounts: Record<string, number> = {};
      for (const row of knowledgeSummary?.classes || []) {
        nextCounts[row.content_class] = row.count;
      }
      setKnowledgeClassCounts(nextCounts);
    } catch (err) {
      console.error('Failed to load context data:', err);
    } finally {
      setLoading(false);
    }
  }, [knowledgeClassParam]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const s = normalizeSection(searchParams.get('section'));
    if (s !== activeSection) {
      setActiveSection(s);
    }
  }, [searchParams, activeSection]);

  const handleSectionChange = (section: Section) => {
    setActiveSection(section);
    const params = new URLSearchParams(searchParams.toString());
    params.set('section', section);
    if (section !== 'knowledge') {
      params.delete('class');
    }
    router.replace(`/context?${params.toString()}`, { scroll: false });
  };

  const handleKnowledgeClassChange = (contentClass?: KnowledgeContentClass) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set('section', 'knowledge');
    if (contentClass) {
      params.set('class', contentClass);
    } else {
      params.delete('class');
    }
    router.replace(`/context?${params.toString()}`, { scroll: false });
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      await api.documents.upload(file);
      const result = await api.documents.list();
      setDocuments(result.documents || []);
    } catch (err) {
      console.error('Upload failed:', err);
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full py-24">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Files</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Browse platforms, documents, and knowledge in one filesystem view
            </p>
          </div>
          <button
            onClick={() => {
              setRefreshing(true);
              loadData().finally(() => setRefreshing(false));
            }}
            disabled={refreshing}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          >
            <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} />
            Refresh
          </button>
        </div>

        {/* Mobile section navigation (desktop uses sidebar) */}
        <div className="md:hidden flex items-center gap-2 mb-6">
          {SECTIONS.map((section) => (
            <button
              key={section.id}
              onClick={() => handleSectionChange(section.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-full border ${
                activeSection === section.id
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'border-border hover:bg-muted'
              }`}
            >
              {section.icon}
              {section.label}
            </button>
          ))}
        </div>

        {/* Content */}
        {activeSection === 'platforms' && (
          <PlatformsSection
            platforms={platforms}
            loading={false}
            onNavigate={(platform) => router.push(`/context/${platform}`)}
          />
        )}

        {activeSection === 'documents' && (
          <DocumentsSection
            documents={documents}
            loading={false}
            onUpload={() => fileInputRef.current?.click()}
          />
        )}

        {activeSection === 'knowledge' && (
          <KnowledgeSection
            files={knowledgeFiles}
            loading={false}
            activeClass={knowledgeClassParam}
            classCounts={knowledgeClassCounts}
            onClassChange={handleKnowledgeClassChange}
            onFileCreated={() => loadData()}
          />
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept=".pdf,.doc,.docx,.txt,.md"
        onChange={handleFileUpload}
      />
    </div>
  );
}
