'use client';

/**
 * AgentAvatar — Animated SVG character for workfloor
 *
 * Minimalist geometric persona (circle head + rounded body)
 * with state-driven CSS animations. Each agent type gets
 * an accent color; states drive the animation behavior.
 */

import { cn } from '@/lib/utils';

type AvatarState = 'working' | 'ready' | 'paused' | 'idle' | 'error';

interface AgentAvatarProps {
  state: AvatarState;
  color: string; // CSS color for body accent
  size?: number;
  className?: string;
}

export function AgentAvatar({ state, color, size = 64, className }: AgentAvatarProps) {
  const s = size;
  const cx = s / 2;
  const headR = s * 0.17;
  const headY = s * 0.28;
  const bodyW = s * 0.3;
  const bodyH = s * 0.26;
  const bodyY = s * 0.48;
  const armW = s * 0.07;
  const armH = s * 0.16;
  const armY = bodyY + s * 0.02;
  const leftArmX = cx - bodyW / 2 - armW - s * 0.015;
  const rightArmX = cx + bodyW / 2 + s * 0.015;
  const deskY = bodyY + bodyH + s * 0.05;
  const deskW = s * 0.65;
  const deskH = s * 0.05;
  const paused = state === 'paused';

  // Unique animation ID to avoid CSS collisions at different sizes
  const id = `av${s}`;

  return (
    <div className={cn('inline-flex items-center justify-center', className)}>
      <svg width={s} height={s} viewBox={`0 0 ${s} ${s}`} fill="none">
        <style>{`
          @keyframes ${id}-bob { 0%,100%{transform:translateY(0)} 40%{transform:translateY(-${s*0.025}px)} }
          @keyframes ${id}-typeL { 0%,100%{transform:translateY(0)} 30%{transform:translateY(-${s*0.04}px)} }
          @keyframes ${id}-typeR { 0%,100%{transform:translateY(0)} 60%{transform:translateY(-${s*0.04}px)} }
          @keyframes ${id}-breathe { 0%,100%{transform:scaleY(1)} 50%{transform:scaleY(1.035)} }
          @keyframes ${id}-blink { 0%,91%,100%{transform:scaleY(1)} 94%{transform:scaleY(0.08)} }
          @keyframes ${id}-nod { 0%,100%{transform:rotate(0) translateY(0)} 50%{transform:rotate(10deg) translateY(${s*0.015}px)} }
          @keyframes ${id}-zzz { 0%{opacity:0;transform:translate(0,0) scale(.5)} 25%{opacity:.6} 100%{opacity:0;transform:translate(${s*0.1}px,-${s*0.18}px) scale(1)} }
          @keyframes ${id}-look { 0%,45%,100%{transform:translateX(0)} 18%{transform:translateX(-${s*0.025}px)} 32%{transform:translateX(${s*0.025}px)} }
          @keyframes ${id}-wobble { 0%,100%{transform:translateX(0)} 25%{transform:translateX(-${s*0.015}px)} 75%{transform:translateX(${s*0.015}px)} }

          .${id}-working .${id}-head { animation:${id}-bob 1s ease-in-out infinite }
          .${id}-working .${id}-armL { animation:${id}-typeL .7s ease-in-out infinite }
          .${id}-working .${id}-armR { animation:${id}-typeR .7s ease-in-out infinite .15s }
          .${id}-ready .${id}-body { animation:${id}-breathe 4.5s ease-in-out infinite; transform-origin:bottom center }
          .${id}-ready .${id}-eyes { animation:${id}-blink 5.5s ease-in-out infinite; transform-origin:center }
          .${id}-paused .${id}-char { animation:${id}-nod 3.5s ease-in-out infinite; transform-origin:bottom center }
          .${id}-paused .${id}-z { animation:${id}-zzz 2.8s ease-out infinite }
          .${id}-idle .${id}-eyes { animation:${id}-look 7s ease-in-out infinite }
          .${id}-idle .${id}-body { animation:${id}-breathe 5s ease-in-out infinite; transform-origin:bottom center }
          .${id}-error .${id}-char { animation:${id}-wobble .4s ease-in-out infinite }
        `}</style>

        <g className={`${id}-${state}`}>
          {/* Desk */}
          <rect x={(s-deskW)/2} y={deskY} width={deskW} height={deskH} rx={deskH/2} fill="currentColor" opacity={.07} />
          {/* Desk item — small screen/paper on desk when working */}
          {state === 'working' && (
            <rect x={cx - s*0.08} y={deskY - s*0.04} width={s*0.16} height={s*0.04} rx={2} fill={color} opacity={0.15} />
          )}

          <g className={`${id}-char`}>
            {/* Body */}
            <rect className={`${id}-body`} x={cx-bodyW/2} y={bodyY} width={bodyW} height={bodyH} rx={s*0.09} fill={color} opacity={paused?.25:.65} />

            {/* Arms */}
            <rect className={`${id}-armL`} x={leftArmX} y={armY} width={armW} height={armH} rx={armW/2} fill={color} opacity={paused?.15:.4} />
            <rect className={`${id}-armR`} x={rightArmX} y={armY} width={armW} height={armH} rx={armW/2} fill={color} opacity={paused?.15:.4} />

            {/* Head */}
            <g className={`${id}-head`}>
              <circle cx={cx} cy={headY} r={headR} fill={color} opacity={paused?.3:.8} />
              {/* Eyes */}
              <g className={`${id}-eyes`}>
                {paused ? (
                  <>
                    <line x1={cx-headR*.35} y1={headY+headR*.05} x2={cx-headR*.08} y2={headY+headR*.05} stroke="white" strokeWidth={1.2} strokeLinecap="round" />
                    <line x1={cx+headR*.08} y1={headY+headR*.05} x2={cx+headR*.35} y2={headY+headR*.05} stroke="white" strokeWidth={1.2} strokeLinecap="round" />
                  </>
                ) : (
                  <>
                    <circle cx={cx-headR*.28} cy={headY-headR*.02} r={headR*.11} fill="white" />
                    <circle cx={cx+headR*.28} cy={headY-headR*.02} r={headR*.11} fill="white" />
                  </>
                )}
              </g>
              {/* Smile for ready state */}
              {state === 'ready' && (
                <path d={`M ${cx-headR*.2} ${headY+headR*.25} Q ${cx} ${headY+headR*.42} ${cx+headR*.2} ${headY+headR*.25}`} stroke="white" strokeWidth={1} strokeLinecap="round" fill="none" opacity={.6} />
              )}
            </g>

            {/* Zzz */}
            {paused && (
              <>
                <text className={`${id}-z`} x={cx+headR} y={headY-headR*.4} fill={color} opacity={.35} fontSize={s*.09} fontWeight="bold">z</text>
                <text className={`${id}-z`} x={cx+headR*1.3} y={headY-headR*.9} fill={color} opacity={.25} fontSize={s*.07} fontWeight="bold" style={{animationDelay:'.7s'}}>z</text>
                <text className={`${id}-z`} x={cx+headR*1.5} y={headY-headR*1.3} fill={color} opacity={.15} fontSize={s*.06} fontWeight="bold" style={{animationDelay:'1.4s'}}>z</text>
              </>
            )}
          </g>

          {/* Error badge */}
          {state === 'error' && (
            <>
              <circle cx={cx+headR*.85} cy={headY-headR*.65} r={s*.035} fill="#ef4444" />
              <text x={cx+headR*.85} y={headY-headR*.55} textAnchor="middle" fill="white" fontSize={s*.04} fontWeight="bold">!</text>
            </>
          )}
        </g>
      </svg>
    </div>
  );
}

