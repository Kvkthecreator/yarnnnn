/**
 * MCP Client Manager
 *
 * Manages MCP connections for each provider.
 * Supports both:
 * - Local stdio transport (spawns subprocess) - Slack
 * - Remote HTTP transport (connects to hosted MCP) - Notion
 *
 * ADR-050: Notion uses hosted MCP at mcp.notion.com because the open-source
 * @notionhq/notion-mcp-server requires internal integration tokens (ntn_...),
 * but YARNNN uses OAuth access tokens. The hosted MCP supports OAuth.
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';

// =============================================================================
// Provider Configuration
// =============================================================================

// Local provider: spawns subprocess via stdio
interface LocalProviderConfig {
  type: 'local';
  command: string;
  args: string[];
}

// Remote provider: connects via HTTP to hosted MCP server
interface RemoteProviderConfig {
  type: 'remote';
  url: string;
}

type ProviderConfig = LocalProviderConfig | RemoteProviderConfig;

const PROVIDERS: Record<string, ProviderConfig> = {
  // Slack: Local stdio transport - MCP server supports OAuth tokens
  slack: {
    type: 'local',
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-slack'],
  },
  // Notion: Remote HTTP transport - hosted MCP supports OAuth
  // The open-source @notionhq/notion-mcp-server requires ntn_... tokens
  // which are incompatible with our OAuth flow
  notion: {
    type: 'remote',
    url: 'https://mcp.notion.com/mcp',
  },
};

// Tool definitions for each provider (static, for listing)
// These are discovered dynamically but we cache for faster responses
const PROVIDER_TOOLS: Record<string, Array<{ name: string; description: string }>> = {
  slack: [
    { name: 'slack_post_message', description: 'Post a message to a Slack channel or DM' },
    { name: 'slack_list_channels', description: 'List all channels in the workspace' },
    { name: 'slack_get_channel_history', description: 'Get message history from a channel' },
    { name: 'slack_get_users', description: 'List all users in the workspace' },
    { name: 'slack_get_user_profile', description: 'Get a user\'s profile information' },
  ],
  notion: [
    // Notion hosted MCP tool names
    { name: 'notion-search', description: 'Search for pages in the workspace' },
    { name: 'notion-fetch', description: 'Fetch page content' },
    { name: 'notion-create-pages', description: 'Create new pages' },
    { name: 'notion-update-page', description: 'Update a page\'s properties' },
    { name: 'notion-create-comment', description: 'Add a comment to a page' },
    { name: 'notion-get-comments', description: 'Get comments from a page' },
  ],
};

// =============================================================================
// Session Types
// =============================================================================

interface BaseSession {
  client: Client;
  createdAt: Date;
  discoveredTools?: string[];
}

interface LocalSession extends BaseSession {
  type: 'local';
  transport: StdioClientTransport;
}

interface RemoteSession extends BaseSession {
  type: 'remote';
  transport: StreamableHTTPClientTransport;
}

type ActiveSession = LocalSession | RemoteSession;

// =============================================================================
// Client Manager
// =============================================================================

export class MCPClientManager {
  private sessions: Map<string, ActiveSession> = new Map();
  private sessionTimeout = 5 * 60 * 1000; // 5 minutes

  /**
   * List available tools for a provider
   */
  async listTools(provider: string): Promise<Array<{ name: string; description: string }>> {
    const config = PROVIDERS[provider];
    if (!config) {
      throw new Error(`Unknown provider: ${provider}. Available: ${Object.keys(PROVIDERS).join(', ')}`);
    }
    return PROVIDER_TOOLS[provider] || [];
  }

  /**
   * Call a tool on a provider
   */
  async callTool(
    provider: string,
    toolName: string,
    args: Record<string, unknown>,
    auth: { token: string; metadata?: Record<string, string> }
  ): Promise<unknown> {
    const config = PROVIDERS[provider];
    if (!config) {
      throw new Error(`Unknown provider: ${provider}`);
    }

    // Get or create session
    const sessionKey = `${provider}:${auth.token.substring(0, 8)}`;
    let session = this.sessions.get(sessionKey);

    if (!session || this.isSessionExpired(session)) {
      if (session) {
        await this.closeSession(sessionKey);
      }
      session = await this.createSession(provider, config, auth);
      this.sessions.set(sessionKey, session);
    }

    // Call the tool
    try {
      console.log(`[MCP] Calling ${provider}/${toolName}`);
      const result = await session.client.callTool({
        name: toolName,
        arguments: args,
      });

      return this.parseResult(result);
    } catch (error) {
      console.error(`[MCP] Error calling ${provider}/${toolName}:`, error);
      // Session might be dead, clean up and rethrow
      await this.closeSession(sessionKey);
      throw error;
    }
  }

  /**
   * Create a new MCP session (local or remote)
   */
  private async createSession(
    provider: string,
    config: ProviderConfig,
    auth: { token: string; metadata?: Record<string, string> }
  ): Promise<ActiveSession> {
    if (config.type === 'local') {
      return this.createLocalSession(provider, config, auth);
    } else {
      return this.createRemoteSession(provider, config, auth);
    }
  }

  /**
   * Create local session (stdio transport - subprocess)
   */
  private async createLocalSession(
    provider: string,
    config: LocalProviderConfig,
    auth: { token: string; metadata?: Record<string, string> }
  ): Promise<LocalSession> {
    console.log(`[MCP] Creating local session for ${provider}`);

    // Build environment for MCP server
    const env = this.buildEnv(provider, auth);

    // Create transport - StdioClientTransport manages the subprocess internally
    const transport = new StdioClientTransport({
      command: config.command,
      args: config.args,
      env,
      stderr: 'pipe',
    });

    // Log stderr from MCP server for debugging
    if (transport.stderr) {
      transport.stderr.on('data', (data: Buffer) => {
        console.log(`[MCP:${provider}:stderr] ${data.toString().trim()}`);
      });
    }

    const client = new Client({
      name: 'yarnnn-mcp-gateway',
      version: '1.0.0',
    }, {
      capabilities: {},
    });

    await client.connect(transport);

    // Discover available tools
    const discoveredTools = await this.discoverTools(provider, client);

    console.log(`[MCP] Local session created for ${provider}`);

    return {
      type: 'local',
      client,
      transport,
      createdAt: new Date(),
      discoveredTools,
    };
  }

  /**
   * Create remote session (HTTP transport - hosted MCP)
   */
  private async createRemoteSession(
    provider: string,
    config: RemoteProviderConfig,
    auth: { token: string; metadata?: Record<string, string> }
  ): Promise<RemoteSession> {
    console.log(`[MCP] Creating remote session for ${provider} at ${config.url}`);

    // Create HTTP transport with OAuth bearer token
    const transport = new StreamableHTTPClientTransport(
      new URL(config.url),
      {
        requestInit: {
          headers: {
            'Authorization': `Bearer ${auth.token}`,
          },
        },
      }
    );

    const client = new Client({
      name: 'yarnnn-mcp-gateway',
      version: '1.0.0',
    }, {
      capabilities: {},
    });

    await client.connect(transport);

    // Discover available tools
    const discoveredTools = await this.discoverTools(provider, client);

    console.log(`[MCP] Remote session created for ${provider}`);

    return {
      type: 'remote',
      client,
      transport,
      createdAt: new Date(),
      discoveredTools,
    };
  }

  /**
   * Build environment variables for local MCP server
   */
  private buildEnv(
    provider: string,
    auth: { token: string; metadata?: Record<string, string> }
  ): Record<string, string> {
    const env: Record<string, string> = { ...process.env as Record<string, string> };

    if (provider === 'slack') {
      env.SLACK_BOT_TOKEN = auth.token;
      if (auth.metadata?.team_id) {
        env.SLACK_TEAM_ID = auth.metadata.team_id;
      }
    }

    return env;
  }

  /**
   * Discover available tools from the MCP server
   */
  private async discoverTools(provider: string, client: Client): Promise<string[]> {
    console.log(`[MCP] Discovering tools for ${provider}...`);
    try {
      const toolsResult = await client.listTools();
      const toolNames = toolsResult.tools.map(t => t.name);
      console.log(`[MCP] ${provider} tools discovered: ${toolNames.join(', ')}`);
      return toolNames;
    } catch (err) {
      console.error(`[MCP] Failed to list tools for ${provider}:`, err);
      return [];
    }
  }

  /**
   * Check if session is expired
   */
  private isSessionExpired(session: ActiveSession): boolean {
    return Date.now() - session.createdAt.getTime() > this.sessionTimeout;
  }

  /**
   * Close a session
   */
  private async closeSession(key: string): Promise<void> {
    const session = this.sessions.get(key);
    if (session) {
      console.log(`[MCP] Closing session ${key}`);
      try {
        await session.client.close();
      } catch (error) {
        console.error(`[MCP] Error closing session:`, error);
      }
      this.sessions.delete(key);
    }
  }

  /**
   * Parse MCP CallToolResult into plain object
   */
  private parseResult(result: unknown): unknown {
    // MCP SDK returns CallToolResult with content array
    if (result && typeof result === 'object' && 'content' in result) {
      const content = (result as { content: Array<{ type: string; text?: string }> }).content;
      if (Array.isArray(content)) {
        for (const item of content) {
          if (item.type === 'text' && item.text) {
            try {
              return JSON.parse(item.text);
            } catch {
              return item.text;
            }
          }
        }
      }
    }
    return result;
  }

  /**
   * Close all sessions (cleanup)
   */
  async closeAll(): Promise<void> {
    for (const key of this.sessions.keys()) {
      await this.closeSession(key);
    }
  }
}
