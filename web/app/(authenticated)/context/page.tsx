'use client';

/**
 * ADR-063: Context Page — Four-Layer Model
 *
 * Layer 3: Context — What's in the user's platforms right now
 *
 * Sections:
 * - Platforms: Connected integrations (Slack, Gmail, Notion, Calendar)
 * - Documents: Uploaded files (PDF, DOC, TXT, MD)
 *
 * Data lives in: platform_connections, platform_content, filesystem_documents
 * Written by: OAuth flow, platform_worker sync, document upload
 * Read by: TP via Search tool, deliverable pipeline via TP execution mode
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
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import type { Document } from '@/types';
import type { PlatformSummary } from '@/components/ui/PlatformCard';

// =============================================================================
// Types
// =============================================================================

type Section = 'platforms' | 'documents';
const VALID_SECTIONS: readonly Section[] = ['platforms', 'documents'] as const;

function normalizeSection(value: string | null): Section {
  return VALID_SECTIONS.includes(value as Section) ? (value as Section) : 'platforms';
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
          // Always navigate to the platform's dedicated page (calendar has its own page)
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
// Main Component
// =============================================================================

export default function ContextPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const sectionParam = normalizeSection(searchParams.get('section'));
  const [activeSection, setActiveSection] = useState<Section>(sectionParam);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [platforms, setPlatforms] = useState<PlatformSummary[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);

  const loadData = useCallback(async () => {
    try {
      const [platformsResult, documentsResult] = await Promise.all([
        api.integrations.getSummary().catch(() => ({ platforms: [] })),
        api.documents.list().catch(() => ({ documents: [] })),
      ]);

      setPlatforms(platformsResult?.platforms || []);
      setDocuments(documentsResult?.documents || []);
    } catch (err) {
      console.error('Failed to load context data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

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
    router.replace(`/context?section=${section}`, { scroll: false });
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
            <h1 className="text-2xl font-bold">Context</h1>
            <p className="text-sm text-muted-foreground mt-1">
              What's in your platforms right now
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
