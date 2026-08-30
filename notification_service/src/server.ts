import http from 'http';
import { createApp } from './app';

export function createServer() {
  const app = createApp();
  const httpServer = http.createServer(app);

  return { httpServer };
}