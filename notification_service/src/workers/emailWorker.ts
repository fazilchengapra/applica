import { Worker } from 'bullmq';
import { bullmqConnection } from '../config/redis';
import { sendEmailViaGmail } from '../providers/email/gmail';
import { logger } from '../lib/logger';

const worker = new Worker(
  'email-dispatch',
  async (job) => {
    await sendEmailViaGmail(job.data);
  },
  { connection: bullmqConnection, concurrency: 10 }
);

worker.on('failed', (job, err) => {
  logger.error({ jobId: job?.id, err }, 'email job exhausted retries');
});

process.on('SIGTERM', async () => {
  await worker.close();
  process.exit(0);
});