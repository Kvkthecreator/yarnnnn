/**
 * MCP Client Manager
 *
 * ADR-050: Manages MCP connections for Slack ONLY.
 *
 * Why only Slack?
 * - Slack's @modelcontextprotocol/server-slack works with OAuth tokens
 * - Notion's MCP servers are incompatible with OAuth (see ADR-050)
 * - Gmail/Calendar use Direct API (no suitable MCP servers)
 *
 * This gateway exists because MCP servers require Node.js (npx spawns subprocess)
 * and our Python API can't run Node.js directly on Render.
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

// =============================================================================
// Provider Configuration
// =============================================================================

interface ProviderConfig {
  command: string;
  args: string[];
}

// Only Slack uses MCP Gateway
const PROVIDERS: Record<string, ProviderConfig> = {
  slack: {
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-slack'],
  },
};

// Tool definitions for listing (discovered dynamically on connect)
const PROVIDER_TOOLS: Record<string, Array<{ name: string; description: string }>> = {
  slack: [
    { name: 'slack_post_message', description: 'Post a message to a Slack channel or DM' },
    { name: 'slack_list_channels', description: 'List all channels in the workspace' },
    { name: 'slack_get_channel_history', description: 'Get message history from a channel' },
    { name: 'slack_get_users', description: 'List all users in the workspace' },
    { name: 'slack_get_user_profile', description: 'Get a user\'s profile information' },
  ],
};

// =============================================================================
// Session Management
// =============================================================================

interface ActiveSession {
  client: Client;
  transport: StdioClientTransport;
  createdAt: Date;
  discoveredTools?: string[];
}

export class MCPClientManager {
  private sessions: Map<string, ActiveSession> = new Map();
  private sessionTimeout = 5 * 60 * 1000; // 5 minutes

  /**
   * List available tools for a provider
   */
  async listTools(provider: string): Promise<Array<{ name: string; description: string }>> {
    const config = PROVIDERS[provider];
    if (!config) {
      throw new Error(`Unknown provider: ${provider}. Only 'slack' is supported via MCP Gateway.`);
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
      throw new Error(`Unknown provider: ${provider}. Only 'slack' is supported via MCP Gateway.`);
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
      await this.closeSession(sessionKey);
      throw error;
    }
  }

  /**
   * Create a new MCP session (local stdio subprocess)
   */
  private async createSession(
    provider: string,
    config: ProviderConfig,
    auth: { token: string; metadata?: Record<string, string> }
  ): Promise<ActiveSession> {
    console.log(`[MCP] Creating session for ${provider}`);

    // Build environment for MCP server
    const env = this.buildEnv(provider, auth);

    // Create transport - StdioClientTransport manages subprocess
    const transport = new StdioClientTransport({
      command: config.command,
      args: config.args,
      env,
      stderr: 'pipe',
    });

    // Log stderr for debugging
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

    console.log(`[MCP] Session created for ${provider}`);

    return {
      client,
      transport,
      createdAt: new Date(),
      discoveredTools,
    };
  }

  /**
   * Build environment variables for MCP server
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
