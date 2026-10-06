import { env } from '../../../config/env';
import { logger } from '../../../lib/logger';
import * as repository from '../repositories/notificationRepository';

/**
 * Rows per DELETE. Small enough that no single statement holds a lock set worth
 * noticing, large enough that a normal day's prune is one round trip.
 */
const DELETE_BATCH_SIZE = 500;

/** Stops the loop if the table is somehow far larger than the cutoff suggests. */
const MAX_BATCHES_PER_SWEEP = 100;

/**
 * Deletes notifications the user has already dealt with — read or dismissed —
 * once they are older than the retention window.
 *
 * Rows still unread and in the inbox are never touched: they are live content, not
 * history, however old they are.
 *
 * Batched and looped rather than issued as one DELETE, because a single
 * `DELETE ... WHERE created_at < now() - interval` over a large table takes a lock
 * set that grows with the table and bloats WAL in one transaction.
 */
export async function pruneSettledNotifications(now: Date = new Date()): Promise<{ deleted: number }> {
  const cutoff = new Date(now.getTime() - env.NOTIFICATION_RETENTION_DAYS * 24 * 60 * 60 * 1000);

  let deleted = 0;

  for (let batch = 0; batch < MAX_BATCHES_PER_SWEEP; batch += 1) {
    const count = await repository.pruneSettledBefore(cutoff, DELETE_BATCH_SIZE);

    deleted += count;

    // A short batch means there were fewer matches than the batch size, so there is
    // nothing left to collect.
    if (count < DELETE_BATCH_SIZE) {
      break;
    }
  }

  if (deleted > 0) {
    logger.info(
      { deleted, cutoff: cutoff.toISOString(), retentionDays: env.NOTIFICATION_RETENTION_DAYS },
      'retention_sweep_complete',
    );
  }

  return { deleted };
}