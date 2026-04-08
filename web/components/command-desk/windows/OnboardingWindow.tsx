'use client';

import { ContextSetup } from '@/components/tp/ContextSetup';

interface OnboardingWindowProps {
  onSubmit: (message: string) => void;
}

export function OnboardingWindow({ onSubmit }: OnboardingWindowProps) {
  return (
    <div className="p-3">
      <ContextSetup onSubmit={onSubmit} embedded />
    </div>
  );
}
