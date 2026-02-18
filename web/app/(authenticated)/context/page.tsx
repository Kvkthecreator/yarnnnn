'use client';

/**
 * ADR-059: Simplified Context Model
 *
 * Two sections:
 * - KNOWLEDGE: Profile, Styles, Entries
 * - FILESYSTEM: Platforms, Documents
 *
 * Removed: Domains section (domain grouping is a UI concept on deliverables, not a data concept)
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Loader2,
  Upload,
  Plus,
  RefreshCw,
  User,
  Palette,
  BookOpen,
  FileText,
  Slack,
  Mail,
  FileCode,
  Calendar,
  Database,
  Edit2,
  Trash2,
  ChevronRight,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import { cn } from '@/lib/utils';
import type { Document } from '@/types';
import type { PlatformSummary } from '@/components/ui/PlatformCard';

// =============================================================================
// Types
// =============================================================================

type Section = 'profile' | 'styles' | 'entries' | 'platforms' | 'documents';

interface Profile {
  name?: string;
  role?: string;
  company?: string;
  timezone?: string;
  summary?: string;
}

interface StyleItem {
  platform: string;
  tone?: string;
  verbosity?: string;
}

interface ContextEntry {
  id: string;
  key: string;
  value: string;
  source: string;
  confidence: number;
  created_at: string;
  updated_at: string;
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
// Profile Section
// =============================================================================

interface ProfileSectionProps {
  profile: Profile;
  loading: boolean;
  onUpdate: (data: Partial<Profile>) => Promise<void>;
}

function ProfileSection({ profile, loading, onUpdate }: ProfileSectionProps) {
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState<Partial<Profile>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setFormData({
      name: profile.name || '',
      role: profile.role || '',
      company: profile.company || '',
      timezone: profile.timezone || '',
      summary: profile.summary || '',
    });
  }, [profile]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onUpdate(formData);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const hasProfile = profile.name || profile.role || profile.company;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">Profile</h2>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="flex items-center gap-1.5 text-sm text-primary hover:text-primary/80"
          >
            <Edit2 className="w-4 h-4" />
            Edit
          </button>
        )}
      </div>

      {!hasProfile && !editing ? (
        <div className="bg-muted/50 rounded-lg p-6 text-center">
          <User className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
          <p className="text-muted-foreground mb-4">
            No profile information yet. Add details about yourself so TP can personalize responses.
          </p>
          <button
            onClick={() => setEditing(true)}
            className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium"
          >
            Set Up Profile
          </button>
        </div>
      ) : editing ? (
        <div className="bg-card rounded-lg border border-border p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Name</label>
              <input
                type="text"
                value={formData.name || ''}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground"
                placeholder="Your name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Role</label>
              <input
                type="text"
                value={formData.role || ''}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground"
                placeholder="e.g., Product Manager"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Company</label>
              <input
                type="text"
                value={formData.company || ''}
                onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground"
                placeholder="Company name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">Timezone</label>
              <input
                type="text"
                value={formData.timezone || ''}
                onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground"
                placeholder="e.g., America/New_York"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Summary</label>
            <textarea
              value={formData.summary || ''}
              onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground"
              placeholder="Brief description of your work..."
            />
          </div>
          <div className="flex justify-end gap-3">
            <button
              onClick={() => setEditing(false)}
              className="px-4 py-2 text-muted-foreground hover:text-foreground"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-card rounded-lg border border-border p-6">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white text-xl font-semibold">
              {profile.name?.charAt(0)?.toUpperCase() || '?'}
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-semibold text-foreground">
                {profile.name || 'Anonymous'}
              </h3>
              {profile.role && (
                <p className="text-muted-foreground">
                  {profile.role}
                  {profile.company && ` at ${profile.company}`}
                </p>
              )}
              {profile.summary && (
                <p className="mt-2 text-muted-foreground text-sm">{profile.summary}</p>
              )}
              {profile.timezone && (
                <p className="mt-2 text-xs text-muted-foreground">Timezone: {profile.timezone}</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Styles Section
// =============================================================================

interface StylesSectionProps {
  styles: StyleItem[];
  loading: boolean;
  onUpdate: (platform: string, data: { tone?: string; verbosity?: string }) => Promise<void>;
}

function StylesSection({ styles, loading, onUpdate }: StylesSectionProps) {
  const [editingPlatform, setEditingPlatform] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<{ tone?: string; verbosity?: string }>({});
  const [saving, setSaving] = useState(false);

  const handleEdit = (style: StyleItem) => {
    setEditingPlatform(style.platform);
    setEditForm({ tone: style.tone || '', verbosity: style.verbosity || '' });
  };

  const handleSave = async () => {
    if (!editingPlatform) return;
    setSaving(true);
    try {
      await onUpdate(editingPlatform, editForm);
      setEditingPlatform(null);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Show all 4 platforms — empty ones can be configured
  const allPlatformStyles: StyleItem[] = ALL_PLATFORMS.map((p) => {
    const existing = styles.find((s) => s.platform === p);
    return existing || { platform: p };
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Communication Styles</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Set your preferred tone and verbosity per platform. TP uses these when writing content for you.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {allPlatformStyles.map((style) => {
          const config = PLATFORM_CONFIG[style.platform] || {
            label: style.platform,
            icon: <Database className="w-4 h-4" />,
            colors: { bg: 'bg-gray-100', text: 'text-gray-600' },
          };
          const isEditing = editingPlatform === style.platform;
          const hasPrefs = style.tone || style.verbosity;

          return (
            <div key={style.platform} className="bg-card rounded-lg border border-border p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className={cn("p-2 rounded-lg", config.colors.bg, config.colors.text)}>
                    {config.icon}
                  </div>
                  <span className="font-medium text-foreground">{config.label}</span>
                  {hasPrefs && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary">set</span>
                  )}
                </div>
                {!isEditing && (
                  <button
                    onClick={() => handleEdit(style)}
                    className="text-xs text-primary hover:text-primary/80"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>

              {isEditing ? (
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Tone</label>
                    <select
                      value={editForm.tone || ''}
                      onChange={(e) => setEditForm({ ...editForm, tone: e.target.value })}
                      className="w-full px-2 py-1.5 text-sm border border-border rounded bg-background text-foreground"
                    >
                      <option value="">Not set</option>
                      <option value="casual">Casual</option>
                      <option value="formal">Formal</option>
                      <option value="professional">Professional</option>
                      <option value="friendly">Friendly</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-muted-foreground mb-1">Verbosity</label>
                    <select
                      value={editForm.verbosity || ''}
                      onChange={(e) => setEditForm({ ...editForm, verbosity: e.target.value })}
                      className="w-full px-2 py-1.5 text-sm border border-border rounded bg-background text-foreground"
                    >
                      <option value="">Not set</option>
                      <option value="minimal">Minimal</option>
                      <option value="moderate">Moderate</option>
                      <option value="detailed">Detailed</option>
                    </select>
                  </div>
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={() => setEditingPlatform(null)}
                      className="flex-1 px-2 py-1.5 text-xs text-muted-foreground hover:text-foreground"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="flex-1 px-2 py-1.5 text-xs bg-primary hover:bg-primary/90 text-primary-foreground rounded disabled:opacity-50"
                    >
                      {saving ? 'Saving...' : 'Save'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-2 text-sm">
                  {style.tone ? (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Tone</span>
                      <span className="text-foreground capitalize">{style.tone}</span>
                    </div>
                  ) : null}
                  {style.verbosity ? (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Verbosity</span>
                      <span className="text-foreground capitalize">{style.verbosity}</span>
                    </div>
                  ) : null}
                  {!hasPrefs && (
                    <p className="text-xs text-muted-foreground/60">Not configured</p>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// =============================================================================
// Entries Section
// =============================================================================

interface EntriesSectionProps {
  entries: ContextEntry[];
  loading: boolean;
  onAdd: () => void;
  onDelete: (id: string) => Promise<void>;
}

function EntriesSection({ entries, loading, onAdd, onDelete }: EntriesSectionProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await onDelete(id);
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const typeLabel: Record<string, string> = {
    fact: 'Fact',
    preference: 'Prefers',
    instruction: 'Note',
    pattern: 'Pattern',
  };

  // ADR-064: Source styling for implicit memory
  const sourceConfig: Record<string, { label: string; bg: string; text: string }> = {
    user_stated: {
      label: 'You said',
      bg: 'bg-green-100 dark:bg-green-900/30',
      text: 'text-green-700 dark:text-green-400',
    },
    conversation: {
      label: 'From chat',
      bg: 'bg-purple-100 dark:bg-purple-900/30',
      text: 'text-purple-700 dark:text-purple-400',
    },
    feedback: {
      label: 'From edits',
      bg: 'bg-blue-100 dark:bg-blue-900/30',
      text: 'text-blue-700 dark:text-blue-400',
    },
    pattern: {
      label: 'Detected',
      bg: 'bg-amber-100 dark:bg-amber-900/30',
      text: 'text-amber-700 dark:text-amber-400',
    },
    tp_extracted: {
      label: 'TP learned',
      bg: 'bg-purple-100 dark:bg-purple-900/30',
      text: 'text-purple-700 dark:text-purple-400',
    },
  };

  // Confidence indicator
  const getConfidenceLabel = (confidence: number): { label: string; color: string } => {
    if (confidence >= 0.9) return { label: 'high', color: 'text-green-600 dark:text-green-400' };
    if (confidence >= 0.7) return { label: 'medium', color: 'text-amber-600 dark:text-amber-400' };
    return { label: 'low', color: 'text-muted-foreground' };
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Knowledge Entries</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Facts, preferences, and instructions TP keeps in mind every session.
          </p>
        </div>
        <button
          onClick={onAdd}
          className="flex items-center gap-1.5 text-sm text-primary hover:text-primary/80"
        >
          <Plus className="w-4 h-4" />
          Add Entry
        </button>
      </div>

      {entries.length === 0 ? (
        <div className="bg-muted/50 rounded-lg p-6 text-center">
          <BookOpen className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
          <p className="text-muted-foreground mb-4">
            No knowledge entries yet. Add facts, preferences, and instructions for TP to remember.
          </p>
          <button
            onClick={onAdd}
            className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium"
          >
            Add Your First Entry
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {entries.map((entry) => {
            const prefix = entry.key.split(':')[0];
            const label = typeLabel[prefix] || prefix;
            const source = sourceConfig[entry.source] || {
              label: entry.source,
              bg: 'bg-muted',
              text: 'text-muted-foreground',
            };
            const confidence = getConfidenceLabel(entry.confidence);
            const showConfidence = entry.source !== 'user_stated' && entry.confidence < 1.0;

            return (
              <div
                key={entry.id}
                className="bg-card rounded-lg border border-border p-4 flex items-start gap-3"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-xs font-medium text-muted-foreground">{label}</span>
                    {/* Source badge */}
                    <span className={cn(
                      "text-xs px-1.5 py-0.5 rounded",
                      source.bg,
                      source.text
                    )}>
                      {source.label}
                    </span>
                    {/* Confidence indicator for non-user entries */}
                    {showConfidence && (
                      <span className={cn("text-xs", confidence.color)}>
                        · {confidence.label} confidence
                      </span>
                    )}
                  </div>
                  <p className="text-foreground">{entry.value}</p>
                </div>
                <button
                  onClick={() => handleDelete(entry.id)}
                  disabled={deletingId === entry.id}
                  className="p-1 text-muted-foreground hover:text-red-500 dark:hover:text-red-400 transition-colors"
                >
                  {deletingId === entry.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

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
    const key = p.provider === 'google' ? 'calendar' : p.provider;
    platformMap[key] = p;
  }

  const connectedCount = ALL_PLATFORMS.filter((p) => platformMap[p]?.status === 'connected').length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Platforms</h2>
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
          const isConnected = summary?.status === 'connected';
          const navTarget = platformKey === 'calendar' && summary?.provider === 'google' ? 'google' : platformKey;

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
        <h2 className="text-lg font-semibold text-foreground">Uploaded Documents</h2>
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

  const sectionParam = searchParams.get('section') as Section | null;
  const [activeSection, setActiveSection] = useState<Section>(sectionParam || 'profile');

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [profile, setProfile] = useState<Profile>({});
  const [styles, setStyles] = useState<StyleItem[]>([]);
  const [entries, setEntries] = useState<ContextEntry[]>([]);
  const [platforms, setPlatforms] = useState<PlatformSummary[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);

  const loadData = useCallback(async () => {
    try {
      const [
        profileResult,
        stylesResult,
        entriesResult,
        platformsResult,
        documentsResult,
      ] = await Promise.all([
        api.profile.get().catch(() => ({})),
        api.styles.list().catch(() => ({ styles: [] })),
        api.userMemories.list().catch(() => []),
        api.integrations.getSummary().catch(() => ({ platforms: [] })),
        api.documents.list().catch(() => ({ documents: [] })),
      ]);

      setProfile(profileResult || {});
      setStyles(stylesResult?.styles || []);
      setEntries(Array.isArray(entriesResult) ? entriesResult as ContextEntry[] : []);
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

  // Sync section from URL changes
  useEffect(() => {
    const s = searchParams.get('section') as Section | null;
    if (s && s !== activeSection) {
      setActiveSection(s);
    }
  }, [searchParams, activeSection]);

  const handleSectionChange = (section: Section) => {
    setActiveSection(section);
    const url = new URL(window.location.href);
    url.searchParams.set('section', section);
    router.replace(url.pathname + url.search, { scroll: false });
  };

  const handleProfileUpdate = async (data: Partial<Profile>) => {
    const result = await api.profile.update(data);
    setProfile(result);
  };

  const handleStyleUpdate = async (platform: string, data: { tone?: string; verbosity?: string }) => {
    const result = await api.styles.update(platform, data);
    setStyles((prev) => {
      const exists = prev.find((s) => s.platform === platform);
      if (exists) {
        return prev.map((s) => s.platform === platform ? { ...s, ...result } : s);
      }
      return [...prev, result];
    });
  };

  const handleDeleteEntry = async (id: string) => {
    await api.memories.delete(id);
    setEntries((prev) => prev.filter((e) => e.id !== id));
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

  const hasContext = platforms.filter((p) => p.status === 'connected').length > 0 ||
    documents.length > 0 ||
    entries.length > 0;
  const showEmptyState = !hasContext && !profile.name;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full py-24">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <>
      {/* Header */}
      <div className="border-b border-border bg-card px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-foreground">Context</h1>
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

      {/* Content Area */}
      <main className="flex-1 p-6 overflow-auto">
        {showEmptyState && activeSection === 'profile' ? (
          <div className="h-full flex items-center justify-center">
            <div className="max-w-md text-center">
              <h2 className="text-xl font-semibold text-foreground mb-2">
                Get started with context
              </h2>
              <p className="text-muted-foreground mb-6">
                TP works best when it knows about your work. Use the sidebar to add context.
              </p>
              <div className="flex flex-col gap-3">
                <button
                  onClick={() => handleSectionChange('platforms')}
                  className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium"
                >
                  Connect a platform
                </button>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-4 py-2 border border-border text-foreground hover:bg-muted rounded-lg text-sm"
                >
                  Upload a document
                </button>
              </div>
            </div>
          </div>
        ) : (
          <>
            {activeSection === 'profile' && (
              <ProfileSection
                profile={profile}
                loading={false}
                onUpdate={handleProfileUpdate}
              />
            )}

            {activeSection === 'styles' && (
              <StylesSection
                styles={styles}
                loading={false}
                onUpdate={handleStyleUpdate}
              />
            )}

            {activeSection === 'entries' && (
              <EntriesSection
                entries={entries}
                loading={false}
                onAdd={() => router.push('/chat?action=add-knowledge')}
                onDelete={handleDeleteEntry}
              />
            )}

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
          </>
        )}
      </main>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept=".pdf,.doc,.docx,.txt,.md"
        onChange={handleFileUpload}
      />
    </>
  );
}
