'use client';

/**
 * Memory section for Settings page — absorbed from standalone /memory page.
 *
 * Three sub-sections:
 * - Entries: Facts, preferences, instructions (searchable, filterable)
 * - Profile: Name, role, company, timezone, summary
 * - Preferences: Communication tone/verbosity per platform
 */

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  Plus,
  RefreshCw,
  Search,
  User,
  Palette,
  BookOpen,
  Slack,
  FileCode,
  Edit2,
  Trash2,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { HOME_ROUTE } from '@/lib/routes';

// =============================================================================
// Types
// =============================================================================

type Section = 'entries' | 'profile' | 'styles';

interface Profile {
  name?: string;
  role?: string;
  company?: string;
  timezone?: string;
  summary?: string;
}

interface MemoryEntry {
  id: string;
  key: string;
  value: string;
  source: string;
  confidence: number;
  source_ref?: string | null;
  source_type?: string | null;
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
  notion: {
    label: 'Notion',
    icon: <FileCode className="w-4 h-4" />,
    colors: { bg: 'bg-gray-100 dark:bg-gray-800', text: 'text-gray-700 dark:text-gray-300' },
  },
};

const ALL_PLATFORMS = ['slack', 'notion'] as const;

// =============================================================================
// Section Navigation
// =============================================================================

const SECTIONS: { id: Section; label: string; icon: React.ReactNode }[] = [
  { id: 'entries', label: 'Entries', icon: <BookOpen className="w-4 h-4" /> },
  { id: 'profile', label: 'Profile', icon: <User className="w-4 h-4" /> },
  { id: 'styles', label: 'Preferences', icon: <Palette className="w-4 h-4" /> },
];

// =============================================================================
// Profile Section
// =============================================================================

