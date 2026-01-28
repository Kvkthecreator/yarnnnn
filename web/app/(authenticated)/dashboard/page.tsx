"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/lib/api/client";
import { Loader2 } from "lucide-react";

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

  // Fetch workspaces on mount
  useEffect(() => {
    async function fetchWorkspaces() {
      try {
        const data = await api.workspaces.list();
        setWorkspaces(data);
        if (data.length > 0) {
          setSelectedWorkspace(data[0].id);
        }
      } catch (err) {
        console.error("Failed to fetch workspaces:", err);
        setError("Failed to load workspaces");
      }
    }
    fetchWorkspaces();
  }, []);

  // Fetch projects when workspace is selected
  useEffect(() => {
    if (!selectedWorkspace) {
      setIsLoading(false);
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

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold">Projects</h1>
        <button className="px-4 py-2 bg-primary text-primary-foreground rounded-md">
          + New Project
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <p>No projects yet.</p>
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
    </div>
  );
}
