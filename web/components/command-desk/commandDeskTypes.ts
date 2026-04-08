'use client';

import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

export type CommandDeskWindowId =
  | 'onboarding'
  | 'briefing'
  | 'recent-work'
  | 'context-gaps'
  | 'tp-chat';

export interface CommandDeskWindowDefinition {
  id: CommandDeskWindowId;
  title: string;
  eyebrow?: string;
  icon: LucideIcon;
  content: ReactNode;
  desktopClassName: string;
}
