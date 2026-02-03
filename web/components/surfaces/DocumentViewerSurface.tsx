'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 * DocumentViewerSurface - View document content
 */

import { useState, useEffect } from 'react';
import { Loader2, ArrowLeft, Download, FileText } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useDesk } from '@/contexts/DeskContext';
import { format } from 'date-fns';
import type { Document, DocumentDetail } from '@/types';

interface DocumentViewerSurfaceProps {
  documentId: string;
}

export function DocumentViewerSurface({ documentId }: DocumentViewerSurfaceProps) {
  const { setSurface } = useDesk();
  const [loading, setLoading] = useState(true);
  const [document, setDocument] = useState<DocumentDetail | null>(null);

  useEffect(() => {
    loadDocument();
  }, [documentId]);

  const loadDocument = async () => {
    setLoading(true);
    try {
      const data = await api.documents.get(documentId);
      setDocument(data);
    } catch (err) {
      console.error('Failed to load document:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    try {
      const { url } = await api.documents.download(documentId);
      window.open(url, '_blank');
    } catch (err) {
      console.error('Failed to get download URL:', err);
      alert('Failed to download. Please try again.');
    }
  };

  const goBack = () => {
    setSurface({ type: 'document-list' });
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!document) {
    return (
      <div className="h-full flex items-center justify-center text-muted-foreground">
        Document not found
      </div>
    );
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 h-14 border-b border-border flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <button onClick={goBack} className="p-1.5 hover:bg-muted rounded">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="font-medium">{document.filename}</h1>
            <p className="text-xs text-muted-foreground">
              {document.file_type.toUpperCase()} • {formatFileSize(document.file_size)}
              {document.page_count && ` • ${document.page_count} pages`}
            </p>
          </div>
        </div>

        <button
          onClick={handleDownload}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted"
        >
          <Download className="w-3.5 h-3.5" />
          Download
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto px-6 py-6">
          <div className="p-8 border border-border rounded-lg bg-muted/30 text-center">
            <FileText className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <h2 className="text-lg font-medium mb-2">{document.filename}</h2>
            <p className="text-sm text-muted-foreground mb-4">
              Uploaded {format(new Date(document.created_at), 'MMMM d, yyyy')}
            </p>

            <div className="inline-flex items-center gap-4 text-sm text-muted-foreground">
              <span>Status: {document.processing_status}</span>
              {document.word_count && <span>{document.word_count.toLocaleString()} words</span>}
              {document.chunk_count !== undefined && <span>{document.chunk_count} chunks</span>}
              {document.memory_count !== undefined && <span>{document.memory_count} memories</span>}
            </div>

            {document.processing_status === 'completed' && (
              <div className="mt-6">
                <button
                  onClick={handleDownload}
                  className="px-6 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
                >
                  Download Original
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
