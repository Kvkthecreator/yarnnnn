'use client';

/**
 * ADR-018: Chat Interface (Secondary)
 * Preserved chat functionality, now accessible via /dashboard/chat
 */

import { useState, useEffect } from 'react';
import { Chat } from '@/components/Chat';
import { api } from '@/lib/api/client';
import { useSubscriptionGate } from '@/hooks/useSubscriptionGate';
import { UpgradePrompt } from '@/components/subscription';
import { X, Loader2 } from 'lucide-react';

export default function ChatPage() {
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [showUpgradePrompt, setShowUpgradePrompt] = useState(false);
  const [activeProject, setActiveProject] = useState<{ id: string; name: string } | null>(null);

  const { canCreateProject, projects } = useSubscriptionGate();

  // Listen for "New Project" event
  useEffect(() => {
    const handleOpenCreate = () => {
      if (canCreateProject) {
        setShowProjectModal(true);
      } else {
        setShowUpgradePrompt(true);
      }
    };
    window.addEventListener('openCreateProject', handleOpenCreate);
    return () => window.removeEventListener('openCreateProject', handleOpenCreate);
  }, [canCreateProject]);

  const handleCreateProject = async (name: string, description?: string) => {
    setIsCreating(true);
    try {
      const newProject = await api.projects.create({ name, description });
      setShowProjectModal(false);
      setActiveProject({ id: newProject.id, name: newProject.name });
    } catch (err) {
      console.error('Failed to create project:', err);
      alert('Failed to create project');
    } finally {
      setIsCreating(false);
    }
  };

  const chatEmptyMessage = activeProject
    ? `Hi! I'm your Thinking Partner. Let's work on "${activeProject.name}" together.`
    : "Hi! I'm your Thinking Partner. I'm here to help you think through anything - ideas, problems, decisions, or just to chat.";

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <main className="flex-1 container mx-auto px-4 py-4 overflow-hidden">
        <Chat
          projectId={activeProject?.id}
          projectName={activeProject?.name}
          includeContext
          heightClass="h-full"
          emptyMessage={chatEmptyMessage}
        />
      </main>

      {/* Create Project Modal */}
      {showProjectModal && (
        <CreateProjectModal
          onClose={() => setShowProjectModal(false)}
          onCreate={handleCreateProject}
          isCreating={isCreating}
        />
      )}

      {/* Upgrade Prompt */}
      {showUpgradePrompt && (
        <UpgradePrompt
          feature="projects"
          currentUsage={projects.current}
          onDismiss={() => setShowUpgradePrompt(false)}
        />
      )}
    </div>
  );
}

function CreateProjectModal({
  onClose,
  onCreate,
  isCreating,
}: {
  onClose: () => void;
  onCreate: (name: string, description?: string) => void;
  isCreating: boolean;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onCreate(name.trim(), description.trim() || undefined);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background border border-border rounded-lg p-6 w-full max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Create Project</h2>
          <button
            onClick={onClose}
            className="p-1 text-muted-foreground hover:text-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Project Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Project"
              className="w-full px-3 py-2 border border-border rounded-md bg-background text-sm"
              autoFocus
            />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">
              Description (optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this project about?"
              rows={3}
              className="w-full px-3 py-2 border border-border rounded-md bg-background resize-none text-sm"
            />
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-border rounded-md text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || isCreating}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50 inline-flex items-center gap-2 text-sm"
            >
              {isCreating && <Loader2 className="w-4 h-4 animate-spin" />}
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
