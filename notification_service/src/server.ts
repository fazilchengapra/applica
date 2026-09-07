import http from 'http';
import { createApp } from './app';
import { initRealtimeServer } from './modules/realtime/socket.server';

export function createServer() {
  const app = createApp();
  const httpServer = http.createServer(app);

  const { webSocketServer, pubClient, subClient, eventSubscriber } = initRealtimeServer(httpServer);

  return { httpServer, webSocketServer, pubClient, subClient, eventSubscriber };
}