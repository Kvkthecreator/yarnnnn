'use client';

import { DailyBriefing } from '@/components/home/DailyBriefing';
import type { Agent, Task } from '@/types';

interface DailyBriefingWindowProps {
  agents: Agent[];
  tasks: Task[];
  hasMessages: boolean;
}

export function DailyBriefingWindow({ agents, tasks, hasMessages }: DailyBriefingWindowProps) {
  return (
    <DailyBriefing
      agents={agents}
      tasks={tasks}
      hasMessages={hasMessages}
    />
  );
}
