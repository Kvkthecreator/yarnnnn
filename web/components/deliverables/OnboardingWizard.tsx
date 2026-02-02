'use client';

/**
 * ADR-018: Onboarding Wizard
 * ADR-019: Deliverable Types System
 *
 * 5-step wizard for creating a new deliverable (type-first):
 * 1. Select deliverable type
 * 2. Configure type-specific details
 * 3. Who receives it?
 * 4. What sources inform this?
 * 5. When is it due?
 *
 * After completion, triggers first run in background and returns to dashboard.
 */

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  X,
  ArrowLeft,
  ArrowRight,
  Loader2,
  ClipboardList,
  Users,
  Search,
  MessageSquare,
  FileText,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type {
  DeliverableCreate,
  DeliverableType,
  TypeConfig,
  RecipientContext,
  ScheduleConfig,
  DataSource,
  StatusReportConfig,
  StakeholderUpdateConfig,
  ResearchBriefConfig,
  MeetingSummaryConfig,
  CustomConfig,
} from '@/types';

interface OnboardingWizardProps {
  onClose: () => void;
  onComplete: (deliverableId: string) => void;
}

type WizardStep = 1 | 2 | 3 | 4 | 5;

const STEP_TITLES: Record<WizardStep, string> = {
  1: 'What type of deliverable?',
  2: 'Configure your deliverable',
  3: 'Who receives it?',
  4: 'What sources inform this?',
  5: 'When is it due?',
};

// Type metadata for selection cards
const TYPE_INFO: Record<DeliverableType, {
  icon: React.ReactNode;
  title: string;
  description: string;
  examples: string[];
}> = {
  status_report: {
    icon: <ClipboardList className="w-6 h-6" />,
    title: 'Status Report',
    description: 'Weekly or recurring updates on project or team progress',
    examples: ['Weekly team status', 'Project updates', 'Sprint summaries'],
  },
  stakeholder_update: {
    icon: <Users className="w-6 h-6" />,
    title: 'Stakeholder Update',
    description: 'Formal communications to investors, board, or clients',
    examples: ['Monthly investor letter', 'Board update', 'Client progress report'],
  },
  research_brief: {
    icon: <Search className="w-6 h-6" />,
    title: 'Research Brief',
    description: 'Synthesized intelligence on competitors, market, or topics',
    examples: ['Competitive intel', 'Market monitoring', 'Technology trends'],
  },
  meeting_summary: {
    icon: <MessageSquare className="w-6 h-6" />,
    title: 'Meeting Summary',
    description: 'Recurring notes and action items from standing meetings',
    examples: ['Weekly sync notes', '1:1 summaries', 'Standup digests'],
  },
  custom: {
    icon: <FileText className="w-6 h-6" />,
    title: 'Custom',
    description: 'Define your own deliverable structure',
    examples: ['Any recurring written content'],
  },
};

// Default configs for each type
function getDefaultTypeConfig(type: DeliverableType): TypeConfig {
  switch (type) {
    case 'status_report':
      return {
        subject: '',
        audience: 'stakeholders',
        sections: {
          summary: true,
          accomplishments: true,
          blockers: true,
          next_steps: true,
          metrics: false,
        },
        detail_level: 'standard',
        tone: 'formal',
      } as StatusReportConfig;
    case 'stakeholder_update':
      return {
        audience_type: 'client',
        company_or_project: '',
        sections: {
          executive_summary: true,
          highlights: true,
          challenges: true,
          metrics: false,
          outlook: true,
        },
        formality: 'professional',
        sensitivity: 'confidential',
      } as StakeholderUpdateConfig;
    case 'research_brief':
      return {
        focus_area: 'competitive',
        subjects: [],
        sections: {
          key_takeaways: true,
          findings: true,
          implications: true,
          recommendations: false,
        },
        depth: 'analysis',
      } as ResearchBriefConfig;
    case 'meeting_summary':
      return {
        meeting_name: '',
        meeting_type: 'team_sync',
        participants: [],
        sections: {
          context: true,
          discussion: true,
          decisions: true,
          action_items: true,
          followups: true,
        },
        format: 'structured',
      } as MeetingSummaryConfig;
    case 'custom':
    default:
      return {
        description: '',
      } as CustomConfig;
  }
}

