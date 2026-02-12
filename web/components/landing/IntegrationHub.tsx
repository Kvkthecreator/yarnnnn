"use client";

import { useEffect, useState } from "react";

/**
 * Animated Integration Hub - Shows platforms flowing into yarnnn
 *
 * Visual metaphor: Platform icons orbit around the yarnnn logo,
 * with flowing lines/particles showing data coming together.
 */

// Platform icon components with brand colors
const SlackIcon = () => (
  <svg viewBox="0 0 24 24" className="w-full h-full" fill="currentColor">
    <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
  </svg>
);

const GmailIcon = () => (
  <svg viewBox="0 0 24 24" className="w-full h-full" fill="currentColor">
    <path d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.273H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z"/>
  </svg>
);

const NotionIcon = () => (
  <svg viewBox="0 0 24 24" className="w-full h-full" fill="currentColor">
    <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952l1.448.327s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.14c-.093-.514.28-.887.747-.933zM1.936 1.035l13.31-.98c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.047-1.448-.093-1.962-.747l-3.129-4.06c-.56-.747-.793-1.306-.793-1.96V2.667c0-.839.374-1.54 1.447-1.632z"/>
  </svg>
);

const CalendarIcon = () => (
  <svg viewBox="0 0 24 24" className="w-full h-full" fill="currentColor">
    <path d="M19 4h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11zM9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm-8 4H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2z"/>
  </svg>
);

interface Platform {
  name: string;
  icon: React.ReactNode;
  color: string;
  bgColor: string;
  angle: number;
}

const platforms: Platform[] = [
  { name: "Slack", icon: <SlackIcon />, color: "#E01E5A", bgColor: "bg-[#E01E5A]", angle: 0 },
  { name: "Gmail", icon: <GmailIcon />, color: "#EA4335", bgColor: "bg-[#EA4335]", angle: 90 },
  { name: "Notion", icon: <NotionIcon />, color: "#000000", bgColor: "bg-black", angle: 180 },
  { name: "Calendar", icon: <CalendarIcon />, color: "#4285F4", bgColor: "bg-[#4285F4]", angle: 270 },
];

// Floating particle that moves from platform to center
const Particle = ({
  startAngle,
  delay,
  color
}: {
  startAngle: number;
  delay: number;
  color: string;
}) => {
  return (
    <div
      className="absolute w-2 h-2 rounded-full opacity-60"
      style={{
        background: color,
        animation: `particleFlow 3s ease-in-out ${delay}s infinite`,
        transformOrigin: "center",
        left: "50%",
        top: "50%",
        transform: `rotate(${startAngle}deg) translateX(120px)`,
      }}
    />
  );
};

