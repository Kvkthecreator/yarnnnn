/**
 * YARNNN MCP Gateway
 *
 * ADR-050: Unified gateway for MCP communication
 * - Outbound: YARNNN API → Gateway → Platform MCP servers (Slack, Notion)
 * - Inbound: Claude Desktop → Gateway → YARNNN API (future)
 */

import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import dotenv from 'dotenv';
import { toolsRouter } from './routes/tools.js';
import { healthRouter } from './routes/health.js';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(helmet());
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || '*',
}));
app.use(express.json());

// Request logging
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  next();
});

// Routes
app.use('/health', healthRouter);
app.use('/api/mcp/tools', toolsRouter);

// Error handler
app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
  console.error('[ERROR]', err.message);
  res.status(500).json({
    success: false,
    error: err.message,
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`[MCP-GATEWAY] Running on port ${PORT}`);
  console.log(`[MCP-GATEWAY] Health: http://localhost:${PORT}/health`);
  console.log(`[MCP-GATEWAY] Tools API: http://localhost:${PORT}/api/mcp/tools`);
});
