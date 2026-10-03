import "./config/env";
import express, { Express, Request, Response } from 'express';
import v1Routes from './modules/notifications/routes/v1/index'
import userRoutes from './modules/notifications/routes/v1/user.routes'

export function createApp(): Express {
  const app = express();
  app.use(express.json());

  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok too help' });
  });

  // Service-to-service surface: event dispatch and realtime fan-in.
  app.use('/api/v1/notifications', v1Routes)

  // The caller's own inbox. Kept on its own `/api/v1/notify` prefix rather than
  // sharing `/api/v1/notifications` with the internal routes, so the
  // user-authenticated surface can never be widened by accident when an
  // internal path is added.
  app.use('/api/v1/notify', userRoutes)

  return app;
}