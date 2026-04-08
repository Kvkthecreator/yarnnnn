'use client';

import { DailyBriefing } from '@/components/home/DailyBriefing';
import type { Agent, Task } from '@/types';

interface DailyBriefingArtifactProps {
  agents: Agent[];
  tasks: Task[];
}

export function DailyBriefingArtifact({ agents, tasks }: DailyBriefingArtifactProps) {
  return (
    <DailyBriefing
      agents={agents}
      tasks={tasks}
      hasMessages={false}
      forceExpanded
    />
  );
}
