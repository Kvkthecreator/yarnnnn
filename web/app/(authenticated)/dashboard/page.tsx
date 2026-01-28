"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api/client";
import { Loader2, Plus, X } from "lucide-react";

interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

interface Workspace {
  id: string;
  name: string;
}

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<string | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [showWorkspaceModal, setShowWorkspaceModal] = useState(false);
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // Fetch workspaces on mount
  useEffect(() => {
    async function fetchWorkspaces() {
      try {
        const data = await api.workspaces.list();
        setWorkspaces(data);
        if (data.length > 0) {
          setSelectedWorkspace(data[0].id);
        } else {
          setIsLoading(false);
        }
      } catch (err) {
        console.error("Failed to fetch workspaces:", err);
        setError("Failed to load workspaces");
        setIsLoading(false);
      }
    }
    fetchWorkspaces();
  }, []);

  // Fetch projects when workspace is selected
  useEffect(() => {
    if (!selectedWorkspace) {
      return;
    }

    async function fetchProjects() {
      setIsLoading(true);
      try {
        const data = await api.projects.list(selectedWorkspace!);
        setProjects(data);
        setError(null);
      } catch (err) {
        console.error("Failed to fetch projects:", err);
        setError("Failed to load projects");
      } finally {
        setIsLoading(false);
      }
    }
    fetchProjects();
  }, [selectedWorkspace]);

  const handleCreateWorkspace = async (name: string) => {
    setIsCreating(true);
    try {
      const newWorkspace = await api.workspaces.create({ name });
      setWorkspaces((prev) => [...prev, newWorkspace]);
      setSelectedWorkspace(newWorkspace.id);
      setShowWorkspaceModal(false);
    } catch (err) {
      console.error("Failed to create workspace:", err);
      alert("Failed to create workspace");
    } finally {
      setIsCreating(false);
    }
  };

  const handleCreateProject = async (name: string, description?: string) => {
    if (!selectedWorkspace) return;
    setIsCreating(true);
    try {
      const newProject = await api.projects.create(selectedWorkspace, {
        name,
        description,
      });
      setProjects((prev) => [...prev, newProject]);
      setShowProjectModal(false);
    } catch (err) {
      console.error("Failed to create project:", err);
      alert("Failed to create project");
    } finally {
      setIsCreating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto py-8 px-4 flex justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="p-4 bg-destructive/10 text-destructive rounded-lg">
          {error}
        </div>
      </div>
    );
  }

  // No workspaces - show create workspace prompt
  if (workspaces.length === 0) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="text-center py-12">
          <h2 className="text-xl font-semibold mb-2">Welcome to YARNNN</h2>
          <p className="text-muted-foreground mb-6">
            Create your first workspace to get started.
          </p>
          <button
            onClick={() => setShowWorkspaceModal(true)}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md inline-flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Create Workspace
          </button>
        </div>

        {showWorkspaceModal && (
          <CreateWorkspaceModal
            onClose={() => setShowWorkspaceModal(false)}
            onCreate={handleCreateWorkspace}
            isCreating={isCreating}
          />
        )}
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      {/* Workspace selector */}
      <div className="flex items-center gap-4 mb-8">
        <select
          value={selectedWorkspace || ""}
          onChange={(e) => setSelectedWorkspace(e.target.value)}
          className="px-3 py-2 border border-border rounded-md bg-background"
        >
          {workspaces.map((ws) => (
            <option key={ws.id} value={ws.id}>
              {ws.name}
            </option>
          ))}
        </select>
        <button
          onClick={() => setShowWorkspaceModal(true)}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          + New Workspace
        </button>
      </div>

      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold">Projects</h1>
        <button
          onClick={() => setShowProjectModal(true)}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-md inline-flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <p>No projects in this workspace yet.</p>
          <p className="text-sm mt-2">
            Create your first project to get started.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className="block p-6 border border-border rounded-lg hover:border-primary transition-colors"
            >
              <h2 className="text-lg font-semibold mb-2">{project.name}</h2>
              {project.description && (
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {project.description}
                </p>
              )}
            </Link>
          ))}
        </div>
      )}

      {/* Modals */}
      {showWorkspaceModal && (
        <CreateWorkspaceModal
          onClose={() => setShowWorkspaceModal(false)}
          onCreate={handleCreateWorkspace}
          isCreating={isCreating}
        />
      )}

      {showProjectModal && (
        <CreateProjectModal
          onClose={() => setShowProjectModal(false)}
          onCreate={handleCreateProject}
          isCreating={isCreating}
        />
      )}
    </div>
  );
}

function CreateWorkspaceModal({
  onClose,
  onCreate,
  isCreating,
}: {
  onClose: () => void;
  onCreate: (name: string) => void;
  isCreating: boolean;
}) {
  const [name, setName] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onCreate(name.trim());
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-background border border-border rounded-lg p-6 w-full max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Create Workspace</h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">
              Workspace Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Workspace"
              className="w-full px-3 py-2 border border-border rounded-md bg-background"
              autoFocus
            />
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-border rounded-md"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || isCreating}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50 inline-flex items-center gap-2"
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

function CreateProjectModal({
  onClose,
  onCreate,
  isCreating,
}: {
  onClose: () => void;
  onCreate: (name: string, description?: string) => void;
  isCreating: boolean;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onCreate(name.trim(), description.trim() || undefined);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-background border border-border rounded-lg p-6 w-full max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Create Project</h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">
              Project Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Project"
              className="w-full px-3 py-2 border border-border rounded-md bg-background"
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
              className="w-full px-3 py-2 border border-border rounded-md bg-background resize-none"
            />
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-border rounded-md"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || isCreating}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50 inline-flex items-center gap-2"
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
