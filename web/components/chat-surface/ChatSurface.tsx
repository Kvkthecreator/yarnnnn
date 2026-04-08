'use client';

import { useEffect, useMemo, useState } from 'react';
import { ClipboardList, Compass, Newspaper, PanelsTopLeft } from 'lucide-react';
import { ChatPanel } from '@/components/tp/ChatPanel';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import type { Agent, Task } from '@/types';
import { ChatArtifactCard } from './ChatArtifactCard';
import { ChatArtifactTabs } from './ChatArtifactTabs';
import type { ChatArtifactId, ChatArtifactTab } from './chatArtifactTypes';
import { ContextGapsArtifact } from './artifacts/ContextGapsArtifact';
import { DailyBriefingArtifact } from './artifacts/DailyBriefingArtifact';
import { OnboardingArtifact } from './artifacts/OnboardingArtifact';
import { RecentWorkArtifact } from './artifacts/RecentWorkArtifact';

interface ChatSurfaceProps {
  agents: Agent[];
  tasks: Task[];
  dataLoading: boolean;
  isNewUser: boolean;
  plusMenuActions: PlusMenuAction[];
  onContextSubmit: (message: string) => void;
}

const CHAT_EMPTY_STATE = (
  <div className="rounded-lg border border-dashed border-border bg-muted/20 px-4 py-5 text-center">
    <p className="text-sm font-medium">TP is here.</p>
    <p className="mt-1 text-sm text-muted-foreground">
      Ask for a readout, a new task, or what needs attention.
    </p>
  </div>
);

export function ChatSurface({
  agents,
  tasks,
  dataLoading,
  isNewUser,
  plusMenuActions,
  onContextSubmit,
}: ChatSurfaceProps) {
  const [activeArtifactId, setActiveArtifactId] = useState<ChatArtifactId>(isNewUser ? 'onboarding' : 'briefing');

  useEffect(() => {
    if (isNewUser) {
      setActiveArtifactId('onboarding');
      return;
    }

    if (activeArtifactId === 'onboarding') {
      setActiveArtifactId('briefing');
    }
  }, [activeArtifactId, isNewUser]);

  const tabs = useMemo<ChatArtifactTab[]>(() => {
    const baseTabs: ChatArtifactTab[] = [
      {
        id: 'briefing',
        label: 'Daily Briefing',
        icon: Newspaper,
        content: <DailyBriefingArtifact agents={agents} tasks={tasks} />,
      },
      {
        id: 'recent-work',
        label: 'Recent Work',
        icon: ClipboardList,
        content: <RecentWorkArtifact agents={agents} tasks={tasks} loading={dataLoading} />,
      },
      {
        id: 'context-gaps',
        label: 'Context Gaps',
        icon: Compass,
        content: <ContextGapsArtifact agents={agents} tasks={tasks} loading={dataLoading} />,
      },
    ];

    if (!isNewUser) return baseTabs;

    return [
      {
        id: 'onboarding',
        label: 'Get Started',
        icon: PanelsTopLeft,
        content: <OnboardingArtifact onSubmit={onContextSubmit} />,
      },
      ...baseTabs,
    ];
  }, [agents, dataLoading, isNewUser, onContextSubmit, tasks]);

  const activeTab = tabs.find((tab) => tab.id === activeArtifactId) ?? tabs[0];

  return (
    <div className="flex h-full flex-col bg-background">
      <div className="mx-auto flex h-full w-full max-w-5xl flex-col gap-4 overflow-hidden px-4 py-5">
        <ChatArtifactTabs
          tabs={tabs}
          activeId={activeTab.id}
          onSelect={setActiveArtifactId}
        />

        <ChatArtifactCard>
          {activeTab.content}
        </ChatArtifactCard>

        <div className="min-h-0 flex-1 overflow-hidden rounded-lg border border-border bg-background">
          <ChatPanel
            surfaceOverride={{ type: 'chat' }}
            plusMenuActions={plusMenuActions}
            placeholder="Ask anything or type / ..."
            showCommandPicker={true}
            emptyState={CHAT_EMPTY_STATE}
          />
        </div>
      </div>
    </div>
  );
}
