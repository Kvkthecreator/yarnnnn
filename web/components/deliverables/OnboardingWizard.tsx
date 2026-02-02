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
  Briefcase,
  TrendingUp,
  Mail,
  GitBranch,
  UserCheck,
  BarChart3,
  FlaskConical,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';
import type {
  DeliverableCreate,
  DeliverableType,
  DeliverableTier,
  TypeConfig,
  RecipientContext,
  ScheduleConfig,
  DataSource,
  StatusReportConfig,
  StakeholderUpdateConfig,
  ResearchBriefConfig,
  MeetingSummaryConfig,
  CustomConfig,
  // Beta types
  ClientProposalConfig,
  PerformanceSelfAssessmentConfig,
  NewsletterSectionConfig,
  ChangelogConfig,
  OneOnOnePrepConfig,
  BoardUpdateConfig,
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
interface TypeMeta {
  icon: React.ReactNode;
  title: string;
  description: string;
  examples: string[];
  tier: DeliverableTier;
}

const TYPE_INFO: Record<DeliverableType, TypeMeta> = {
  // Tier 1 - Stable
  status_report: {
    icon: <ClipboardList className="w-6 h-6" />,
    title: 'Status Report',
    description: 'Weekly or recurring updates on project or team progress',
    examples: ['Weekly team status', 'Project updates', 'Sprint summaries'],
    tier: 'stable',
  },
  stakeholder_update: {
    icon: <Users className="w-6 h-6" />,
    title: 'Stakeholder Update',
    description: 'Formal communications to investors, board, or clients',
    examples: ['Monthly investor letter', 'Board update', 'Client progress report'],
    tier: 'stable',
  },
  research_brief: {
    icon: <Search className="w-6 h-6" />,
    title: 'Research Brief',
    description: 'Synthesized intelligence on competitors, market, or topics',
    examples: ['Competitive intel', 'Market monitoring', 'Technology trends'],
    tier: 'stable',
  },
  meeting_summary: {
    icon: <MessageSquare className="w-6 h-6" />,
    title: 'Meeting Summary',
    description: 'Recurring notes and action items from standing meetings',
    examples: ['Weekly sync notes', '1:1 summaries', 'Standup digests'],
    tier: 'stable',
  },
  // Beta Tier
  client_proposal: {
    icon: <Briefcase className="w-6 h-6" />,
    title: 'Client Proposal',
    description: 'Project proposals for consultants, agencies, freelancers',
    examples: ['Project proposals', 'SOWs', 'Renewal proposals'],
    tier: 'beta',
  },
  performance_self_assessment: {
    icon: <TrendingUp className="w-6 h-6" />,
    title: 'Performance Self-Assessment',
    description: 'Quarterly or annual self-reviews with quantified impact',
    examples: ['Quarterly review', 'Annual self-assessment', 'Promotion packet'],
    tier: 'beta',
  },
  newsletter_section: {
    icon: <Mail className="w-6 h-6" />,
    title: 'Newsletter Section',
    description: 'Recurring content for newsletters and digests',
    examples: ['Weekly product update', 'Monthly founder letter', 'Community digest'],
    tier: 'beta',
  },
  changelog: {
    icon: <GitBranch className="w-6 h-6" />,
    title: 'Changelog / Release Notes',
    description: 'Product update communications for users or developers',
    examples: ['Weekly release notes', 'Feature announcements', 'Version changelog'],
    tier: 'beta',
  },
  one_on_one_prep: {
    icon: <UserCheck className="w-6 h-6" />,
    title: '1:1 Prep',
    description: 'Manager prep for recurring 1:1 meetings with reports',
    examples: ['Weekly 1:1 prep', 'Skip-level prep', 'Mentorship session'],
    tier: 'beta',
  },
  board_update: {
    icon: <BarChart3 className="w-6 h-6" />,
    title: 'Board Update',
    description: 'Quarterly board deck narrative sections',
    examples: ['Quarterly board update', 'Investor update', 'Advisory briefing'],
    tier: 'beta',
  },
  // Experimental
  custom: {
    icon: <FileText className="w-6 h-6" />,
    title: 'Custom',
    description: 'Define your own deliverable structure',
    examples: ['Any recurring written content'],
    tier: 'experimental',
  },
};

// Default configs for each type
function getDefaultTypeConfig(type: DeliverableType): TypeConfig {
  switch (type) {
    // Tier 1 - Stable
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
    // Beta Tier
    case 'client_proposal':
      return {
        client_name: '',
        project_type: 'new_engagement',
        service_category: '',
        sections: {
          executive_summary: true,
          needs_understanding: true,
          approach: true,
          deliverables: true,
          timeline: true,
          investment: true,
          social_proof: false,
        },
        tone: 'consultative',
        include_pricing: true,
      } as ClientProposalConfig;
    case 'performance_self_assessment':
      return {
        review_period: 'quarterly',
        role_level: 'ic',
        sections: {
          summary: true,
          accomplishments: true,
          goals_progress: true,
          challenges: true,
          development: true,
          next_period_goals: true,
        },
        tone: 'balanced',
        quantify_impact: true,
      } as PerformanceSelfAssessmentConfig;
    case 'newsletter_section':
      return {
        newsletter_name: '',
        section_type: 'main_story',
        audience: 'customers',
        sections: {
          hook: true,
          main_content: true,
          highlights: true,
          cta: true,
        },
        voice: 'brand',
        length: 'medium',
      } as NewsletterSectionConfig;
    case 'changelog':
      return {
        product_name: '',
        release_type: 'weekly',
        audience: 'mixed',
        sections: {
          highlights: true,
          new_features: true,
          improvements: true,
          bug_fixes: true,
          breaking_changes: false,
          whats_next: false,
        },
        format: 'user_friendly',
        include_links: true,
      } as ChangelogConfig;
    case 'one_on_one_prep':
      return {
        report_name: '',
        meeting_cadence: 'weekly',
        relationship: 'direct_report',
        sections: {
          context: true,
          topics: true,
          recognition: true,
          concerns: true,
          career: true,
          previous_actions: true,
        },
        focus_areas: ['performance', 'growth'],
      } as OneOnOnePrepConfig;
    case 'board_update':
      return {
        company_name: '',
        stage: 'seed',
        update_type: 'quarterly',
        sections: {
          executive_summary: true,
          metrics: true,
          strategic_progress: true,
          challenges: true,
          financials: true,
          asks: true,
          outlook: true,
        },
        tone: 'balanced',
        include_comparisons: true,
      } as BoardUpdateConfig;
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
        // Tier 1 - Stable
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
        // Beta Tier
        if (deliverableType === 'client_proposal') {
          const cfg = typeConfig as ClientProposalConfig;
          return cfg.client_name?.trim().length > 0 && cfg.service_category?.trim().length > 0;
        }
        if (deliverableType === 'performance_self_assessment') {
          return true; // All fields have defaults
        }
        if (deliverableType === 'newsletter_section') {
          return (typeConfig as NewsletterSectionConfig).newsletter_name?.trim().length > 0;
        }
        if (deliverableType === 'changelog') {
          return (typeConfig as ChangelogConfig).product_name?.trim().length > 0;
        }
        if (deliverableType === 'one_on_one_prep') {
          return (typeConfig as OneOnOnePrepConfig).report_name?.trim().length > 0;
        }
        if (deliverableType === 'board_update') {
          return (typeConfig as BoardUpdateConfig).company_name?.trim().length > 0;
        }
        // Experimental
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
        // Tier 1 - Stable
        status_report: 'Weekly Status Report',
        stakeholder_update: 'Monthly Update',
        research_brief: 'Competitive Brief',
        meeting_summary: 'Meeting Notes',
        // Beta Tier
        client_proposal: 'Project Proposal',
        performance_self_assessment: 'Quarterly Self-Assessment',
        newsletter_section: 'Weekly Newsletter',
        changelog: 'Release Notes',
        one_on_one_prep: '1:1 Prep',
        board_update: 'Quarterly Board Update',
        // Experimental
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
  const stableTypes: DeliverableType[] = [
    'status_report',
    'stakeholder_update',
    'research_brief',
    'meeting_summary',
  ];

  const betaTypes: DeliverableType[] = [
    'client_proposal',
    'performance_self_assessment',
    'newsletter_section',
    'changelog',
    'one_on_one_prep',
    'board_update',
  ];

  const TypeCard = ({ type }: { type: DeliverableType }) => {
    const info = TYPE_INFO[type];
    const isBeta = info.tier === 'beta';
    return (
      <button
        onClick={() => onSelect(type)}
        className={cn(
          "flex flex-col items-start p-4 border rounded-lg text-left transition-all relative",
          selectedType === type
            ? "border-primary bg-primary/5 ring-1 ring-primary"
            : "border-border hover:border-foreground/20 hover:bg-muted/50"
        )}
      >
        {isBeta && (
          <span className="absolute top-2 right-2 inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium bg-amber-500/10 text-amber-600 border border-amber-500/20 rounded">
            <FlaskConical className="w-3 h-3" />
            Beta
          </span>
        )}
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
  };

  return (
    <div className="space-y-6">
      <p className="text-muted-foreground">
        Choose the type of deliverable you need. Each type has a proven structure
        that YARNNN can reliably produce.
      </p>

      {/* Stable Types */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {stableTypes.map((type) => (
          <TypeCard key={type} type={type} />
        ))}
      </div>

      {/* Beta Types */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Beta</span>
          <span className="text-xs text-muted-foreground">— Quality is evolving</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {betaTypes.map((type) => (
            <TypeCard key={type} type={type} />
          ))}
        </div>
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
    // Tier 1 - Stable
    case 'status_report':
      return <StatusReportConfigForm config={config as StatusReportConfig} setConfig={setConfig} />;
    case 'stakeholder_update':
      return <StakeholderUpdateConfigForm config={config as StakeholderUpdateConfig} setConfig={setConfig} />;
    case 'research_brief':
      return <ResearchBriefConfigForm config={config as ResearchBriefConfig} setConfig={setConfig} />;
    case 'meeting_summary':
      return <MeetingSummaryConfigForm config={config as MeetingSummaryConfig} setConfig={setConfig} />;
    // Beta Tier
    case 'client_proposal':
      return <ClientProposalConfigForm config={config as ClientProposalConfig} setConfig={setConfig} />;
    case 'performance_self_assessment':
      return <PerformanceSelfAssessmentConfigForm config={config as PerformanceSelfAssessmentConfig} setConfig={setConfig} />;
    case 'newsletter_section':
      return <NewsletterSectionConfigForm config={config as NewsletterSectionConfig} setConfig={setConfig} />;
    case 'changelog':
      return <ChangelogConfigForm config={config as ChangelogConfig} setConfig={setConfig} />;
    case 'one_on_one_prep':
      return <OneOnOnePrepConfigForm config={config as OneOnOnePrepConfig} setConfig={setConfig} />;
    case 'board_update':
      return <BoardUpdateConfigForm config={config as BoardUpdateConfig} setConfig={setConfig} />;
    // Experimental
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

// =============================================================================
// Beta Tier Config Forms
// =============================================================================

// Client Proposal Configuration
function ClientProposalConfigForm({
  config,
  setConfig,
}: {
  config: ClientProposalConfig;
  setConfig: (c: TypeConfig) => void;
}) {
  return (
    <div className="space-y-6">
      <BetaBadge />

      <div>
        <label className="block text-sm font-medium mb-2">
          Client name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.client_name || ''}
          onChange={(e) => setConfig({ ...config, client_name: e.target.value })}
          placeholder="e.g., Acme Corp, Client X"
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          autoFocus
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">
          Service category <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.service_category || ''}
          onChange={(e) => setConfig({ ...config, service_category: e.target.value })}
          placeholder="e.g., Brand Strategy, Web Development, Consulting"
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Project type</label>
        <div className="flex flex-wrap gap-2">
          {(['new_engagement', 'expansion', 'renewal'] as const).map((pt) => (
            <button
              key={pt}
              onClick={() => setConfig({ ...config, project_type: pt })}
              className={cn(
                "px-3 py-2 border rounded-md text-sm transition-colors",
                config.project_type === pt
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {pt === 'new_engagement' ? 'New Engagement' : pt === 'expansion' ? 'Expansion' : 'Renewal'}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Tone</label>
        <div className="flex gap-2">
          {(['formal', 'consultative', 'friendly'] as const).map((tone) => (
            <button
              key={tone}
              onClick={() => setConfig({ ...config, tone })}
              className={cn(
                "flex-1 px-3 py-2 border rounded-md text-sm capitalize transition-colors",
                config.tone === tone
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {tone}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={config.include_pricing}
            onChange={(e) => setConfig({ ...config, include_pricing: e.target.checked })}
            className="w-4 h-4 rounded border-border"
          />
          <span className="text-sm">Include pricing/investment section</span>
        </label>
      </div>
    </div>
  );
}

// Performance Self-Assessment Configuration
function PerformanceSelfAssessmentConfigForm({
  config,
  setConfig,
}: {
  config: PerformanceSelfAssessmentConfig;
  setConfig: (c: TypeConfig) => void;
}) {
  return (
    <div className="space-y-6">
      <BetaBadge />

      <div>
        <label className="block text-sm font-medium mb-2">Review period</label>
        <div className="flex gap-2">
          {(['quarterly', 'semi_annual', 'annual'] as const).map((period) => (
            <button
              key={period}
              onClick={() => setConfig({ ...config, review_period: period })}
              className={cn(
                "flex-1 px-3 py-2 border rounded-md text-sm transition-colors",
                config.review_period === period
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {period === 'quarterly' ? 'Quarterly' : period === 'semi_annual' ? 'Semi-Annual' : 'Annual'}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Role level</label>
        <div className="flex flex-wrap gap-2">
          {(['ic', 'senior_ic', 'lead', 'manager', 'director'] as const).map((level) => (
            <button
              key={level}
              onClick={() => setConfig({ ...config, role_level: level })}
              className={cn(
                "px-3 py-2 border rounded-md text-sm transition-colors",
                config.role_level === level
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {level === 'ic' ? 'IC' : level === 'senior_ic' ? 'Senior IC' : level.charAt(0).toUpperCase() + level.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Tone</label>
        <div className="flex gap-2">
          {(['humble', 'balanced', 'confident'] as const).map((tone) => (
            <button
              key={tone}
              onClick={() => setConfig({ ...config, tone })}
              className={cn(
                "flex-1 px-3 py-2 border rounded-md text-sm capitalize transition-colors",
                config.tone === tone
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {tone}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={config.quantify_impact}
            onChange={(e) => setConfig({ ...config, quantify_impact: e.target.checked })}
            className="w-4 h-4 rounded border-border"
          />
          <span className="text-sm">Emphasize quantified impact (metrics, %s, numbers)</span>
        </label>
      </div>
    </div>
  );
}

// Newsletter Section Configuration
function NewsletterSectionConfigForm({
  config,
  setConfig,
}: {
  config: NewsletterSectionConfig;
  setConfig: (c: TypeConfig) => void;
}) {
  return (
    <div className="space-y-6">
      <BetaBadge />

      <div>
        <label className="block text-sm font-medium mb-2">
          Newsletter name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.newsletter_name || ''}
          onChange={(e) => setConfig({ ...config, newsletter_name: e.target.value })}
          placeholder="e.g., Weekly Product Update, Founder's Letter"
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          autoFocus
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Section type</label>
        <div className="flex flex-wrap gap-2">
          {(['intro', 'main_story', 'roundup', 'outro'] as const).map((st) => (
            <button
              key={st}
              onClick={() => setConfig({ ...config, section_type: st })}
              className={cn(
                "px-3 py-2 border rounded-md text-sm transition-colors",
                config.section_type === st
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {st === 'main_story' ? 'Main Story' : st.charAt(0).toUpperCase() + st.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Audience</label>
        <div className="flex flex-wrap gap-2">
          {(['customers', 'team', 'investors', 'community'] as const).map((aud) => (
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
        <label className="block text-sm font-medium mb-2">Length</label>
        <div className="flex gap-2">
          {(['short', 'medium', 'long'] as const).map((len) => (
            <button
              key={len}
              onClick={() => setConfig({ ...config, length: len })}
              className={cn(
                "flex-1 px-3 py-2 border rounded-md text-sm transition-colors",
                config.length === len
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {len === 'short' ? 'Short (100-200)' : len === 'medium' ? 'Medium (200-400)' : 'Long (400-800)'}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// Changelog Configuration
function ChangelogConfigForm({
  config,
  setConfig,
}: {
  config: ChangelogConfig;
  setConfig: (c: TypeConfig) => void;
}) {
  return (
    <div className="space-y-6">
      <BetaBadge />

      <div>
        <label className="block text-sm font-medium mb-2">
          Product name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.product_name || ''}
          onChange={(e) => setConfig({ ...config, product_name: e.target.value })}
          placeholder="e.g., Acme App, Platform v2"
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          autoFocus
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Release type</label>
        <div className="flex flex-wrap gap-2">
          {(['weekly', 'patch', 'minor', 'major'] as const).map((rt) => (
            <button
              key={rt}
              onClick={() => setConfig({ ...config, release_type: rt })}
              className={cn(
                "px-3 py-2 border rounded-md text-sm capitalize transition-colors",
                config.release_type === rt
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {rt}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Audience</label>
        <div className="flex gap-2">
          {(['developers', 'end_users', 'mixed'] as const).map((aud) => (
            <button
              key={aud}
              onClick={() => setConfig({ ...config, audience: aud })}
              className={cn(
                "flex-1 px-3 py-2 border rounded-md text-sm transition-colors",
                config.audience === aud
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {aud === 'end_users' ? 'End Users' : aud.charAt(0).toUpperCase() + aud.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Format</label>
        <div className="flex gap-2">
          {(['technical', 'user_friendly', 'marketing'] as const).map((fmt) => (
            <button
              key={fmt}
              onClick={() => setConfig({ ...config, format: fmt })}
              className={cn(
                "flex-1 px-3 py-2 border rounded-md text-sm transition-colors",
                config.format === fmt
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {fmt === 'user_friendly' ? 'User-Friendly' : fmt.charAt(0).toUpperCase() + fmt.slice(1)}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// 1:1 Prep Configuration
function OneOnOnePrepConfigForm({
  config,
  setConfig,
}: {
  config: OneOnOnePrepConfig;
  setConfig: (c: TypeConfig) => void;
}) {
  return (
    <div className="space-y-6">
      <BetaBadge />

      <div>
        <label className="block text-sm font-medium mb-2">
          Report name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.report_name || ''}
          onChange={(e) => setConfig({ ...config, report_name: e.target.value })}
          placeholder="e.g., Alex, Sarah, Team Member"
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          autoFocus
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Meeting cadence</label>
        <div className="flex gap-2">
          {(['weekly', 'biweekly', 'monthly'] as const).map((cad) => (
            <button
              key={cad}
              onClick={() => setConfig({ ...config, meeting_cadence: cad })}
              className={cn(
                "flex-1 px-3 py-2 border rounded-md text-sm capitalize transition-colors",
                config.meeting_cadence === cad
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {cad}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Relationship</label>
        <div className="flex gap-2">
          {(['direct_report', 'skip_level', 'mentee'] as const).map((rel) => (
            <button
              key={rel}
              onClick={() => setConfig({ ...config, relationship: rel })}
              className={cn(
                "flex-1 px-3 py-2 border rounded-md text-sm transition-colors",
                config.relationship === rel
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {rel === 'direct_report' ? 'Direct Report' : rel === 'skip_level' ? 'Skip Level' : 'Mentee'}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Focus areas</label>
        <div className="flex flex-wrap gap-2">
          {(['performance', 'growth', 'wellbeing', 'blockers'] as const).map((area) => (
            <button
              key={area}
              onClick={() => {
                const current = config.focus_areas || [];
                const updated = current.includes(area)
                  ? current.filter((a) => a !== area)
                  : [...current, area];
                setConfig({ ...config, focus_areas: updated });
              }}
              className={cn(
                "px-3 py-2 border rounded-md text-sm capitalize transition-colors",
                config.focus_areas?.includes(area)
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {area}
            </button>
          ))}
        </div>
        <p className="text-xs text-muted-foreground mt-1">Select one or more</p>
      </div>
    </div>
  );
}

// Board Update Configuration
function BoardUpdateConfigForm({
  config,
  setConfig,
}: {
  config: BoardUpdateConfig;
  setConfig: (c: TypeConfig) => void;
}) {
  return (
    <div className="space-y-6">
      <BetaBadge />

      <div>
        <label className="block text-sm font-medium mb-2">
          Company name <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={config.company_name || ''}
          onChange={(e) => setConfig({ ...config, company_name: e.target.value })}
          placeholder="e.g., Acme Inc."
          className="w-full px-4 py-3 border border-border rounded-md bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
          autoFocus
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Company stage</label>
        <div className="flex flex-wrap gap-2">
          {(['pre_seed', 'seed', 'series_a', 'series_b_plus', 'growth'] as const).map((stage) => (
            <button
              key={stage}
              onClick={() => setConfig({ ...config, stage })}
              className={cn(
                "px-3 py-2 border rounded-md text-sm transition-colors",
                config.stage === stage
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {stage === 'pre_seed' ? 'Pre-Seed' : stage === 'series_b_plus' ? 'Series B+' : stage.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Update type</label>
        <div className="flex gap-2">
          {(['quarterly', 'monthly', 'special'] as const).map((ut) => (
            <button
              key={ut}
              onClick={() => setConfig({ ...config, update_type: ut })}
              className={cn(
                "flex-1 px-3 py-2 border rounded-md text-sm capitalize transition-colors",
                config.update_type === ut
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {ut}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Tone</label>
        <div className="flex gap-2">
          {(['optimistic', 'balanced', 'candid'] as const).map((tone) => (
            <button
              key={tone}
              onClick={() => setConfig({ ...config, tone })}
              className={cn(
                "flex-1 px-3 py-2 border rounded-md text-sm capitalize transition-colors",
                config.tone === tone
                  ? "border-primary bg-primary/5 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              {tone}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={config.include_comparisons}
            onChange={(e) => setConfig({ ...config, include_comparisons: e.target.checked })}
            className="w-4 h-4 rounded border-border"
          />
          <span className="text-sm">Include comparisons (vs last quarter, vs plan)</span>
        </label>
      </div>
    </div>
  );
}

// Beta Badge Component
function BetaBadge() {
  return (
    <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 flex items-start gap-2">
      <FlaskConical className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
      <p className="text-sm text-amber-800 dark:text-amber-200">
        This is a <strong>Beta</strong> type. Quality is actively improving based on user feedback.
      </p>
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
