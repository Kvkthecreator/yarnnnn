'use client';

/**
 * KernelMaintenanceActions — kernel-default chrome actions for
 * system_maintenance (ADR-225 Phase 3). Back-office tasks expose no
 * user-driven actions; render nothing. Preserved as a distinct
 * component so bundles can override if a system_maintenance task ever
 * needs an operator-facing affordance.
 */

export function KernelMaintenanceActions() {
  return null;
}
