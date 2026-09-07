import type { IncomingMessage, Server as HttpServer } from 'http';
import { WebSocketServer, type WebSocket } from 'ws';
import {
  createRealtimeAdapterClients,
  createRealtimeEventClients,
  REALTIME_CV_STATUS_CHANNEL,
} from '../../config/redis';
import { addUserSocket, emitToUser, removeUserSocket } from './socket.emitter';
import { logger } from '../../lib/logger';

function getUserId(request: IncomingMessage): string | null {
  const userId = request.headers['x-user-id'];
  return typeof userId === 'string' && userId.length > 0 ? userId : null;
}

export function initRealtimeServer(httpServer: HttpServer) {
  const webSocketServer = new WebSocketServer({ noServer: true });
  const { pubClient, subClient } = createRealtimeAdapterClients();

  pubClient.on('error', (err) => logger.error({ err }, 'redis_pub_error'));
  subClient.on('error', (err) => logger.error({ err }, 'redis_sub_error'));

  httpServer.on('upgrade', (request, socket, head) => {
    const pathname = new URL(request.url ?? '/', 'http://localhost').pathname;
    if (pathname !== '/ws/notifications' && pathname !== '/ws/notifications/') {
      socket.destroy();
      return;
    }

    const userId = getUserId(request);
    if (!userId) {
      socket.write('HTTP/1.1 401 Unauthorized\r\n\r\n');
      socket.destroy();
      return;
    }

    webSocketServer.handleUpgrade(request, socket, head, (client) => {
      handleConnection(client, userId);
    });
  });

  const { subscriber } = createRealtimeEventClients();
  subscriber.on('error', (err) => logger.error({ err }, 'redis_event_sub_error'));
  subscriber.subscribe(REALTIME_CV_STATUS_CHANNEL).catch((err) => {
    logger.error({ err }, 'redis_event_subscribe_failed');
  });
  subscriber.on('message', (channel, message) => {
    if (channel !== REALTIME_CV_STATUS_CHANNEL) return;

    try {
      const event = JSON.parse(message) as {
        userId: string;
        cvId: string;
        status: string;
      };
      emitToUser(event.userId, 'cv.updated', {
        cv_id: event.cvId,
        status: event.status,
      });
    } catch (err) {
      logger.error({ err }, 'redis_event_message_invalid');
    }
  });

  return { webSocketServer, pubClient, subClient, eventSubscriber: subscriber };
}

function handleConnection(socket: WebSocket, userId: string) {
  addUserSocket(userId, socket);
  logger.info({ userId }, 'ws_connected');

  socket.on('close', () => {
    removeUserSocket(userId, socket);
    logger.info({ userId }, 'ws_disconnected');
  });

  socket.on('error', (err) => {
    logger.error({ userId, err }, 'ws_socket_error');
  });
}
