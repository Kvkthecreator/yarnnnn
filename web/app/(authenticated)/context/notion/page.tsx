import { redirect } from 'next/navigation';

interface NotionContextRedirectPageProps {
  searchParams?: {
    status?: string | string[];
  };
}

export default function NotionContextRedirectPage({ searchParams }: NotionContextRedirectPageProps) {
  const status = Array.isArray(searchParams?.status) ? searchParams?.status[0] : searchParams?.status;
  const params = new URLSearchParams({ agent: 'notion-bot' });
  if (status) params.set('status', status);
  redirect(`/agents?${params.toString()}`);
}
