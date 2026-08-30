import express, { Express, Request, Response } from 'express';

export function createApp(): Express {
  const app = express();

  app.use(express.json());

  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok too help' });
  });

  return app;
}