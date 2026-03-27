'use client';

/**
 * AgentAvatar + TPAvatar — Habbo-inspired blocky humanoid characters
 *
 * Proportional humanoid with:
 * - Blocky head with face (eyes, mouth)
 * - Hair/hat accent (darker shade of agent color)
 * - Torso (agent color = outfit)
 * - Arms (animate when working)
 * - Legs + feet
 *
 * States via Framer Motion:
 * - Working: head bobs, arms type, body breathes
 * - Ready: gentle breathing, occasional blink
 * - Paused: tilted, sleeping z's, dimmed
 * - Idle: slow sway, looking around
 * - Error: shake, red badge
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

// Darken a hex color by a factor (0-1)
function darken(hex: string, amount: number): string {
  const num = parseInt(hex.replace('#', ''), 16);
  const r = Math.max(0, Math.round((num >> 16) * (1 - amount)));
  const g = Math.max(0, Math.round(((num >> 8) & 0x00ff) * (1 - amount)));
  const b = Math.max(0, Math.round((num & 0x0000ff) * (1 - amount)));
  return `rgb(${r},${g},${b})`;
}

// Lighten a hex color
function lighten(hex: string, amount: number): string {
  const num = parseInt(hex.replace('#', ''), 16);
  const r = Math.min(255, Math.round((num >> 16) + (255 - (num >> 16)) * amount));
  const g = Math.min(255, Math.round(((num >> 8) & 0x00ff) + (255 - ((num >> 8) & 0x00ff)) * amount));
  const b = Math.min(255, Math.round((num & 0x0000ff) + (255 - (num & 0x0000ff)) * amount));
  return `rgb(${r},${g},${b})`;
}

// =============================================================================
// Agent Avatar — Blocky Humanoid
// =============================================================================

export function AgentAvatar({ state, color, icon, size = 64, className }: AgentAvatarProps) {
  const s = size;
  const paused = state === 'paused';

  // Derived colors
  const outfit = color;
  const outfitDark = darken(color, 0.25);
  const hair = darken(color, 0.35);
  const skin = '#F5D0A9'; // warm skin tone
  const skinShadow = '#E8B888';
  const pantsColor = '#4A5568'; // dark gray pants for all
  const shoeColor = '#2D3748';

  // Proportions (all relative to size)
  const headW = s * 0.38;
  const headH = s * 0.28;
  const hairH = s * 0.08;
  const bodyW = s * 0.34;
  const bodyH = s * 0.22;
  const armW = s * 0.09;
  const armH = s * 0.18;
  const legW = s * 0.12;
  const legH = s * 0.16;
  const footW = s * 0.14;
  const footH = s * 0.04;
  const eyeSize = Math.max(2, s * 0.045);
  const mouthW = s * 0.08;

  // Y positions (top-down)
  const hairTop = s * 0.06;
  const headTop = hairTop + hairH - 1;
  const bodyTop = headTop + headH - 2;
  const armTop = bodyTop + s * 0.02;
  const legTop = bodyTop + bodyH - 1;
  const footTop = legTop + legH - 1;

  // State animations
  const bodyAnim = {
    working: { scaleY: [1, 1.02, 1], transition: { duration: 1.5, repeat: Infinity, ease: 'easeInOut' as const } },
    ready: { scaleY: [1, 1.01, 1], transition: { duration: 4, repeat: Infinity, ease: 'easeInOut' as const } },
    paused: { scaleY: 1, opacity: 0.35, rotate: 6, transition: { duration: 0.8 } },
    idle: { scaleY: [1, 1.008, 1], transition: { duration: 5, repeat: Infinity, ease: 'easeInOut' as const } },
    error: { x: [-2, 2, -2, 2, 0], transition: { duration: 0.4, repeat: Infinity } },
  };

  const headAnim = {
    working: { y: [0, -s * 0.02, 0], transition: { duration: 0.8, repeat: Infinity, ease: 'easeInOut' as const } },
    ready: { y: 0 },
    paused: { rotate: 10, y: s * 0.01, transition: { duration: 1.5, repeat: Infinity, repeatType: 'reverse' as const, ease: 'easeInOut' as const } },
    idle: { x: [0, -s * 0.01, s * 0.01, 0], transition: { duration: 5, repeat: Infinity, ease: 'easeInOut' as const } },
    error: { y: 0 },
  };

  const leftArmAnim = {
    working: { rotate: [0, -20, 0], transition: { duration: 0.4, repeat: Infinity, ease: 'easeInOut' as const } },
    ready: { rotate: 0 },
    paused: { rotate: 0, opacity: 0.2 },
    idle: { rotate: [0, -3, 0], transition: { duration: 4, repeat: Infinity, ease: 'easeInOut' as const } },
    error: { rotate: 0 },
  };

  const rightArmAnim = {
    working: { rotate: [0, 20, 0], transition: { duration: 0.4, repeat: Infinity, ease: 'easeInOut' as const, delay: 0.15 } },
    ready: { rotate: 0 },
    paused: { rotate: 0, opacity: 0.2 },
    idle: { rotate: [0, 3, 0], transition: { duration: 4, repeat: Infinity, ease: 'easeInOut' as const, delay: 0.5 } },
    error: { rotate: 0 },
  };

  const blinkAnim = {
    scaleY: [1, 1, 0.1, 1, 1],
    transition: { duration: 4, repeat: Infinity, times: [0, 0.92, 0.94, 0.96, 1] },
  };

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)} style={{ width: s, height: s }}>
      {/* Full character group — body animations applied here */}
      <motion.div
        className="absolute inset-0"
        animate={bodyAnim[state]}
        style={{ originY: 1, originX: 0.5 }}
      >
        {/* Hair / hat */}
        <div
          className="absolute rounded-t-lg"
          style={{
            width: headW + 2,
            height: hairH,
            top: hairTop,
            left: '50%',
            transform: 'translateX(-50%)',
            background: hair,
            borderRadius: `${s * 0.06}px ${s * 0.06}px 0 0`,
            opacity: paused ? 0.3 : 1,
          }}
        />

        {/* Head group — animated separately */}
        <motion.div
          className="absolute"
          style={{
            width: headW,
            height: headH,
            top: headTop,
            left: '50%',
            transform: 'translateX(-50%)',
          }}
          animate={headAnim[state]}
        >
          {/* Face */}
          <div
            className="w-full h-full rounded-lg"
            style={{
              background: skin,
              opacity: paused ? 0.3 : 1,
              borderRadius: s * 0.05,
            }}
          />

          {/* Eyes */}
          {paused ? (
            // Closed eyes (lines)
            <div className="absolute flex gap-[3px]" style={{ top: '40%', left: '50%', transform: 'translate(-50%, -50%)' }}>
              <div style={{ width: eyeSize * 1.5, height: 1.5, background: '#5D4E37', borderRadius: 1 }} />
              <div style={{ width: eyeSize * 1.5, height: 1.5, background: '#5D4E37', borderRadius: 1 }} />
            </div>
          ) : (
            <div className="absolute flex gap-[3px]" style={{ top: '40%', left: '50%', transform: 'translate(-50%, -50%)' }}>
              <motion.div
                style={{ width: eyeSize, height: eyeSize, background: '#3D2E1E', borderRadius: '50%' }}
                animate={state === 'idle' || state === 'ready' ? blinkAnim : undefined}
              />
              <motion.div
                style={{ width: eyeSize, height: eyeSize, background: '#3D2E1E', borderRadius: '50%' }}
                animate={state === 'idle' || state === 'ready' ? blinkAnim : undefined}
              />
            </div>
          )}

          {/* Mouth */}
          <div
            className="absolute"
            style={{
              width: mouthW,
              height: state === 'error' ? 2 : 1.5,
              bottom: '22%',
              left: '50%',
              transform: 'translateX(-50%)',
              background: state === 'error' ? '#E53E3E' : '#8B6F5E',
              borderRadius: state === 'working' ? '0 0 4px 4px' : 1,
              opacity: paused ? 0.2 : 0.7,
            }}
          />
        </motion.div>

        {/* Torso / shirt */}
        <div
          className="absolute"
          style={{
            width: bodyW,
            height: bodyH,
            top: bodyTop,
            left: '50%',
            transform: 'translateX(-50%)',
            background: outfit,
            borderRadius: `${s * 0.03}px ${s * 0.03}px ${s * 0.02}px ${s * 0.02}px`,
            opacity: paused ? 0.25 : 0.9,
          }}
        />

        {/* Left arm */}
        <motion.div
          className="absolute"
          style={{
            width: armW,
            height: armH,
            top: armTop,
            left: `calc(50% - ${bodyW / 2 + armW + 1}px)`,
            background: outfit,
            borderRadius: armW / 2,
            opacity: paused ? 0.2 : 0.75,
            originY: 0,
          }}
          animate={leftArmAnim[state]}
        />

        {/* Right arm */}
        <motion.div
          className="absolute"
          style={{
            width: armW,
            height: armH,
            top: armTop,
            left: `calc(50% + ${bodyW / 2 + 1}px)`,
            background: outfit,
            borderRadius: armW / 2,
            opacity: paused ? 0.2 : 0.75,
            originY: 0,
          }}
          animate={rightArmAnim[state]}
        />

        {/* Left leg */}
        <div
          className="absolute"
          style={{
            width: legW,
            height: legH,
            top: legTop,
            left: `calc(50% - ${legW + 1}px)`,
            background: pantsColor,
            borderRadius: `0 0 ${s * 0.02}px ${s * 0.02}px`,
            opacity: paused ? 0.2 : 0.8,
          }}
        />

        {/* Right leg */}
        <div
          className="absolute"
          style={{
            width: legW,
            height: legH,
            top: legTop,
            left: `calc(50% + 1px)`,
            background: pantsColor,
            borderRadius: `0 0 ${s * 0.02}px ${s * 0.02}px`,
            opacity: paused ? 0.2 : 0.8,
          }}
        />

        {/* Left foot */}
        <div
          className="absolute"
          style={{
            width: footW,
            height: footH,
            top: footTop,
            left: `calc(50% - ${legW + 2}px)`,
            background: shoeColor,
            borderRadius: `0 0 ${s * 0.02}px ${s * 0.02}px`,
            opacity: paused ? 0.2 : 0.9,
          }}
        />

        {/* Right foot */}
        <div
          className="absolute"
          style={{
            width: footW,
            height: footH,
            top: footTop,
            left: `calc(50%)`,
            background: shoeColor,
            borderRadius: `0 0 ${s * 0.02}px ${s * 0.02}px`,
            opacity: paused ? 0.2 : 0.9,
          }}
        />
      </motion.div>

      {/* Floating Z's for paused */}
      <AnimatePresence>
        {paused && [0, 1, 2].map(i => (
          <motion.span
            key={i}
            className="absolute font-bold pointer-events-none select-none"
            style={{ color, right: s * 0.08, top: s * 0.05, fontSize: s * (0.12 - i * 0.02) }}
            initial={{ opacity: 0, x: 0, y: 0, scale: 0.5 }}
            animate={{ opacity: [0, 0.6, 0], x: s * 0.12, y: -(s * 0.12 + i * s * 0.1), scale: 1 }}
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
          style={{ width: s * 0.16, height: s * 0.16, top: s * 0.02, right: s * 0.1, fontSize: s * 0.09, fontWeight: 'bold' }}
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ duration: 0.8, repeat: Infinity }}
        >
          !
        </motion.div>
      )}
    </div>
  );
}

