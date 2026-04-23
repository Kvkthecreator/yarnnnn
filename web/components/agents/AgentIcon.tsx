'use client';

/**
 * AgentIcon — role-specific icon for agent cards and detail views.
 *
 * Single source of truth for which icon represents each agent role.
 * Icon names are declared in agent-identity.ts (ROLE_META.iconName) and
 * resolved here to the actual lucide component. Both AgentRosterSurface
 * and AgentContentView import this — no icon logic lives in either surface.
 */

import {
  BarChart3,
  BookOpen,
  Brain,
  Crosshair,
  GitBranch,
  Handshake,
  Hash,
  Megaphone,
  MessageCircle,
  Settings2,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { roleIconName } from '@/lib/agent-identity';

const ICON_MAP: Record<string, React.ElementType> = {
  BarChart3,
  BookOpen,
  Brain,
  Crosshair,
  GitBranch,
  Handshake,
  Hash,
  Megaphone,
  MessageCircle,
  Settings2,
  ShieldCheck,  // ADR-214: Reviewer role icon
  TrendingUp,
};

interface AgentIconProps {
  role?: string | null;
  className?: string;
}

export function AgentIcon({ role, className }: AgentIconProps) {
  const name = roleIconName(role);
  const Icon = ICON_MAP[name] ?? Brain;
  return <Icon className={cn('w-4 h-4', className)} />;
}
