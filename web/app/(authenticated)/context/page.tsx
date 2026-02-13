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
    <nav className="w-48 flex-shrink-0 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
      <div className="p-4 space-y-1">
        {navItems.map((item) => {
          const showGroupHeader = item.group && item.group !== currentGroup;
          if (item.group) currentGroup = item.group;

          return (
            <div key={item.section}>
              {showGroupHeader && (
                <div className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider px-3 pt-4 pb-2">
                  {item.group}
                </div>
              )}
              <button
                onClick={() => onSectionChange(item.section)}
                className={cn(
                  "w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors",
                  activeSection === item.section
                    ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                    : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
                )}
              >
                <span className="flex items-center gap-2">
                  {item.icon}
                  {item.label}
                </span>
                {item.count !== undefined && item.count > 0 && (
                  <span className="text-xs bg-gray-200 dark:bg-gray-700 px-1.5 py-0.5 rounded">
                    {item.count}
                  </span>
                )}
              </button>
            </div>
          );
        })}
      </div>

      {/* Actions */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={() => onSectionChange('entries')}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
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
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  const hasProfile = profile.name || profile.role || profile.company;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Profile</h2>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
          >
            <Edit2 className="w-4 h-4" />
            Edit
          </button>
        )}
      </div>

      {!hasProfile && !editing ? (
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-6 text-center">
          <User className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            No profile information yet. Add details about yourself so TP can personalize responses.
          </p>
          <button
            onClick={() => setEditing(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
          >
            Set Up Profile
          </button>
        </div>
      ) : editing ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Name
              </label>
              <input
                type="text"
                value={formData.name || ''}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                placeholder="Your name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Role
              </label>
              <input
                type="text"
                value={formData.role || ''}
                onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                placeholder="e.g., Product Manager"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Company
              </label>
              <input
                type="text"
                value={formData.company || ''}
                onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                placeholder="Company name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Timezone
              </label>
              <input
                type="text"
                value={formData.timezone || ''}
                onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
                placeholder="e.g., America/New_York"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Summary
            </label>
            <textarea
              value={formData.summary || ''}
              onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
              placeholder="Brief description of your work..."
            />
          </div>
          <div className="flex justify-end gap-3">
            <button
              onClick={() => setEditing(false)}
              className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-white text-xl font-semibold">
              {profile.name?.charAt(0)?.toUpperCase() || '?'}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                  {profile.name || 'Anonymous'}
                </h3>
                {profile.name_source === 'inferred' && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300">
                    inferred
                  </span>
                )}
              </div>
              {profile.role && (
                <p className="text-gray-600 dark:text-gray-400">
                  {profile.role}
                  {profile.company && ` at ${profile.company}`}
                </p>
              )}
              {profile.summary && (
                <p className="mt-2 text-gray-600 dark:text-gray-400 text-sm">
                  {profile.summary}
                </p>
              )}
              {profile.timezone && (
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-500">
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
}

function StylesSection({ styles, loading }: StylesSectionProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Communication Styles</h2>
      </div>

      {styles.length === 0 ? (
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-6 text-center">
          <Palette className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-gray-600 dark:text-gray-400">
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

            return (
              <div
                key={style.platform}
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4"
              >
                <div className="flex items-center gap-2 mb-3">
                  <div className={cn("p-2 rounded-lg", config.colors.bg, config.colors.text)}>
                    {config.icon}
                  </div>
                  <span className="font-medium text-gray-900 dark:text-gray-100">
                    {config.label}
                  </span>
                </div>

                <div className="space-y-2 text-sm">
                  {style.tone && (
                    <div className="flex justify-between">
                      <span className="text-gray-500 dark:text-gray-400">Tone</span>
                      <span className="text-gray-900 dark:text-gray-100 capitalize">{style.tone}</span>
                    </div>
                  )}
                  {style.verbosity && (
                    <div className="flex justify-between">
                      <span className="text-gray-500 dark:text-gray-400">Verbosity</span>
                      <span className="text-gray-900 dark:text-gray-100 capitalize">{style.verbosity}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-gray-500 dark:text-gray-400">Samples</span>
                    <span className="text-gray-900 dark:text-gray-100">{style.sample_count}</span>
                  </div>
                </div>

                {style.sample_excerpts && style.sample_excerpts.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Example:</p>
                    <p className="text-xs text-gray-600 dark:text-gray-400 italic line-clamp-2">
                      &ldquo;{style.sample_excerpts[0]}&rdquo;
                    </p>
                  </div>
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
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Work Domains</h2>
      </div>

      {domains.length === 0 ? (
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-6 text-center">
          <FolderKanban className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-gray-600 dark:text-gray-400">
            No domains yet. Domains are automatically created when you group platform sources.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {domains.map((domain) => (
            <button
              key={domain.id}
              onClick={() => onNavigate(domain.id)}
              className="w-full bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 text-left hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FolderKanban className="w-5 h-5 text-blue-500" />
                  <span className="font-medium text-gray-900 dark:text-gray-100">
                    {domain.name}
                  </span>
                  {domain.is_default && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
                      default
                    </span>
                  )}
                </div>
                <ChevronRight className="w-4 h-4 text-gray-400" />
              </div>
              {domain.summary && (
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
                  {domain.summary}
                </p>
              )}
              {domain.sources && domain.sources.length > 0 && (
                <div className="mt-2 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
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
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
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
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Knowledge Entries</h2>
        <button
          onClick={onAdd}
          className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
        >
          <Plus className="w-4 h-4" />
          Add Entry
        </button>
      </div>

      {entries.length === 0 ? (
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-6 text-center">
          <BookOpen className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            No knowledge entries yet. Add facts, preferences, and decisions for TP to remember.
          </p>
          <button
            onClick={onAdd}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
          >
            Add Your First Entry
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {entries.map((entry) => (
            <div
              key={entry.id}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 flex items-start gap-3"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                    {entryTypeLabel[entry.entry_type] || entry.entry_type}
                  </span>
                  <span className="text-xs text-gray-400 dark:text-gray-500">
                    · {entry.source}
                  </span>
                </div>
                <p className="text-gray-900 dark:text-gray-100">{entry.content}</p>
                {entry.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {entry.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
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
                className="p-1 text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
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
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
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
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Connected Platforms</h2>
      </div>

      {connectedPlatforms.length === 0 ? (
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-6 text-center">
          <Database className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-gray-600 dark:text-gray-400 mb-4">
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
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 text-left hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn("p-2 rounded-lg", config.colors.bg, config.colors.text)}>
                      {config.icon}
                    </div>
                    <div>
                      <span className="font-medium text-gray-900 dark:text-gray-100">
                        {config.label}
                      </span>
                      {platform.workspace_name && (
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {platform.workspace_name}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {platform.status === 'connected' && (
                      <CheckCircle2 className="w-4 h-4 text-green-500" />
                    )}
                    <ChevronRight className="w-4 h-4 text-gray-400" />
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                  <span>{platform.source_count || 0} sources</span>
                  <span>{platform.item_count || 0} items</span>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {availablePlatforms.length > 0 && (
        <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Connect more platforms
          </h3>
          <div className="flex flex-wrap gap-2">
            {availablePlatforms.map((platform) => {
              const config = PLATFORM_CONFIG[platform];
              return (
                <button
                  key={platform}
                  onClick={() => router.push(`/context/${platform}`)}
                  className="flex items-center gap-2 px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-600 transition-colors"
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
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Uploaded Documents</h2>
        <button
          onClick={onUpload}
          className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
        >
          <Upload className="w-4 h-4" />
          Upload
        </button>
      </div>

      {documents.length === 0 ? (
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-6 text-center">
          <FileText className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-3" />
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            No documents uploaded yet. Upload PDFs, docs, or notes to add context.
          </p>
          <button
            onClick={onUpload}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
          >
            Upload Document
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 flex items-center gap-3"
            >
              <FileText className="w-8 h-8 text-blue-500" />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 dark:text-gray-100 truncate">
                  {doc.filename}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {doc.file_type?.toUpperCase()} · {formatDistanceToNow(new Date(doc.uploaded_at), { addSuffix: true })}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {doc.processing_status === 'completed' && (
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                )}
                {doc.processing_status === 'processing' && (
                  <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
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
// Empty State
// =============================================================================

function EmptyState({ onConnectPlatforms, onUploadDocs, onAddKnowledge }: {
  onConnectPlatforms: () => void;
  onUploadDocs: () => void;
  onAddKnowledge: () => void;
}) {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="max-w-xl text-center">
        <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Your context is empty
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-8">
          TP works best when it knows about your work. Add context from any of these sources:
        </p>

        <div className="grid grid-cols-3 gap-4">
          <button
            onClick={onConnectPlatforms}
            className="p-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
          >
            <Database className="w-8 h-8 mx-auto text-blue-500 mb-3" />
            <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-1">
              Connect Platforms
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Slack, Gmail, Notion
            </p>
          </button>

          <button
            onClick={onUploadDocs}
            className="p-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
          >
            <FileText className="w-8 h-8 mx-auto text-green-500 mb-3" />
            <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-1">
              Upload Documents
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              PDFs, docs, notes
            </p>
          </button>

          <button
            onClick={onAddKnowledge}
            className="p-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
          >
            <BookOpen className="w-8 h-8 mx-auto text-purple-500 mb-3" />
            <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-1">
              Add Knowledge
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Tell TP about you directly
            </p>
          </button>
        </div>

        <p className="mt-8 text-sm text-gray-500 dark:text-gray-400">
          Connect platforms to auto-learn your style and context.
          <br />
          Or add knowledge directly — TP will remember it.
        </p>
      </div>
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
        api.user.memories().catch(() => []),
        api.integrations.getSummary().catch(() => ({ platforms: [] })),
        api.documents.list().catch(() => ({ documents: [] })),
      ]);

      setProfile(profileResult);
      setStyles(stylesResult.styles || []);
      setDomains(domainsResult as Domain[]);
      setEntries(entriesResult as Entry[]);
      setPlatforms(platformsResult.platforms || []);
      setDocuments(documentsResult.documents || []);
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  // Show empty state if no context
  if (!hasContext && !profile.name) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-6 py-4">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Context</h1>
        </div>
        <EmptyState
          onConnectPlatforms={() => handleSectionChange('platforms')}
          onUploadDocs={() => fileInputRef.current?.click()}
          onAddKnowledge={() => handleSectionChange('entries')}
        />
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

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Context</h1>
        <button
          onClick={() => {
            setRefreshing(true);
            loadData().finally(() => setRefreshing(false));
          }}
          disabled={refreshing}
          className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
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
