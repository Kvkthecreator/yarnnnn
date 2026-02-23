'use client';

import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { cn } from '@/lib/utils';

interface PlatformHeaderProps {
  label: string;
  icon: React.ReactNode;
  bgColor: string;
  color: string;
  onConnectionDetails: () => void;
  /** Optional extra content to render in the right side of the header (e.g. view toggle) */
  rightContent?: React.ReactNode;
}

export function PlatformHeader({
  label,
  icon,
  bgColor,
  color,
  onConnectionDetails,
  rightContent,
}: PlatformHeaderProps) {
  const router = useRouter();

  return (
    <div className="border-b border-border px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/context')}
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="w-4 h-4" />
            Context
          </button>
          <div className="flex items-center gap-3">
            <div className={cn('w-10 h-10 rounded-full flex items-center justify-center', bgColor)}>
              <span className={color}>{icon}</span>
            </div>
            <h1 className="text-lg font-semibold">{label}</h1>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {rightContent}
          <button
            onClick={onConnectionDetails}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            Connection details
          </button>
        </div>
      </div>
    </div>
  );
}
