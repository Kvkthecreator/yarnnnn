'use client';

/**
 * Calendar Context Page
 *
 * ADR-046: Google Calendar integration.
 *
 * Calendar is different from Slack/Gmail/Notion:
 * - Events are queried on-demand by TP (no background sync)
 * - No "sources to select" — TP can access any calendar the user grants
 * - User sets a DEFAULT calendar for TP-created events (designated_calendar_id)
 * - Full CRUD: list, get, create, update, delete (TP handles scheduling intelligence)
 *
 * This page handles:
 * 1. Not connected → Connect CTA (Google OAuth, same as Gmail)
 * 2. Connected → Designated calendar picker + capabilities summary + deliverables
 */

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Calendar,
  Check,
  ChevronDown,
  Loader2,
  Plus,
  Sparkles,
  CalendarDays,
  List,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { ConnectionDetailsModal } from '@/components/context/ConnectionDetailsModal';
import { CalendarView } from '@/components/calendar/CalendarView';

interface CalendarOption {
  id: string;
  summary: string;
  primary?: boolean;
}

interface IntegrationData {
  id: string;
  provider: string;
  status: string;
  workspace_name: string | null;
  created_at: string;
  last_used_at: string | null;
  metadata?: {
    email?: string;
    [key: string]: unknown;
  };
}

interface PlatformDeliverable {
  id: string;
  title: string;
  status: string;
  next_run_at?: string | null;
  deliverable_type: string;
  destination?: { platform?: string };
}

const CAPABILITIES = [
  'Ask about upcoming meetings, schedules, and free time',
  'Create new events on your calendar',
  'Update existing events — reschedule, add attendees, change details',
  'Delete events with your confirmation',
  'Reason about scheduling conflicts and find open slots',
];