// =============================================================================
// TP Avatar — The Orchestrator (distinct personality)
// =============================================================================

export function TPAvatar({ size = 64, className }: { size?: number; className?: string }) {
  const s = size;
  const headW = s * 0.38;
  const headH = s * 0.28;
  const primaryColor = 'hsl(var(--primary))';

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)} style={{ width: s, height: s }}>
      {/* Pulse ring */}
      <motion.div
        className="absolute rounded-full"
        style={{
          width: headW * 1.6,
          height: headW * 1.6,
          top: s * 0.04,
          left: '50%',
          marginLeft: -(headW * 0.8),
          background: primaryColor,
        }}
        animate={{ scale: [1, 1.15, 1], opacity: [0.06, 0.03, 0.06] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' as const }}
      />

      {/* Headset arc */}
      <div
        className="absolute"
        style={{
          width: headW * 0.95,
          height: headW * 0.35,
          top: s * 0.06,
          left: '50%',
          marginLeft: -(headW * 0.475),
          borderTop: `2px solid ${primaryColor}`,
          borderRadius: '50% 50% 0 0',
          opacity: 0.5,
        }}
      />

      {/* Head */}
      <motion.div
        className="absolute flex items-center justify-center rounded-lg"
        style={{
          width: headW,
          height: headH,
          top: s * 0.12,
          left: '50%',
          marginLeft: -(headW / 2),
          background: primaryColor,
          opacity: 0.8,
          borderRadius: s * 0.05,
        }}
        animate={{ y: [0, -1, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' as const }}
      >
        {/* Eyes */}
        <div className="flex gap-1.5">
          <motion.div
            style={{ width: s * 0.04, height: s * 0.04, background: 'white', borderRadius: '50%' }}
            animate={{ scaleY: [1, 1, 0.1, 1, 1] }}
            transition={{ duration: 4, repeat: Infinity, times: [0, 0.9, 0.93, 0.96, 1] }}
          />
          <motion.div
            style={{ width: s * 0.04, height: s * 0.04, background: 'white', borderRadius: '50%' }}
            animate={{ scaleY: [1, 1, 0.1, 1, 1] }}
            transition={{ duration: 4, repeat: Infinity, times: [0, 0.9, 0.93, 0.96, 1] }}
          />
        </div>
      </motion.div>

      {/* Body */}
      <div
        className="absolute rounded-lg"
        style={{
          width: s * 0.3,
          height: s * 0.2,
          bottom: s * 0.18,
          left: '50%',
          marginLeft: -(s * 0.15),
          background: primaryColor,
          opacity: 0.5,
          borderRadius: s * 0.04,
        }}
      />

      {/* Legs */}
      <div className="absolute flex gap-[2px]" style={{ bottom: s * 0.06, left: '50%', transform: 'translateX(-50%)' }}>
        <div style={{ width: s * 0.1, height: s * 0.12, background: '#4A5568', borderRadius: `0 0 ${s * 0.02}px ${s * 0.02}px`, opacity: 0.7 }} />
        <div style={{ width: s * 0.1, height: s * 0.12, background: '#4A5568', borderRadius: `0 0 ${s * 0.02}px ${s * 0.02}px`, opacity: 0.7 }} />
      </div>
    </div>
  );
}
