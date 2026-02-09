'use client';

/**
 * DeliverableCreateWizard - ADR-032 Destination-First Creation Flow
 *
 * 4-step wizard for creating deliverables:
 * 1. Destination (where does this go?)
 * 2. Type (what kind of content?)
 * 3. Sources (what context informs it?)
 * 4. Schedule (when should it run?)
 *
 * This provides a guided UI alternative to TP conversation-based creation.
 */

import { useState, useCallback } from 'react';
import {
  X,
  Loader2,
  ArrowLeft,
  ArrowRight,
  Check,
  Send,
  FileText,
  Database,
  Clock,
  CheckCircle2,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import { DestinationSelector } from '@/components/ui/DestinationSelector';
import { TypeSelector } from '@/components/deliverables/TypeSelector';
import { SourcePicker } from '@/components/deliverables/SourcePicker';
import type {
  Deliverable,
  DeliverableCreate,
  DeliverableType,
  Destination,
  DataSource,
  ScheduleConfig,
  ScheduleFrequency,
  IntegrationProvider,
} from '@/types';

interface DeliverableCreateWizardProps {
  open: boolean;
  onClose: () => void;
  onCreated: (deliverable: Deliverable) => void;
  /** Pre-fill destination from platform click */
  initialDestination?: Destination;
  /** Suggested platform for sources */
  suggestedPlatform?: IntegrationProvider;
}

type WizardStep = 'destination' | 'type' | 'sources' | 'schedule';

const STEPS: { key: WizardStep; label: string; icon: React.ReactNode }[] = [
  { key: 'destination', label: 'Destination', icon: <Send className="w-4 h-4" /> },
  { key: 'type', label: 'Type', icon: <FileText className="w-4 h-4" /> },
  { key: 'sources', label: 'Sources', icon: <Database className="w-4 h-4" /> },
  { key: 'schedule', label: 'Schedule', icon: <Clock className="w-4 h-4" /> },
];

const FREQUENCY_OPTIONS: { value: ScheduleFrequency; label: string }[] = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'biweekly', label: 'Every 2 weeks' },
  { value: 'monthly', label: 'Monthly' },
];

const DAY_OPTIONS = [
  { value: 'monday', label: 'Monday' },
  { value: 'tuesday', label: 'Tuesday' },
  { value: 'wednesday', label: 'Wednesday' },
  { value: 'thursday', label: 'Thursday' },
  { value: 'friday', label: 'Friday' },
  { value: 'saturday', label: 'Saturday' },
  { value: 'sunday', label: 'Sunday' },
];

