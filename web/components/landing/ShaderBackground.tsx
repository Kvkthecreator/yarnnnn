"use client";

export function ShaderBackground() {
  return (
    <div className="fixed inset-0 z-0 overflow-hidden">
      {/* Animated gradient background */}
      <div
        className="absolute inset-0 animate-gradient-shift"
        style={{
          background: `
            radial-gradient(ellipse 80% 60% at 20% 30%, rgba(30, 30, 35, 0.8), transparent),
            radial-gradient(ellipse 60% 50% at 80% 70%, rgba(25, 25, 30, 0.6), transparent),
            radial-gradient(ellipse 100% 80% at 50% 50%, rgba(20, 20, 25, 0.9), transparent),
            #0a0a0a
          `,
        }}
      />
      {/* Subtle noise texture */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
        }}
      />
    </div>
  );
}
