'use client';

/**
 * Calendar Context Page
 *
 * Calendar is different from Slack/Gmail/Notion:
 * - Events are queried on-demand by TP (no background sync)
 * - No "sources to select" — TP can access any calendar the user grants
 * - User sets a DEFAULT calendar for TP-created events (designated_calendar_id)
 * - Full CRUD: list, get, create, update, delete
 */

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Calendar,
  Check,
  CheckCircle2,
  ChevronDown,
  Loader2,
  CalendarDays,
  List,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type { IntegrationData } from '@/types';
import { PlatformNotConnected } from '@/components/context/PlatformNotConnected';
import { PlatformHeader } from '@/components/context/PlatformHeader';
import { PlatformSyncActivity } from '@/components/context/PlatformSyncActivity';
import { ConnectionDetailsModal } from '@/components/context/ConnectionDetailsModal';
import { CalendarView } from '@/components/calendar/CalendarView';

interface CalendarOption {
  id: string;
  summary: string;
  primary?: boolean;
}

const CAPABILITIES = [
  'Ask about upcoming meetings, schedules, and free time',
  'Create new events on your calendar',
  'Update existing events — reschedule, add attendees, change details',
  'Delete events with your confirmation',
  'Reason about scheduling conflicts and find open slots',
];

const BENEFITS = [
  ...CAPABILITIES,
];

export default function CalendarContextPage() {
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [integration, setIntegration] = useState<IntegrationData | null>(null);
  const [calendars, setCalendars] = useState<CalendarOption[]>([]);
  const [designatedCalendarId, setDesignatedCalendarId] = useState<string | null>(null);
  const [designatedCalendarName, setDesignatedCalendarName] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showPicker, setShowPicker] = useState(false);
  const [showConnectionModal, setShowConnectionModal] = useState(false);
  const [viewMode, setViewMode] = useState<'calendar' | 'details'>('calendar');
  const [activeCalendarId, setActiveCalendarId] = useState<string>('primary');
  const [justConnected, setJustConnected] = useState(false);

  // Handle OAuth redirect: detect first-connect, then clean URL
  useEffect(() => {
    if (searchParams.get('status') === 'connected') {
      setJustConnected(true);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [searchParams]);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (designatedCalendarId) {
      setActiveCalendarId(designatedCalendarId);
    } else if (calendars.length > 0) {
      const primary = calendars.find(c => c.primary);
      setActiveCalendarId(primary?.id || calendars[0].id);
    }
  }, [designatedCalendarId, calendars]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [integrationResult, calendarsResult, designatedResult] = await Promise.all([
        api.integrations.get('calendar').catch(() => null),
        api.integrations.listGoogleCalendars().catch(() => ({ calendars: [] })),
        api.integrations.getGoogleDesignatedSettings().catch(() => ({
          designated_calendar_id: null,
          designated_calendar_name: null,
        })),
      ]);

      setIntegration(integrationResult as IntegrationData | null);
      setCalendars(calendarsResult?.calendars || []);
      setDesignatedCalendarId(designatedResult?.designated_calendar_id || null);
      setDesignatedCalendarName(designatedResult?.designated_calendar_name || null);
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

  // Loading
  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Not connected
  if (!integration) {
    return (
      <PlatformNotConnected
        platform="calendar"
        label="Calendar"
        icon={<Calendar className="w-6 h-6" />}
        bgColor="bg-blue-50 dark:bg-blue-950/30"
        color="text-blue-500"
        benefits={BENEFITS}
        oauthProvider="google"
      />
    );
  }

  // Connected
  const currentCalendar = designatedCalendarId
    ? calendars.find(c => c.id === designatedCalendarId) || { id: designatedCalendarId, summary: designatedCalendarName || designatedCalendarId }
    : calendars.find(c => c.primary) || null;

  const viewToggle = (
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
  );

  return (
    <div className="h-full overflow-auto">
      <PlatformHeader
        label="Calendar"
        icon={<Calendar className="w-5 h-5" />}
        bgColor="bg-blue-50 dark:bg-blue-950/30"
        color="text-blue-500"
        onConnectionDetails={() => setShowConnectionModal(true)}
        rightContent={viewToggle}
      />

      {/* First-connect banner */}
      {justConnected && (
        <div className="mx-6 mt-6 p-4 bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-800 rounded-lg">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-green-800 dark:text-green-300">
                Calendar Connected
              </p>
              <p className="text-sm text-green-700 dark:text-green-400 mt-0.5">
                TP can now access your calendar. Set a default calendar below for new events.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Calendar View */}
      {viewMode === 'calendar' && (
        <div className="p-4 md:p-6 max-w-6xl space-y-6">
          <PlatformSyncActivity
            platform="calendar"
            liveQueryMode
          />

          <CalendarView
            calendarId={activeCalendarId}
            calendars={calendars}
            onCalendarChange={(calendarId: string) => setActiveCalendarId(calendarId)}
          />
        </div>
      )}

      {/* Details View */}
      {viewMode === 'details' && (
        <div className="p-4 md:p-6 space-y-6 max-w-4xl">
          {/* Default Calendar */}
          <section className="rounded-xl border border-border bg-card p-4 md:p-5">
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
                              ? `${currentCalendar.summary}${(currentCalendar as CalendarOption).primary ? ' (primary)' : ''}`
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
          <section className="rounded-xl border border-border bg-card p-4 md:p-5">
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

          <PlatformSyncActivity
            platform="calendar"
            liveQueryMode
          />
        </div>
      )}

      {/* Connection Details Modal */}
      <ConnectionDetailsModal
        isOpen={showConnectionModal}
        onClose={() => setShowConnectionModal(false)}
        integration={integration}
        platformLabel="Calendar"
        platformIcon={<Calendar className="w-5 h-5 text-blue-500" />}
        onDisconnect={() => setIntegration(null)}
      />
    </div>
  );
}
