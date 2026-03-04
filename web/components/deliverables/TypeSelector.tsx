'use client';

/**
 * TypeSelector - ADR-044 Binding-First Deliverable Type Selection
 *
 * Two-step flow:
 * 1. Select context binding (Platform Monitor, Cross-Platform, Research, Custom)
 * 2. Select specific type within that binding
 *
 * Part of the destination-first wizard:
 * Destination → Type → Sources → Schedule
 */

import { useState } from 'react';
import { cn } from '@/lib/utils';
import {
  Users,
  Search,
  Sparkles,
  Mail,
  BarChart3,
  Hash,
  FileCode,
  ChevronLeft,
  Monitor,
  Combine,
  Microscope,
  Calendar,
  Clock,
} from 'lucide-react';
import type { DeliverableType, ContextBinding, TypeClassification } from '@/types';

// =============================================================================
// BINDING CATEGORIES (ADR-044)
// =============================================================================

interface BindingOption {
  value: ContextBinding;
  label: string;
  description: string;
  icon: React.ReactNode;
}

const BINDING_OPTIONS: BindingOption[] = [
  {
    value: 'platform_bound',
    label: 'Platform Monitor',
    description: 'Stay on top of a specific platform',
    icon: <Monitor className="w-6 h-6" />,
  },
  {
    value: 'cross_platform',
    label: 'Cross-Platform',
    description: 'Combine context from multiple sources',
    icon: <Combine className="w-6 h-6" />,
  },
  {
    value: 'research',
    label: 'Research & Discovery',
    description: 'Build understanding through research',
    icon: <Microscope className="w-6 h-6" />,
  },
  {
    value: 'hybrid',
    label: 'Custom',
    description: 'Define your own format',
    icon: <Sparkles className="w-6 h-6" />,
  },
];

// =============================================================================
// PLATFORM-BOUND TYPES
// =============================================================================

interface PlatformTypeOption {
  value: DeliverableType;
  label: string;
  description: string;
  icon: React.ReactNode;
  platform: 'slack' | 'gmail' | 'notion' | 'calendar';
}

// ADR-093: digest type shown as platform-grouped (platform inferred from sources[])
const PLATFORM_TYPES: PlatformTypeOption[] = [
  {
    value: 'digest',
    label: 'Digest',
    description: 'Regular synthesis of a specific channel, inbox, or page',
    icon: <Hash className="w-5 h-5" />,
    platform: 'slack',  // default display platform; actual platform comes from sources
  },
];

// =============================================================================
// CROSS-PLATFORM TYPES
// =============================================================================

interface CrossPlatformTypeOption {
  value: DeliverableType;
  label: string;
  description: string;
  icon: React.ReactNode;
}

// ADR-093: cross-platform types
const CROSS_PLATFORM_TYPES: CrossPlatformTypeOption[] = [
  {
    value: 'brief',
    label: 'Brief',
    description: 'Situation-specific document before a key event or meeting',
    icon: <Users className="w-5 h-5" />,
  },
  {
    value: 'status',
    label: 'Status Update',
    description: 'Regular cross-platform summary for a person or audience',
    icon: <BarChart3 className="w-5 h-5" />,
  },
  {
    value: 'watch',
    label: 'Watch',
    description: 'Standing-order intelligence on a domain worth monitoring',
    icon: <Clock className="w-5 h-5" />,
  },
  {
    value: 'custom',
    label: 'Custom',
    description: 'Define your own output from scratch',
    icon: <FileCode className="w-5 h-5" />,
  },
];

// =============================================================================
// RESEARCH TYPES
// =============================================================================

const RESEARCH_TYPES: CrossPlatformTypeOption[] = [
  {
    value: 'deep_research',
    label: 'Deep Research',
    description: 'Bounded investigation into something specific, then done',
    icon: <Search className="w-5 h-5" />,
  },
];

// =============================================================================
// COMPONENT
// =============================================================================

interface TypeSelectorProps {
  value: DeliverableType | undefined;
  onChange: (type: DeliverableType, classification?: TypeClassification) => void;
}

type Platform = 'slack' | 'gmail' | 'notion' | 'calendar';

