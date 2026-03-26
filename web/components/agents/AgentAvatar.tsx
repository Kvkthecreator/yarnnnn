'use client';

/**
 * AgentAvatar + TPAvatar — Framer Motion animated characters
 *
 * Uses motion.div for spring-based physics:
 * - Working: head bobs, arms type, glow pulse
 * - Ready: gentle breathing, occasional blink
 * - Paused: tilted, sleeping z's float
 * - Idle: slow sway, looking around
 * - Error: shake
 *
 * TP: always-on pulse ring, headset, distinct personality.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

type AvatarState = 'working' | 'ready' | 'paused' | 'idle' | 'error';

interface AgentAvatarProps {
  state: AvatarState;
  color: string;
  icon?: React.ReactNode;
  size?: number;
  className?: string;
}

// =============================================================================
// Agent Avatar
// =============================================================================

export function AgentAvatar({ state, color, icon, size = 64, className }: AgentAvatarProps) {
  const s = size;
  const paused = state === 'paused';

  // State-dependent animation variants
  const bodyVariants = {
    working: { scaleY: [1, 1.02, 1], transition: { duration: 1.5, repeat: Infinity, ease: 'easeInOut' as const } },
    ready: { scaleY: [1, 1.015, 1], transition: { duration: 4, repeat: Infinity, ease: 'easeInOut' as const } },
    paused: { scaleY: 1, opacity: 0.3, rotate: 5, transition: { duration: 0.8 } },
    idle: { scaleY: [1, 1.01, 1], transition: { duration: 5, repeat: Infinity, ease: 'easeInOut' as const } },
    error: { x: [-2, 2, -2, 2, 0], transition: { duration: 0.4, repeat: Infinity } },
  };

  const headVariants = {
    working: { y: [0, -s * 0.03, 0], transition: { duration: 0.8, repeat: Infinity, ease: 'easeInOut' as const } },
    ready: { y: 0, transition: { duration: 0.5 } },
    paused: { rotate: 12, y: s * 0.02, transition: { duration: 1.5, repeat: Infinity, repeatType: 'reverse' as const, ease: 'easeInOut' as const } },
    idle: { x: [0, -s * 0.02, s * 0.02, 0], transition: { duration: 5, repeat: Infinity, ease: 'easeInOut' as const } },
    error: { y: 0 },
  };

  const leftArmVariants = {
    working: { y: [0, -s * 0.05, 0], transition: { duration: 0.5, repeat: Infinity, ease: 'easeInOut' as const } },
    ready: { y: 0 },
    paused: { y: 0, opacity: 0.15 },
    idle: { y: 0 },
    error: { y: 0 },
  };

  const rightArmVariants = {
    working: { y: [0, -s * 0.05, 0], transition: { duration: 0.5, repeat: Infinity, ease: 'easeInOut' as const, delay: 0.2 } },
    ready: { y: 0 },
    paused: { y: 0, opacity: 0.15 },
    idle: { y: 0 },
    error: { y: 0 },
  };

  const glowVariants = {
    working: { scale: [1, 1.4, 1], opacity: [0.15, 0.3, 0.15], transition: { duration: 2, repeat: Infinity, ease: 'easeInOut' as const } },
    ready: { scale: 1, opacity: 0.05 },
    paused: { scale: 1, opacity: 0 },
    idle: { scale: 1, opacity: 0.03 },
    error: { scale: [1, 1.2, 1], opacity: [0.1, 0.2, 0.1], transition: { duration: 0.8, repeat: Infinity } },
  };

  const iconSize = Math.round(s * 0.22);
  const headSize = Math.round(s * 0.36);
  const bodyWidth = Math.round(s * 0.36);
  const bodyHeight = Math.round(s * 0.28);
  const armWidth = Math.round(s * 0.08);
  const armHeight = Math.round(s * 0.2);

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)} style={{ width: s, height: s }}>
      {/* Glow ring behind character */}
      <motion.div
        className="absolute rounded-full"
        style={{
          width: headSize * 1.6,
          height: headSize * 1.6,
          top: s * 0.08,
          left: '50%',
          marginLeft: -(headSize * 0.8),
          background: color,
        }}
        animate={glowVariants[state]}
      />

      {/* Character body group */}
      <motion.div
        className="absolute"
        style={{ bottom: s * 0.12, left: '50%', marginLeft: -(bodyWidth / 2), originY: 1 }}
        animate={bodyVariants[state]}
      >
        {/* Body */}
        <div
          className="rounded-xl"
          style={{
            width: bodyWidth,
            height: bodyHeight,
            background: color,
            opacity: paused ? 0.2 : 0.6,
            borderRadius: s * 0.1,
          }}
        />
      </motion.div>

      {/* Left arm */}
      <motion.div
        className="absolute"
        style={{
          bottom: s * 0.14,
          left: '50%',
          marginLeft: -(bodyWidth / 2) - armWidth - 2,
          width: armWidth,
          height: armHeight,
          background: color,
          opacity: paused ? 0.12 : 0.35,
          borderRadius: armWidth / 2,
        }}
        animate={leftArmVariants[state]}
      />

      {/* Right arm */}
      <motion.div
        className="absolute"
        style={{
          bottom: s * 0.14,
          left: '50%',
          marginLeft: bodyWidth / 2 + 2,
          width: armWidth,
          height: armHeight,
          background: color,
          opacity: paused ? 0.12 : 0.35,
          borderRadius: armWidth / 2,
        }}
        animate={rightArmVariants[state]}
      />

      {/* Head */}
      <motion.div
        className="absolute flex items-center justify-center"
        style={{
          width: headSize,
          height: headSize,
          top: s * 0.1,
          left: '50%',
          marginLeft: -(headSize / 2),
          background: color,
          borderRadius: '50%',
          opacity: paused ? 0.3 : 0.85,
        }}
        animate={headVariants[state]}
      >
        {/* Icon or eyes inside head */}
        {icon ? (
          <div style={{ color: 'white', opacity: paused ? 0.4 : 0.9 }}>
            {icon}
          </div>
        ) : (
          <div className="flex gap-1">
            {paused ? (
              <>
                <div style={{ width: iconSize * 0.4, height: 2, background: 'white', borderRadius: 1 }} />
                <div style={{ width: iconSize * 0.4, height: 2, background: 'white', borderRadius: 1 }} />
              </>
            ) : (
              <>
                <div style={{ width: iconSize * 0.18, height: iconSize * 0.18, background: 'white', borderRadius: '50%' }} />
                <div style={{ width: iconSize * 0.18, height: iconSize * 0.18, background: 'white', borderRadius: '50%' }} />
              </>
            )}
          </div>
        )}
      </motion.div>

      {/* Floating Z's for paused */}
      <AnimatePresence>
        {paused && [0, 1, 2].map(i => (
          <motion.span
            key={i}
            className="absolute font-bold pointer-events-none select-none"
            style={{ color, right: s * 0.12, top: s * 0.1, fontSize: s * (0.1 - i * 0.015) }}
            initial={{ opacity: 0, x: 0, y: 0, scale: 0.5 }}
            animate={{ opacity: [0, 0.5, 0], x: s * 0.1, y: -(s * 0.15 + i * s * 0.08), scale: 1 }}
            transition={{ duration: 2.5, repeat: Infinity, delay: i * 0.6, ease: 'easeOut' as const }}
          >
            z
          </motion.span>
        ))}
      </AnimatePresence>

      {/* Error badge */}
      {state === 'error' && (
        <motion.div
          className="absolute flex items-center justify-center bg-red-500 text-white rounded-full"
          style={{ width: s * 0.14, height: s * 0.14, top: s * 0.05, right: s * 0.15, fontSize: s * 0.08, fontWeight: 'bold' }}
          animate={{ scale: [1, 1.15, 1] }}
          transition={{ duration: 0.8, repeat: Infinity }}
        >
          !
        </motion.div>
      )}

      {/* Desk surface */}
      <div
        className="absolute"
        style={{
          bottom: s * 0.04,
          left: '50%',
          marginLeft: -(s * 0.35),
          width: s * 0.7,
          height: s * 0.05,
          background: 'currentColor',
          opacity: 0.06,
          borderRadius: s * 0.025,
        }}
      />

      {/* Working: small screen on desk */}
      {state === 'working' && (
        <motion.div
          className="absolute"
          style={{
            bottom: s * 0.08,
            left: '50%',
            marginLeft: -(s * 0.09),
            width: s * 0.18,
            height: s * 0.05,
            background: color,
            opacity: 0.15,
            borderRadius: 2,
          }}
          animate={{ opacity: [0.1, 0.2, 0.1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        />
      )}
    </div>
  );
}

// =============================================================================
// TP Avatar — The Orchestrator
// =============================================================================

export function TPAvatar({ size = 64, className }: { size?: number; className?: string }) {
  const s = size;
  const headSize = Math.round(s * 0.38);

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)} style={{ width: s, height: s }}>
      {/* Pulse ring */}
      <motion.div
        className="absolute rounded-full"
        style={{
          width: headSize * 1.5,
          height: headSize * 1.5,
          top: s * 0.1,
          left: '50%',
          marginLeft: -(headSize * 0.75),
          background: 'hsl(var(--primary))',
        }}
        animate={{ scale: [1, 1.15, 1], opacity: [0.08, 0.04, 0.08] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' as const }}
      />

      {/* Headset arc */}
      <div
        className="absolute"
        style={{
          width: headSize * 0.9,
          height: headSize * 0.4,
          top: s * 0.08,
          left: '50%',
          marginLeft: -(headSize * 0.45),
          borderTop: '2px solid hsl(var(--primary))',
          borderRadius: '50% 50% 0 0',
          opacity: 0.4,
        }}
      />

      {/* Head */}
      <motion.div
        className="absolute flex items-center justify-center rounded-full"
        style={{
          width: headSize,
          height: headSize,
          top: s * 0.15,
          left: '50%',
          marginLeft: -(headSize / 2),
          background: 'hsl(var(--primary))',
          opacity: 0.75,
        }}
        animate={{ y: [0, -1, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' as const }}
      >
        {/* Eyes */}
        <div className="flex gap-1.5">
          <motion.div
            style={{ width: headSize * 0.1, height: headSize * 0.1, background: 'white', borderRadius: '50%' }}
            animate={{ scaleY: [1, 1, 0.1, 1, 1] }}
            transition={{ duration: 4, repeat: Infinity, times: [0, 0.9, 0.93, 0.96, 1] }}
          />
          <motion.div
            style={{ width: headSize * 0.1, height: headSize * 0.1, background: 'white', borderRadius: '50%' }}
            animate={{ scaleY: [1, 1, 0.1, 1, 1] }}
            transition={{ duration: 4, repeat: Infinity, times: [0, 0.9, 0.93, 0.96, 1] }}
          />
        </div>
      </motion.div>

      {/* Body */}
      <div
        className="absolute rounded-xl"
        style={{
          width: s * 0.3,
          height: s * 0.22,
          bottom: s * 0.12,
          left: '50%',
          marginLeft: -(s * 0.15),
          background: 'hsl(var(--primary))',
          opacity: 0.45,
          borderRadius: s * 0.08,
        }}
      />
    </div>
  );
}
