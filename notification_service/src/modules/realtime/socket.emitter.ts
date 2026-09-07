import type { WebSocket } from 'ws';
import { logger } from '../../lib/logger';

const socketsByUser = new Map<string, Set<WebSocket>>();

export function addUserSocket(userId: string, socket: WebSocket) {
  const sockets = socketsByUser.get(userId) ?? new Set<WebSocket>();
  sockets.add(socket);
  socketsByUser.set(userId, sockets);
}

export function removeUserSocket(userId: string, socket: WebSocket) {
  const sockets = socketsByUser.get(userId);
  if (!sockets) return;

  sockets.delete(socket);
  if (sockets.size === 0) socketsByUser.delete(userId);
}

export function emitToUser(userId: string, event: string, payload: unknown) {
  const sockets = socketsByUser.get(userId);
  if (!sockets) return;

  const message = JSON.stringify({ event, data: payload });
  for (const socket of sockets) {
    if (socket.readyState !== socket.OPEN) {
      removeUserSocket(userId, socket);
      continue;
    }

    try {
      socket.send(message);
    } catch (err) {
      logger.error({ userId, event, err }, 'ws_emit_failed');
    }
  }
}
