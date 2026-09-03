import http from 'http';
import { createApp } from './app';
import { initRealtimeServer } from './modules/realtime/socket.server';

export function createServer() {
  const app = createApp();
  const httpServer = http.createServer(app);

  const { io, pubClient, subClient } = initRealtimeServer(httpServer);

  return { httpServer, io, pubClient, subClient };
}