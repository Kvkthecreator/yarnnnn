'use client';

/**
 * ADR-063/064: Memory Page — Four-Layer Model
 *
 * Layer 1: Memory — What YARNNN knows about the user
 *
 * Sections:
 * - Profile: Name, role, company, timezone, summary
 * - Communication Styles: Tone/verbosity per platform
 * - Knowledge Entries: Facts, preferences, instructions (with source badges)
 *
 * Data lives in: user_context table
 * Written by: User directly, backend extraction (ADR-064)
 * Read by: working_memory.py at session start
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Loader2,
  Plus,
  RefreshCw,
  User,
  Palette,
  BookOpen,
  Brain,
  Slack,
  Mail,
  FileCode,
  Calendar,
  Database,
  Edit2,
  Trash2,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

type Section = 'profile' | 'styles' | 'entries';

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

interface MemoryEntry {
  id: string;
  key: string;
  value: string;
  source: string;
  confidence: number;
  source_ref?: string | null;  // ADR-072: FK to source record
  source_type?: string | null;  // ADR-072: type of source
  created_at: string;
  updated_at: string;
}

// =============================================================================
// Platform Configuration (for styles)
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
  { id: 'profile', label: 'Profile', icon: <User className="w-4 h-4" /> },
  { id: 'styles', label: 'Styles', icon: <Palette className="w-4 h-4" /> },
  { id: 'entries', label: 'Entries', icon: <BookOpen className="w-4 h-4" /> },
];

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
        <div>
          <h2 className="text-lg font-semibold text-foreground">Profile</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Basic information about you that TP uses to personalize responses.
          </p>
        </div>
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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
// Entries Section (with ADR-064 source badges)
// =============================================================================

interface EntriesSectionProps {
  entries: MemoryEntry[];
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
            No knowledge entries yet. TP will learn from your conversations, or you can add entries manually.
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
                    <span className={cn(
                      "text-xs px-1.5 py-0.5 rounded",
                      source.bg,
                      source.text
                    )}>
                      {source.label}
                    </span>
                    {/* ADR-072: Show source_type provenance badge */}
                    {entry.source_type && (
                      <span className={cn(
                        "text-xs px-1.5 py-0.5 rounded",
                        entry.source_type === 'deliverable_feedback' && "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
                        entry.source_type === 'conversation_extraction' && "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
                        entry.source_type === 'pattern_analysis' && "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
                        !['deliverable_feedback', 'conversation_extraction', 'pattern_analysis'].includes(entry.source_type) && "bg-muted text-muted-foreground"
                      )}>
                        {entry.source_type === 'deliverable_feedback' && 'from feedback'}
                        {entry.source_type === 'conversation_extraction' && 'from chat'}
                        {entry.source_type === 'pattern_analysis' && 'from patterns'}
                        {!['deliverable_feedback', 'conversation_extraction', 'pattern_analysis'].includes(entry.source_type) && entry.source_type}
                      </span>
                    )}
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
// Main Component
// =============================================================================

export default function MemoryPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const sectionParam = searchParams.get('section') as Section | null;
  const [activeSection, setActiveSection] = useState<Section>(sectionParam || 'profile');

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [profile, setProfile] = useState<Profile>({});
  const [styles, setStyles] = useState<StyleItem[]>([]);
  const [entries, setEntries] = useState<MemoryEntry[]>([]);

  const loadData = useCallback(async () => {
    try {
      const [profileResult, stylesResult, entriesResult] = await Promise.all([
        api.profile.get().catch(() => ({})),
        api.styles.list().catch(() => ({ styles: [] })),
        api.userMemories.list().catch(() => []),
      ]);

      setProfile(profileResult || {});
      setStyles(stylesResult?.styles || []);
      setEntries(Array.isArray(entriesResult) ? entriesResult as MemoryEntry[] : []);
    } catch (err) {
      console.error('Failed to load memory data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full py-24">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b border-border bg-card px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <Brain className="w-6 h-6 text-purple-500" />
          <div>
            <h1 className="text-xl font-semibold text-foreground">Memory</h1>
            <p className="text-sm text-muted-foreground">What YARNNN knows about you</p>
          </div>
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

      {/* Section Navigation */}
      <div className="border-b border-border bg-card px-6 shrink-0">
        <nav className="flex gap-6">
          {SECTIONS.map((section) => (
            <button
              key={section.id}
              onClick={() => handleSectionChange(section.id)}
              className={cn(
                "flex items-center gap-2 py-3 text-sm border-b-2 transition-colors",
                activeSection === section.id
                  ? "border-primary text-primary font-medium"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {section.icon}
              {section.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <main className="flex-1 overflow-auto">
        <div className="max-w-3xl mx-auto px-6 py-6">
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
            onAdd={() => router.push('/dashboard?action=add-memory')}
            onDelete={handleDeleteEntry}
          />
        )}
        </div>
      </main>
    </div>
  );
}
