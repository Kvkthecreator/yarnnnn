import { redirect } from 'next/navigation';

interface SlackContextRedirectPageProps {
  searchParams?: {
    status?: string | string[];
  };
}

export default function SlackContextRedirectPage({ searchParams }: SlackContextRedirectPageProps) {
  const status = Array.isArray(searchParams?.status) ? searchParams?.status[0] : searchParams?.status;
  const params = new URLSearchParams({ agent: 'slack-bot' });
  if (status) params.set('status', status);
  redirect(`/agents?${params.toString()}`);
}
