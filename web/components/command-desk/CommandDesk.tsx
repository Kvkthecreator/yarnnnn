'use client';

import { useEffect, useMemo, useState } from 'react';
import { Bot, ClipboardList, Compass, MessageCircle, Newspaper } from 'lucide-react';
import { ChatPanel } from '@/components/tp/ChatPanel';
import type { PlusMenuAction } from '@/components/tp/PlusMenu';
import type { Agent, Task } from '@/types';
import { CommandDeskDock } from './CommandDeskDock';
import { CommandDeskWindow } from './CommandDeskWindow';
import type { CommandDeskWindowDefinition, CommandDeskWindowId } from './commandDeskTypes';
import { ContextGapsWindow } from './windows/ContextGapsWindow';
import { DailyBriefingWindow } from './windows/DailyBriefingWindow';
import { OnboardingWindow } from './windows/OnboardingWindow';
import { RecentWorkWindow } from './windows/RecentWorkWindow';

interface CommandDeskProps {
  agents: Agent[];
  tasks: Task[];
  dataLoading: boolean;
  hasMessages: boolean;
  isNewUser: boolean;
  plusMenuActions: PlusMenuAction[];
  onContextSubmit: (message: string) => void;
}

const CHAT_EMPTY_STATE = (
  <div className="rounded-lg border border-dashed border-border bg-muted/20 px-4 py-5 text-center">
    <p className="text-sm font-medium">TP is here.</p>
    <p className="mt-1 text-xs text-muted-foreground">
      Ask for a readout, a new task, or what needs attention.
    </p>
  </div>
);

export function CommandDesk({
  agents,
  tasks,
  dataLoading,
  hasMessages,
  isNewUser,
  plusMenuActions,
  onContextSubmit,
}: CommandDeskProps) {
  const [focusedWindowId, setFocusedWindowId] = useState<CommandDeskWindowId>(isNewUser ? 'onboarding' : 'briefing');
  const [minimizedWindowIds, setMinimizedWindowIds] = useState<CommandDeskWindowId[]>([]);

  useEffect(() => {
    if (isNewUser) {
      setFocusedWindowId('onboarding');
      setMinimizedWindowIds((current) => current.filter((id) => id !== 'onboarding'));
      return;
    }

    if (focusedWindowId === 'onboarding') {
      setFocusedWindowId('briefing');
    }
  }, [focusedWindowId, isNewUser]);

  const windows = useMemo<CommandDeskWindowDefinition[]>(() => {
    const baseWindows: CommandDeskWindowDefinition[] = [
      {
        id: 'briefing',
        title: 'Daily Briefing',
        eyebrow: 'today',
        icon: Newspaper,
        desktopClassName: 'left-6 top-6 z-20 h-[46%] w-[46%] max-w-[680px]',
        content: (
          <DailyBriefingWindow
            agents={agents}
            tasks={tasks}
            hasMessages={hasMessages}
          />
        ),
      },
      {
        id: 'recent-work',
        title: 'Recent Work',
        eyebrow: 'running',
        icon: ClipboardList,
        desktopClassName: 'left-10 bottom-20 z-10 h-[34%] w-[38%] max-w-[560px]',
        content: (
          <RecentWorkWindow
            agents={agents}
            tasks={tasks}
            loading={dataLoading}
          />
        ),
      },
      {
        id: 'context-gaps',
        title: 'Context Gaps',
        eyebrow: 'attention',
        icon: Compass,
        desktopClassName: 'left-[42%] bottom-24 z-10 h-[34%] w-[25%] min-w-[300px]',
        content: (
          <ContextGapsWindow
            agents={agents}
            tasks={tasks}
            loading={dataLoading}
          />
        ),
      },
      {
        id: 'tp-chat',
        title: 'TP Console',
        eyebrow: 'chat',
        icon: MessageCircle,
        desktopClassName: 'right-6 top-6 z-30 h-[calc(100%-104px)] w-[34%] min-w-[360px] max-w-[480px]',
        content: (
          <ChatPanel
            surfaceOverride={{ type: 'chat' }}
            plusMenuActions={plusMenuActions}
            placeholder="Ask anything or type / ..."
            showCommandPicker={true}
            emptyState={CHAT_EMPTY_STATE}
          />
        ),
      },
    ];

    if (!isNewUser) return baseWindows;

    return [
      {
        id: 'onboarding',
        title: 'Start With Context',
        eyebrow: 'setup',
        icon: Bot,
        desktopClassName: 'left-1/2 top-8 z-40 h-[calc(100%-112px)] w-[48%] max-w-[720px] -translate-x-1/2',
        content: <OnboardingWindow onSubmit={onContextSubmit} />,
      },
      ...baseWindows.map((window) => {
        if (window.id === 'briefing') {
          return {
            ...window,
            desktopClassName: 'left-6 top-8 z-10 h-[32%] w-[28%] min-w-[320px]',
          };
        }
        if (window.id === 'tp-chat') {
          return {
            ...window,
            desktopClassName: 'right-6 top-8 z-20 h-[calc(100%-120px)] w-[30%] min-w-[340px] max-w-[440px]',
          };
        }
        return window;
      }),
    ];
  }, [agents, tasks, dataLoading, hasMessages, isNewUser, onContextSubmit, plusMenuActions]);

  const focusWindow = (id: CommandDeskWindowId) => {
    setFocusedWindowId(id);
    setMinimizedWindowIds((current) => current.filter((windowId) => windowId !== id));
  };

  const minimizeWindow = (id: CommandDeskWindowId) => {
    setMinimizedWindowIds((current) => current.includes(id) ? current : [...current, id]);
  };

  const visibleDesktopWindows = windows.filter((window) => !minimizedWindowIds.includes(window.id));

  return (
    <div className="relative h-full overflow-hidden bg-muted/20">
      <div className="relative z-10 hidden h-full lg:block">
        {visibleDesktopWindows.map((window) => (
          <CommandDeskWindow
            key={window.id}
            window={window}
            focused={focusedWindowId === window.id}
            minimized={false}
            onFocus={focusWindow}
            onMinimize={minimizeWindow}
          />
        ))}
        <CommandDeskDock
          windows={windows}
          focusedWindowId={focusedWindowId}
          minimizedWindowIds={minimizedWindowIds}
          onSelect={focusWindow}
        />
      </div>

      <div className="relative z-10 flex h-full flex-col gap-3 overflow-y-auto p-3 lg:hidden">
        {windows.map((window) => (
          <CommandDeskWindow
            key={window.id}
            window={window}
            focused={focusedWindowId === window.id}
            minimized={false}
            onFocus={focusWindow}
            onMinimize={minimizeWindow}
            mobile
          />
        ))}
      </div>
    </div>
  );
}
