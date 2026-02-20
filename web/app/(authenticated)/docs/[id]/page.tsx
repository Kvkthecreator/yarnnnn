'use client';

/**
 * ADR-037: Document Detail Page (Route-based)
 *
 * Standalone page for viewing a specific document.
 * This is a route (/docs/[id]) not a surface.
 */

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Loader2, FileText, ChevronLeft, Download, Trash2, CheckCircle2, XCircle, Clock, AlertCircle } from 'lucide-react';
import { api } from '@/lib/api/client';
import { formatDistanceToNow } from 'date-fns';
import type { Document } from '@/types';

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();
  const [document, setDocument] = useState<Document | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadDocument();
  }, [id]);

  const loadDocument = async () => {
    setLoading(true);
    setError(null);
    try {
      const doc = await api.documents.get(id);
      setDocument(doc);
    } catch (err) {
      console.error('Failed to load document:', err);
      setError('Failed to load document');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    setDeleting(true);
    try {
      await api.documents.delete(id);
      router.push('/docs');
    } catch (err) {
      console.error('Failed to delete document:', err);
      alert('Failed to delete document');
      setDeleting(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-600" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-600" />;
      case 'processing':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'pending':
        return <Clock className="w-5 h-5 text-amber-500" />;
      default:
        return <FileText className="w-5 h-5 text-muted-foreground" />;
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'completed':
        return 'Processed';
      case 'failed':
        return 'Processing failed';
      case 'processing':
        return 'Processing...';
      case 'pending':
        return 'Pending';
      default:
        return status;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !document) {
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
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/docs')}
              className="p-2 hover:bg-muted rounded-lg transition-colors"
              title="Back to Documents"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <FileText className="w-6 h-6" />
              <div>
                <h1 className="text-xl font-semibold">{document.filename}</h1>
                <p className="text-sm text-muted-foreground">
                  {document.file_type.toUpperCase()} · {formatFileSize(document.file_size)}
                  {document.page_count && ` · ${document.page_count} pages`}
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="p-2 rounded-lg hover:bg-destructive/10 text-destructive transition-colors disabled:opacity-50"
              title="Delete document"
            >
              {deleting ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Trash2 className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>

        {/* Status Card */}
        <div className="p-4 border border-border rounded-lg mb-6">
          <div className="flex items-center gap-3">
            {getStatusIcon(document.processing_status)}
            <div>
              <p className="font-medium">{getStatusLabel(document.processing_status)}</p>
              <p className="text-sm text-muted-foreground">
                Uploaded {formatDistanceToNow(new Date(document.created_at), { addSuffix: true })}
              </p>
            </div>
          </div>
        </div>

        {/* Document Info */}
        {document.processing_status === 'completed' && (
          <div className="p-4 border border-border rounded-lg bg-muted/30">
            <p className="text-muted-foreground">
              Document processed successfully.
              {document.word_count && ` ${document.word_count.toLocaleString()} words extracted.`}
            </p>
          </div>
        )}

        {document.processing_status === 'failed' && (
          <div className="p-4 border border-destructive/30 rounded-lg bg-destructive/5">
            <p className="text-destructive">
              Failed to process this document. Please try uploading again.
            </p>
          </div>
        )}

        {document.processing_status === 'processing' && (
          <div className="p-4 border border-border rounded-lg bg-muted/30 text-center">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
            <p className="text-muted-foreground">Processing document...</p>
          </div>
        )}
      </div>
    </div>
  );
}
