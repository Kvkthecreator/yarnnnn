'use client';

/**
 * ADR-013: Conversation + Surfaces
 * Export Surface - handles PDF/DOCX/Email export flows
 */

import { useState } from 'react';
import {
  FileText,
  FileDown,
  Mail,
  Loader2,
  Check,
  AlertCircle,
  Copy,
  ExternalLink,
} from 'lucide-react';
import type { SurfaceData } from '@/types/surfaces';

interface ExportSurfaceProps {
  data: SurfaceData | null;
}

type ExportStatus = 'idle' | 'processing' | 'success' | 'error';

interface ExportState {
  status: ExportStatus;
  message?: string;
  url?: string;
}

export function ExportSurface({ data }: ExportSurfaceProps) {
  const [exportState, setExportState] = useState<ExportState>({ status: 'idle' });
  const [emailAddress, setEmailAddress] = useState('');

  const exportType = data?.exportType || 'pdf';
  const content = data?.content;
  const title = data?.title || 'Export';

  const handleExportPDF = async () => {
    setExportState({ status: 'processing', message: 'Generating PDF...' });
    try {
      // TODO: Implement PDF export via API
      // const result = await api.exports.pdf({ content, title });
      // setExportState({ status: 'success', url: result.url });

      // Simulated for now
      await new Promise((resolve) => setTimeout(resolve, 1500));
      setExportState({
        status: 'success',
        message: 'PDF generated successfully',
        url: '#',
      });
    } catch (err) {
      console.error('PDF export failed:', err);
      setExportState({
        status: 'error',
        message: 'Failed to generate PDF. Please try again.',
      });
    }
  };

  const handleExportDOCX = async () => {
    setExportState({ status: 'processing', message: 'Generating DOCX...' });
    try {
      // TODO: Implement DOCX export via API
      await new Promise((resolve) => setTimeout(resolve, 1500));
      setExportState({
        status: 'success',
        message: 'DOCX generated successfully',
        url: '#',
      });
    } catch (err) {
      console.error('DOCX export failed:', err);
      setExportState({
        status: 'error',
        message: 'Failed to generate DOCX. Please try again.',
      });
    }
  };

  const handleSendEmail = async () => {
    if (!emailAddress.trim()) {
      setExportState({
        status: 'error',
        message: 'Please enter an email address',
      });
      return;
    }

    setExportState({ status: 'processing', message: 'Sending email...' });
    try {
      // TODO: Implement email send via API
      await new Promise((resolve) => setTimeout(resolve, 1500));
      setExportState({
        status: 'success',
        message: `Email sent to ${emailAddress}`,
      });
    } catch (err) {
      console.error('Email send failed:', err);
      setExportState({
        status: 'error',
        message: 'Failed to send email. Please try again.',
      });
    }
  };

  const handleCopyContent = async () => {
    if (!content) return;

    try {
      const textContent =
        typeof content === 'string' ? content : JSON.stringify(content, null, 2);
      await navigator.clipboard.writeText(textContent);
      setExportState({
        status: 'success',
        message: 'Content copied to clipboard',
      });
      setTimeout(() => setExportState({ status: 'idle' }), 2000);
    } catch (err) {
      console.error('Copy failed:', err);
      setExportState({
        status: 'error',
        message: 'Failed to copy content',
      });
    }
  };

  const renderStatusMessage = () => {
    if (exportState.status === 'idle') return null;

    return (
      <div
        className={`flex items-center gap-2 p-3 rounded-lg mb-4 ${
          exportState.status === 'processing'
            ? 'bg-blue-50 text-blue-700'
            : exportState.status === 'success'
            ? 'bg-green-50 text-green-700'
            : 'bg-red-50 text-red-700'
        }`}
      >
        {exportState.status === 'processing' && (
          <Loader2 className="w-4 h-4 animate-spin" />
        )}
        {exportState.status === 'success' && <Check className="w-4 h-4" />}
        {exportState.status === 'error' && <AlertCircle className="w-4 h-4" />}
        <span className="text-sm">{exportState.message}</span>
        {exportState.url && exportState.status === 'success' && (
          <a
            href={exportState.url}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto inline-flex items-center gap-1 text-xs hover:underline"
          >
            Download <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    );
  };

  // If no content, show placeholder
  if (!content) {
    return (
      <div className="p-4">
        <div className="text-center py-8 text-muted-foreground">
          <FileDown className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-sm font-medium">Nothing to export</p>
          <p className="text-xs mt-1">
            Select content from a work output to export.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      {/* Header */}
      <div className="mb-4">
        <h3 className="text-sm font-medium">{title}</h3>
        <p className="text-xs text-muted-foreground mt-1">
          Choose an export format
        </p>
      </div>

      {/* Status message */}
      {renderStatusMessage()}

      {/* Export options */}
      <div className="space-y-3">
        {/* PDF Export */}
        {(exportType === 'pdf' || !exportType) && (
          <button
            onClick={handleExportPDF}
            disabled={exportState.status === 'processing'}
            className="w-full flex items-center gap-3 p-3 border border-border rounded-lg hover:border-primary/50 hover:bg-primary/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="p-2 bg-red-100 rounded-lg">
              <FileText className="w-5 h-5 text-red-600" />
            </div>
            <div className="text-left flex-1">
              <p className="text-sm font-medium">Export as PDF</p>
              <p className="text-xs text-muted-foreground">
                Formatted document, ready to share
              </p>
            </div>
          </button>
        )}

        {/* DOCX Export */}
        {(exportType === 'docx' || !exportType) && (
          <button
            onClick={handleExportDOCX}
            disabled={exportState.status === 'processing'}
            className="w-full flex items-center gap-3 p-3 border border-border rounded-lg hover:border-primary/50 hover:bg-primary/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="p-2 bg-blue-100 rounded-lg">
              <FileText className="w-5 h-5 text-blue-600" />
            </div>
            <div className="text-left flex-1">
              <p className="text-sm font-medium">Export as Word</p>
              <p className="text-xs text-muted-foreground">
                Editable .docx file
              </p>
            </div>
          </button>
        )}

        {/* Email */}
        {(exportType === 'email' || !exportType) && (
          <div className="border border-border rounded-lg p-3">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Mail className="w-5 h-5 text-purple-600" />
              </div>
              <div className="text-left">
                <p className="text-sm font-medium">Send via Email</p>
                <p className="text-xs text-muted-foreground">
                  Share directly to an email address
                </p>
              </div>
            </div>
            <div className="flex gap-2">
              <input
                type="email"
                value={emailAddress}
                onChange={(e) => setEmailAddress(e.target.value)}
                placeholder="recipient@example.com"
                className="flex-1 px-3 py-2 text-sm border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
              <button
                onClick={handleSendEmail}
                disabled={exportState.status === 'processing' || !emailAddress.trim()}
                className="px-4 py-2 text-sm font-medium text-white bg-primary rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Send
              </button>
            </div>
          </div>
        )}

        {/* Copy to clipboard */}
        <button
          onClick={handleCopyContent}
          disabled={exportState.status === 'processing'}
          className="w-full flex items-center gap-3 p-3 border border-dashed border-border rounded-lg hover:border-muted-foreground/50 hover:bg-muted/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <div className="p-2 bg-muted rounded-lg">
            <Copy className="w-5 h-5 text-muted-foreground" />
          </div>
          <div className="text-left flex-1">
            <p className="text-sm font-medium text-muted-foreground">
              Copy to Clipboard
            </p>
            <p className="text-xs text-muted-foreground">
              Copy raw content for pasting elsewhere
            </p>
          </div>
        </button>
      </div>
    </div>
  );
}
