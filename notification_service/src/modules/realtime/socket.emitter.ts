import type { Server } from "socket.io";
import { logger } from "../../lib/logger";

let ioInstance: Server | null = null;

export function bindEmitter(io: Server) {
  ioInstance = io;
}

// Called by the notification-worker-realtime BullMQ processor
export function emitToUser(userId: string, event: string, payload: unknown) {
  if (!ioInstance) {
    logger.error({ userId, event }, "ws_emitter_not_bound");
    return;
  }

  try {
    ioInstance.to(`user:${userId}`).emit(event, payload);
  } catch (err) {
    // failure isolation — never let a delivery failure bubble up to the caller
    logger.error({ userId, event, err }, "ws_emit_failed");
  }
}