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
  Briefcase,
  Edit2,
  Trash2,
  CheckCircle2,
} from 'lucide-react';
import Link from 'next/link';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { HOME_ROUTE } from '@/lib/routes';
import ReactMarkdown from 'react-markdown';

// =============================================================================
// Types
// =============================================================================

type Section = 'entries' | 'profile' | 'brand';

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
// Section Navigation
// =============================================================================

const SECTIONS: { id: Section; label: string; icon: React.ReactNode }[] = [
  { id: 'entries', label: 'Entries', icon: <BookOpen className="w-4 h-4" /> },
  { id: 'profile', label: 'Profile', icon: <User className="w-4 h-4" /> },
  { id: 'brand', label: 'Brand', icon: <Palette className="w-4 h-4" /> },
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

// (TopicsSection deleted — topics layer dissolved, projects are workstreams directly)

// =============================================================================
// Brand Section (ADR-132 — replaces per-platform Preferences)
// =============================================================================

export function BrandSection() {
  const [brandContent, setBrandContent] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.brand.get().then((data) => {
      if (data.exists && data.content) setBrandContent(data.content);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.brand.save(draft);
      setBrandContent(draft);
      setEditing(false);
    } catch (err) {
      console.error('Failed to save brand:', err);
    } finally { setSaving(false); }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Brand</h2>
          {brandContent && !editing && (
            <button
              onClick={() => { setDraft(brandContent); setEditing(true); }}
              className="text-sm text-primary hover:underline"
            >
              Edit
            </button>
          )}
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          Your brand identity — colors, tone, voice. Applied to all agent outputs.
        </p>
      </div>

      {editing ? (
        <div className="space-y-3">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={14}
            className="w-full text-sm px-3 py-2 rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/30 font-mono"
          />
          <div className="flex items-center gap-3">
            <button onClick={handleSave} disabled={saving} className="text-sm font-medium text-primary hover:underline disabled:opacity-50">
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button onClick={() => setEditing(false)} className="text-sm text-muted-foreground hover:text-foreground">
              Cancel
            </button>
          </div>
        </div>
      ) : brandContent ? (
        <div className="prose prose-sm dark:prose-invert max-w-none border border-border rounded-lg p-4">
          <ReactMarkdown>{brandContent}</ReactMarkdown>
        </div>
      ) : (
        <div className="border border-dashed border-border rounded-lg p-6 text-center">
          <Palette className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
          <p className="text-sm text-muted-foreground mb-3">No brand defined yet</p>
          <button
            onClick={() => {
              setDraft('# Brand: My Company\n\n## Colors\n- Primary: #000000\n- Accent: #3b82f6\n\n## Tone\nProfessional and concise\n\n## Voice\nDirect, honest, no fluff\n');
              setEditing(true);
            }}
            className="text-sm font-medium text-primary hover:underline"
          >
            Set up your brand
          </button>
        </div>
      )}
    </div>
  );
}


// (StylesSection deleted — ADR-133: preferences dissolved into BRAND.md + IDENTITY.md)

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
      {activeSection === 'brand' && (
        <BrandSection />
      )}
    </div>
  );
}
