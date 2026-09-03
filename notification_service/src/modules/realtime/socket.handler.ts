import type { Server, Socket } from "socket.io";
import { logger } from "../../lib/logger";

export function registerConnectionHandlers(io: Server) {
  io.on("connection", (socket: Socket) => {
    const userId = socket.data.userId as string;

    socket.join(`user:${userId}`);
    logger.info({ userId, socketId: socket.id }, "ws_connected");

    socket.on("disconnect", (reason) => {
      logger.info({ userId, socketId: socket.id, reason }, "ws_disconnected");
    });

    socket.on("error", (err) => {
      logger.error({ userId, socketId: socket.id, err }, "ws_socket_error");
    });
  });
}