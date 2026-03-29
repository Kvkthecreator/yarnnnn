"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Check,
  ExternalLink,
  Link2,
  Loader2,
} from "lucide-react";
import { api } from "@/lib/api/client";

interface Integration {
  id: string;
  provider: string;
  status: string;
  workspace_name: string | null;
  last_used_at: string | null;
  created_at: string;
}

interface SummaryPlatform {
  provider: string;
  status: string;
}

interface ConnectedIntegrationsSectionProps {
  title?: string;
  description?: string;
  className?: string;
  children?: React.ReactNode;
  /** Frontend path to return to after OAuth (e.g. "/system"). Defaults to /dashboard. */
  redirectTo?: string;
}

export function ConnectedIntegrationsSection({
  title = "Connected Platforms",
  description = "Connect platforms to sync context. Manage sources in each platform's context page.",
  className,
  children,
  redirectTo,
}: ConnectedIntegrationsSectionProps) {
  const router = useRouter();

  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [platformStatuses, setPlatformStatuses] = useState<Record<string, string>>({});
  const [isLoadingIntegrations, setIsLoadingIntegrations] = useState(false);
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
  const [disconnectingProvider, setDisconnectingProvider] = useState<string | null>(null);

  const loadIntegrations = async () => {
    setIsLoadingIntegrations(true);
    try {
      const [listResult, summaryResult] = await Promise.all([
        api.integrations.list(),
        api.integrations.getSummary(),
      ]);

      setIntegrations(listResult.integrations || []);

      const statuses: Record<string, string> = {};
      (summaryResult.platforms || []).forEach((platform: SummaryPlatform) => {
        statuses[platform.provider] = platform.status;
      });

      setPlatformStatuses(statuses);
    } catch (err) {
      console.error("Failed to fetch integrations:", err);
    } finally {
      setIsLoadingIntegrations(false);
    }
  };

  useEffect(() => {
    loadIntegrations();
  }, []);

  const handleConnectIntegration = async (provider: string) => {
    setConnectingProvider(provider);
    try {
      const result = await api.integrations.getAuthorizationUrl(provider, redirectTo);
      window.location.href = result.authorization_url;
    } catch (err) {
      console.error(`Failed to initiate ${provider} OAuth:`, err);
      setConnectingProvider(null);
    }
  };

  const handleDisconnectIntegration = async (provider: string) => {
    if (!confirm(`Disconnect ${provider}? You'll need to reconnect to export to ${provider} again.`)) {
      return;
    }

    setDisconnectingProvider(provider);
    try {
      await api.integrations.disconnect(provider);
      await loadIntegrations();
    } catch (err) {
      console.error(`Failed to disconnect ${provider}:`, err);
    } finally {
      setDisconnectingProvider(null);
    }
  };

  const slackConnected = platformStatuses.slack === "active";
  const notionConnected = platformStatuses.notion === "active";
  const githubConnected = platformStatuses.github === "active";

  return (
    <section className={className}>
      <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <Link2 className="w-5 h-5" />
        {title}
      </h2>
      <p className="text-sm text-muted-foreground mb-6">{description}</p>

      {isLoadingIntegrations ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="space-y-4">
          {(() => {
            const slackIntegration = integrations.find((i) => i.provider === "slack");
            return (
              <div className="p-4 border border-border rounded-lg">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-[#4A154B] rounded-lg flex items-center justify-center shrink-0">
                    <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <div className="font-medium">Slack</div>
                        <div className="text-sm text-muted-foreground">Team collaboration and context</div>
                      </div>
                      {slackConnected ? (
                        <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1 shrink-0">
                          <Check className="w-4 h-4" />
                          Connected
                        </span>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-2 mt-3 flex-wrap">
                      {slackIntegration ? (
                        <>
                          <button
                            onClick={() => handleConnectIntegration("slack")}
                            disabled={connectingProvider === "slack"}
                            className="px-3 py-1.5 text-sm text-muted-foreground border border-border rounded-md hover:bg-muted transition-colors"
                          >
                            {connectingProvider === "slack" ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              "Reconnect"
                            )}
                          </button>
                          <button
                            onClick={() => handleDisconnectIntegration(slackIntegration.provider)}
                            disabled={disconnectingProvider === slackIntegration.provider}
                            className="px-3 py-1.5 text-sm text-muted-foreground hover:text-destructive border border-border rounded-md hover:border-destructive/30 transition-colors"
                          >
                            {disconnectingProvider === slackIntegration.provider ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              "Disconnect"
                            )}
                          </button>
                          <button
                            onClick={() => router.push("/context/slack")}
                            className="px-3 py-1.5 text-sm text-primary border border-primary/30 rounded-md hover:bg-primary/10 transition-colors"
                          >
                            Manage
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => handleConnectIntegration("slack")}
                          disabled={connectingProvider === "slack"}
                          className="px-4 py-2 bg-[#4A154B] text-white rounded-md text-sm font-medium hover:bg-[#3d1140] flex items-center gap-2"
                        >
                          {connectingProvider === "slack" ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <>
                              <ExternalLink className="w-4 h-4" />
                              Connect
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })()}

          {(() => {
            const notionIntegration = integrations.find((i) => i.provider === "notion");
            return (
              <div className="p-4 border border-border rounded-lg">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-black dark:bg-white rounded-lg flex items-center justify-center shrink-0">
                    <svg className="w-6 h-6 text-white dark:text-black" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.98-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466l1.823 1.447zm.793 3.08v13.904c0 .747.373 1.027 1.213.98l14.523-.84c.84-.046.934-.56.934-1.166V6.354c0-.606-.234-.933-.746-.886l-15.177.887c-.56.046-.747.326-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952l1.448.327s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.14c-.093-.513.28-.886.747-.933l3.222-.187zM2.87.119l13.449-.933c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.046-1.448-.093-1.962-.747L1.945 18.79c-.56-.747-.793-1.306-.793-1.958V2.005C1.152.933 1.525.212 2.87.119z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <div className="font-medium">Notion</div>
                        <div className="text-sm text-muted-foreground">Knowledge base and context</div>
                      </div>
                      {notionConnected ? (
                        <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1 shrink-0">
                          <Check className="w-4 h-4" />
                          Connected
                        </span>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-2 mt-3 flex-wrap">
                      {notionIntegration ? (
                        <>
                          <button
                            onClick={() => handleConnectIntegration("notion")}
                            disabled={connectingProvider === "notion"}
                            className="px-3 py-1.5 text-sm text-muted-foreground border border-border rounded-md hover:bg-muted transition-colors"
                          >
                            {connectingProvider === "notion" ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              "Reconnect"
                            )}
                          </button>
                          <button
                            onClick={() => handleDisconnectIntegration(notionIntegration.provider)}
                            disabled={disconnectingProvider === notionIntegration.provider}
                            className="px-3 py-1.5 text-sm text-muted-foreground hover:text-destructive border border-border rounded-md hover:border-destructive/30 transition-colors"
                          >
                            {disconnectingProvider === notionIntegration.provider ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              "Disconnect"
                            )}
                          </button>
                          <button
                            onClick={() => router.push("/context/notion")}
                            className="px-3 py-1.5 text-sm text-primary border border-primary/30 rounded-md hover:bg-primary/10 transition-colors"
                          >
                            Manage
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => handleConnectIntegration("notion")}
                          disabled={connectingProvider === "notion"}
                          className="px-4 py-2 bg-black dark:bg-white text-white dark:text-black rounded-md text-sm font-medium hover:bg-gray-800 dark:hover:bg-gray-200 flex items-center gap-2"
                        >
                          {connectingProvider === "notion" ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <>
                              <ExternalLink className="w-4 h-4" />
                              Connect
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })()}

          {(() => {
            const githubIntegration = integrations.find((i) => i.provider === "github");
            return (
              <div className="p-4 border border-border rounded-lg">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-gray-900 dark:bg-white rounded-lg flex items-center justify-center shrink-0">
                    <svg className="w-6 h-6 text-white dark:text-black" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <div className="font-medium">GitHub</div>
                        <div className="text-sm text-muted-foreground">Repositories, issues, and pull requests</div>
                      </div>
                      {githubConnected ? (
                        <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1 shrink-0">
                          <Check className="w-4 h-4" />
                          Connected
                        </span>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-2 mt-3 flex-wrap">
                      {githubIntegration ? (
                        <>
                          <button
                            onClick={() => handleConnectIntegration("github")}
                            disabled={connectingProvider === "github"}
                            className="px-3 py-1.5 text-sm text-muted-foreground border border-border rounded-md hover:bg-muted transition-colors"
                          >
                            {connectingProvider === "github" ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              "Reconnect"
                            )}
                          </button>
                          <button
                            onClick={() => handleDisconnectIntegration(githubIntegration.provider)}
                            disabled={disconnectingProvider === githubIntegration.provider}
                            className="px-3 py-1.5 text-sm text-muted-foreground hover:text-destructive border border-border rounded-md hover:border-destructive/30 transition-colors"
                          >
                            {disconnectingProvider === githubIntegration.provider ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              "Disconnect"
                            )}
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => handleConnectIntegration("github")}
                          disabled={connectingProvider === "github"}
                          className="px-4 py-2 bg-gray-900 dark:bg-white text-white dark:text-black rounded-md text-sm font-medium hover:bg-gray-800 dark:hover:bg-gray-200 flex items-center gap-2"
                        >
                          {connectingProvider === "github" ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <>
                              <ExternalLink className="w-4 h-4" />
                              Connect
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })()}

          {children}

          <div className="p-4 bg-muted/30 rounded-lg text-sm text-muted-foreground">
            <p>
              <strong>How it works:</strong> After connecting, select sources on each platform&apos;s context page.
              Context syncs automatically based on your tier — used in conversations and agents.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
