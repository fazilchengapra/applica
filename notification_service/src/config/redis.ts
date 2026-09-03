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

export function createRealtimeAdapterClients() {
  const pubClient = new Redis({
    ...baseConfig,
    db: 4,
  });
  const subClient = pubClient.duplicate();

  return { pubClient, subClient };
}
