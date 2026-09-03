import { Server } from "socket.io";
import { createAdapter } from "@socket.io/redis-adapter";
import type { Server as HttpServer } from "http";
import { createRealtimeAdapterClients } from "../../config/redis";
import { socketAuth } from "./socket.auth";
import { registerConnectionHandlers } from "./socket.handler";
import { logger } from "../../lib/logger";

export function initRealtimeServer(httpServer: HttpServer) {
  const io = new Server(httpServer, {
    path: "/ws/notifications",
    cors: { origin: process.env.FRONTEND_ORIGIN, credentials: true },
    transports: ["websocket", "polling"],
  });

  const { pubClient, subClient } = createRealtimeAdapterClients();

  pubClient.on("error", (err) => logger.error({ err }, "redis_pub_error"));
  subClient.on("error", (err) => logger.error({ err }, "redis_sub_error"));

  io.adapter(createAdapter(pubClient, subClient));
  io.use(socketAuth);
  registerConnectionHandlers(io);

  return { io, pubClient, subClient };
}