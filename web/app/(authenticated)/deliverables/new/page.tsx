'use client';

import { useRouter } from 'next/navigation';
import { DeliverableCreateSurface } from '@/components/surfaces/DeliverableCreateSurface';

export default function NewDeliverablePage() {
  const router = useRouter();

  return (
    <DeliverableCreateSurface
      onBack={() => router.push('/deliverables')}
    />
  );
}