export function OnboardingWizard({ onClose, onComplete }: OnboardingWizardProps) {
  const router = useRouter();
  const [step, setStep] = useState<WizardStep>(1);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form state
  const [deliverableType, setDeliverableType] = useState<DeliverableType | null>(null);
  const [typeConfig, setTypeConfig] = useState<TypeConfig | null>(null);
  const [title, setTitle] = useState('');
  const [recipient, setRecipient] = useState<RecipientContext>({});
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
        return deliverableType !== null;
      case 2:
        // Type-specific validation
        if (!typeConfig) return false;
        if (deliverableType === 'status_report') {
          return (typeConfig as StatusReportConfig).subject?.trim().length > 0;
        }
        if (deliverableType === 'stakeholder_update') {
          return (typeConfig as StakeholderUpdateConfig).company_or_project?.trim().length > 0;
        }
        if (deliverableType === 'research_brief') {
          return (typeConfig as ResearchBriefConfig).subjects?.length > 0;
        }
        if (deliverableType === 'meeting_summary') {
          return (typeConfig as MeetingSummaryConfig).meeting_name?.trim().length > 0;
        }
        if (deliverableType === 'custom') {
          return (typeConfig as CustomConfig).description?.trim().length > 0;
        }
        return true;
      case 3:
        return true; // Optional
      case 4:
        return true; // Optional
      case 5:
        return schedule.frequency !== undefined && title.trim().length > 0;
      default:
        return false;
    }
  }, [step, deliverableType, typeConfig, schedule, title]);

  const handleTypeSelect = (type: DeliverableType) => {
    setDeliverableType(type);
    setTypeConfig(getDefaultTypeConfig(type));
    // Auto-generate title suggestion based on type
    if (!title) {
      const suggestions: Record<DeliverableType, string> = {
        status_report: 'Weekly Status Report',
        stakeholder_update: 'Monthly Update',
        research_brief: 'Competitive Brief',
        meeting_summary: 'Meeting Notes',
        custom: 'Deliverable',
      };
      setTitle(suggestions[type]);
    }
  };

  const handleNext = async () => {
    if (step < 5) {
      setStep((step + 1) as WizardStep);
    } else if (step === 5) {
      setIsSubmitting(true);
      try {
        const data: DeliverableCreate = {
          title,
          deliverable_type: deliverableType || 'custom',
          type_config: typeConfig || undefined,
          recipient_context: Object.keys(recipient).length > 0 ? recipient : undefined,
          schedule,
          sources: sources.length > 0 ? sources : undefined,
        };

        const deliverable = await api.deliverables.create(data);

        // Trigger first run in background (don't await)
        api.deliverables.run(deliverable.id).catch((err) => {
          console.error('Failed to trigger first run:', err);
        });

        onComplete(deliverable.id);
      } catch (err) {
        console.error('Failed to create deliverable:', err);
        alert('Failed to create deliverable. Please try again.');
        setIsSubmitting(false);
      }
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep((step - 1) as WizardStep);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background border border-border rounded-lg w-full max-w-2xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
          <div>
            <div className="text-xs text-muted-foreground mb-1">
              Step {step} of 5
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
            {[1, 2, 3, 4, 5].map((s) => (
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
            <StepTypeSelection
              selectedType={deliverableType}
              onSelect={handleTypeSelect}
            />
          )}
          {step === 2 && deliverableType && typeConfig && (
            <StepTypeConfig
              type={deliverableType}
              config={typeConfig}
              setConfig={setTypeConfig}
            />
          )}
          {step === 3 && (
            <StepRecipient
              recipient={recipient}
              setRecipient={setRecipient}
            />
          )}
          {step === 4 && (
            <StepSources
              sources={sources}
              setSources={setSources}
              deliverableType={deliverableType}
            />
          )}
          {step === 5 && (
            <StepSchedule
              schedule={schedule}
              setSchedule={setSchedule}
              title={title}
              setTitle={setTitle}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-border shrink-0">
          <div>
            {step > 1 && (
              <button
                onClick={handleBack}
                disabled={isSubmitting}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-sm text-muted-foreground hover:text-foreground disabled:opacity-50"
              >
                <ArrowLeft className="w-4 h-4" />
                Back
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            {step > 2 && step < 5 && (
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
                'Create Deliverable'
              ) : (
                <>
                  Continue
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Step 1: Select Type
function StepTypeSelection({
  selectedType,
  onSelect,
}: {
  selectedType: DeliverableType | null;
  onSelect: (type: DeliverableType) => void;
}) {
  const types: DeliverableType[] = [
    'status_report',
    'stakeholder_update',
    'research_brief',
    'meeting_summary',
  ];

  return (
    <div className="space-y-6">
      <p className="text-muted-foreground">
        Choose the type of deliverable you need. Each type has a proven structure
        that YARNNN can reliably produce.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {types.map((type) => {
          const info = TYPE_INFO[type];
          return (
            <button
              key={type}
              onClick={() => onSelect(type)}
              className={cn(
                "flex flex-col items-start p-4 border rounded-lg text-left transition-all",
                selectedType === type
                  ? "border-primary bg-primary/5 ring-1 ring-primary"
                  : "border-border hover:border-foreground/20 hover:bg-muted/50"
              )}
            >
              <div className={cn(
                "p-2 rounded-md mb-3",
                selectedType === type ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
              )}>
                {info.icon}
              </div>
              <h3 className="font-medium text-sm mb-1">{info.title}</h3>
              <p className="text-xs text-muted-foreground mb-2">{info.description}</p>
              <div className="flex flex-wrap gap-1">
                {info.examples.slice(0, 2).map((ex, i) => (
                  <span key={i} className="text-xs px-2 py-0.5 bg-muted rounded-full">
                    {ex}
                  </span>
                ))}
              </div>
            </button>
          );
        })}
      </div>

      {/* Custom option */}
      <button
        onClick={() => onSelect('custom')}
        className={cn(
          "w-full flex items-center gap-3 p-4 border rounded-lg text-left transition-all",
          selectedType === 'custom'
            ? "border-primary bg-primary/5 ring-1 ring-primary"
            : "border-border hover:border-foreground/20 hover:bg-muted/50"
        )}
      >
        <div className={cn(
          "p-2 rounded-md",
          selectedType === 'custom' ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
        )}>
          <FileText className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-medium text-sm">Custom Deliverable</h3>
          <p className="text-xs text-muted-foreground">
            Define your own structure (experimental)
          </p>
        </div>
      </button>
    </div>
  );
}

// Step 2: Type-specific Configuration
function StepTypeConfig({
  type,
  config,
  setConfig,
}: {
  type: DeliverableType;
  config: TypeConfig;
  setConfig: (c: TypeConfig) => void;
}) {
  switch (type) {
    case 'status_report':
      return <StatusReportConfigForm config={config as StatusReportConfig} setConfig={setConfig} />;
    case 'stakeholder_update':
      return <StakeholderUpdateConfigForm config={config as StakeholderUpdateConfig} setConfig={setConfig} />;
    case 'research_brief':
      return <ResearchBriefConfigForm config={config as ResearchBriefConfig} setConfig={setConfig} />;
    case 'meeting_summary':
      return <MeetingSummaryConfigForm config={config as MeetingSummaryConfig} setConfig={setConfig} />;
    case 'custom':
      return <CustomConfigForm config={config as CustomConfig} setConfig={setConfig} />;
    default:
      return null;
  }
}

// Status Report Configuration
function StatusReportConfigForm({
  config,
  setConfig,
}: {
  config: StatusReportConfig;
  setConfig: (c: TypeConfig) => void;
}) {
  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium mb-2">
          What is this status report about? <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.subject || ''}
          onChange={(e) => setConfig({ ...config, subject: e.target.value })}
          placeholder="e.g., Engineering Team, Project Alpha, Q1 Initiative"
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          autoFocus
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Who is the audience?</label>
        <div className="flex flex-wrap gap-2">
          {(['manager', 'stakeholders', 'team', 'executive'] as const).map((aud) => (
            <button
              key={aud}
              onClick={() => setConfig({ ...config, audience: aud })}
              className={cn(
                "px-3 py-2 border rounded-md text-sm capitalize transition-colors",
                config.audience === aud
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {aud}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Detail level</label>
        <div className="flex gap-2">
          {(['brief', 'standard', 'detailed'] as const).map((level) => (
            <button
              key={level}
              onClick={() => setConfig({ ...config, detail_level: level })}
              className={cn(
                "flex-1 px-3 py-2 border rounded-md text-sm capitalize transition-colors",
                config.detail_level === level
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {level}
            </button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Brief: 200-400 words | Standard: 400-800 words | Detailed: 800+ words
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Sections to include</label>
        <div className="space-y-2">
          {[
            { key: 'summary', label: 'Summary/TL;DR' },
            { key: 'accomplishments', label: 'Accomplishments' },
            { key: 'blockers', label: 'Blockers/Challenges' },
            { key: 'next_steps', label: 'Next Steps' },
            { key: 'metrics', label: 'Metrics/Numbers' },
          ].map(({ key, label }) => (
            <label key={key} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={config.sections[key as keyof typeof config.sections]}
                onChange={(e) => setConfig({
                  ...config,
                  sections: { ...config.sections, [key]: e.target.checked },
                })}
                className="w-4 h-4 rounded border-border"
              />
              <span className="text-sm">{label}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

// Stakeholder Update Configuration
function StakeholderUpdateConfigForm({
  config,
  setConfig,
}: {
  config: StakeholderUpdateConfig;
  setConfig: (c: TypeConfig) => void;
}) {
  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium mb-2">
          Company or project name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.company_or_project || ''}
          onChange={(e) => setConfig({ ...config, company_or_project: e.target.value })}
          placeholder="e.g., Acme Corp, Project Phoenix"
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          autoFocus
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Audience type</label>
        <div className="flex flex-wrap gap-2">
          {(['investor', 'board', 'client', 'executive'] as const).map((aud) => (
            <button
              key={aud}
              onClick={() => setConfig({ ...config, audience_type: aud })}
              className={cn(
                "px-3 py-2 border rounded-md text-sm capitalize transition-colors",
                config.audience_type === aud
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {aud}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Relationship context (optional)</label>
        <input
          type="text"
          value={config.relationship_context || ''}
          onChange={(e) => setConfig({ ...config, relationship_context: e.target.value })}
          placeholder="e.g., Series A investor, Enterprise client since 2024"
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Formality</label>
        <div className="flex gap-2">
          {(['formal', 'professional', 'conversational'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setConfig({ ...config, formality: f })}
              className={cn(
                "flex-1 px-3 py-2 border rounded-md text-sm capitalize transition-colors",
                config.formality === f
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Sections to include</label>
        <div className="space-y-2">
          {[
            { key: 'executive_summary', label: 'Executive Summary' },
            { key: 'highlights', label: 'Key Highlights/Wins' },
            { key: 'challenges', label: 'Challenges & Mitigations' },
            { key: 'metrics', label: 'Financial/Metric Snapshot' },
            { key: 'outlook', label: 'Outlook/Next Period' },
          ].map(({ key, label }) => (
            <label key={key} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={config.sections[key as keyof typeof config.sections]}
                onChange={(e) => setConfig({
                  ...config,
                  sections: { ...config.sections, [key]: e.target.checked },
                })}
                className="w-4 h-4 rounded border-border"
              />
              <span className="text-sm">{label}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

// Research Brief Configuration
function ResearchBriefConfigForm({
  config,
  setConfig,
}: {
  config: ResearchBriefConfig;
  setConfig: (c: TypeConfig) => void;
}) {
  const [subjectInput, setSubjectInput] = useState('');

  const addSubject = () => {
    if (subjectInput.trim()) {
      setConfig({ ...config, subjects: [...config.subjects, subjectInput.trim()] });
      setSubjectInput('');
    }
  };

  const removeSubject = (index: number) => {
    setConfig({ ...config, subjects: config.subjects.filter((_, i) => i !== index) });
  };

  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium mb-2">Focus area</label>
        <div className="flex flex-wrap gap-2">
          {(['competitive', 'market', 'technology', 'industry'] as const).map((area) => (
            <button
              key={area}
              onClick={() => setConfig({ ...config, focus_area: area })}
              className={cn(
                "px-3 py-2 border rounded-md text-sm capitalize transition-colors",
                config.focus_area === area
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {area}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">
          What to monitor <span className="text-red-500">*</span>
        </label>
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={subjectInput}
            onChange={(e) => setSubjectInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSubject())}
            placeholder={
              config.focus_area === 'competitive'
                ? "e.g., Competitor A, Competitor B"
                : "e.g., AI trends, Regulation changes"
            }
            className="flex-1 px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
          <button
            onClick={addSubject}
            className="px-4 py-2 border border-border rounded-md hover:bg-muted text-sm"
          >
            Add
          </button>
        </div>
        {config.subjects.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {config.subjects.map((s, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 px-3 py-1 bg-muted rounded-full text-sm"
              >
                {s}
                <button
                  onClick={() => removeSubject(i)}
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
        <label className="block text-sm font-medium mb-2">Depth</label>
        <div className="flex gap-2">
          {(['scan', 'analysis', 'deep_dive'] as const).map((d) => (
            <button
              key={d}
              onClick={() => setConfig({ ...config, depth: d })}
              className={cn(
                "flex-1 px-3 py-2 border rounded-md text-sm transition-colors",
                config.depth === d
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {d === 'deep_dive' ? 'Deep Dive' : d.charAt(0).toUpperCase() + d.slice(1)}
            </button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Scan: 300-500 words | Analysis: 500-1000 words | Deep Dive: 1000+ words
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Purpose (optional)</label>
        <input
          type="text"
          value={config.purpose || ''}
          onChange={(e) => setConfig({ ...config, purpose: e.target.value })}
          placeholder="e.g., Inform product roadmap decisions"
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
        />
      </div>
    </div>
  );
}

// Meeting Summary Configuration
function MeetingSummaryConfigForm({
  config,
  setConfig,
}: {
  config: MeetingSummaryConfig;
  setConfig: (c: TypeConfig) => void;
}) {
  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium mb-2">
          Meeting name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.meeting_name || ''}
          onChange={(e) => setConfig({ ...config, meeting_name: e.target.value })}
          placeholder="e.g., Engineering Weekly, Product Sync, 1:1 with Sarah"
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          autoFocus
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Meeting type</label>
        <div className="flex flex-wrap gap-2">
          {(['team_sync', 'one_on_one', 'standup', 'review', 'planning'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setConfig({ ...config, meeting_type: t })}
              className={cn(
                "px-3 py-2 border rounded-md text-sm transition-colors",
                config.meeting_type === t
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {t.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Format</label>
        <div className="flex gap-2">
          {(['narrative', 'bullet_points', 'structured'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setConfig({ ...config, format: f })}
              className={cn(
                "flex-1 px-3 py-2 border rounded-md text-sm transition-colors",
                config.format === f
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {f.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Sections to include</label>
        <div className="space-y-2">
          {[
            { key: 'context', label: 'Context/Attendees' },
            { key: 'discussion', label: 'Discussion Points' },
            { key: 'decisions', label: 'Decisions Made' },
            { key: 'action_items', label: 'Action Items' },
            { key: 'followups', label: 'Follow-ups for Next Meeting' },
          ].map(({ key, label }) => (
            <label key={key} className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={config.sections[key as keyof typeof config.sections]}
                onChange={(e) => setConfig({
                  ...config,
                  sections: { ...config.sections, [key]: e.target.checked },
                })}
                className="w-4 h-4 rounded border-border"
              />
              <span className="text-sm">{label}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

// Custom Configuration
function CustomConfigForm({
  config,
  setConfig,
}: {
  config: CustomConfig;
  setConfig: (c: TypeConfig) => void;
}) {
  return (
    <div className="space-y-6">
      <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
        <p className="text-sm text-amber-800 dark:text-amber-200">
          Custom deliverables have less predictable quality. We recommend using
          a predefined type when possible.
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">
          Describe what you need <span className="text-red-500">*</span>
        </label>
        <textarea
          value={config.description || ''}
          onChange={(e) => setConfig({ ...config, description: e.target.value })}
          placeholder="Describe the deliverable, its structure, purpose, and what it should contain..."
          rows={4}
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          autoFocus
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Structure notes (optional)</label>
        <textarea
          value={config.structure_notes || ''}
          onChange={(e) => setConfig({ ...config, structure_notes: e.target.value })}
          placeholder="Describe sections, format, typical length, tone, etc."
          rows={3}
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
        />
      </div>
    </div>
  );
}

// Step 3: Who receives it?
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

// Step 4: What sources inform this?
function StepSources({
  sources,
  setSources,
  deliverableType,
}: {
  sources: DataSource[];
  setSources: (v: DataSource[]) => void;
  deliverableType: DeliverableType | null;
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

  // Type-specific hints
  const typeHints: Record<DeliverableType, string> = {
    status_report: 'Add project management tools, Slack channels, or team standups',
    stakeholder_update: 'Add financial dashboards, key metrics sources, or project trackers',
    research_brief: 'Add competitor websites, industry news sources, or market data feeds',
    meeting_summary: 'Add meeting notes, calendar invites, or previous summaries',
    custom: 'Add any relevant information sources',
  };

  return (
    <div className="space-y-6">
      <p className="text-muted-foreground">
        What information feeds into this deliverable? This helps YARNNN gather
        the right context each cycle.
      </p>

      {deliverableType && (
        <div className="bg-muted/50 rounded-lg p-4">
          <p className="text-xs text-muted-foreground">
            <strong>Tip:</strong> {typeHints[deliverableType]}
          </p>
        </div>
      )}

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
    </div>
  );
}

// Step 5: When is it due? + Title confirmation
function StepSchedule({
  schedule,
  setSchedule,
  title,
  setTitle,
}: {
  schedule: ScheduleConfig;
  setSchedule: (v: ScheduleConfig) => void;
  title: string;
  setTitle: (v: string) => void;
}) {
  const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];

  return (
    <div className="space-y-6">
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
        />
        <p className="text-xs text-muted-foreground mt-1">
          This is how it will appear in your dashboard
        </p>
      </div>

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
