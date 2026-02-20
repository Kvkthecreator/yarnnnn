'use client';

/**
 * CalendarView Component
 *
 * Visual calendar display using FullCalendar.
 * Shows user's Google Calendar events in month/week view.
 *
 * Features:
 * - Month and week views
 * - Click event to see details
 * - Responsive design
 * - Dark mode support
 */

import { useState, useEffect, useCallback } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { EventClickArg, DatesSetArg } from '@fullcalendar/core';
import { Loader2, MapPin, Users, Video, X, ExternalLink, ChevronDown, Calendar } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';

interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  attendees: Array<{ email: string; name?: string; self?: boolean }>;
  location?: string;
  description?: string;
  meeting_link?: string;
  recurring: boolean;
}

interface CalendarOption {
  id: string;
  summary: string;
  primary?: boolean;
}

interface CalendarViewProps {
  calendarId?: string;
  calendars?: CalendarOption[];
  onCalendarChange?: (calendarId: string) => void;
  className?: string;
}

export function CalendarView({ calendarId = 'primary', calendars = [], onCalendarChange, className }: CalendarViewProps) {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [showCalendarPicker, setShowCalendarPicker] = useState(false);

  // Find the current calendar name
  const currentCalendar = calendars.find(c => c.id === calendarId);
  const currentCalendarName = currentCalendar?.summary || calendarId;

  const fetchEvents = useCallback(async (start: Date, end: Date) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.integrations.getCalendarEvents({
        calendarId,
        timeMin: start.toISOString(),
        timeMax: end.toISOString(),
        maxResults: 100,
      });
      setEvents(result.events);
    } catch (err) {
      console.error('Failed to fetch calendar events:', err);
      setError('Failed to load calendar events');
    } finally {
      setLoading(false);
    }
  }, [calendarId]);

  // Initial load - fetch current month
  useEffect(() => {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), 1);
    const end = new Date(now.getFullYear(), now.getMonth() + 2, 0);
    fetchEvents(start, end);
  }, [fetchEvents]);

  const handleDatesSet = (arg: DatesSetArg) => {
    fetchEvents(arg.start, arg.end);
  };

  const handleEventClick = (arg: EventClickArg) => {
    const event = events.find(e => e.id === arg.event.id);
    if (event) {
      setSelectedEvent(event);
    }
  };

  // Convert events to FullCalendar format
  const fullCalendarEvents = events.map(event => ({
    id: event.id,
    title: event.title,
    start: event.start,
    end: event.end,
    extendedProps: {
      attendees: event.attendees,
      location: event.location,
      description: event.description,
      meeting_link: event.meeting_link,
      recurring: event.recurring,
    },
  }));

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className={cn('relative', className)}>
      {/* Calendar Selector Header */}
      {calendars.length > 0 && (
        <div className="mb-4 flex items-center justify-between">
          <div className="relative">
            <button
              onClick={() => setShowCalendarPicker(v => !v)}
              className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg hover:bg-muted/50 transition-colors"
            >
              <Calendar className="w-4 h-4 text-blue-500" />
              <span className="text-sm font-medium">{currentCalendarName}</span>
              {currentCalendar?.primary && (
                <span className="text-xs text-muted-foreground">(primary)</span>
              )}
              <ChevronDown className={cn('w-4 h-4 text-muted-foreground transition-transform', showCalendarPicker && 'rotate-180')} />
            </button>

            {showCalendarPicker && (
              <div className="absolute z-20 top-full left-0 mt-1 bg-background border border-border rounded-lg shadow-lg overflow-hidden min-w-[250px]">
                {calendars.map((cal) => (
                  <button
                    key={cal.id}
                    onClick={() => {
                      setShowCalendarPicker(false);
                      if (onCalendarChange) {
                        onCalendarChange(cal.id);
                      }
                    }}
                    className={cn(
                      'w-full flex items-center justify-between px-4 py-2.5 text-left hover:bg-muted transition-colors',
                      cal.id === calendarId && 'bg-muted/50'
                    )}
                  >
                    <div>
                      <p className="text-sm font-medium">
                        {cal.summary}
                        {cal.primary && <span className="ml-1.5 text-xs text-muted-foreground">(primary)</span>}
                      </p>
                    </div>
                    {cal.id === calendarId && (
                      <span className="w-2 h-2 rounded-full bg-primary shrink-0" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          <p className="text-xs text-muted-foreground">
            {events.length} event{events.length !== 1 ? 's' : ''} in view
          </p>
        </div>
      )}

      {loading && (
        <div className="absolute inset-0 bg-background/50 flex items-center justify-center z-10">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Empty state when no events */}
      {!loading && events.length === 0 && (
        <div className="mb-4 p-4 border border-dashed border-border rounded-lg text-center">
          <p className="text-sm text-muted-foreground">
            No events found in this calendar for the current view.
          </p>
          {calendars.length > 1 && (
            <p className="text-xs text-muted-foreground mt-1">
              Try selecting a different calendar above.
            </p>
          )}
        </div>
      )}

      <div className="calendar-container">
        <FullCalendar
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
          initialView="dayGridMonth"
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek',
          }}
          events={fullCalendarEvents}
          eventClick={handleEventClick}
          datesSet={handleDatesSet}
          height="auto"
          eventDisplay="block"
          dayMaxEvents={3}
          moreLinkClick="popover"
          weekends={true}
          nowIndicator={true}
          eventClassNames="cursor-pointer"
        />
      </div>

      {/* Event Detail Modal */}
      {selectedEvent && (
        <EventDetailModal
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}

      {/* Custom styles for FullCalendar */}
      <style jsx global>{`
        .calendar-container {
          --fc-border-color: hsl(var(--border));
          --fc-button-bg-color: hsl(var(--primary));
          --fc-button-border-color: hsl(var(--primary));
          --fc-button-hover-bg-color: hsl(var(--primary) / 0.9);
          --fc-button-hover-border-color: hsl(var(--primary) / 0.9);
          --fc-button-active-bg-color: hsl(var(--primary) / 0.8);
          --fc-button-active-border-color: hsl(var(--primary) / 0.8);
          --fc-event-bg-color: hsl(var(--primary));
          --fc-event-border-color: hsl(var(--primary));
          --fc-today-bg-color: hsl(var(--primary) / 0.05);
          --fc-page-bg-color: hsl(var(--background));
          --fc-neutral-bg-color: hsl(var(--muted));
          --fc-neutral-text-color: hsl(var(--muted-foreground));
        }

        .calendar-container .fc {
          font-family: inherit;
        }

        .calendar-container .fc-toolbar-title {
          font-size: 1.25rem;
          font-weight: 600;
          color: hsl(var(--foreground));
        }

        .calendar-container .fc-button {
          font-size: 0.875rem;
          padding: 0.375rem 0.75rem;
          border-radius: 0.375rem;
        }

        .calendar-container .fc-button-primary:not(:disabled).fc-button-active,
        .calendar-container .fc-button-primary:not(:disabled):active {
          background-color: hsl(var(--primary) / 0.8);
          border-color: hsl(var(--primary) / 0.8);
        }

        .calendar-container .fc-daygrid-day-number,
        .calendar-container .fc-col-header-cell-cushion {
          color: hsl(var(--foreground));
          text-decoration: none;
        }

        .calendar-container .fc-event {
          border-radius: 0.25rem;
          font-size: 0.75rem;
          padding: 0.125rem 0.25rem;
        }

        .calendar-container .fc-event-title {
          font-weight: 500;
        }

        .calendar-container .fc-daygrid-day.fc-day-today {
          background-color: hsl(var(--primary) / 0.05);
        }

        .calendar-container .fc-timegrid-slot-label {
          font-size: 0.75rem;
          color: hsl(var(--muted-foreground));
        }

        .calendar-container .fc-timegrid-axis-cushion {
          color: hsl(var(--muted-foreground));
        }

        .calendar-container .fc-scrollgrid {
          border-color: hsl(var(--border));
        }

        .calendar-container .fc-theme-standard td,
        .calendar-container .fc-theme-standard th {
          border-color: hsl(var(--border));
        }

        .calendar-container .fc-more-link {
          color: hsl(var(--primary));
          font-weight: 500;
        }

        .dark .calendar-container {
          --fc-page-bg-color: hsl(var(--background));
        }
      `}</style>
    </div>
  );
}

// Event Detail Modal Component
function EventDetailModal({
  event,
  onClose,
}: {
  event: CalendarEvent;
  onClose: () => void;
}) {
  const startDate = new Date(event.start);
  const endDate = new Date(event.end);
  const isAllDay = !event.start.includes('T');
  const otherAttendees = event.attendees.filter(a => !a.self);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-background border border-border rounded-lg shadow-xl max-w-md w-full mx-4 max-h-[80vh] overflow-auto">
        {/* Header */}
        <div className="flex items-start justify-between p-4 border-b border-border">
          <div className="pr-8">
            <h3 className="text-lg font-semibold text-foreground">
              {event.title}
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              {isAllDay ? (
                format(startDate, 'EEEE, MMMM d, yyyy')
              ) : (
                <>
                  {format(startDate, 'EEEE, MMMM d, yyyy')}
                  <br />
                  {format(startDate, 'h:mm a')} – {format(endDate, 'h:mm a')}
                </>
              )}
            </p>
            {event.recurring && (
              <span className="inline-block mt-2 text-xs bg-muted px-2 py-0.5 rounded">
                Recurring
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-muted rounded"
          >
            <X className="w-5 h-5 text-muted-foreground" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Meeting Link */}
          {event.meeting_link && (
            <div className="flex items-center gap-3">
              <Video className="w-4 h-4 text-blue-500 shrink-0" />
              <a
                href={event.meeting_link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary hover:underline flex items-center gap-1"
              >
                Join meeting
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}

          {/* Location */}
          {event.location && (
            <div className="flex items-start gap-3">
              <MapPin className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
              <p className="text-sm text-foreground">{event.location}</p>
            </div>
          )}

          {/* Attendees */}
          {otherAttendees.length > 0 && (
            <div className="flex items-start gap-3">
              <Users className="w-4 h-4 text-muted-foreground shrink-0 mt-0.5" />
              <div className="text-sm">
                <p className="text-muted-foreground mb-1">
                  {otherAttendees.length} attendee{otherAttendees.length !== 1 ? 's' : ''}
                </p>
                <div className="space-y-1">
                  {otherAttendees.slice(0, 5).map((attendee, i) => (
                    <p key={i} className="text-foreground">
                      {attendee.name || attendee.email}
                    </p>
                  ))}
                  {otherAttendees.length > 5 && (
                    <p className="text-muted-foreground">
                      +{otherAttendees.length - 5} more
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Description */}
          {event.description && (
            <div className="pt-2 border-t border-border">
              <p className="text-sm text-foreground whitespace-pre-wrap">
                {event.description.length > 300
                  ? event.description.slice(0, 300) + '...'
                  : event.description}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
