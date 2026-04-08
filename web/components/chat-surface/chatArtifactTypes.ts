'use client';

import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';

export type ChatArtifactId =
  | 'onboarding'
  | 'briefing'
  | 'recent-work'
  | 'context-gaps'
  | 'chat';

export interface ChatArtifactTab {
  id: ChatArtifactId;
  label: string;
  icon: LucideIcon;
  content?: ReactNode;
}
