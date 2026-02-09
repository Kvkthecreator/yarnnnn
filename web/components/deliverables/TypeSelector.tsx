'use client';

/**
 * TypeSelector - Deliverable type selection for create wizard
 *
 * Step 2 in the destination-first flow:
 * Destination → Type → Sources → Schedule
 *
 * Shows deliverable types as cards with descriptions.
 */

import { cn } from '@/lib/utils';
import {
  FileText,
  Users,
  Search,
  MessageSquare,
  Sparkles,
  Mail,
  BarChart3,
  ClipboardList,
  Newspaper,
  GitCommit,
  UserCheck,
  Building2,
} from 'lucide-react';
import type { DeliverableType } from '@/types';

interface TypeOption {
  value: DeliverableType;
  label: string;
  description: string;
  icon: React.ReactNode;
}

const TYPE_OPTIONS: TypeOption[] = [
  {
    value: 'status_report',
    label: 'Status Report',
    description: 'Weekly or daily progress updates',
    icon: <BarChart3 className="w-5 h-5" />,
  },
  {
    value: 'stakeholder_update',
    label: 'Stakeholder Update',
    description: 'Executive summaries for leadership',
    icon: <Users className="w-5 h-5" />,
  },
  {
    value: 'meeting_summary',
    label: 'Meeting Summary',
    description: 'Action items and decisions from meetings',
    icon: <MessageSquare className="w-5 h-5" />,
  },
  {
    value: 'research_brief',
    label: 'Research Brief',
    description: 'Synthesized findings on a topic',
    icon: <Search className="w-5 h-5" />,
  },
  {
    value: 'one_on_one_prep',
    label: '1:1 Prep',
    description: 'Talking points for one-on-one meetings',
    icon: <UserCheck className="w-5 h-5" />,
  },
  {
    value: 'inbox_summary',
    label: 'Inbox Summary',
    description: 'Digest of important emails',
    icon: <Mail className="w-5 h-5" />,
  },
  {
    value: 'changelog',
    label: 'Changelog',
    description: 'Product or project change log',
    icon: <GitCommit className="w-5 h-5" />,
  },
  {
    value: 'newsletter_section',
    label: 'Newsletter',
    description: 'Content for newsletters or updates',
    icon: <Newspaper className="w-5 h-5" />,
  },
  {
    value: 'board_update',
    label: 'Board Update',
    description: 'Formal updates for board meetings',
    icon: <Building2 className="w-5 h-5" />,
  },
  {
    value: 'custom',
    label: 'Custom',
    description: 'Define your own format',
    icon: <Sparkles className="w-5 h-5" />,
  },
];

interface TypeSelectorProps {
  value: DeliverableType | undefined;
  onChange: (type: DeliverableType) => void;
}

export function TypeSelector({ value, onChange }: TypeSelectorProps) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        What type of content should this deliverable produce?
      </p>

      <div className="grid grid-cols-2 gap-2">
        {TYPE_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={cn(
              'p-3 rounded-lg border text-left transition-all',
              value === option.value
                ? 'border-primary bg-primary/5 ring-1 ring-primary/20'
                : 'border-border hover:border-muted-foreground/50 hover:bg-muted/30'
            )}
          >
            <div className="flex items-start gap-3">
              <div
                className={cn(
                  'shrink-0 mt-0.5',
                  value === option.value ? 'text-primary' : 'text-muted-foreground'
                )}
              >
                {option.icon}
              </div>
              <div className="min-w-0">
                <div className="text-sm font-medium">{option.label}</div>
                <div className="text-xs text-muted-foreground line-clamp-2">
                  {option.description}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
