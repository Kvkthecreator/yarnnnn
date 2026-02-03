'use client';

/**
 * ADR-023: Supervisor Desk Architecture
 *
 * Single desk view - one surface at a time, TP always present
 */

import { Desk } from '@/components/desk/Desk';

export default function DashboardPage() {
  return <Desk />;
}
