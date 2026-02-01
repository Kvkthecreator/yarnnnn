'use client';

/**
 * ADR-018: Onboarding Wizard
 *
 * 6-step wizard for creating a new deliverable:
 * 1. What do you deliver?
 * 2. Who receives it?
 * 3. Show me examples
 * 4. What sources inform this?
 * 5. When is it due?
 * 6. First draft generation + review
 */

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { X, ArrowLeft, ArrowRight, Loader2, Check } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type {
  DeliverableCreate,
  RecipientContext,
  TemplateStructure,
  ScheduleConfig,
  DataSource,
} from '@/types';

interface OnboardingWizardProps {
  onClose: () => void;
  onComplete: (deliverableId: string) => void;
}

type WizardStep = 1 | 2 | 3 | 4 | 5 | 6;

const STEP_TITLES: Record<WizardStep, string> = {
  1: 'What do you deliver?',
  2: 'Who receives it?',
  3: 'Show me examples',
  4: 'What sources inform this?',
  5: 'When is it due?',
  6: 'Your first draft',
};

export function OnboardingWizard({ onClose, onComplete }: OnboardingWizardProps) {
  const router = useRouter();
  const [step, setStep] = useState<WizardStep>(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [createdDeliverableId, setCreatedDeliverableId] = useState<string | null>(null);

  // Form state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [recipient, setRecipient] = useState<RecipientContext>({});
  const [examples, setExamples] = useState<File[]>([]);
  const [templateNotes, setTemplateNotes] = useState('');
  const [sources, setSources] = useState<DataSource[]>([]);
  const [schedule, setSchedule] = useState<ScheduleConfig>({
    frequency: 'weekly',
    day: 'monday',
    time: '09:00',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  });

  const canProceed = useCallback((): boolean => {
    switch (step) {
      case 1:
        return title.trim().length > 0;
      case 2:
        return true; // Optional
      case 3:
        return true; // Optional but encouraged
      case 4:
        return true; // Optional
      case 5:
        return schedule.frequency !== undefined;
      case 6:
        return true;
      default:
        return false;
    }
  }, [step, title, schedule]);

  const handleNext = async () => {
    if (step < 5) {
      setStep((step + 1) as WizardStep);
    } else if (step === 5) {
      // Create deliverable and move to step 6
      setIsSubmitting(true);
      try {
        const templateStructure: TemplateStructure = {};
        if (templateNotes) {
          templateStructure.format_notes = templateNotes;
        }

        const data: DeliverableCreate = {
          title,
          description: description || undefined,
          recipient_context: Object.keys(recipient).length > 0 ? recipient : undefined,
          template_structure: Object.keys(templateStructure).length > 0 ? templateStructure : undefined,
          schedule,
          sources: sources.length > 0 ? sources : undefined,
        };

        const deliverable = await api.deliverables.create(data);
        setCreatedDeliverableId(deliverable.id);
        setStep(6);

        // Trigger first run
        setIsGenerating(true);
        await api.deliverables.run(deliverable.id);
        setIsGenerating(false);
      } catch (err) {
        console.error('Failed to create deliverable:', err);
        alert('Failed to create deliverable. Please try again.');
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep((step - 1) as WizardStep);
    }
  };

  const handleFinish = () => {
    if (createdDeliverableId) {
      onComplete(createdDeliverableId);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background border border-border rounded-lg w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
          <div>
            <div className="text-xs text-muted-foreground mb-1">
              Step {step} of 6
            </div>
            <h2 className="text-lg font-semibold">{STEP_TITLES[step]}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-muted-foreground hover:text-foreground rounded-md hover:bg-muted"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Progress */}
        <div className="px-6 py-3 border-b border-border shrink-0">
          <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5, 6].map((s) => (
              <div
                key={s}
                className={cn(
                  "h-1 flex-1 rounded-full transition-colors",
                  s <= step ? "bg-primary" : "bg-muted"
                )}
              />
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto px-6 py-6">
          {step === 1 && (
            <StepDeliverable
              title={title}
              setTitle={setTitle}
              description={description}
              setDescription={setDescription}
            />
          )}
          {step === 2 && (
            <StepRecipient
              recipient={recipient}
              setRecipient={setRecipient}
            />
          )}
          {step === 3 && (
            <StepExamples
              examples={examples}
              setExamples={setExamples}
              templateNotes={templateNotes}
              setTemplateNotes={setTemplateNotes}
            />
          )}
          {step === 4 && (
            <StepSources
              sources={sources}
              setSources={setSources}
            />
          )}
          {step === 5 && (
            <StepSchedule
              schedule={schedule}
              setSchedule={setSchedule}
            />
          )}
          {step === 6 && (
            <StepFirstDraft
              isGenerating={isGenerating}
              deliverableId={createdDeliverableId}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border shrink-0">
          <div>
            {step > 1 && step < 6 && (
              <button
                onClick={handleBack}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
              >
                <ArrowLeft className="w-4 h-4" />
                Back
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            {step < 6 ? (
              <>
                {step > 1 && step < 5 && (
                  <button
                    onClick={handleNext}
                    className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
                  >
                    Skip
                  </button>
                )}
                <button
                  onClick={handleNext}
                  disabled={!canProceed() || isSubmitting}
                  className="inline-flex items-center gap-1.5 px-6 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Creating...
                    </>
                  ) : step === 5 ? (
                    <>
                      Create & Generate
                      <ArrowRight className="w-4 h-4" />
                    </>
                  ) : (
                    <>
                      Continue
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </>
            ) : (
              <button
                onClick={handleFinish}
                disabled={isGenerating}
                className="inline-flex items-center gap-1.5 px-6 py-2 bg-primary text-primary-foreground text-sm font-medium rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    View Deliverable
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

// Step 1: What do you deliver?
function StepDeliverable({
  title,
  setTitle,
  description,
  setDescription,
}: {
  title: string;
  setTitle: (v: string) => void;
  description: string;
  setDescription: (v: string) => void;
}) {
  return (
    <div className="space-y-6">
      <p className="text-muted-foreground">
        Describe the recurring work you owe to someone. This could be a report,
        update, brief, or any regular deliverable.
      </p>

      <div>
        <label className="block text-sm font-medium mb-2">
          Deliverable title <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g., Weekly Status Report for Client X"
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          autoFocus
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">
          Description (optional)
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="What is this deliverable about? What does it cover?"
          rows={3}
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
        />
      </div>

      <div className="bg-muted/50 rounded-lg p-4">
        <p className="text-xs text-muted-foreground">
          <strong>Tip:</strong> Be specific. "Weekly Status Report for Client X" is better
          than "Weekly Report". The title helps YARNNN understand the context.
        </p>
      </div>
    </div>
  );
}

// Step 2: Who receives it?
function StepRecipient({
  recipient,
  setRecipient,
}: {
  recipient: RecipientContext;
  setRecipient: (v: RecipientContext) => void;
}) {
  const [priorityInput, setPriorityInput] = useState('');

  const addPriority = () => {
    if (priorityInput.trim()) {
      setRecipient({
        ...recipient,
        priorities: [...(recipient.priorities || []), priorityInput.trim()],
      });
      setPriorityInput('');
    }
  };

  const removePriority = (index: number) => {
    setRecipient({
      ...recipient,
      priorities: (recipient.priorities || []).filter((_, i) => i !== index),
    });
  };

  return (
    <div className="space-y-6">
      <p className="text-muted-foreground">
        Who receives this deliverable? Understanding your audience helps YARNNN
        tailor the tone and emphasis.
      </p>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium mb-2">Name</label>
          <input
            type="text"
            value={recipient.name || ''}
            onChange={(e) => setRecipient({ ...recipient, name: e.target.value })}
            placeholder="e.g., Sarah Johnson"
            className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Role</label>
          <input
            type="text"
            value={recipient.role || ''}
            onChange={(e) => setRecipient({ ...recipient, role: e.target.value })}
            placeholder="e.g., VP Marketing"
            className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">
          What do they care about?
        </label>
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={priorityInput}
            onChange={(e) => setPriorityInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addPriority())}
            placeholder="e.g., ROI metrics, competitive updates"
            className="flex-1 px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
          <button
            onClick={addPriority}
            className="px-4 py-2 border border-border rounded-md hover:bg-muted text-sm"
          >
            Add
          </button>
        </div>
        {(recipient.priorities || []).length > 0 && (
          <div className="flex flex-wrap gap-2">
            {(recipient.priorities || []).map((p, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 px-3 py-1 bg-muted rounded-full text-sm"
              >
                {p}
                <button
                  onClick={() => removePriority(i)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">
          Additional notes
        </label>
        <textarea
          value={recipient.notes || ''}
          onChange={(e) => setRecipient({ ...recipient, notes: e.target.value })}
          placeholder="Any other context about the recipient..."
          rows={2}
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
        />
      </div>
    </div>
  );
}

// Step 3: Show me examples
function StepExamples({
  examples,
  setExamples,
  templateNotes,
  setTemplateNotes,
}: {
  examples: File[];
  setExamples: (v: File[]) => void;
  templateNotes: string;
  setTemplateNotes: (v: string) => void;
}) {
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files).slice(0, 3 - examples.length);
      setExamples([...examples, ...newFiles]);
    }
  };

  const removeFile = (index: number) => {
    setExamples(examples.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-6">
      <div className="bg-primary/5 border border-primary/20 rounded-lg p-4">
        <p className="text-sm">
          <strong>Highly recommended:</strong> Upload 2-3 past examples of this deliverable.
          This is the highest-leverage input — YARNNN will learn your structure, tone, and content priorities.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">
          Upload examples (PDF, DOCX, TXT)
        </label>
        <div className="border-2 border-dashed border-border rounded-lg p-8 text-center">
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md"
            multiple
            onChange={handleFileChange}
            className="hidden"
            id="example-upload"
            disabled={examples.length >= 3}
          />
          <label
            htmlFor="example-upload"
            className={cn(
              "cursor-pointer",
              examples.length >= 3 && "cursor-not-allowed opacity-50"
            )}
          >
            <p className="text-muted-foreground mb-2">
              Drag files here or click to upload
            </p>
            <p className="text-xs text-muted-foreground">
              Up to 3 files, 10MB each
            </p>
          </label>
        </div>

        {examples.length > 0 && (
          <div className="mt-4 space-y-2">
            {examples.map((file, i) => (
              <div
                key={i}
                className="flex items-center justify-between px-4 py-2 bg-muted rounded-md"
              >
                <span className="text-sm truncate">{file.name}</span>
                <button
                  onClick={() => removeFile(i)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">
          Or describe the format
        </label>
        <textarea
          value={templateNotes}
          onChange={(e) => setTemplateNotes(e.target.value)}
          placeholder="Describe the structure, sections, typical length, tone, etc."
          rows={4}
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
        />
      </div>
    </div>
  );
}

// Step 4: What sources inform this?
function StepSources({
  sources,
  setSources,
}: {
  sources: DataSource[];
  setSources: (v: DataSource[]) => void;
}) {
  const [newSource, setNewSource] = useState<Partial<DataSource>>({ type: 'description' });

  const addSource = () => {
    if (newSource.value?.trim()) {
      setSources([
        ...sources,
        {
          type: newSource.type || 'description',
          value: newSource.value.trim(),
          label: newSource.label?.trim(),
        },
      ]);
      setNewSource({ type: 'description' });
    }
  };

  const removeSource = (index: number) => {
    setSources(sources.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-6">
      <p className="text-muted-foreground">
        What information feeds into this deliverable? This helps YARNNN gather
        the right context each cycle.
      </p>

      <div className="space-y-4">
        <div className="flex gap-2">
          <select
            value={newSource.type}
            onChange={(e) => setNewSource({ ...newSource, type: e.target.value as DataSource['type'] })}
            className="px-3 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          >
            <option value="description">Description</option>
            <option value="url">URL</option>
            <option value="document">Document</option>
          </select>
          <input
            type="text"
            value={newSource.value || ''}
            onChange={(e) => setNewSource({ ...newSource, value: e.target.value })}
            placeholder={
              newSource.type === 'url'
                ? 'https://...'
                : newSource.type === 'document'
                ? 'Document name or ID'
                : 'Describe the information source...'
            }
            className="flex-1 px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSource())}
          />
          <button
            onClick={addSource}
            className="px-4 py-2 border border-border rounded-md hover:bg-muted text-sm"
          >
            Add
          </button>
        </div>

        {sources.length > 0 && (
          <div className="space-y-2">
            {sources.map((source, i) => (
              <div
                key={i}
                className="flex items-center justify-between px-4 py-3 bg-muted rounded-md"
              >
                <div>
                  <span className="text-xs text-muted-foreground uppercase tracking-wide">
                    {source.type}
                  </span>
                  <p className="text-sm">{source.value}</p>
                </div>
                <button
                  onClick={() => removeSource(i)}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="bg-muted/50 rounded-lg p-4">
        <p className="text-xs text-muted-foreground">
          <strong>Examples:</strong> "Weekly sales numbers from CRM", "https://competitor.com/blog",
          "Project status updates from team Slack"
        </p>
      </div>
    </div>
  );
}

// Step 5: When is it due?
function StepSchedule({
  schedule,
  setSchedule,
}: {
  schedule: ScheduleConfig;
  setSchedule: (v: ScheduleConfig) => void;
}) {
  const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];

  return (
    <div className="space-y-6">
      <p className="text-muted-foreground">
        When should YARNNN produce this deliverable? You'll receive it for review
        before the scheduled time.
      </p>

      <div>
        <label className="block text-sm font-medium mb-3">Frequency</label>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {(['daily', 'weekly', 'biweekly', 'monthly'] as const).map((freq) => (
            <button
              key={freq}
              onClick={() => setSchedule({ ...schedule, frequency: freq })}
              className={cn(
                "px-4 py-3 border rounded-md text-sm capitalize transition-colors",
                schedule.frequency === freq
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {freq}
            </button>
          ))}
        </div>
      </div>

      {schedule.frequency === 'weekly' && (
        <div>
          <label className="block text-sm font-medium mb-3">Day of week</label>
          <div className="flex flex-wrap gap-2">
            {days.map((day) => (
              <button
                key={day}
                onClick={() => setSchedule({ ...schedule, day })}
                className={cn(
                  "px-3 py-2 border rounded-md text-sm capitalize transition-colors",
                  schedule.day === day
                    ? "border-primary bg-primary/5 text-primary"
                    : "border-border hover:bg-muted"
                )}
              >
                {day.slice(0, 3)}
              </button>
            ))}
          </div>
        </div>
      )}

      {schedule.frequency === 'monthly' && (
        <div>
          <label className="block text-sm font-medium mb-2">Day of month</label>
          <select
            value={schedule.day || '1'}
            onChange={(e) => setSchedule({ ...schedule, day: e.target.value })}
            className="px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          >
            {Array.from({ length: 28 }, (_, i) => i + 1).map((d) => (
              <option key={d} value={d.toString()}>
                {d}
              </option>
            ))}
            <option value="last">Last day</option>
          </select>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium mb-2">Time</label>
        <input
          type="time"
          value={schedule.time || '09:00'}
          onChange={(e) => setSchedule({ ...schedule, time: e.target.value })}
          className="px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
        />
        <p className="text-xs text-muted-foreground mt-1">
          Timezone: {schedule.timezone}
        </p>
      </div>
    </div>
  );
}

// Step 6: First draft
function StepFirstDraft({
  isGenerating,
  deliverableId,
}: {
  isGenerating: boolean;
  deliverableId: string | null;
}) {
  if (isGenerating) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Loader2 className="w-12 h-12 animate-spin text-primary mb-4" />
        <h3 className="text-lg font-medium mb-2">Generating your first draft...</h3>
        <p className="text-muted-foreground max-w-md">
          YARNNN is gathering context and producing your deliverable.
          This usually takes 1-2 minutes.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="w-16 h-16 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mb-4">
        <Check className="w-8 h-8 text-green-600" />
      </div>
      <h3 className="text-lg font-medium mb-2">Your deliverable is ready!</h3>
      <p className="text-muted-foreground max-w-md">
        Your first draft has been generated and is waiting for your review.
        Click below to view it and provide feedback.
      </p>
    </div>
  );
}
