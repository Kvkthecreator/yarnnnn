"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Calendar,
  Check,
  ExternalLink,
  Link2,
  Loader2,
  Mail,
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

interface ConnectedIntegrationsSectionProps {
  title?: string;
  description?: string;
  className?: string;
}

export function ConnectedIntegrationsSection({
  title = "Connected Integrations",
  description = "Connect platforms to sync context. Manage sources in each platform's context page.",
  className,
}: ConnectedIntegrationsSectionProps) {
  const router = useRouter();

  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [isLoadingIntegrations, setIsLoadingIntegrations] = useState(false);
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
  const [disconnectingProvider, setDisconnectingProvider] = useState<string | null>(null);

  const loadIntegrations = async () => {
    setIsLoadingIntegrations(true);
    try {
      const result = await api.integrations.list();
      setIntegrations(result.integrations);
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
      const result = await api.integrations.getAuthorizationUrl(provider);
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
      setIntegrations((current) => current.filter((i) => i.provider !== provider));
    } catch (err) {
      console.error(`Failed to disconnect ${provider}:`, err);
    } finally {
      setDisconnectingProvider(null);
    }
  };

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
                      {slackIntegration ? (
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
                      {notionIntegration ? (
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
            const googleIntegration = integrations.find((i) => i.provider === "gmail");
            return (
              <div className="p-4 border border-border rounded-lg">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-blue-500 via-red-500 to-yellow-500 rounded-lg flex items-center justify-center shrink-0">
                    <svg className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <div className="font-medium">Google</div>
                        <div className="text-sm text-muted-foreground">Gmail and Calendar access</div>
                      </div>
                      {googleIntegration ? (
                        <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1 shrink-0">
                          <Check className="w-4 h-4" />
                          Connected
                        </span>
                      ) : null}
                    </div>

                    {googleIntegration ? (
                      <div className="mt-3 pt-3 border-t border-border/50">
                        <div className="grid grid-cols-2 gap-3">
                          <div className="flex items-center justify-between p-2.5 rounded-md bg-muted/30">
                            <div className="flex items-center gap-2">
                              <Mail className="w-4 h-4 text-red-500" />
                              <span className="text-sm font-medium">Gmail</span>
                            </div>
                            <button
                              onClick={() => router.push("/context/gmail")}
                              className="px-2.5 py-1 text-xs text-primary border border-primary/30 rounded hover:bg-primary/10 transition-colors"
                            >
                              Manage
                            </button>
                          </div>

                          <div className="flex items-center justify-between p-2.5 rounded-md bg-muted/30">
                            <div className="flex items-center gap-2">
                              <Calendar className="w-4 h-4 text-blue-500" />
                              <span className="text-sm font-medium">Calendar</span>
                            </div>
                            <button
                              onClick={() => router.push("/context/calendar")}
                              className="px-2.5 py-1 text-xs text-primary border border-primary/30 rounded hover:bg-primary/10 transition-colors"
                            >
                              Manage
                            </button>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 mt-3">
                          <button
                            onClick={() => handleDisconnectIntegration(googleIntegration.provider)}
                            disabled={disconnectingProvider === googleIntegration.provider}
                            className="px-3 py-1.5 text-sm text-muted-foreground hover:text-destructive border border-border rounded-md hover:border-destructive/30 transition-colors"
                          >
                            {disconnectingProvider === googleIntegration.provider ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              "Disconnect"
                            )}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="mt-3">
                        <button
                          onClick={() => handleConnectIntegration("google")}
                          disabled={connectingProvider === "google"}
                          className="px-4 py-2 bg-gradient-to-r from-blue-500 to-red-500 text-white rounded-md text-sm font-medium hover:from-blue-600 hover:to-red-600 flex items-center gap-2"
                        >
                          {connectingProvider === "google" ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <>
                              <ExternalLink className="w-4 h-4" />
                              Connect
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })()}

          <div className="p-4 bg-muted/30 rounded-lg text-sm text-muted-foreground">
            <p>
              <strong>How it works:</strong> After connecting, select sources on each platform&apos;s context page.
              Context syncs automatically based on your tier — TP uses it in conversations and deliverables.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
