'use client';

/**
 * ADR-058: Knowledge Base Architecture - Context Page
 *
 * Two-layer model with sidebar navigation:
 * - KNOWLEDGE: Profile, Styles, Domains, Entries
 * - FILESYSTEM: Platforms, Documents
 *
 * Replaces ADR-039's flat filter-based view with a hierarchical sidebar.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Loader2,
  Upload,
  Plus,
  Search,
  RefreshCw,
  User,
  Palette,
  FolderKanban,
  BookOpen,
  Database,
  FileText,
  Slack,
  Mail,
  FileCode,
  Calendar,
  Edit2,
  Trash2,
  ChevronRight,
  Info,
  CheckCircle2,
  Clock,
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

type Section = 'profile' | 'styles' | 'domains' | 'entries' | 'platforms' | 'documents';

interface Profile {
  id?: string;
  name?: string;
  role?: string;
  company?: string;
  timezone?: string;
  summary?: string;
  name_source?: string;
  role_source?: string;
  company_source?: string;
  timezone_source?: string;
  summary_source?: string;
  last_inferred_at?: string;
  inference_confidence?: number;
}

interface Style {
  id?: string;
  platform: string;
  tone?: string;
  verbosity?: string;
  formatting?: Record<string, unknown>;
  vocabulary_notes?: string;
  sample_excerpts?: string[];
  stated_preferences?: Record<string, unknown>;
  sample_count: number;
  last_inferred_at?: string;
}

interface Domain {
  id: string;
  name: string;
  summary?: string;
  sources?: Array<{ platform: string; resource_id: string; resource_name?: string }>;
  is_default: boolean;
  is_active: boolean;
}

interface Entry {
  id: string;
  content: string;
  entry_type: string;
  source: string;
  tags: string[];
  importance: number;
  domain_id?: string;
  created_at: string;
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

// =============================================================================
// Sidebar Navigation
// =============================================================================

interface SidebarProps {
  activeSection: Section;
  onSectionChange: (section: Section) => void;
  counts: {
    styles: number;
    domains: number;
    entries: number;
    platforms: number;
    documents: number;
  };
}

function Sidebar({ activeSection, onSectionChange, counts }: SidebarProps) {
  const navItems: Array<{ section: Section; label: string; icon: React.ReactNode; count?: number; group?: string }> = [
    { section: 'profile', label: 'Profile', icon: <User className="w-4 h-4" />, group: 'KNOWLEDGE' },
    { section: 'styles', label: 'Styles', icon: <Palette className="w-4 h-4" />, count: counts.styles, group: 'KNOWLEDGE' },
    { section: 'domains', label: 'Domains', icon: <FolderKanban className="w-4 h-4" />, count: counts.domains, group: 'KNOWLEDGE' },
    { section: 'entries', label: 'Entries', icon: <BookOpen className="w-4 h-4" />, count: counts.entries, group: 'KNOWLEDGE' },
    { section: 'platforms', label: 'Platforms', icon: <Database className="w-4 h-4" />, count: counts.platforms, group: 'FILESYSTEM' },
    { section: 'documents', label: 'Documents', icon: <FileText className="w-4 h-4" />, count: counts.documents, group: 'FILESYSTEM' },
  ];

  let currentGroup = '';

  return (
    <nav className="w-48 flex-shrink-0 border-r border-border bg-muted/50">
      <div className="p-4 space-y-1">
        {navItems.map((item) => {
          const showGroupHeader = item.group && item.group !== currentGroup;
          if (item.group) currentGroup = item.group;

          return (
            <div key={item.section}>
              {showGroupHeader && (
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-3 pt-4 pb-2">
                  {item.group}
                </div>
              )}
              <button
                onClick={() => onSectionChange(item.section)}
                className={cn(
                  "w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors",
                  activeSection === item.section
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <span className="flex items-center gap-2">
                  {item.icon}
                  {item.label}
                </span>
                {item.count !== undefined && item.count > 0 && (
                  <span className="text-xs bg-muted px-1.5 py-0.5 rounded">
                    {item.count}
                  </span>
                )}
              </button>
            </div>
          );
        })}
      </div>

      {/* Actions */}
      <div className="p-4 border-t border-border">
        <button
          onClick={() => onSectionChange('entries')}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Knowledge
        </button>
      </div>
    </nav>
  );
}

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
              <label className="block text-sm font-medium text-foreground mb-1">
                Name
              </label>
              <input
                type="text"
                value={formData.name || ''}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground"
                placeholder="Your name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Role
              </label>
              <input
                type="text"
                value={formData.role || ''}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground"
                placeholder="e.g., Product Manager"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Company
              </label>
              <input
                type="text"
                value={formData.company || ''}
                onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground"
                placeholder="Company name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Timezone
              </label>
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
            <label className="block text-sm font-medium text-foreground mb-1">
              Summary
            </label>
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
              <div className="flex items-center gap-2">
                <h3 className="text-xl font-semibold text-foreground">
                  {profile.name || 'Anonymous'}
                </h3>
                {profile.name_source === 'inferred' && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">
                    inferred
                  </span>
                )}
              </div>
              {profile.role && (
                <p className="text-muted-foreground">
                  {profile.role}
                  {profile.company && ` at ${profile.company}`}
                </p>
              )}
              {profile.summary && (
                <p className="mt-2 text-muted-foreground text-sm">
                  {profile.summary}
                </p>
              )}
              {profile.timezone && (
                <p className="mt-2 text-xs text-muted-foreground">
                  Timezone: {profile.timezone}
                </p>
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
  styles: Style[];
  loading: boolean;
  onUpdate?: (platform: string, data: { tone?: string; verbosity?: string }) => Promise<void>;
}

function StylesSection({ styles, loading, onUpdate }: StylesSectionProps) {
  const [editingPlatform, setEditingPlatform] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<{ tone?: string; verbosity?: string }>({});
  const [saving, setSaving] = useState(false);

  const handleEdit = (style: Style) => {
    setEditingPlatform(style.platform);
    setEditForm({
      tone: style.stated_preferences?.tone as string || style.tone || '',
      verbosity: style.stated_preferences?.verbosity as string || style.verbosity || '',
    });
  };

  const handleSave = async () => {
    if (!editingPlatform || !onUpdate) return;
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">Communication Styles</h2>
      </div>

      <p className="text-sm text-muted-foreground">
        These styles are inferred from your messages. Override them to control how TP generates content for you.
      </p>

      {styles.length === 0 ? (
        <div className="bg-muted/50 rounded-lg p-6 text-center">
          <Palette className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
          <p className="text-muted-foreground">
            No styles inferred yet. Connect platforms and sync content to learn your communication patterns.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {styles.map((style) => {
            const config = PLATFORM_CONFIG[style.platform] || {
              label: style.platform,
              icon: <Database className="w-4 h-4" />,
              colors: { bg: 'bg-gray-100', text: 'text-gray-600' },
            };
            const isEditing = editingPlatform === style.platform;
            const hasOverride = style.stated_preferences && Object.keys(style.stated_preferences).length > 0;

            return (
              <div
                key={style.platform}
                className="bg-card rounded-lg border border-border p-4"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className={cn("p-2 rounded-lg", config.colors.bg, config.colors.text)}>
                      {config.icon}
                    </div>
                    <span className="font-medium text-foreground">
                      {config.label}
                    </span>
                    {hasOverride && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-primary/10 text-primary">
                        custom
                      </span>
                    )}
                  </div>
                  {!isEditing && onUpdate && (
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
                        <option value="">Auto (inferred)</option>
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
                        <option value="">Auto (inferred)</option>
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
                  <>
                    <div className="space-y-2 text-sm">
                      {(style.tone || (style.stated_preferences?.tone as string | undefined)) && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Tone</span>
                          <span className="text-foreground capitalize">
                            {String((style.stated_preferences?.tone as string | undefined) || style.tone)}
                          </span>
                        </div>
                      )}
                      {(style.verbosity || (style.stated_preferences?.verbosity as string | undefined)) && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Verbosity</span>
                          <span className="text-foreground capitalize">
                            {String((style.stated_preferences?.verbosity as string | undefined) || style.verbosity)}
                          </span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Samples</span>
                        <span className="text-foreground">{style.sample_count}</span>
                      </div>
                    </div>

                    {style.sample_excerpts && style.sample_excerpts.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-border">
                        <p className="text-xs text-muted-foreground mb-1">Example:</p>
                        <p className="text-xs text-muted-foreground italic line-clamp-2">
                          &ldquo;{style.sample_excerpts[0]}&rdquo;
                        </p>
                      </div>
                    )}
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Domains Section
// =============================================================================

interface DomainsSectionProps {
  domains: Domain[];
  loading: boolean;
  onNavigate: (domainId: string) => void;
}

function DomainsSection({ domains, loading, onNavigate }: DomainsSectionProps) {
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
        <h2 className="text-lg font-semibold text-foreground">Work Domains</h2>
      </div>

      {domains.length === 0 ? (
        <div className="bg-muted/50 rounded-lg p-6 text-center">
          <FolderKanban className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
          <p className="text-muted-foreground">
            No domains yet. Domains are automatically created when you group platform sources.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {domains.map((domain) => (
            <button
              key={domain.id}
              onClick={() => onNavigate(domain.id)}
              className="w-full bg-card rounded-lg border border-border p-4 text-left hover:border-primary/50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FolderKanban className="w-5 h-5 text-primary" />
                  <span className="font-medium text-foreground">
                    {domain.name}
                  </span>
                  {domain.is_default && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                      default
                    </span>
                  )}
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              </div>
              {domain.summary && (
                <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                  {domain.summary}
                </p>
              )}
              {domain.sources && domain.sources.length > 0 && (
                <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{domain.sources.length} source{domain.sources.length !== 1 ? 's' : ''}</span>
                </div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Entries Section
// =============================================================================

interface EntriesSectionProps {
  entries: Entry[];
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

  const entryTypeLabel: Record<string, string> = {
    preference: 'Prefers',
    instruction: 'Note',
    decision: 'Decided',
    fact: 'Fact',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">Knowledge Entries</h2>
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
            No knowledge entries yet. Add facts, preferences, and decisions for TP to remember.
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
          {entries.map((entry) => (
            <div
              key={entry.id}
              className="bg-card rounded-lg border border-border p-4 flex items-start gap-3"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium text-muted-foreground">
                    {entryTypeLabel[entry.entry_type] || entry.entry_type}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    · {entry.source}
                  </span>
                </div>
                <p className="text-foreground">{entry.content}</p>
                {entry.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {entry.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
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
          ))}
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
  const router = useRouter();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const connectedPlatforms = platforms.filter((p) => p.status === 'connected');
  const availablePlatforms = ['slack', 'gmail', 'notion', 'calendar'].filter(
    (p) => !connectedPlatforms.some((cp) => cp.provider === p || (p === 'calendar' && cp.provider === 'google'))
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">Connected Platforms</h2>
      </div>

      {connectedPlatforms.length === 0 ? (
        <div className="bg-muted/50 rounded-lg p-6 text-center">
          <Database className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
          <p className="text-muted-foreground mb-4">
            No platforms connected yet. Connect Slack, Gmail, Notion, or Calendar to auto-learn your context.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {connectedPlatforms.map((platform) => {
            const config = PLATFORM_CONFIG[platform.provider] || {
              label: platform.provider,
              icon: <Database className="w-4 h-4" />,
              colors: { bg: 'bg-gray-100', text: 'text-gray-600' },
            };

            return (
              <button
                key={platform.provider}
                onClick={() => onNavigate(platform.provider)}
                className="bg-card rounded-lg border border-border p-4 text-left hover:border-primary/50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn("p-2 rounded-lg", config.colors.bg, config.colors.text)}>
                      {config.icon}
                    </div>
                    <div>
                      <span className="font-medium text-foreground">
                        {config.label}
                      </span>
                      {platform.workspace_name && (
                        <p className="text-xs text-muted-foreground">
                          {platform.workspace_name}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {platform.status === 'connected' && (
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                    )}
                    <ChevronRight className="w-4 h-4 text-muted-foreground" />
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                  <span>{platform.resource_count || 0} {platform.resource_type || 'sources'}</span>
                  <span>{platform.activity_7d || 0} items (7d)</span>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {availablePlatforms.length > 0 && (
        <div className="pt-4 border-t border-border">
          <h3 className="text-sm font-medium text-foreground mb-3">
            Connect more platforms
          </h3>
          <div className="flex flex-wrap gap-2">
            {availablePlatforms.map((platform) => {
              const config = PLATFORM_CONFIG[platform];
              return (
                <button
                  key={platform}
                  onClick={() => router.push(`/context/${platform}`)}
                  className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg text-sm text-muted-foreground hover:border-primary/50 hover:text-foreground transition-colors"
                >
                  {config.icon}
                  {config.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
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
                <p className="font-medium text-foreground truncate">
                  {doc.filename}
                </p>
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

  // Determine initial section from URL
  const sectionParam = searchParams.get('section') as Section | null;
  const [activeSection, setActiveSection] = useState<Section>(sectionParam || 'profile');

  // Loading states
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Data states
  const [profile, setProfile] = useState<Profile>({});
  const [styles, setStyles] = useState<Style[]>([]);
  const [domains, setDomains] = useState<Domain[]>([]);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [platforms, setPlatforms] = useState<PlatformSummary[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);

  // Counts for sidebar
  const counts = {
    styles: styles.length,
    domains: domains.length,
    entries: entries.length,
    platforms: platforms.filter((p) => p.status === 'connected').length,
    documents: documents.length,
  };

  // Load all data
  const loadData = useCallback(async () => {
    try {
      const [
        profileResult,
        stylesResult,
        domainsResult,
        entriesResult,
        platformsResult,
        documentsResult,
      ] = await Promise.all([
        api.profile.get().catch(() => ({})),
        api.styles.list().catch(() => ({ styles: [] })),
        api.domains.list().catch(() => []),
        api.userMemories.list().catch(() => []),
        api.integrations.getSummary().catch(() => ({ platforms: [] })),
        api.documents.list().catch(() => ({ documents: [] })),
      ]);

      setProfile(profileResult || {});
      setStyles(stylesResult?.styles || []);
      setDomains(Array.isArray(domainsResult) ? domainsResult : []);
      setEntries(Array.isArray(entriesResult) ? entriesResult as Entry[] : []);
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

  // Update URL when section changes
  const handleSectionChange = (section: Section) => {
    setActiveSection(section);
    const url = new URL(window.location.href);
    url.searchParams.set('section', section);
    router.replace(url.pathname + url.search, { scroll: false });
  };

  // Profile update handler
  const handleProfileUpdate = async (data: Partial<Profile>) => {
    const result = await api.profile.update(data);
    setProfile(result);
  };

  // Style update handler (ADR-058: user override)
  const handleStyleUpdate = async (platform: string, data: { tone?: string; verbosity?: string }) => {
    const result = await api.styles.update(platform, data);
    // Update the styles array with the new values
    setStyles(styles.map((s) =>
      s.platform === platform
        ? { ...s, stated_preferences: result.stated_preferences }
        : s
    ));
  };

  // Entry delete handler
  const handleDeleteEntry = async (id: string) => {
    await api.memories.delete(id);
    setEntries(entries.filter((e) => e.id !== id));
  };

  // File upload handler
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      await api.documents.upload(file);
      // Refresh documents
      const result = await api.documents.list();
      setDocuments(result.documents || []);
    } catch (err) {
      console.error('Upload failed:', err);
    }

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Check if user has any context
  const hasContext = counts.platforms > 0 || counts.documents > 0 || counts.entries > 0;
  const showEmptyState = !hasContext && !profile.name;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Always show sidebar, with empty state in content area when no data
  return (
    <div className="min-h-screen bg-background flex flex-col">
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

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Sidebar */}
        <Sidebar
          activeSection={activeSection}
          onSectionChange={handleSectionChange}
          counts={counts}
        />

        {/* Content Area */}
        <main className="flex-1 p-6 overflow-auto">
          {/* Show welcome prompt only on profile section when empty, otherwise show section content */}
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

              {activeSection === 'domains' && (
                <DomainsSection
                  domains={domains}
                  loading={false}
                  onNavigate={(id) => router.push(`/domains/${id}`)}
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
