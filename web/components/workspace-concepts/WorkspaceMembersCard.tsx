'use client';

/**
 * WorkspaceMembersCard — read-only legibility for the workspace's principals
 * (ADR-373 D2). The "who can write here, and what regions" view over
 * principal_grants.
 *
 * In the multi-principal model (ADR-373) a *member* is any authenticated
 * principal bound to the workspace by a grant: the human owner, other humans,
 * their agents, third-party platforms, and — crucially — foreign LLMs reaching
 * in over MCP (claude.ai, ChatGPT, Cursor, Copilot, …). An MCP connector IS a
 * member (a foreign-llm principal), which is why this panel is "Workspace
 * Members", not "Users".
 *
 * Read-only at launch (ADR-373 D4): the grant table ships now, the consult
 * authorizes per-principal now, and this surfaces the same facts the gate
 * reads. Provisioning — inviting a member, scoping a grant — is deferred to a
 * separate Workspace Members ADR. At N=1 this shows just the owner; the surface
 * is multi-principal-ready, so the moment a member / foreign-LLM grant is
 * written it appears here.
 *
 * ADR-338 management-plane idiom: legible "who can touch this workspace"
 * without the provisioning mechanics.
 */

import { useEffect, useState } from 'react';
import { Users, ShieldCheck, Bot, Plug, User, Cpu, Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { cn } from '@/lib/utils';

type Member = Awaited<ReturnType<typeof api.workspace.getMembers>>['members'][number];

export type WorkspaceMembersVariant = 'full' | 'compact';

interface WorkspaceMembersCardProps {
  variant?: WorkspaceMembersVariant;
  className?: string;
}

// Role → presentation (icon + human label). The internal slugs are stable
// (GLOSSARY exceptions); these are the operator-facing names.
const ROLE_META: Record<string, { label: string; icon: typeof Users; tone: string }> = {
  owner: { label: 'Owner', icon: ShieldCheck, tone: 'text-emerald-600 dark:text-emerald-400' },
  member: { label: 'Member', icon: User, tone: 'text-blue-600 dark:text-blue-400' },
  'own-agent': { label: 'Agent', icon: Bot, tone: 'text-violet-600 dark:text-violet-400' },
  'foreign-llm': { label: 'External LLM', icon: Cpu, tone: 'text-amber-600 dark:text-amber-400' },
  platform: { label: 'Platform', icon: Plug, tone: 'text-cyan-600 dark:text-cyan-400' },
  a2a: { label: 'Agent (A2A)', icon: Bot, tone: 'text-violet-600 dark:text-violet-400' },
};

// Write-region root → a short operator-facing name. The roots are the ADR-320
// semantic classes; operators don't think in path prefixes.
const REGION_LABEL: Record<string, string> = {
  'governance/': 'Governance',
  'constitution/': 'Constitution',
  'persona/': 'Persona',
  'operation/': 'Operation',
  'contract/': 'Contract',
  'system/': 'System',
  'agents/': 'Agents',
};

function regionLabel(region: string): string {
  return REGION_LABEL[region] ?? REGION_LABEL[region.replace(/\/?$/, '/')] ?? region;
}

export function WorkspaceMembersCard({ variant = 'full', className }: WorkspaceMembersCardProps) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.workspace.getMembers();
        if (!cancelled) setMembers(res.members);
      } catch {
        if (!cancelled) setMembers([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className={cn('flex items-center gap-2 rounded-lg border border-border px-4 py-6 text-sm text-muted-foreground', className)}>
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading members…
      </div>
    );
  }

  if (members.length === 0) {
    return (
      <div className={cn('rounded-lg border border-dashed border-border/60 px-4 py-6 text-center', className)}>
        <Users className="mx-auto h-5 w-5 text-muted-foreground/50" />
        <p className="mt-2 text-sm font-medium text-foreground/80">No members yet</p>
        <p className="mt-1 text-xs text-muted-foreground/70 max-w-sm mx-auto">
          This workspace has no principal grants. Once you author substrate, you become its owner.
        </p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {variant === 'full' && (
        <p className="text-sm text-muted-foreground">
          Everyone — and everything — that can write to this workspace. In this model an MCP
          connection from an external LLM is a <span className="font-medium text-foreground/80">member</span>:
          it attributes its writes as itself and is authorized to a specific region of the substrate.
          Inviting members and narrowing their access is coming soon.
        </p>
      )}

      <ul className="divide-y divide-border rounded-lg border border-border">
        {members.map((m) => {
          const meta = ROLE_META[m.role] ?? { label: m.role, icon: Users, tone: 'text-muted-foreground' };
          const Icon = meta.icon;
          const name = m.label ?? m.principal_id;
          return (
            <li key={`${m.principal_id}-${m.role}`} className="flex items-start gap-3 px-4 py-3">
              <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted">
                <Icon className={cn('h-4 w-4', meta.tone)} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-medium text-foreground">{name}</span>
                  <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
                    {meta.label}
                  </span>
                </div>
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] text-muted-foreground/70">
                    {m.scopes_explicit ? 'Can write' : 'Can write (default)'}:
                  </span>
                  {m.write_regions.length === 0 ? (
                    <span className="text-[11px] text-muted-foreground/60 italic">nothing</span>
                  ) : (
                    m.write_regions.map((region) => (
                      <span
                        key={region}
                        className="rounded border border-border/60 px-1.5 py-0.5 text-[11px] text-foreground/70"
                      >
                        {regionLabel(region)}
                      </span>
                    ))
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
