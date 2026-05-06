import { redirect } from 'next/navigation';

interface IntegrationProviderRedirectProps {
  params: {
    provider: string;
  };
}

const AGENT_BY_PROVIDER: Record<string, string> = {
  slack: 'slack-bot',
  notion: 'notion-bot',
  github: 'github-bot',
};

export default function IntegrationProviderRedirect({ params }: IntegrationProviderRedirectProps) {
  const agent = AGENT_BY_PROVIDER[params.provider];
  if (agent) {
    redirect(`/agents?agent=${encodeURIComponent(agent)}`);
  }
  redirect('/connectors');
}
