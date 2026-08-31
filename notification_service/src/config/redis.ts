import { Redis } from 'ioredis';
import {env} from '../config/env'

export const bullmqConnection = new Redis({
  host: env.REDIS_HOST ?? 'localhost',
  port: Number(env.REDIS_PORT ?? 6379),
  db: 3,
  maxRetriesPerRequest: null, // required by BullMQ
});