export default function CalendarContextPage() {
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [integration, setIntegration] = useState<IntegrationData | null>(null);
  const [calendars, setCalendars] = useState<CalendarOption[]>([]);
  const [designatedCalendarId, setDesignatedCalendarId] = useState<string | null>(null);
  const [designatedCalendarName, setDesignatedCalendarName] = useState<string | null>(null);
  const [deliverables, setDeliverables] = useState<PlatformDeliverable[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showPicker, setShowPicker] = useState(false);
  const [showConnectionModal, setShowConnectionModal] = useState(false);
  const [viewMode, setViewMode] = useState<'calendar' | 'details'>('calendar');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [integrationResult, calendarsResult, designatedResult, deliverablesResult] = await Promise.all([
        api.integrations.get('google').catch(() => null),
        api.integrations.listGoogleCalendars().catch(() => ({ calendars: [] })),
        api.integrations.getGoogleDesignatedSettings().catch(() => ({
          designated_calendar_id: null,
          designated_calendar_name: null,
        })),
        api.deliverables.list().catch(() => []),
      ]);

      setIntegration(integrationResult);
      setCalendars(calendarsResult?.calendars || []);
      setDesignatedCalendarId(designatedResult?.designated_calendar_id || null);
      setDesignatedCalendarName(designatedResult?.designated_calendar_name || null);

      const calendarDeliverables = (deliverablesResult || []).filter(
        (d: PlatformDeliverable) => ['calendar', 'google'].includes(d.destination?.platform || '')
      );
      setDeliverables(calendarDeliverables);
    } catch (err) {
      console.error('Failed to load calendar data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectCalendar = async (cal: CalendarOption) => {
    setShowPicker(false);
    setSaving(true);
    setSaved(false);
    try {
      await api.integrations.setGoogleDesignatedSettings({
        calendarId: cal.id,
        calendarName: cal.summary,
      });
      setDesignatedCalendarId(cal.id);
      setDesignatedCalendarName(cal.summary);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error('Failed to set designated calendar:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateDeliverable = () => {
    router.push('/deliverables/new?platform=calendar');
  };

  const handleConnectionDisconnect = () => {
    setIntegration(null);
  };

  // =============================================================================
  // Render: Loading
  // =============================================================================

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // =============================================================================
  // Render: Not Connected
  // =============================================================================

  if (!integration) {
    return (
      <div className="h-full overflow-auto">
        <div className="border-b border-border px-6 py-4">
          <button
            onClick={() => router.push('/context')}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Context
          </button>
        </div>
        <div className="p-6 max-w-lg">
          <div className="flex items-center gap-4 mb-6">
            <div className="w-14 h-14 rounded-xl flex items-center justify-center bg-blue-50 dark:bg-blue-950/30">
              <Calendar className="w-7 h-7 text-blue-500" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-foreground">Calendar</h2>
              <p className="text-sm text-muted-foreground">Not connected</p>
            </div>
          </div>

          <div className="mb-6 space-y-2">
            {CAPABILITIES.map((capability) => (
              <div key={capability} className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 shrink-0" />
                {capability}
              </div>
            ))}
          </div>

          <p className="text-sm text-muted-foreground mb-4">
            Calendar uses your Google account — the same connection as Gmail.
            Connecting here grants access to both.
          </p>

          <button
            onClick={async () => {
              try {
                const { authorization_url } = await api.integrations.getAuthorizationUrl('google');
                window.location.href = authorization_url;
              } catch {
                router.push('/settings?tab=integrations');
              }
            }}
            className="px-5 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            Connect Google Calendar
          </button>
        </div>
      </div>
    );
  }

  // =============================================================================
  // Render: Connected
  // =============================================================================

  const currentCalendar = designatedCalendarId
    ? calendars.find(c => c.id === designatedCalendarId) || { id: designatedCalendarId, summary: designatedCalendarName || designatedCalendarId }
    : calendars.find(c => c.primary) || null;

  const activeCalendarId = designatedCalendarId || currentCalendar?.id || 'primary';

  return (
    <div className="h-full overflow-auto">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/context')}
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="w-4 h-4" />
              Context
            </button>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full flex items-center justify-center bg-blue-50 dark:bg-blue-950/30">
                <Calendar className="w-5 h-5 text-blue-500" />
              </div>
              <h1 className="text-lg font-semibold">Calendar</h1>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {/* View Toggle */}
            <div className="flex items-center border border-border rounded-lg p-0.5">
              <button
                onClick={() => setViewMode('calendar')}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors',
                  viewMode === 'calendar'
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                <CalendarDays className="w-4 h-4" />
                Calendar
              </button>
              <button
                onClick={() => setViewMode('details')}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors',
                  viewMode === 'details'
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                <List className="w-4 h-4" />
                Details
              </button>
            </div>
            <button
              onClick={() => setShowConnectionModal(true)}
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Connection details
            </button>
          </div>
        </div>
      </div>

      {/* Calendar View */}
      {viewMode === 'calendar' && (
        <div className="p-6">
          <CalendarView calendarId={activeCalendarId} />
        </div>
      )}

      {/* Details View */}
      {viewMode === 'details' && (
      <div className="p-6 space-y-8 max-w-2xl">

        {/* Default Calendar */}
        <section>
          <h2 className="text-base font-semibold mb-1">Default calendar</h2>
          <p className="text-sm text-muted-foreground mb-4">
            Where TP creates new events. Events are queried live — no sync needed.
            {calendars.length > 0 && ` ${calendars.length} calendar${calendars.length === 1 ? '' : 's'} available.`}
          </p>

          {calendars.length === 0 ? (
            <div className="border border-dashed border-border rounded-lg p-6 text-center text-sm text-muted-foreground">
              No calendars found. Make sure Google Calendar access was granted when connecting.
            </div>
          ) : (
            <div className="space-y-2">
              <div className="relative">
                <button
                  onClick={() => setShowPicker(v => !v)}
                  className="w-full flex items-center justify-between p-3 border border-border rounded-lg hover:bg-muted/50 transition-colors text-left"
                >
                  <div className="flex items-center gap-3">
                    <Calendar className="w-4 h-4 text-blue-500 shrink-0" />
                    <div>
                      <p className="text-sm font-medium">
                        {designatedCalendarId
                          ? (designatedCalendarName || designatedCalendarId)
                          : currentCalendar
                            ? `${currentCalendar.summary}${currentCalendar.primary ? ' (primary)' : ''}`
                            : 'Select a calendar'}
                      </p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {designatedCalendarId ? 'Default for new events' : 'Using primary calendar'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {saving && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
                    {saved && <Check className="w-4 h-4 text-green-500" />}
                    <ChevronDown className={cn('w-4 h-4 text-muted-foreground transition-transform', showPicker && 'rotate-180')} />
                  </div>
                </button>

                {showPicker && (
                  <div className="absolute z-10 top-full left-0 right-0 mt-1 bg-background border border-border rounded-lg shadow-lg overflow-hidden">
                    {calendars.map((cal) => (
                      <button
                        key={cal.id}
                        onClick={() => handleSelectCalendar(cal)}
                        className="w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-muted transition-colors"
                      >
                        <div>
                          <p className="text-sm font-medium">
                            {cal.summary}
                            {cal.primary && <span className="ml-1.5 text-xs text-muted-foreground">(primary)</span>}
                          </p>
                          <p className="text-xs text-muted-foreground truncate max-w-xs">{cal.id}</p>
                        </div>
                        {designatedCalendarId === cal.id && (
                          <Check className="w-4 h-4 text-primary shrink-0 ml-2" />
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {saved && (
                <p className="text-xs text-green-600 dark:text-green-400">
                  Default calendar saved.
                </p>
              )}
            </div>
          )}
        </section>

        {/* Capabilities */}
        <section>
          <h2 className="text-base font-semibold mb-3">What TP can do</h2>
          <div className="border border-border rounded-lg divide-y divide-border">
            {CAPABILITIES.map((capability) => (
              <div key={capability} className="flex items-center gap-3 px-4 py-3">
                <Check className="w-4 h-4 text-green-500 shrink-0" />
                <p className="text-sm text-foreground">{capability}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            TP queries your calendar live in conversation — no background sync.
          </p>
        </section>

        {/* Deliverables */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-semibold">Deliverables → Calendar</h2>
              <p className="text-sm text-muted-foreground mt-0.5">Scheduled outputs that create or update calendar events.</p>
            </div>
            <button
              onClick={handleCreateDeliverable}
              className="text-sm text-primary hover:underline flex items-center gap-1 shrink-0"
            >
              <Plus className="w-3 h-3" />
              New
            </button>
          </div>

          {deliverables.length === 0 ? (
            <div className="border border-dashed border-border rounded-lg p-6 text-center">
              <p className="text-sm text-muted-foreground">No deliverables targeting Calendar yet.</p>
              <button
                onClick={handleCreateDeliverable}
                className="mt-2 text-sm text-primary hover:underline"
              >
                Create your first
              </button>
            </div>
          ) : (
            <div className="border border-border rounded-lg divide-y divide-border">
              {deliverables.map((d) => (
                <button
                  key={d.id}
                  onClick={() => router.push(`/deliverables/${d.id}`)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-muted/50 transition-colors"
                >
                  <div>
                    <p className="text-sm font-medium">{d.title}</p>
                    <p className="text-xs text-muted-foreground capitalize">{d.status}</p>
                  </div>
                  <Sparkles className="w-4 h-4 text-muted-foreground shrink-0" />
                </button>
              ))}
            </div>
          )}
        </section>
      </div>
      )}

      {/* Connection Details Modal */}
      <ConnectionDetailsModal
        isOpen={showConnectionModal}
        onClose={() => setShowConnectionModal(false)}
        integration={integration}
        platformLabel="Calendar"
        platformIcon={<Calendar className="w-5 h-5 text-blue-500" />}
        onDisconnect={handleConnectionDisconnect}
      />
    </div>
  );
}
