import { maintenanceQueue, emailQueue, otpQueue } from '../../queues/definitions';
import {EmailJobPayload, RetentionJobPayload, SMSPayload} from '../../queues/types'
import {env} from '../../config/env'

export async function dispatchEmail(payload: EmailJobPayload) {
  await emailQueue.add('send-email', payload, {
    attempts: 3,
    backoff: { type: 'exponential', delay: 30_000 }, // mirrors default_retry_delay=30
    removeOnComplete: 1000,
    removeOnFail: false, // keep failed jobs for inspection
  });
}

export async function dispatchOtpSms(payload: SMSPayload) {
    await otpQueue.add('otp-dispatch', payload, {
    attempts: 3,
    backoff: { type: 'exponential', delay: 30_000 }, // mirrors default_retry_delay=30
    removeOnComplete: 1000,
    removeOnFail: false, // keep failed jobs for inspection
  })
}

/** Stable scheduler id, so re-registering on every boot updates rather than duplicates. */
export const RETENTION_SCHEDULER_ID = 'notification-retention-sweep';

/**
 * Registers the daily retention sweep as a BullMQ repeatable job.
 *
 * Called on worker start rather than from a deploy script or a hand-run command:
 * the scheduler lives in Redis, so it survives a restart, and `upsertJobScheduler`
 * is keyed on the id, which makes calling this on every boot safe and keeps the
 * schedule correct if the cron or the retention window changes.
 *
 * The sweep reads the window from the environment when it runs, so the payload
 * only carries the cutoff it was scheduled with — recomputed by the job itself if
 * the schedule has drifted.
 */
export async function scheduleRetentionSweep(): Promise<void> {
  await maintenanceQueue.upsertJobScheduler(
    RETENTION_SCHEDULER_ID,
    { pattern: env.NOTIFICATION_RETENTION_CRON },
    {
      name: 'prune-read-notifications',
      data: {
        cutoff: new Date(
          Date.now() - env.NOTIFICATION_RETENTION_DAYS * 24 * 60 * 60 * 1000,
        ).toISOString(),
      } satisfies RetentionJobPayload,
      opts: {
        attempts: 3,
        backoff: { type: 'exponential', delay: 30_000 },
        removeOnComplete: 100,
        removeOnFail: false,
      },
    },
  );
}