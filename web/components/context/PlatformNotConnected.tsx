'use client';

import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';

interface PlatformNotConnectedProps {
  platform: string;
  label: string;
  icon: React.ReactNode;
  bgColor: string;
  color: string;
  benefits: string[];
  /** The OAuth provider to use (e.g. 'google' for both Gmail and Calendar) */
  oauthProvider?: string;
}

export function PlatformNotConnected({
  platform,
  label,
  icon,
  bgColor,
  color,
  benefits,
  oauthProvider,
}: PlatformNotConnectedProps) {
  const router = useRouter();
  const provider = oauthProvider || platform;

  return (
    <div className="h-full overflow-auto">
      <div className="border-b border-border px-6 py-4">
        <button
          onClick={() => router.push('/context')}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Context
        </button>
      </div>
      <div className="p-6 max-w-lg">
        <div className="flex items-center gap-4 mb-6">
          <div className={cn('w-14 h-14 rounded-xl flex items-center justify-center', bgColor)}>
            <span className={cn(color, 'scale-150')}>{icon}</span>
          </div>
          <div>
            <h2 className="text-xl font-semibold text-foreground">{label}</h2>
            <p className="text-sm text-muted-foreground">Not connected</p>
          </div>
        </div>

        {benefits.length > 0 && (
          <div className="mb-6 space-y-2">
            {benefits.map((benefit) => (
              <div key={benefit} className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 shrink-0" />
                {benefit}
              </div>
            ))}
          </div>
        )}

        <button
          onClick={async () => {
            try {
              const { authorization_url } = await api.integrations.getAuthorizationUrl(provider);
              window.location.href = authorization_url;
            } catch {
              router.push('/settings?tab=integrations');
            }
          }}
          className="px-5 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          Connect {label}
        </button>
      </div>
    </div>
  );
}
