'use client';

/**
 * Shared mode badge for deliverables.
 *
 * Renders the execution mode (recurring, goal, reactive, proactive, coordinator)
 * as a colored icon+label pill or icon-only indicator.
 *
 * Used on: list page cards (icon variant), workspace header (pill variant).
 */

import { Repeat, Target, Zap, Eye, Bot } from 'lucide-react';
import type { DeliverableMode } from '@/types';

interface DeliverableModeBadgeProps {
  mode?: DeliverableMode;
  variant?: 'pill' | 'icon';
}

const MODE_CONFIG: Record<string, {
  icon: typeof Repeat;
  label: string;
  colors: string;
  iconColor: string;
}> = {
  recurring: {
    icon: Repeat,
    label: 'Rec',
    colors: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
    iconColor: 'text-gray-500 dark:text-gray-400',
  },
  goal: {
    icon: Target,
    label: 'Goal',
    colors: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    iconColor: 'text-blue-600 dark:text-blue-400',
  },
  reactive: {
    icon: Zap,
    label: 'Reactive',
    colors: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
    iconColor: 'text-orange-500 dark:text-orange-400',
  },
  proactive: {
    icon: Eye,
    label: 'Proactive',
    colors: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
    iconColor: 'text-violet-500 dark:text-violet-400',
  },
  coordinator: {
    icon: Bot,
    label: 'Coordinator',
    colors: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
    iconColor: 'text-amber-500 dark:text-amber-400',
  },
};

export function DeliverableModeBadge({ mode, variant = 'pill' }: DeliverableModeBadgeProps) {
  const config = MODE_CONFIG[mode || 'recurring'];
  const Icon = config.icon;

  if (variant === 'icon') {
    return <Icon className={`w-4 h-4 ${config.iconColor}`} />;
  }

  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium ${config.colors}`}>
      <Icon className="w-2.5 h-2.5" />
      {config.label}
    </span>
  );
}