export function DeliverableCreateWizard({
  open,
  onClose,
  onCreated,
  initialDestination,
  suggestedPlatform,
}: DeliverableCreateWizardProps) {
  const [currentStep, setCurrentStep] = useState<WizardStep>(
    initialDestination ? 'type' : 'destination'
  );
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [destination, setDestination] = useState<Destination | undefined>(initialDestination);
  const [deliverableType, setDeliverableType] = useState<DeliverableType | undefined>();
  const [title, setTitle] = useState('');
  const [sources, setSources] = useState<DataSource[]>([]);
  const [schedule, setSchedule] = useState<ScheduleConfig>({
    frequency: 'weekly',
    day: 'friday',
    time: '16:00',
  });

  const currentStepIndex = STEPS.findIndex((s) => s.key === currentStep);

  const canProceed = useCallback(() => {
    switch (currentStep) {
      case 'destination':
        return !!destination;
      case 'type':
        return !!deliverableType && title.trim().length > 0;
      case 'sources':
        return true; // Sources are optional
      case 'schedule':
        return !!schedule.frequency;
      default:
        return false;
    }
  }, [currentStep, destination, deliverableType, title, schedule]);

  const goNext = () => {
    const nextIndex = currentStepIndex + 1;
    if (nextIndex < STEPS.length) {
      setCurrentStep(STEPS[nextIndex].key);
    }
  };

  const goBack = () => {
    const prevIndex = currentStepIndex - 1;
    if (prevIndex >= 0) {
      setCurrentStep(STEPS[prevIndex].key);
    }
  };

  const handleCreate = async () => {
    if (!destination || !deliverableType || !title.trim()) {
      setError('Please complete all required fields');
      return;
    }

    setCreating(true);
    setError(null);

    try {
      const createData: DeliverableCreate = {
        title: title.trim(),
        deliverable_type: deliverableType,
        destination,
        sources,
        schedule,
        governance: 'manual', // ADR-032: Default to draft mode
      };

      const deliverable = await api.deliverables.create(createData);
      onCreated(deliverable);
      onClose();
    } catch (err) {
      console.error('Failed to create deliverable:', err);
      setError('Failed to create deliverable. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  const handleClose = () => {
    // Reset form on close
    setCurrentStep(initialDestination ? 'type' : 'destination');
    setDestination(initialDestination);
    setDeliverableType(undefined);
    setTitle('');
    setSources([]);
    setSchedule({ frequency: 'weekly', day: 'friday', time: '16:00' });
    setError(null);
    onClose();
  };

  if (!open) return null;

  const showDaySelector = schedule.frequency === 'weekly' || schedule.frequency === 'biweekly';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={handleClose} />

      {/* Modal */}
      <div className="relative bg-background rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <div>
            <h2 className="text-lg font-semibold">Create Deliverable</h2>
            <p className="text-sm text-muted-foreground">
              Set up recurring content generation
            </p>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-muted rounded-md text-muted-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step Indicator */}
        <div className="px-6 py-3 border-b border-border bg-muted/30">
          <div className="flex items-center justify-between">
            {STEPS.map((step, index) => {
              const isActive = step.key === currentStep;
              const isComplete = index < currentStepIndex;
              return (
                <div
                  key={step.key}
                  className={cn(
                    'flex items-center gap-2',
                    isActive ? 'text-primary' : isComplete ? 'text-green-600' : 'text-muted-foreground'
                  )}
                >
                  <div
                    className={cn(
                      'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium',
                      isActive
                        ? 'bg-primary text-primary-foreground'
                        : isComplete
                          ? 'bg-green-100 text-green-600'
                          : 'bg-muted'
                    )}
                  >
                    {isComplete ? <Check className="w-3.5 h-3.5" /> : index + 1}
                  </div>
                  <span className="text-xs font-medium hidden sm:inline">{step.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {/* Error */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Step 1: Destination */}
          {currentStep === 'destination' && (
            <DestinationSelector
              value={destination}
              onChange={setDestination}
              onClose={handleClose}
            />
          )}

          {/* Step 2: Type */}
          {currentStep === 'type' && (
            <div className="space-y-4">
              <TypeSelector value={deliverableType} onChange={setDeliverableType} />

              <div className="pt-4 border-t border-border">
                <label className="block text-sm font-medium mb-1.5">Title</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g., Weekly Status Report"
                  className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  autoFocus
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Give your deliverable a descriptive name
                </p>
              </div>
            </div>
          )}

          {/* Step 3: Sources */}
          {currentStep === 'sources' && (
            <SourcePicker
              value={sources}
              onChange={setSources}
              suggestedPlatform={suggestedPlatform || (destination?.platform as IntegrationProvider)}
            />
          )}

          {/* Step 4: Schedule */}
          {currentStep === 'schedule' && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                When should this deliverable run?
              </p>

              <div className="space-y-4">
                {/* Frequency */}
                <div>
                  <label className="block text-sm font-medium mb-1.5">Frequency</label>
                  <div className="grid grid-cols-2 gap-2">
                    {FREQUENCY_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => setSchedule({ ...schedule, frequency: opt.value })}
                        className={cn(
                          'p-3 rounded-md border text-sm font-medium transition-colors',
                          schedule.frequency === opt.value
                            ? 'border-primary bg-primary/5 text-primary'
                            : 'border-border hover:border-muted-foreground/50'
                        )}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Day (for weekly/biweekly) */}
                {showDaySelector && (
                  <div>
                    <label className="block text-sm font-medium mb-1.5">Day</label>
                    <select
                      value={schedule.day || 'friday'}
                      onChange={(e) => setSchedule({ ...schedule, day: e.target.value })}
                      className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                    >
                      {DAY_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Time */}
                <div>
                  <label className="block text-sm font-medium mb-1.5">Time</label>
                  <input
                    type="time"
                    value={schedule.time || '16:00'}
                    onChange={(e) => setSchedule({ ...schedule, time: e.target.value })}
                    className="w-full px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>

                {/* Summary */}
                <div className="p-3 bg-muted/50 rounded-md">
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    <span>
                      Draft mode: You'll review content before it's sent
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-muted/30">
          <button
            onClick={goBack}
            disabled={currentStepIndex === 0 || creating}
            className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>

          <div className="flex items-center gap-3">
            <button
              onClick={handleClose}
              disabled={creating}
              className="px-4 py-2 text-sm border border-border rounded-md hover:bg-muted"
            >
              Cancel
            </button>

            {currentStepIndex < STEPS.length - 1 ? (
              <button
                onClick={goNext}
                disabled={!canProceed()}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
              >
                Next
                <ArrowRight className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={handleCreate}
                disabled={!canProceed() || creating}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
              >
                {creating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    Create Deliverable
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
