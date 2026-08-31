import "./config/env";
import express, { Express, Request, Response } from 'express';
import v1Routes from './modules/notifications/routes/v1/index'

export function createApp(): Express {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok too help' });
  });

  app.use('/api/v1/notifications', v1Routes)

  return app;
}