export function IntegrationHub() {
  const [mounted, setMounted] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    setMounted(true);

    // Cycle through highlighting each platform
    const interval = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % platforms.length);
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  if (!mounted) return null;

  return (
    <div className="relative w-[320px] h-[320px] md:w-[400px] md:h-[400px]">
      {/* CSS for animations */}
      <style jsx>{`
        @keyframes particleFlow {
          0% {
            opacity: 0;
            transform: rotate(var(--angle)) translateX(140px);
          }
          20% {
            opacity: 0.8;
          }
          80% {
            opacity: 0.8;
          }
          100% {
            opacity: 0;
            transform: rotate(var(--angle)) translateX(20px);
          }
        }

        @keyframes orbit {
          0% {
            transform: rotate(0deg) translateX(120px) rotate(0deg);
          }
          100% {
            transform: rotate(360deg) translateX(120px) rotate(-360deg);
          }
        }

        @keyframes pulse {
          0%, 100% {
            transform: scale(1);
            opacity: 0.3;
          }
          50% {
            transform: scale(1.2);
            opacity: 0.6;
          }
        }

        @keyframes connectionPulse {
          0%, 100% {
            opacity: 0.1;
          }
          50% {
            opacity: 0.4;
          }
        }

        @keyframes floatIn {
          0% {
            opacity: 0;
            transform: scale(0.8);
          }
          100% {
            opacity: 1;
            transform: scale(1);
          }
        }
      `}</style>

      {/* Orbital rings */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div
          className="absolute w-[240px] h-[240px] md:w-[300px] md:h-[300px] rounded-full border border-[#1a1a1a]/10"
          style={{ animation: "pulse 4s ease-in-out infinite" }}
        />
        <div
          className="absolute w-[200px] h-[200px] md:w-[250px] md:h-[250px] rounded-full border border-[#1a1a1a]/5"
          style={{ animation: "pulse 4s ease-in-out infinite 1s" }}
        />
      </div>

      {/* Connection lines from platforms to center */}
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 400 400">
        {platforms.map((platform, i) => {
          const centerX = 200;
          const centerY = 200;
          const radius = 120;
          const angle = (platform.angle - 90) * (Math.PI / 180);
          const x = centerX + radius * Math.cos(angle);
          const y = centerY + radius * Math.sin(angle);

          return (
            <line
              key={i}
              x1={centerX}
              y1={centerY}
              x2={x}
              y2={y}
              stroke={platform.color}
              strokeWidth="2"
              strokeDasharray="4 4"
              style={{
                opacity: activeIndex === i ? 0.6 : 0.15,
                transition: "opacity 0.5s ease",
                animation: "connectionPulse 2s ease-in-out infinite",
                animationDelay: `${i * 0.5}s`,
              }}
            />
          );
        })}
      </svg>

      {/* Floating particles */}
      {platforms.map((platform, i) => (
        <div key={`particles-${i}`}>
          {[0, 1, 2].map((j) => (
            <div
              key={`particle-${i}-${j}`}
              className="absolute w-1.5 h-1.5 md:w-2 md:h-2 rounded-full"
              style={{
                background: platform.color,
                left: "50%",
                top: "50%",
                opacity: activeIndex === i ? 0.7 : 0.2,
                animation: `particleFlow 2.5s ease-in-out ${j * 0.4}s infinite`,
                ["--angle" as string]: `${platform.angle}deg`,
                transform: `rotate(${platform.angle}deg) translateX(${100 + j * 20}px)`,
                transition: "opacity 0.5s ease",
              }}
            />
          ))}
        </div>
      ))}

      {/* Platform icons */}
      {platforms.map((platform, i) => {
        const radius = 110; // Distance from center (in pixels, will be scaled)
        const angle = (platform.angle - 90) * (Math.PI / 180);
        const x = Math.cos(angle) * radius;
        const y = Math.sin(angle) * radius;
        const isActive = activeIndex === i;

        return (
          <div
            key={platform.name}
            className="absolute left-1/2 top-1/2 transition-all duration-500"
            style={{
              transform: `translate(calc(-50% + ${x * 0.75}px), calc(-50% + ${y * 0.75}px)) scale(${isActive ? 1.15 : 1})`,
              animation: `floatIn 0.6s ease-out ${i * 0.1}s both`,
            }}
          >
            <div
              className={`w-12 h-12 md:w-14 md:h-14 rounded-xl ${platform.bgColor} p-2.5 md:p-3 text-white shadow-lg transition-all duration-500`}
              style={{
                boxShadow: isActive
                  ? `0 8px 32px ${platform.color}40, 0 0 0 3px ${platform.color}20`
                  : `0 4px 16px ${platform.color}20`,
              }}
            >
              {platform.icon}
            </div>
            <div
              className={`text-xs font-medium text-center mt-2 transition-all duration-500 ${
                isActive ? "text-[#1a1a1a]" : "text-[#1a1a1a]/40"
              }`}
            >
              {platform.name}
            </div>
          </div>
        );
      })}

      {/* Center yarnnn logo */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        <div
          className="w-20 h-20 md:w-24 md:h-24 rounded-2xl bg-white shadow-2xl flex items-center justify-center"
          style={{
            animation: "floatIn 0.6s ease-out 0.5s both",
            boxShadow: "0 16px 64px rgba(0,0,0,0.1), 0 0 0 1px rgba(0,0,0,0.05)",
          }}
        >
          <span className="font-brand text-2xl md:text-3xl text-[#1a1a1a]">y</span>
        </div>
        {/* Glow effect */}
        <div
          className="absolute inset-0 rounded-2xl bg-white/50 blur-xl -z-10"
          style={{ animation: "pulse 3s ease-in-out infinite" }}
        />
      </div>

      {/* Active platform indicator text */}
      <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 whitespace-nowrap">
        <span className="text-sm text-[#1a1a1a]/50">
          Connecting <span className="text-[#1a1a1a] font-medium">{platforms[activeIndex].name}</span> to yarnnn
        </span>
      </div>
    </div>
  );
}
