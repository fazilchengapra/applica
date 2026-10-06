import 'dotenv/config';
import { z } from 'zod';

const envSchema = z.object({
  PORT: z.coerce.number().default(3002),
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),

  DATABASE_URL: z.string(),

  GATEWAY_INTERNAL_SECRET: z.string().min(1),

  USER_SERVICE_URL: z.string().url().default('http://kong:8000'),
  USER_SERVICE_TIMEOUT: z.coerce.number().positive().default(5),

  GMAIL_USER: z.string().email(),
  GMAIL_APP_PASSWORD: z.string().min(1),

  REDIS_HOST: z.string(),
  REDIS_PORT: z.string(),

  /**
   * How long a read notification is kept before the daily sweep deletes it. Unread
   * rows are never pruned, however old: the user has not dealt with them yet, so
   * they are still live inbox content rather than history.
   */
  NOTIFICATION_RETENTION_DAYS: z.coerce.number().int().positive().default(30),
  /**
   * When the sweep runs. Off the hour on purpose — every service that grows a
   * database nightly tends to pick :00, and this shares Redis with BullMQ.
   */
  NOTIFICATION_RETENTION_CRON: z.string().default('17 3 * * *'),

  FRONTEND_URL: z.string(),

  TWILIO_FROM_NUMBER: z.string(),
  TWILIO_ACCOUNT_SID: z.string(),
  TWILIO_AUTH_TOKEN:  z.string()
});

export const env = envSchema.parse(process.env);