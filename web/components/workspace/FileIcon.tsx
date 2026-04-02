'use client';

/**
 * FileIcon — type-aware file icon (ADR-154: Agent OS)
 *
 * Maps file extensions to appropriate lucide icons.
 * Used across all workspace views: domains, outputs, uploads, settings.
 */

import {
  FileText,
  FileCode,
  Image,
  FileSpreadsheet,
  Presentation,
  File,
  FileType,
  BookOpen,
  BarChart3,
  Clapperboard,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const ICON_MAP: Record<string, { icon: typeof FileText; color: string }> = {
  // Markdown
  '.md': { icon: FileText, color: 'text-blue-500' },
  // HTML — rendered reports/deliverables, not web pages
  '.html': { icon: BookOpen, color: 'text-violet-500' },
  // Images
  '.png': { icon: Image, color: 'text-green-500' },
  '.jpg': { icon: Image, color: 'text-green-500' },
  '.jpeg': { icon: Image, color: 'text-green-500' },
  '.svg': { icon: Image, color: 'text-green-500' },
  '.gif': { icon: Image, color: 'text-green-500' },
  '.webp': { icon: Image, color: 'text-green-500' },
  // Video / motion
  '.mp4': { icon: Clapperboard, color: 'text-rose-500' },
  '.webm': { icon: Clapperboard, color: 'text-rose-500' },
  // Documents
  '.pdf': { icon: BookOpen, color: 'text-red-500' },
  '.docx': { icon: FileType, color: 'text-blue-600' },
  '.doc': { icon: FileType, color: 'text-blue-600' },
  '.txt': { icon: FileText, color: 'text-muted-foreground' },
  // Spreadsheets
  '.xlsx': { icon: FileSpreadsheet, color: 'text-emerald-600' },
  '.xls': { icon: FileSpreadsheet, color: 'text-emerald-600' },
  '.csv': { icon: FileSpreadsheet, color: 'text-emerald-600' },
  // Presentations
  '.pptx': { icon: Presentation, color: 'text-amber-500' },
  '.ppt': { icon: Presentation, color: 'text-amber-500' },
  // Data
  '.json': { icon: FileCode, color: 'text-yellow-600' },
  // Charts/visuals
  '.chart': { icon: BarChart3, color: 'text-purple-500' },
};

interface FileIconProps {
  filename: string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function FileIcon({ filename, className, size = 'sm' }: FileIconProps) {
  const ext = '.' + (filename.split('.').pop() || '').toLowerCase();
  const match = ICON_MAP[ext] || { icon: File, color: 'text-muted-foreground' };
  const Icon = match.icon;

  const sizeClass = {
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  }[size];

  return <Icon className={cn(sizeClass, match.color, 'flex-shrink-0', className)} />;
}