// =============================================================================
// TP Avatar — Distinct orchestrator character with headset
// =============================================================================

export function TPAvatar({ size = 64, className }: { size?: number; className?: string }) {
  const s = size;
  const cx = s / 2;
  const headR = s * 0.19;
  const headY = s * 0.34;
  const id = `tp${s}`;

  return (
    <div className={cn('inline-flex items-center justify-center', className)}>
      <svg width={s} height={s} viewBox={`0 0 ${s} ${s}`} fill="none">
        <style>{`
          @keyframes ${id}-ring { 0%,100%{opacity:.08;r:${s*.24}} 50%{opacity:.04;r:${s*.28}} }
          @keyframes ${id}-blink { 0%,88%,100%{transform:scaleY(1)} 92%{transform:scaleY(.1)} }
          .${id}-ring { animation:${id}-ring 3s ease-in-out infinite }
          .${id}-eyes { animation:${id}-blink 4.5s ease-in-out infinite; transform-origin:center }
        `}</style>

        {/* Pulse ring */}
        <circle className={`${id}-ring`} cx={cx} cy={headY} r={s*.24} fill="hsl(var(--primary))" />

        {/* Headset arc */}
        <path
          d={`M${cx-headR*.75} ${headY-headR*.55} Q${cx} ${headY-headR*1.5} ${cx+headR*.75} ${headY-headR*.55}`}
          stroke="hsl(var(--primary))" strokeWidth={1.8} strokeLinecap="round" fill="none" opacity={.45}
        />
        <circle cx={cx-headR*.72} cy={headY-headR*.45} r={s*.025} fill="hsl(var(--primary))" opacity={.5} />
        <circle cx={cx+headR*.72} cy={headY-headR*.45} r={s*.025} fill="hsl(var(--primary))" opacity={.5} />

        {/* Head */}
        <circle cx={cx} cy={headY} r={headR} fill="hsl(var(--primary))" opacity={.75} />

        {/* Eyes */}
        <g className={`${id}-eyes`}>
          <circle cx={cx-headR*.3} cy={headY-headR*.05} r={headR*.1} fill="white" />
          <circle cx={cx+headR*.3} cy={headY-headR*.05} r={headR*.1} fill="white" />
        </g>

        {/* Smile */}
        <path d={`M${cx-headR*.18} ${headY+headR*.25} Q${cx} ${headY+headR*.4} ${cx+headR*.18} ${headY+headR*.25}`} stroke="white" strokeWidth={1} strokeLinecap="round" fill="none" opacity={.5} />

        {/* Body */}
        <rect x={cx-s*.14} y={headY+headR+s*.025} width={s*.28} height={s*.2} rx={s*.08} fill="hsl(var(--primary))" opacity={.45} />
      </svg>
    </div>
  );
}
