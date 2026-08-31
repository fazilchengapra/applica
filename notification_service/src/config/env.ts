import 'dotenv/config';
import { z } from 'zod';

const envSchema = z.object({
  PORT: z.coerce.number().default(3002),
  NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),

  DATABASE_URL: z.string(),

  GMAIL_USER: z.string().email(),
  GMAIL_APP_PASSWORD: z.string().min(1),

  REDIS_HOST: z.string(),
  REDIS_PORT: z.string()
});

export const env = envSchema.parse(process.env);