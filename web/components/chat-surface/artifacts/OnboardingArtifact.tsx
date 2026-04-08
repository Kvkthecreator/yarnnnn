'use client';

import { ContextSetup } from '@/components/tp/ContextSetup';

interface OnboardingArtifactProps {
  onSubmit: (message: string) => void;
}

export function OnboardingArtifact({ onSubmit }: OnboardingArtifactProps) {
  return (
    <div className="p-3">
      <ContextSetup onSubmit={onSubmit} embedded />
    </div>
  );
}
