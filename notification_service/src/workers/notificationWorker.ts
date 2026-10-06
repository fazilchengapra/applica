import { Worker } from 'bullmq';
import { bullmqConnection } from '../config/redis';
import { sendSms} from '../providers/phone/phone'
import { sendEmailViaGmail } from '../providers/email/gmail';
import { pruneSettledNotifications } from '../modules/notifications/services/retentionService';
import { scheduleRetentionSweep } from '../modules/notifications/service';
import { logger } from '../lib/logger';
import { print } from 'ioredis';

const emailWorker = new Worker(
  'email-dispatch',
  async (job) => {
    await sendEmailViaGmail(job.data);
  },
  { connection: bullmqConnection, concurrency: 10 }
);

const otpWorker = new Worker(
  'otp-dispatch',
  async (job) => {
    await sendSms(job.data);
  },
  { connection: bullmqConnection, concurrency: 10 }
);

/**
 * Concurrency 1 on purpose: the sweep deletes in batches and a second copy running
 * alongside it would duplicate the scan for no benefit. Two sweeps overlapping is
 * still harmless — the deletes are idempotent — which is what the BullMQ lock and
 * the short batch loop between them rely on.
 */
const retentionWorker = new Worker(
  'maintenance-dispatch',
  async (job) => {
    if (job.name !== 'prune-read-notifications') {
      logger.warn({ jobName: job.name }, 'unknown maintenance job ignored');
      return;
    }

    await pruneSettledNotifications();
  },
  { connection: bullmqConnection, concurrency: 1 }
);

// Registered here rather than in a deploy step: the schedule lives in Redis, so it
// survives restarts, and upsertJobScheduler is keyed on the id, making a boot-time
// call idempotent and the single place the retention window is wired up.
scheduleRetentionSweep().catch((err) => {
  logger.error({ err }, 'retention_schedule_failed');
});

emailWorker.on('failed', (job, err) => {
  logger.error({ jobId: job?.id, err }, 'email job exhausted retries');
});

otpWorker.on('failed', (job, err) => {
  logger.error({ jobId: job?.id, phone: job?.data?.phone, err }, 'OTP job exhausted retries');
});

retentionWorker.on('failed', (job, err) => {
  logger.error({ jobId: job?.id, jobName: job?.name, err }, 'retention sweep exhausted retries');
});

process.on('SIGTERM', async () => {
  await Promise.all([emailWorker.close(), otpWorker.close(), retentionWorker.close()]);
  process.exit(0);
});