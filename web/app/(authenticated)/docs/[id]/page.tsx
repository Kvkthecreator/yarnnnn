'use client';

/**
 * ADR-249: Workspace Upload Detail Page
 *
 * 'id' is the URL-encoded workspace path, e.g.
 *   /docs/workspace%2Fuploads%2Facme-brief.md
 * Reads the workspace file directly, shows metadata + download link.
 */

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Loader2, FileText, ChevronLeft, Download, Trash2, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api/client';
import type { WorkspaceUpload } from '@/types';

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();

  // Decode the workspace path from the URL segment
  const workspacePath = decodeURIComponent(params.id);
  const fullPath = workspacePath.startsWith('/') ? workspacePath : `/${workspacePath}`;

  const [doc, setDoc] = useState<WorkspaceUpload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadDocument();
  }, [fullPath]);

  const loadDocument = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.documents.list();
      const found = result.uploads.find((u) => u.path === fullPath);
      if (!found) throw new Error('Not found');
      setDoc(found);
    } catch {
      setError('Document not found');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    try {
      const result = await api.documents.download(fullPath);
      window.open(result.url, '_blank');
    } catch {
      alert('Failed to get download link');
    }
  };

  const handleDelete = async () => {
    if (!confirm('Delete this document from your workspace?')) return;
    setDeleting(true);
    try {
      await api.documents.delete(fullPath);
      router.push('/docs');
    } catch {
      alert('Failed to delete document');
      setDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <AlertCircle className="w-8 h-8 text-muted-foreground" />
        <p className="text-muted-foreground">{error || 'Document not found'}</p>
        <button onClick={() => router.push('/docs')} className="text-sm text-primary hover:underline">
          Back to Documents
        </button>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.back()}
              className="p-2 hover:bg-muted rounded-lg transition-colors"
              title="Back"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <FileText className="w-6 h-6" />
              <div>
                <h1 className="text-xl font-semibold">{doc.filename}</h1>
                <p className="text-sm text-muted-foreground">
                  {doc.word_count > 0 ? `${doc.word_count.toLocaleString()} words` : 'Workspace file'} · uploaded {doc.uploaded_at}
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownload}
              className="p-2 rounded-lg hover:bg-muted transition-colors"
              title="Download original"
            >
              <Download className="w-5 h-5" />
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="p-2 rounded-lg hover:bg-destructive/10 text-destructive transition-colors disabled:opacity-50"
              title="Delete document"
            >
              {deleting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Trash2 className="w-5 h-5" />}
            </button>
          </div>
        </div>

        <div className="p-4 border border-border rounded-lg bg-muted/30">
          <p className="text-sm text-muted-foreground">
            This document is in your workspace at{' '}
            <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">{doc.path}</code>.
            YARNNN can read it via <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">ReadFile</code>.
          </p>
        </div>
      </div>
    </div>
  );
}
