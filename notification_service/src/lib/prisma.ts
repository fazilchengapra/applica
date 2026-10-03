import { PrismaPg } from '@prisma/adapter-pg';

import { env } from '../config/env';
import { logger } from './logger';
import { PrismaClient } from '../generated/prisma/client';

/**
 * The notification inbox lives here, in this service's own Postgres, so this is
 * the only client that touches it.
 *
 * Prisma 7 has no query engine, so a driver adapter is mandatory. `PrismaPg`
 * keeps a pool underneath; the pool size is left at the `pg` default because
 * the inbox is not a hot path and a wrong ceiling would only mask a leak.
 */
const adapter = new PrismaPg({ connectionString: env.DATABASE_URL });

export const prisma = new PrismaClient({
  adapter,
  log: env.NODE_ENV === 'development' ? ['warn', 'error'] : ['error'],
});

prisma.$connect().catch((err) => {
  logger.error({ err }, 'prisma_connect_failed');
});

export type { Prisma } from '../generated/prisma/client';
