'use client';

/**
 * ADR-014: Top Bar with Minimal Chrome
 * Project selector dropdown for context switching
 */

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, FolderOpen, Plus, Check, LayoutDashboard } from 'lucide-react';
import { useProjectContext } from '@/contexts/ProjectContext';
import { cn } from '@/lib/utils';

export function ProjectSelector() {
  const { projects, activeProject, setActiveProject, isLoading } = useProjectContext();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close dropdown on escape
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, []);

  const handleSelect = (project: { id: string; name: string } | null) => {
    setActiveProject(project);
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
          "hover:bg-muted border border-transparent",
          isOpen && "bg-muted border-border"
        )}
        disabled={isLoading}
      >
        {activeProject ? (
          <>
            <FolderOpen className="w-4 h-4 text-primary" />
            <span className="max-w-[150px] truncate">{activeProject.name}</span>
          </>
        ) : (
          <>
            <LayoutDashboard className="w-4 h-4 text-muted-foreground" />
            <span>Dashboard</span>
          </>
        )}
        <ChevronDown className={cn(
          "w-4 h-4 text-muted-foreground transition-transform",
          isOpen && "rotate-180"
        )} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-64 bg-background border border-border rounded-lg shadow-lg z-50 py-1 max-h-80 overflow-y-auto">
          {/* Dashboard option */}
          <button
            onClick={() => handleSelect(null)}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2 text-sm text-left hover:bg-muted transition-colors",
              !activeProject && "bg-primary/5 text-primary"
            )}
          >
            <LayoutDashboard className="w-4 h-4" />
            <span className="flex-1">Dashboard</span>
            {!activeProject && <Check className="w-4 h-4" />}
          </button>

          {/* Divider */}
          {projects.length > 0 && (
            <div className="border-t border-border my-1" />
          )}

          {/* Projects list */}
          {projects.map((project) => {
            const isActive = activeProject?.id === project.id;
            return (
              <button
                key={project.id}
                onClick={() => handleSelect({ id: project.id, name: project.name })}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2 text-sm text-left hover:bg-muted transition-colors",
                  isActive && "bg-primary/5 text-primary"
                )}
              >
                <FolderOpen className="w-4 h-4" />
                <span className="flex-1 truncate">{project.name}</span>
                {isActive && <Check className="w-4 h-4" />}
              </button>
            );
          })}

          {/* New Project option */}
          <>
            <div className="border-t border-border my-1" />
            <button
              onClick={() => {
                setIsOpen(false);
                // Dispatch event for dashboard to handle (with subscription check)
                window.dispatchEvent(new CustomEvent('openCreateProject'));
              }}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-left hover:bg-muted transition-colors text-muted-foreground"
            >
              <Plus className="w-4 h-4" />
              <span>New Project</span>
            </button>
          </>
        </div>
      )}
    </div>
  );
}