export function TypeSelector({ value, onChange }: TypeSelectorProps) {
  const [selectedBinding, setSelectedBinding] = useState<ContextBinding | null>(null);
  const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(null);

  // Reset to binding selection
  const handleBack = () => {
    if (selectedPlatform) {
      setSelectedPlatform(null);
    } else {
      setSelectedBinding(null);
    }
  };

  // Handle binding selection
  const handleBindingSelect = (binding: ContextBinding) => {
    setSelectedBinding(binding);
    setSelectedPlatform(null);

    // For custom/hybrid, select immediately
    if (binding === 'hybrid') {
      onChange('custom', {
        binding: 'hybrid',
        temporal_pattern: 'scheduled',
        freshness_requirement_hours: 4,
      });
    }
  };

  // Handle platform selection (for platform-bound)
  const handlePlatformSelect = (platform: Platform) => {
    setSelectedPlatform(platform);
  };

  // Handle final type selection
  const handleTypeSelect = (type: DeliverableType, binding: ContextBinding, platform?: Platform) => {
    const classification: TypeClassification = {
      binding,
      temporal_pattern: 'scheduled',
      primary_platform: platform,
      freshness_requirement_hours: binding === 'platform_bound' ? 1 : 4,
    };
    onChange(type, classification);
  };

  // STEP 1: Binding selection
  if (!selectedBinding) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">
          What kind of deliverable do you need?
        </p>

        <div className="space-y-2">
          {BINDING_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => handleBindingSelect(option.value)}
              className={cn(
                'w-full p-4 rounded-lg border text-left transition-all',
                'border-border hover:border-muted-foreground/50 hover:bg-muted/30'
              )}
            >
              <div className="flex items-start gap-4">
                <div className="shrink-0 text-muted-foreground">
                  {option.icon}
                </div>
                <div className="min-w-0">
                  <div className="text-sm font-medium">{option.label}</div>
                  <div className="text-xs text-muted-foreground">
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

  // STEP 2a: Platform selection (for platform-bound)
  if (selectedBinding === 'platform_bound' && !selectedPlatform) {
    return (
      <div className="space-y-3">
        <button
          type="button"
          onClick={handleBack}
          className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          <ChevronLeft className="w-4 h-4" />
          Back
        </button>

        <p className="text-sm text-muted-foreground">
          Which platform do you want to monitor?
        </p>

        <div className="grid grid-cols-2 gap-3">
          {(['slack', 'gmail', 'notion', 'calendar'] as const).map((platform) => (
            <button
              key={platform}
              type="button"
              onClick={() => handlePlatformSelect(platform)}
              className={cn(
                'p-4 rounded-lg border text-center transition-all',
                'border-border hover:border-muted-foreground/50 hover:bg-muted/30'
              )}
            >
              <div className="flex flex-col items-center gap-2">
                {platform === 'slack' && <Hash className="w-6 h-6 text-purple-500" />}
                {platform === 'gmail' && <Mail className="w-6 h-6 text-red-500" />}
                {platform === 'notion' && <FileCode className="w-6 h-6 text-gray-700 dark:text-gray-300" />}
                {platform === 'calendar' && <Calendar className="w-6 h-6 text-blue-500" />}
                <span className="text-sm font-medium capitalize">{platform}</span>
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  // STEP 2b: Type selection within binding
  const showBackButton = selectedBinding !== null;
  let typesForBinding: (PlatformTypeOption | CrossPlatformTypeOption)[] = [];
  let titleText = '';

  if (selectedBinding === 'platform_bound' && selectedPlatform) {
    typesForBinding = PLATFORM_TYPES.filter((t) => t.platform === selectedPlatform);
    titleText = `What do you want from ${selectedPlatform}?`;
  } else if (selectedBinding === 'cross_platform') {
    typesForBinding = CROSS_PLATFORM_TYPES;
    titleText = 'What type of synthesis?';
  } else if (selectedBinding === 'research') {
    typesForBinding = RESEARCH_TYPES;
    titleText = 'What kind of research?';
  }

  return (
    <div className="space-y-3">
      {showBackButton && (
        <button
          type="button"
          onClick={handleBack}
          className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
        >
          <ChevronLeft className="w-4 h-4" />
          Back
        </button>
      )}

      <p className="text-sm text-muted-foreground">{titleText}</p>

      <div className="grid grid-cols-2 gap-2">
        {typesForBinding.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() =>
              handleTypeSelect(
                option.value,
                selectedBinding!,
                selectedBinding === 'platform_bound' ? selectedPlatform ?? undefined : undefined
              )
            }
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