function ProfileSection({ profile, loading, onUpdate }: {
  profile: Profile;
  loading: boolean;
  onUpdate: (data: Partial<Profile>) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState<Partial<Profile>>({});
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'saved' | 'failed' | null>(null);

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
    setSaveStatus(null);
    try {
      await onUpdate(formData);
      setEditing(false);
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus(null), 2500);
    } catch {
      setSaveStatus('failed');
      setTimeout(() => setSaveStatus(null), 3000);
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
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-foreground">Profile</h2>
            {saveStatus && (
              <span className={cn(
                "text-xs px-1.5 py-0.5 rounded animate-in fade-in duration-200",
                saveStatus === 'saved'
                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                  : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
              )}>
                {saveStatus === 'saved' ? 'Saved' : 'Failed to save'}
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Basic information about you that yarnnn uses to personalize responses.
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
            No profile information yet. Add details about yourself so yarnnn can personalize responses.
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

function StylesSection({ loading }: { loading: boolean }) {
  const [formData, setFormData] = useState<Record<string, { tone: string; verbosity: string }>>(() => {
    const map: Record<string, { tone: string; verbosity: string }> = {};
    for (const p of ALL_PLATFORMS) map[p] = { tone: '', verbosity: '' };
    return map;
  });
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'saved' | 'failed' | null>(null);

  useEffect(() => {
    api.styles.list().then((res) => {
      setFormData((prev) => {
        const next = { ...prev };
        for (const s of res.styles || []) {
          next[s.platform] = { tone: s.tone || '', verbosity: s.verbosity || '' };
        }
        return next;
      });
    }).catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaveStatus(null);
    try {
      for (const platform of ALL_PLATFORMS) {
        const { tone, verbosity } = formData[platform];
        await api.styles.update(platform, {
          tone: tone || undefined,
          verbosity: verbosity || undefined,
        });
      }
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus(null), 2500);
    } catch {
      setSaveStatus('failed');
      setTimeout(() => setSaveStatus(null), 3000);
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
      <div>
        <h2 className="text-lg font-semibold text-foreground">Communication Preferences</h2>
        <p className="text-sm text-muted-foreground mt-0.5">
          Set your preferred tone and verbosity per platform.
        </p>
      </div>

      <div className="bg-card rounded-lg border border-border p-6 space-y-5">
        {ALL_PLATFORMS.map((platform) => {
          const config = PLATFORM_CONFIG[platform];
          const pref = formData[platform];

          return (
            <div key={platform} className="space-y-3">
              <div className="flex items-center gap-2">
                <div className={cn("p-1.5 rounded-md", config.colors.bg, config.colors.text)}>
                  {config.icon}
                </div>
                <span className="font-medium text-sm text-foreground">{config.label}</span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-muted-foreground mb-1">Tone</label>
                  <select
                    value={pref.tone}
                    onChange={(e) => setFormData((prev) => ({
                      ...prev,
                      [platform]: { ...prev[platform], tone: e.target.value },
                    }))}
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
                    value={pref.verbosity}
                    onChange={(e) => setFormData((prev) => ({
                      ...prev,
                      [platform]: { ...prev[platform], verbosity: e.target.value },
                    }))}
                    className="w-full px-2 py-1.5 text-sm border border-border rounded bg-background text-foreground"
                  >
                    <option value="">Not set</option>
                    <option value="minimal">Minimal</option>
                    <option value="moderate">Moderate</option>
                    <option value="detailed">Detailed</option>
                  </select>
                </div>
              </div>
            </div>
          );
        })}

        <div className="flex items-center justify-end gap-3 pt-2">
          {saveStatus && (
            <span className={cn(
              "text-xs animate-in fade-in duration-200",
              saveStatus === 'saved'
                ? "text-green-600 dark:text-green-400"
                : "text-red-600 dark:text-red-400"
            )}>
              {saveStatus === 'saved' ? 'Saved' : 'Failed to save'}
            </span>
          )}
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Entries Section
// =============================================================================

const TYPE_LABELS: Record<string, string> = {
  fact: 'Fact',
  preference: 'Preference',
  instruction: 'Instruction',
};

const TYPE_COLORS: Record<string, string> = {
  fact: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  preference: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  instruction: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
};

function EntriesSection({ entries, loading, onAdd, onDelete }: {
  entries: MemoryEntry[];
  loading: boolean;
  onAdd: () => void;
  onDelete: (id: string) => Promise<void>;
}) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<'all' | 'fact' | 'preference' | 'instruction'>('all');
  const [visibleCount, setVisibleCount] = useState(20);

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

  const getEntryType = (entry: MemoryEntry) => entry.key.split(':')[0]?.toLowerCase() || 'fact';

  const typeCounts = entries.reduce<Record<string, number>>((acc, entry) => {
    const type = getEntryType(entry);
    if (type in acc) {
      acc[type] += 1;
    }
    return acc;
  }, { fact: 0, preference: 0, instruction: 0 });

  const normalizedQuery = query.trim().toLowerCase();
  const filteredEntries = entries.filter((entry) => {
    const entryType = getEntryType(entry);
    if (typeFilter !== 'all' && entryType !== typeFilter) return false;
    if (!normalizedQuery) return true;
    return entry.value.toLowerCase().includes(normalizedQuery);
  });

  // Reset visible count on filter change
  useEffect(() => {
    setVisibleCount(20);
  }, [query, typeFilter]);

  const visibleEntries = filteredEntries.slice(0, visibleCount);
  const remainingCount = Math.max(0, filteredEntries.length - visibleEntries.length);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Knowledge Entries</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Facts, preferences, and instructions yarnnn keeps in mind every session.
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
            No knowledge entries yet. yarnnn will learn from your conversations, or you can add entries manually.
          </p>
          <button
            onClick={onAdd}
            className="px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium"
          >
            Add Your First Entry
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-card rounded-lg border border-border p-4 space-y-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span><strong className="text-foreground">{entries.length}</strong> entries</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="relative">
                <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search entries..."
                  className="w-full pl-9 pr-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm"
                />
              </div>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value as 'all' | 'fact' | 'preference' | 'instruction')}
                className="w-full px-3 py-2 border border-border rounded-lg bg-background text-foreground text-sm"
              >
                <option value="all">All types ({entries.length})</option>
                <option value="fact">Facts ({typeCounts.fact || 0})</option>
                <option value="preference">Preferences ({typeCounts.preference || 0})</option>
                <option value="instruction">Instructions ({typeCounts.instruction || 0})</option>
              </select>
            </div>
            {(query || typeFilter !== 'all') && (
              <button
                onClick={() => { setQuery(''); setTypeFilter('all'); }}
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                Reset filters
              </button>
            )}
          </div>

          {filteredEntries.length === 0 ? (
            <div className="bg-muted/50 rounded-lg p-6 text-center">
              <p className="text-muted-foreground mb-2">No entries match your current filters.</p>
              <button
                onClick={() => { setQuery(''); setTypeFilter('all'); }}
                className="text-sm text-primary hover:text-primary/80"
              >
                Clear filters
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              {visibleEntries.map((entry) => {
                const entryType = getEntryType(entry);
                const label = TYPE_LABELS[entryType] || entryType;
                const colorClass = TYPE_COLORS[entryType] || 'bg-muted text-muted-foreground';

                return (
                  <div
                    key={entry.id}
                    className="bg-card rounded-lg border border-border p-4 flex items-start gap-3"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={cn("text-xs px-1.5 py-0.5 rounded font-medium", colorClass)}>
                          {label}
                        </span>
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
              {remainingCount > 0 && (
                <div className="pt-2">
                  <button
                    onClick={() => setVisibleCount((prev) => prev + 20)}
                    className="w-full py-2 border border-border rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  >
                    Load 20 more ({remainingCount} remaining)
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main Exported Component
// =============================================================================

export function MemorySection() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeSection, setActiveSection] = useState<Section>('entries');
  const [profile, setProfile] = useState<Profile>({});
  const [entries, setEntries] = useState<MemoryEntry[]>([]);

  const loadData = useCallback(async () => {
    try {
      const [profileResult, entriesResult] = await Promise.all([
        api.profile.get().catch(() => ({})),
        api.userMemories.list().catch(() => []),
      ]);
      setProfile(profileResult || {});
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

  const handleProfileUpdate = async (data: Partial<Profile>) => {
    const result = await api.profile.update(data);
    setProfile(result);
  };

  const handleDeleteEntry = async (id: string) => {
    await api.memories.delete(id);
    setEntries((prev) => prev.filter((e) => e.id !== id));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with refresh */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Memory</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            What YARNNN knows about you — profile, preferences, and learned facts.
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

      {/* Sub-section chips */}
      <div className="flex items-center gap-2">
        {SECTIONS.map((section) => (
          <button
            key={section.id}
            onClick={() => setActiveSection(section.id)}
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
      {activeSection === 'entries' && (
        <EntriesSection
          entries={entries}
          loading={false}
          onAdd={() => router.push(`${HOME_ROUTE}?action=add-memory`)}
          onDelete={handleDeleteEntry}
        />
      )}
      {activeSection === 'profile' && (
        <ProfileSection
          profile={profile}
          loading={false}
          onUpdate={handleProfileUpdate}
        />
      )}
      {activeSection === 'styles' && (
        <StylesSection loading={false} />
      )}
    </div>
  );
}
