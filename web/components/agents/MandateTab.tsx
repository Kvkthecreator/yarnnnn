'use client';

/**
 * MandateTab — YARNNN detail Mandate tab.
 *
 * Renders /workspace/constitution/MANDATE.md per ADR-207. The
 * mandate is the operator's standing intent — Primary Action +
 * success criteria + boundary conditions. It's the substrate YARNNN
 * gates task creation on (per ADR-207 hard gate).
 *
 * Authored 2026-04-30 by ADR-236 Round 5+ extension. Replaces the
 * always-empty Tasks tab on TP detail with substrate-shaped tab
 * content — operator wanted to see TP's mandate; this surfaces it.
 */

import { Compass } from 'lucide-react';
import { SubstrateTab } from './SubstrateTab';

export function MandateTab() {
  return (
    <SubstrateTab
      title="Mandate"
      icon={Compass}
      tagline="What you're here to get done — the real-world action that moves the needle (place an order, ship a campaign, publish a piece), plus what success looks like and the limits you won't cross. Nothing runs until you've set this."
      path="/workspace/constitution/MANDATE.md"
      editPrompt="Help me revise my mandate. Show me the current Primary Action declaration and walk me through sharpening success criteria + boundary conditions."
      emptyBody={
        <>
          Your mandate is your Primary-Action declaration — the external write you&apos;re
          trying to move value with (submit an order, list a product, ship a campaign)
          plus success criteria and guardrails. YARNNN uses it as the gate for creating
          tasks. <strong>Use Edit in chat</strong> to author yours.
        </>
      }
    />
  );
}
