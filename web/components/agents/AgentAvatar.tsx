'use client';

/**
 * AgentAvatar — Shared avatar component for all agent identity displays.
 *
 * Renders a role-colored circle with initials, or an image if avatarUrl is provided.
 * Supports three sizes (sm/md/lg) and an optional status indicator dot.
 *
 * Usage:
 *   <AgentAvatar name="Slack Recap" role="digest" size="md" status="active" />
 *   <AgentAvatar name="PM Agent" role="pm" size="sm" avatarUrl="https://..." />
 */

import { cn } from '@/lib/utils';
import { avatarColor, agentInitials, statusIndicator } from '@/lib/agent-identity';

export type AgentAvatarSize = 'sm' | 'md' | 'lg';

interface AgentAvatarProps {
  /** Display name — used for initials fallback */
  name: string;
  /** Agent role — determines background color */
  role?: string;
  /** Optional avatar image URL */
  avatarUrl?: string | null;
  /** Size variant */
  size?: AgentAvatarSize;
  /** Optional status indicator dot */
  status?: 'active' | 'paused' | 'archived';
  /** Additional className on the outer wrapper */
  className?: string;
}

const SIZE_CONFIG = {
  sm: {
    container: 'w-7 h-7',
    text: 'text-[10px]',
    statusDot: 'w-2 h-2 border',
    statusPos: '-bottom-0.5 -right-0.5',
  },
  md: {
    container: 'w-10 h-10',
    text: 'text-sm',
    statusDot: 'w-3 h-3 border-2',
    statusPos: '-bottom-0.5 -right-0.5',
  },
  lg: {
    container: 'w-14 h-14',
    text: 'text-lg',
    statusDot: 'w-3.5 h-3.5 border-2',
    statusPos: '-bottom-0.5 -right-0.5',
  },
} as const;

export function AgentAvatar({
  name,
  role,
  avatarUrl,
  size = 'md',
  status,
  className,
}: AgentAvatarProps) {
  const config = SIZE_CONFIG[size];
  const initials = agentInitials(name);
  const si = status ? statusIndicator(status) : null;

  return (
    <div className={cn('relative shrink-0', className)}>
      {avatarUrl ? (
        <img
          src={avatarUrl}
          alt={name}
          className={cn(
            config.container,
            'rounded-full object-cover',
          )}
        />
      ) : (
        <div
          className={cn(
            config.container,
            'rounded-full flex items-center justify-center text-white font-semibold',
            config.text,
          )}
          style={{ backgroundColor: avatarColor(role) }}
        >
          {initials}
        </div>
      )}
      {si && (
        <span
          className={cn(
            'absolute rounded-full border-background',
            config.statusDot,
            config.statusPos,
            si.color,
          )}
        />
      )}
    </div>
  );
}
