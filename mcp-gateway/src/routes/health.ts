/**
 * Health check endpoint
 */

import { Router } from 'express';

export const healthRouter = Router();

healthRouter.get('/', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'yarnnn-mcp-gateway',
    timestamp: new Date().toISOString(),
  });
});
