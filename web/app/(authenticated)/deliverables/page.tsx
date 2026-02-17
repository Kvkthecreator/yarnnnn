'use client';

/**
 * ADR-037: Deliverables Page (Route-based)
 * ADR-060: Includes suggested deliverables from Conversation Analyst
 *
 * Standalone page for listing and managing recurring deliverables.
 * Core feature page - list, filter, and navigate to deliverable details.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Loader2,
  Play,
  Pause,
  Calendar,
  Clock,
  FileText,
  Plus,
  Send,
  Mail,
  FileCode,
  MessageSquare,
  Sparkles,
  Check,
  X,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import { PlatformFilter, type PlatformFilterValue } from '@/components/ui/PlatformFilter';
import type { Deliverable, DeliverableStatus, SuggestedVersion } from '@/types';

export default function DeliverablesPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [deliverables, setDeliverables] = useState<Deliverable[]>([]);
  const [currentFilter, setCurrentFilter] = useState<DeliverableStatus | 'all'>('all');
  const [platformFilter, setPlatformFilter] = useState<PlatformFilterValue>('all');

  // ADR-060: Suggested deliverables from Conversation Analyst
  const [suggestions, setSuggestions] = useState<SuggestedVersion[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(true);
  const [actioningId, setActioningId] = useState<string | null>(null);

  useEffect(() => {
    loadDeliverables();
    loadSuggestions();
  }, [currentFilter]);

  const loadDeliverables = async () => {
    setLoading(true);
    try {
      const statusParam = currentFilter !== 'all' ? currentFilter : undefined;
      const data = await api.deliverables.list(statusParam);
      setDeliverables(data);
    } catch (err) {
      console.error('Failed to load deliverables:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadSuggestions = async () => {
    setLoadingSuggestions(true);
    try {
      const data = await api.deliverables.listSuggested();
      setSuggestions(data);
    } catch (err) {
      console.error('Failed to load suggestions:', err);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const handleEnableSuggestion = useCallback(async (suggestion: SuggestedVersion) => {
    setActioningId(suggestion.version_id);
    try {
      await api.deliverables.enableSuggested(suggestion.deliverable_id, suggestion.version_id);
      // Remove from suggestions and refresh deliverables
      setSuggestions((prev) => prev.filter((s) => s.version_id !== suggestion.version_id));
      loadDeliverables();
    } catch (err) {
      console.error('Failed to enable suggestion:', err);
    } finally {
      setActioningId(null);
    }
  }, []);

  const handleDismissSuggestion = useCallback(async (suggestion: SuggestedVersion) => {
    setActioningId(suggestion.version_id);
    try {
      await api.deliverables.dismissSuggested(suggestion.deliverable_id, suggestion.version_id);
      setSuggestions((prev) => prev.filter((s) => s.version_id !== suggestion.version_id));
    } catch (err) {
      console.error('Failed to dismiss suggestion:', err);
    } finally {
      setActioningId(null);
    }
  }, []);

  const getStatusIcon = (status: DeliverableStatus) => {
    switch (status) {
      case 'active':
        return <Play className="w-4 h-4 text-green-600" />;
      case 'paused':
        return <Pause className="w-4 h-4 text-amber-500" />;
      case 'archived':
        return <FileText className="w-4 h-4 text-muted-foreground" />;
      default:
        return <Calendar className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getPlatformIcon = (platform?: string) => {
    switch (platform) {
      case 'slack':
        return <MessageSquare className="w-3 h-3" />;
      case 'gmail':
        return <Mail className="w-3 h-3" />;
      case 'notion':
        return <FileCode className="w-3 h-3" />;
      default:
        return <Send className="w-3 h-3" />;
    }
  };

  const formatSchedule = (schedule: Deliverable['schedule']) => {
    const freq = schedule.frequency;
    const day = schedule.day;
    const time = schedule.time || '09:00';

    let timeStr = time;
    try {
      const [hour, minute] = time.split(':').map(Number);
      const ampm = hour >= 12 ? 'PM' : 'AM';
      const h12 = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour;
      timeStr = `${h12}:${minute.toString().padStart(2, '0')} ${ampm}`;
    } catch {
      // Keep original
    }

    switch (freq) {
      case 'daily':
        return `Daily at ${timeStr}`;
      case 'weekly':
        return `Weekly on ${day ? day.charAt(0).toUpperCase() + day.slice(1) : 'Monday'} at ${timeStr}`;
      case 'biweekly':
        return `Every 2 weeks on ${day ? day.charAt(0).toUpperCase() + day.slice(1) : 'Monday'}`;
      case 'monthly':
        return `Monthly on the ${day || '1st'} at ${timeStr}`;
      default:
        return freq;
    }
  };

  const formatDestination = (d: Deliverable) => {
    if (!d.destination) return null;
    const platform = d.destination.platform;
    const isAuto = d.governance === 'semi_auto' || d.governance === 'full_auto';

    return {
      platform,
      isAuto,
      icon: getPlatformIcon(platform),
    };
  };

  const filteredDeliverables = useMemo(() => {
    if (platformFilter === 'all') return deliverables;
    return deliverables.filter((d) => d.destination?.platform === platformFilter);
  }, [deliverables, platformFilter]);

  const platformCounts = useMemo(() => {
    const counts: Partial<Record<PlatformFilterValue, number>> = { all: deliverables.length };
    deliverables.forEach((d) => {
      if (d.destination?.platform) {
        const platform = d.destination.platform as PlatformFilterValue;
        counts[platform] = (counts[platform] || 0) + 1;
      }
    });
    return counts;
  }, [deliverables]);

  const availablePlatforms = useMemo(() => {
    const platforms: PlatformFilterValue[] = ['all'];
    if (platformCounts.slack) platforms.push('slack');
    if (platformCounts.notion) platforms.push('notion');
    if (platformCounts.gmail) platforms.push('gmail');
    return platforms;
  }, [platformCounts]);

  const hasPlatformTargets = availablePlatforms.length > 1;

  const handleDeliverableClick = (deliverableId: string) => {
    router.push(`/deliverables/${deliverableId}`);
  };

  const handleCreateNew = () => {
    router.push('/deliverables/new');
  };

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-4xl mx-auto px-4 md:px-6 py-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Calendar className="w-6 h-6" />
          <h1 className="text-2xl font-bold">Deliverables</h1>
        </div>
        <p className="text-muted-foreground mb-6">
          Recurring outputs that are automatically generated on schedule.
        </p>

        {/* Filters and actions */}
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-muted-foreground">
            {loading ? 'Loading...' : `${filteredDeliverables.length} deliverable${filteredDeliverables.length === 1 ? '' : 's'}`}
          </p>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              {(['all', 'active', 'paused'] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setCurrentFilter(f)}
                  className={`px-3 py-1.5 text-xs rounded-full border ${
                    currentFilter === f
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'border-border hover:bg-muted'
                  }`}
                >
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
            <button
              onClick={handleCreateNew}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted"
            >
              <Plus className="w-3.5 h-3.5" />
              New
            </button>
          </div>
        </div>

        {/* Platform filter */}
        {!loading && hasPlatformTargets && (
          <div className="flex items-center gap-2 mb-4">
            <span className="text-xs text-muted-foreground">Target platform:</span>
            <PlatformFilter
              value={platformFilter}
              onChange={setPlatformFilter}
              availablePlatforms={availablePlatforms}
              counts={platformCounts}
            />
          </div>
        )}

        {/* ADR-060: Suggested Deliverables */}
        {!loadingSuggestions && suggestions.length > 0 && (
          <div className="mb-6 p-4 border border-purple-200 dark:border-purple-800 bg-purple-50 dark:bg-purple-950/30 rounded-lg">
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />
              <span className="text-sm font-medium text-purple-900 dark:text-purple-100">
                Suggested for you
              </span>
              <span className="text-xs text-purple-600 dark:text-purple-400">
                Based on your recent conversations
              </span>
            </div>
            <div className="space-y-2">
              {suggestions.map((suggestion) => (
                <div
                  key={suggestion.version_id}
                  className="flex items-center justify-between p-3 bg-white dark:bg-gray-900 border border-purple-100 dark:border-purple-800 rounded-md"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{suggestion.deliverable_title}</p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      {suggestion.deliverable_type && (
                        <span className="capitalize">
                          {suggestion.deliverable_type.replace(/_/g, ' ')}
                        </span>
                      )}
                      {suggestion.analyst_metadata?.confidence && (
                        <>
                          <span>·</span>
                          <span>
                            {Math.round(suggestion.analyst_metadata.confidence * 100)}% confidence
                          </span>
                        </>
                      )}
                      {suggestion.analyst_metadata?.detection_reason && (
                        <>
                          <span>·</span>
                          <span className="truncate max-w-[200px]">
                            {suggestion.analyst_metadata.detection_reason}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 ml-3">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEnableSuggestion(suggestion);
                      }}
                      disabled={actioningId === suggestion.version_id}
                      className="p-1.5 text-green-600 hover:bg-green-50 dark:hover:bg-green-950/30 rounded-md transition-colors disabled:opacity-50"
                      title="Enable this deliverable"
                    >
                      {actioningId === suggestion.version_id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Check className="w-4 h-4" />
                      )}
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDismissSuggestion(suggestion);
                      }}
                      disabled={actioningId === suggestion.version_id}
                      className="p-1.5 text-muted-foreground hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 rounded-md transition-colors disabled:opacity-50"
                      title="Dismiss suggestion"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : filteredDeliverables.length === 0 ? (
          <div className="text-center py-12">
            <Calendar className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground mb-4">
              {deliverables.length === 0
                ? 'No deliverables yet'
                : `No deliverables target ${platformFilter}`}
            </p>
            {deliverables.length === 0 && (
              <button
                onClick={handleCreateNew}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
              >
                <Plus className="w-4 h-4" />
                Create your first deliverable
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {filteredDeliverables.map((d) => {
              const dest = formatDestination(d);
              return (
                <button
                  key={d.id}
                  onClick={() => handleDeliverableClick(d.id)}
                  className="w-full p-4 border border-border rounded-lg text-left hover:bg-muted cursor-pointer"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(d.status)}
                      <div>
                        <span className="text-sm font-medium">{d.title}</span>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span>{d.deliverable_type.replace(/_/g, ' ')}</span>
                          <span>·</span>
                          <span>{formatSchedule(d.schedule)}</span>
                          {dest && (
                            <>
                              <span>·</span>
                              <span className="inline-flex items-center gap-1">
                                {dest.icon}
                                <span className="capitalize">{dest.platform}</span>
                                {dest.isAuto && <span className="text-green-600">(auto)</span>}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      {d.next_run_at && (
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Clock className="w-3 h-3" />
                          <span>Next: {formatDistanceToNow(new Date(d.next_run_at), { addSuffix: true })}</span>
                        </div>
                      )}
                      <span className="text-xs text-muted-foreground">
                        Created {formatDistanceToNow(new Date(d.created_at), { addSuffix: true })}
                      </span>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
