/**
 * MCP Client Manager
 *
 * Manages MCP server subprocesses for each provider.
 * Spawns servers on-demand, caches connections, handles lifecycle.
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { spawn, ChildProcess } from 'child_process';

// Provider configurations
interface ProviderConfig {
  command: string;
  args: string[];
  envKeys: string[]; // Which auth fields map to which env vars
}

const PROVIDERS: Record<string, ProviderConfig> = {
  slack: {
    command: 'npx',
    args: ['-y', '@modelcontextprotocol/server-slack'],
    envKeys: ['SLACK_BOT_TOKEN', 'SLACK_TEAM_ID'],
  },
  notion: {
    command: 'npx',
    args: ['-y', '@notionhq/notion-mcp-server', '--transport', 'stdio'],
    envKeys: ['NOTION_TOKEN'],
  },
};

// Tool definitions for each provider (static, for listing)
const PROVIDER_TOOLS: Record<string, Array<{ name: string; description: string }>> = {
  slack: [
    { name: 'slack_post_message', description: 'Post a message to a Slack channel or DM' },
    { name: 'slack_list_channels', description: 'List all channels in the workspace' },
    { name: 'slack_get_channel_history', description: 'Get message history from a channel' },
    { name: 'slack_get_users', description: 'List all users in the workspace' },
    { name: 'slack_get_user_profile', description: 'Get a user\'s profile information' },
  ],
  notion: [
    { name: 'notion-search', description: 'Search for pages in the workspace' },
    { name: 'notion-fetch', description: 'Fetch a page\'s content' },
    { name: 'notion-create-pages', description: 'Create new pages' },
    { name: 'notion-create-comment', description: 'Add a comment to a page' },
    { name: 'notion-update-page', description: 'Update a page\'s properties or content' },
  ],
};

interface ActiveSession {
  client: Client;
  transport: StdioClientTransport;
  process: ChildProcess;
  createdAt: Date;
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

    // Build environment for MCP server
    const env = this.buildEnv(provider, auth);

    // Get or create session
    const sessionKey = `${provider}:${auth.token.substring(0, 8)}`;
    let session = this.sessions.get(sessionKey);

    if (!session || this.isSessionExpired(session)) {
      if (session) {
        await this.closeSession(sessionKey);
      }
      session = await this.createSession(provider, config, env);
      this.sessions.set(sessionKey, session);
    }

    // Call the tool
    try {
      const result = await session.client.callTool({
        name: toolName,
        arguments: args,
      });

      return this.parseResult(result);
    } catch (error) {
      // Session might be dead, clean up and rethrow
      await this.closeSession(sessionKey);
      throw error;
    }
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
    } else if (provider === 'notion') {
      env.NOTION_TOKEN = auth.token;
    }

    return env;
  }

  /**
   * Create a new MCP session
   */
  private async createSession(
    provider: string,
    config: ProviderConfig,
    env: Record<string, string>
  ): Promise<ActiveSession> {
    console.log(`[MCP] Creating session for ${provider}`);

    // Spawn the MCP server process
    const proc = spawn(config.command, config.args, {
      env,
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    proc.stderr?.on('data', (data) => {
      console.error(`[MCP:${provider}:stderr]`, data.toString());
    });

    proc.on('error', (error) => {
      console.error(`[MCP:${provider}:error]`, error.message);
    });

    proc.on('exit', (code) => {
      console.log(`[MCP:${provider}] Process exited with code ${code}`);
    });

    // Create transport and client
    const transport = new StdioClientTransport({
      command: config.command,
      args: config.args,
      env,
    });

    const client = new Client({
      name: 'yarnnn-mcp-gateway',
      version: '1.0.0',
    }, {
      capabilities: {},
    });

    await client.connect(transport);

    console.log(`[MCP] Session created for ${provider}`);

    return {
      client,
      transport,
      process: proc,
      createdAt: new Date(),
    };
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
        session.process.kill();
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
