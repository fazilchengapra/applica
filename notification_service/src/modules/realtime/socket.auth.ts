import type { Socket } from "socket.io";
import { logger } from "../../lib/logger";

export function socketAuth(socket: Socket, next: (err?: Error) => void) {
  const userId = socket.handshake.headers["x-user-id"];

  if (!userId || Array.isArray(userId)) {
    logger.warn({ socketId: socket.id }, "ws_auth_missing_user_id");
    return next(new Error("UNAUTHORIZED"));
  }

  socket.data.userId = userId;
  next();
}