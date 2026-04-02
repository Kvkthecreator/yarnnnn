"use client";

import { useRef, useState, useCallback } from "react";

/**
 * SpotlightCard — a card with a radial spotlight that follows the cursor.
 * Used in bento grid layouts for visual hierarchy.
 */

interface SpotlightCardProps {
  children: React.ReactNode;
  className?: string;
  /** Spotlight color (any CSS color). Defaults to white. */
  spotlightColor?: string;
  /** Size of the spotlight gradient in px. Defaults to 350. */
  spotlightSize?: number;
  /** Dark variant for dark-themed pages. */
  variant?: "light" | "dark";
}

export function SpotlightCard({
  children,
  className = "",
  spotlightColor,
  spotlightSize = 350,
  variant = "light",
}: SpotlightCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

  const resolvedSpotlightColor =
    spotlightColor ??
    (variant === "dark" ? "rgba(255,255,255,0.06)" : "rgba(255,255,255,0.08)");

  const baseClasses =
    variant === "dark"
      ? "relative overflow-hidden rounded-2xl border border-white/[0.08] bg-white/[0.03] backdrop-blur-sm transition-all duration-300 hover:border-white/[0.15] hover:bg-white/[0.05]"
      : "relative overflow-hidden rounded-2xl border border-[#1a1a1a]/[0.06] bg-white/60 backdrop-blur-sm transition-all duration-300 hover:border-[#1a1a1a]/[0.12] hover:shadow-lg";

  // Disable spotlight on touch devices — no hover, wastes cycles
  const isTouchDevice = typeof window !== 'undefined' && window.matchMedia('(pointer: coarse)').matches;

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (isTouchDevice) return;
      const card = cardRef.current;
      if (!card) return;
      const rect = card.getBoundingClientRect();
      setPosition({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
    },
    [isTouchDevice]
  );

  return (
    <div
      ref={cardRef}
      className={`${baseClasses} ${className}`}
      onMouseMove={isTouchDevice ? undefined : handleMouseMove}
      onMouseEnter={isTouchDevice ? undefined : () => setIsHovered(true)}
      onMouseLeave={isTouchDevice ? undefined : () => setIsHovered(false)}
    >
      {/* Spotlight gradient overlay */}
      <div
        className="pointer-events-none absolute inset-0 z-0 transition-opacity duration-500"
        style={{
          opacity: isHovered ? 1 : 0,
          background: `radial-gradient(${spotlightSize}px circle at ${position.x}px ${position.y}px, ${resolvedSpotlightColor}, transparent 70%)`,
        }}
      />

      {/* Content */}
      <div className="relative z-10">{children}</div>
    </div>
  );
}

/**
 * BentoGrid — wrapper that provides the asymmetric grid layout.
 */
export function BentoGrid({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`grid grid-cols-1 md:grid-cols-6 gap-4 ${className}`}
    >
      {children}
    </div>
  );
}
