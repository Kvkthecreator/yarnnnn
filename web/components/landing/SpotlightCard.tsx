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
}

export function SpotlightCard({
  children,
  className = "",
  spotlightColor = "rgba(255,255,255,0.08)",
  spotlightSize = 350,
}: SpotlightCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const card = cardRef.current;
      if (!card) return;
      const rect = card.getBoundingClientRect();
      setPosition({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
    },
    []
  );

  return (
    <div
      ref={cardRef}
      className={`relative overflow-hidden rounded-2xl border border-[#1a1a1a]/[0.06] bg-white/60 backdrop-blur-sm transition-all duration-300 hover:border-[#1a1a1a]/[0.12] hover:shadow-lg ${className}`}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Spotlight gradient overlay */}
      <div
        className="pointer-events-none absolute inset-0 z-0 transition-opacity duration-500"
        style={{
          opacity: isHovered ? 1 : 0,
          background: `radial-gradient(${spotlightSize}px circle at ${position.x}px ${position.y}px, ${spotlightColor}, transparent 70%)`,
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
