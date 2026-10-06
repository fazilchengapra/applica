import { Redis } from 'ioredis';
import {env} from '../config/env'

const baseConfig = {
  host: env.REDIS_HOST ?? 'localhost',
  port: Number(env.REDIS_PORT ?? 6379),
}

export const bullmqConnection = new Redis({
  ...baseConfig,
  db: 3,
  maxRetriesPerRequest: null,
});

export const REALTIME_CV_STATUS_CHANNEL = 'notification:cv-status';

/**
 * Fan-out for newly created in-app notifications.
 *
 * This is what makes realtime work across replicas. The socket registry in
 * `socket.emitter.ts` is per-process, so an instance can only reach the sockets it
 * holds; publishing to Redis and letting every instance subscribe is what lets a
 * notification created on one instance reach a user connected to another.
 */
export const REALTIME_NOTIFICATION_CHANNEL = 'notification:created';

/**
 * Every connection handed out by `createRealtimeEventClients`, so shutdown can
 * close them all.
 *
 * These are created at module scope by the publishers (which need one connection
 * each for the life of the process) and would otherwise be unreachable from the
 * SIGTERM handler, holding the event loop open past `process.exit`.
 */
const realtimeEventClients = new Set<Redis>();

export function createRealtimeEventClients() {
  const publisher = new Redis({ ...baseConfig, db: 4 });
  const subscriber = publisher.duplicate();

  realtimeEventClients.add(publisher);
  realtimeEventClients.add(subscriber);

  return { publisher, subscriber };
}

/**
 * Closes every realtime pub/sub connection. Safe to call when none were created.
 */
export async function quitRealtimeEventClients(): Promise<void> {
  await Promise.all([...realtimeEventClients].map((client) => client.quit()));
  realtimeEventClients.clear();
}