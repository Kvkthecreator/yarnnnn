'use client';

/**
 * WorkspaceNav — Agent OS navigation panel (ADR-154)
 *
 * Structured nav with four sections:
 *   Tasks    — running kernels with status dots
 *   Domains  — accumulated context with entity counts
 *   Outputs  — deliverables by category
 *   Uploads  — user-contributed files
 *
 * System files are hidden. This replaces WorkspaceTree as the
 * primary navigation component on the workfloor.
 */

import { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, Circle, FolderOpen, FileText, Settings, Plus } from 'lucide-react';
import { FileIcon } from './FileIcon';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';

interface NavData {
  tasks: Array<{
    slug: string; title: string; status: string;
    mode: string | null; schedule: string | null;
    next_run_at: string | null; last_run_at: string | null;
  }>;
  domains: Array<{
    key: string; display_name: string; entity_count: number;
    entity_type: string | null; path: string;
  }>;
  outputs: Array<{
    key: string; display_name: string; file_count: number; path: string;
  }>;
  uploads: Array<{
    name: string; path: string; updated_at: string | null;
  }>;
  settings: Array<{
    name: string; filename: string; path: string; updated_at: string | null;
  }>;
}

interface WorkspaceNavProps {
  onSelectTask: (slug: string) => void;
  onSelectDomain: (domainKey: string) => void;
  onSelectFile: (path: string) => void;
  onCreateTask?: () => void;
  selectedItem?: string;
}

export function WorkspaceNav({
  onSelectTask,
  onSelectDomain,
  onSelectFile,
  onCreateTask,
  selectedItem,
}: WorkspaceNavProps) {
  const [nav, setNav] = useState<NavData | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    tasks: true,
    domains: true,
    outputs: false,
    uploads: false,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.workspace.getNav()
      .then(data => {
        setNav(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const toggle = (section: string) => {
    setExpanded(prev => ({ ...prev, [section]: !prev[section] }));
  };

  if (loading) {
    return (
      <div className="p-3 text-sm text-muted-foreground">Loading...</div>
    );
  }

  if (!nav) {
    return (
      <div className="p-3 text-sm text-muted-foreground">Failed to load navigation</div>
    );
  }

  return (
    <div className="text-sm flex flex-col h-full">
      <div className="flex-1 overflow-y-auto">
        {/* ── Tasks ── */}
        <NavSection
          title="Tasks"
          expanded={expanded.tasks}
          onToggle={() => toggle('tasks')}
          action={onCreateTask ? (
            <button
              onClick={(e) => { e.stopPropagation(); onCreateTask(); }}
              className="p-0.5 rounded hover:bg-accent text-muted-foreground hover:text-foreground"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          ) : undefined}
        >
          {nav.tasks.length === 0 && (
            <div className="px-3 py-1.5 text-sm text-muted-foreground">No tasks yet</div>
          )}
          {nav.tasks.map(task => (
            <button
              key={task.slug}
              onClick={() => onSelectTask(task.slug)}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-accent rounded-sm text-sm",
                selectedItem === `task:${task.slug}` && "bg-accent"
              )}
            >
              <Circle
                className={cn(
                  "w-2 h-2 flex-shrink-0",
                  task.status === 'active' ? "fill-green-500 text-green-500" : "text-muted-foreground"
                )}
              />
              <span className="truncate flex-1">{task.title}</span>
              {task.schedule && (
                <span className="text-[10px] text-muted-foreground flex-shrink-0">{task.schedule}</span>
              )}
            </button>
          ))}
        </NavSection>

        {/* ── Domains ── */}
        <NavSection
          title="Domains"
          expanded={expanded.domains}
          onToggle={() => toggle('domains')}
        >
          {nav.domains.length === 0 && (
            <div className="px-3 py-1.5 text-sm text-muted-foreground">No domains yet</div>
          )}
          {nav.domains.map(domain => (
            <button
              key={domain.key}
              onClick={() => onSelectDomain(domain.key)}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-accent rounded-sm text-sm",
                selectedItem === `domain:${domain.key}` && "bg-accent"
              )}
            >
              <FolderOpen className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
              <span className="truncate flex-1">{domain.display_name}</span>
              {domain.entity_count > 0 && (
                <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded-full flex-shrink-0">
                  {domain.entity_count}
                </span>
              )}
            </button>
          ))}
        </NavSection>

        {/* ── Outputs ── */}
        {nav.outputs.length > 0 && (
          <NavSection
            title="Outputs"
            expanded={expanded.outputs}
            onToggle={() => toggle('outputs')}
          >
            {nav.outputs.map(section => (
              <button
                key={section.key}
                onClick={() => onSelectFile(section.path)}
                className={cn(
                  "w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-accent rounded-sm text-sm",
                  selectedItem === `output:${section.key}` && "bg-accent"
                )}
              >
                <FileText className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                <span className="truncate flex-1">{section.display_name}</span>
                <span className="text-[10px] text-muted-foreground flex-shrink-0">
                  {section.file_count}
                </span>
              </button>
            ))}
          </NavSection>
        )}

        {/* ── Uploads ── */}
        {nav.uploads.length > 0 && (
          <NavSection
            title="Uploads"
            expanded={expanded.uploads}
            onToggle={() => toggle('uploads')}
          >
            {nav.uploads.map(file => (
              <button
                key={file.path}
                onClick={() => onSelectFile(file.path)}
                className={cn(
                  "w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-accent rounded-sm text-sm",
                  selectedItem === file.path && "bg-accent"
                )}
              >
                <FileIcon filename={file.name} size="sm" />
                <span className="truncate flex-1">{file.name}</span>
              </button>
            ))}
          </NavSection>
        )}
      </div>

        {/* ── Settings (user config files) ── */}
        {nav.settings && nav.settings.length > 0 && (
          <NavSection
            title="Settings"
            expanded={expanded.settings ?? false}
            onToggle={() => toggle('settings')}
          >
            {nav.settings.map(file => (
              <button
                key={file.path}
                onClick={() => onSelectFile(file.path)}
                className={cn(
                  "w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-accent rounded-sm text-sm",
                  selectedItem === file.path && "bg-accent"
                )}
              >
                <Settings className="w-3.5 h-3.5 text-muted-foreground flex-shrink-0" />
                <span className="truncate flex-1">{file.name}</span>
              </button>
            ))}
          </NavSection>
        )}
    </div>
  );
}


// ── Section wrapper ──

function NavSection({
  title,
  expanded,
  onToggle,
  action,
  children,
}: {
  title: string;
  expanded: boolean;
  onToggle: () => void;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-1">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-1 px-2 py-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground hover:text-foreground"
      >
        {expanded ? (
          <ChevronDown className="w-3 h-3" />
        ) : (
          <ChevronRight className="w-3 h-3" />
        )}
        <span className="flex-1 text-left">{title}</span>
        {action}
      </button>
      {expanded && <div className="ml-1">{children}</div>}
    </div>
  );
}
