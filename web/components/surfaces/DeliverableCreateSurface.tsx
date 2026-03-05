'use client';

/**
 * Deliverable Creation — Type Selection Grid
 *
 * Type picker that hands off to TP chat for configuration.
 * User selects a type → redirected to /dashboard?create={type} →
 * TP chat pre-fills with "I want to create a {Type} deliverable".
 *
 * ADR-092: Mode is set implicitly from type — no manual mode picker.
 * ADR-093: 7 purpose-first types + coordinator.
 */

import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Slack,
  FileText,
  BarChart3,
  Users,
  Sparkles,
  Bot,
  Eye,
} from 'lucide-react';
import type { DeliverableMode, DeliverableType, ScheduleConfig, TypeClassification } from '@/types';

// =============================================================================
// Types
// =============================================================================

interface DeliverableCreateSurfaceProps {
  onBack?: () => void;
}

interface TypeDefinition {
  id: DeliverableType;
  label: string;
  description: string;
  icon: React.ReactNode;
  category: 'inform' | 'produce' | 'advanced';
  implicitMode: DeliverableMode;
  classification: TypeClassification;
  defaultSchedule: Partial<ScheduleConfig>;
}

// =============================================================================
// Type Definitions (ADR-093 types + ADR-092 implicit modes)
// =============================================================================

const DELIVERABLE_TYPES: TypeDefinition[] = [
  // -- Keep me informed --
  {
    id: 'digest',
    label: 'Digest',
    description: 'Regular synthesis of activity in a specific place',
    icon: <Slack className="w-5 h-5" />,
    category: 'inform',
    implicitMode: 'recurring',
    classification: {
      binding: 'platform_bound',
      temporal_pattern: 'scheduled',
      freshness_requirement_hours: 1,
    },
    defaultSchedule: { frequency: 'weekly', day: 'monday', time: '09:00' },
  },
  {
    id: 'status',
    label: 'Status Update',
    description: 'Periodic summary across your platforms',
    icon: <BarChart3 className="w-5 h-5" />,
    category: 'inform',
    implicitMode: 'recurring',
    classification: {
      binding: 'cross_platform',
      temporal_pattern: 'scheduled',
      freshness_requirement_hours: 4,
    },
    defaultSchedule: { frequency: 'weekly', day: 'friday', time: '16:00' },
  },
  {
    id: 'watch',
    label: 'Watch',
    description: 'Standing-order intelligence on a domain — surfaces things when they matter',
    icon: <Eye className="w-5 h-5" />,
    category: 'inform',
    implicitMode: 'proactive',
    classification: {
      binding: 'cross_platform',
      temporal_pattern: 'on_demand',
      freshness_requirement_hours: 4,
    },
    defaultSchedule: {},
  },
  // -- Get something done --
  {
    id: 'brief',
    label: 'Brief',
    description: 'Situation-specific document before a key event or meeting',
    icon: <Users className="w-5 h-5" />,
    category: 'produce',
    implicitMode: 'recurring',
    classification: {
      binding: 'cross_platform',
      temporal_pattern: 'reactive',
      freshness_requirement_hours: 1,
    },
    defaultSchedule: { frequency: 'weekly', day: 'monday', time: '08:00' },
  },
  {
    id: 'deep_research',
    label: 'Deep Research',
    description: 'Bounded investigation into something specific, then done',
    icon: <FileText className="w-5 h-5" />,
    category: 'produce',
    implicitMode: 'goal',
    classification: {
      binding: 'research',
      temporal_pattern: 'on_demand',
      freshness_requirement_hours: 24,
    },
    defaultSchedule: { frequency: 'weekly', day: 'friday', time: '16:00' },
  },
  {
    id: 'custom',
    label: 'Custom',
    description: 'Define your own recurring output',
    icon: <Sparkles className="w-5 h-5" />,
    category: 'produce',
    implicitMode: 'recurring',
    classification: {
      binding: 'hybrid',
      temporal_pattern: 'scheduled',
      freshness_requirement_hours: 4,
    },
    defaultSchedule: { frequency: 'weekly', day: 'friday', time: '16:00' },
  },
  // -- Advanced --
  {
    id: 'coordinator',
    label: 'Coordinator',
    description: 'Watches a domain and creates or triggers other deliverables',
    icon: <Bot className="w-5 h-5" />,
    category: 'advanced',
    implicitMode: 'coordinator',
    classification: {
      binding: 'cross_platform',
      temporal_pattern: 'on_demand',
      freshness_requirement_hours: 4,
    },
    defaultSchedule: {},
  },
];

// =============================================================================
// Main Component
// =============================================================================

export function DeliverableCreateSurface({ onBack }: DeliverableCreateSurfaceProps) {
  const router = useRouter();

  const handleTypeSelect = (type: TypeDefinition) => {
    router.push(`/dashboard?create=${type.id}`);
  };

  const handleBack = () => {
    if (onBack) {
      onBack();
    } else {
      router.push('/deliverables');
    }
  };

  const informTypes = DELIVERABLE_TYPES.filter((t) => t.category === 'inform');
  const produceTypes = DELIVERABLE_TYPES.filter((t) => t.category === 'produce');
  const advancedTypes = DELIVERABLE_TYPES.filter((t) => t.category === 'advanced');

  const TypeCard = ({ type }: { type: TypeDefinition }) => (
    <button
      key={type.id}
      onClick={() => handleTypeSelect(type)}
      className="p-4 border border-border rounded-lg text-left hover:border-primary hover:bg-primary/5 transition-all"
    >
      <div className="text-primary mb-2">{type.icon}</div>
      <div className="text-sm font-medium">{type.label}</div>
      <div className="text-xs text-muted-foreground mt-1">
        {type.description}
      </div>
    </button>
  );

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-4 px-6 py-4 border-b border-border">
        <button
          onClick={handleBack}
          className="p-2 hover:bg-muted rounded-md text-muted-foreground"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-lg font-semibold">Create Deliverable</h1>
          <p className="text-sm text-muted-foreground">
            What do you need?
          </p>
        </div>
      </div>

      {/* Type Selection */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-2xl mx-auto space-y-8">
          {/* Keep me informed */}
          <section>
            <h2 className="text-sm font-medium text-muted-foreground mb-1">
              Keep me informed
            </h2>
            <p className="text-xs text-muted-foreground mb-4">
              Ongoing monitoring and regular updates
            </p>
            <div className="grid grid-cols-3 gap-3">
              {informTypes.map((type) => (
                <TypeCard key={type.id} type={type} />
              ))}
            </div>
          </section>

          {/* Get something done */}
          <section>
            <h2 className="text-sm font-medium text-muted-foreground mb-1">
              Get something done
            </h2>
            <p className="text-xs text-muted-foreground mb-4">
              Produce a specific output or complete a task
            </p>
            <div className="grid grid-cols-3 gap-3">
              {produceTypes.map((type) => (
                <TypeCard key={type.id} type={type} />
              ))}
            </div>
          </section>

          {/* Advanced */}
          <section>
            <h2 className="text-sm font-medium text-muted-foreground mb-1">
              Advanced
            </h2>
            <p className="text-xs text-muted-foreground mb-4">
              Autonomous agents that manage other deliverables
            </p>
            <div className="grid grid-cols-3 gap-3">
              {advancedTypes.map((type) => (
                <TypeCard key={type.id} type={type} />
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
