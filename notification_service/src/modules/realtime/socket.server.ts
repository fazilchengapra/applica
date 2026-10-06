import type { IncomingMessage, Server as HttpServer } from 'http';
import { WebSocketServer, type WebSocket } from 'ws';
import {
  createRealtimeEventClients,
  REALTIME_CV_STATUS_CHANNEL,
  REALTIME_NOTIFICATION_CHANNEL,
} from '../../config/redis';
import { addUserSocket, emitToUser, removeUserSocket } from './socket.emitter';
import { logger } from '../../lib/logger';

function getUserId(request: IncomingMessage): string | null {
  const userId = request.headers['x-user-id'];
  return typeof userId === 'string' && userId.length > 0 ? userId : null;
}

export function initRealtimeServer(httpServer: HttpServer) {
  const webSocketServer = new WebSocketServer({ noServer: true });

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

  // Both fan-out channels land in the same handler below; the socket registry is
  // per-process, so subscribing here is what lets a message published by any
  // instance reach the sockets this instance happens to be holding.
  const REALTIME_CHANNELS = [REALTIME_CV_STATUS_CHANNEL, REALTIME_NOTIFICATION_CHANNEL];

  subscriber
    .subscribe(...REALTIME_CHANNELS)
    .catch((err) => logger.error({ err }, 'redis_event_subscribe_failed'));

  subscriber.on('message', (channel, message) => {
    if (!REALTIME_CHANNELS.includes(channel)) return;

    try {
      const event = JSON.parse(message) as {
        userId: string;
        cvId?: string;
        status?: string;
        payload?: unknown;
      };

      if (channel === REALTIME_NOTIFICATION_CHANNEL) {
        // Carries the already-rendered NotificationView, so this is a hand-off
        // rather than a database read per connected socket.
        if (typeof event.userId !== 'string' || event.payload === undefined) {
          logger.error({ channel }, 'realtime_notification_message_invalid');
          return;
        }

        emitToUser(event.userId, 'notification.created', event.payload);
        return;
      }

      emitToUser(event.userId, 'cv.updated', {
        cv_id: event.cvId,
        status: event.status,
      });
    } catch (err) {
      logger.error({ err, channel }, 'redis_event_message_invalid');
    }
  });

  return { webSocketServer };
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
