/**
 * Tools API - Route tool calls to appropriate MCP servers
 *
 * POST /api/mcp/tools/:provider/:tool
 * GET  /api/mcp/tools/:provider (list available tools)
 */

import { Router, Request, Response } from 'express';
import { MCPClientManager } from '../mcp/client-manager.js';

export const toolsRouter = Router();

// Singleton client manager
const mcpManager = new MCPClientManager();

/**
 * List available tools for a provider
 */
toolsRouter.get('/:provider', async (req: Request, res: Response) => {
  const { provider } = req.params;

  try {
    const tools = await mcpManager.listTools(provider);
    res.json({
      success: true,
      provider,
      tools,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    res.status(400).json({
      success: false,
      error: message,
    });
  }
});

/**
 * Call a tool on a provider
 *
 * Request body:
 * - args: Tool arguments
 * - auth: { token, metadata } - Provider-specific auth
 */
toolsRouter.post('/:provider/:tool', async (req: Request, res: Response) => {
  const { provider, tool } = req.params;
  const { args, auth } = req.body;

  if (!auth?.token) {
    res.status(401).json({
      success: false,
      error: 'Missing auth.token in request body',
    });
    return;
  }

  console.log(`[TOOLS] Calling ${provider}/${tool}`);

  try {
    const result = await mcpManager.callTool(provider, tool, args || {}, auth);
    res.json({
      success: true,
      provider,
      tool,
      result,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error(`[TOOLS] Error calling ${provider}/${tool}:`, message);
    res.status(500).json({
      success: false,
      error: message,
      provider,
      tool,
    });
  }
});
