import { Worker } from 'bullmq';
import { bullmqConnection } from '../config/redis';
import { sendSms} from '../providers/phone/phone'
import { sendEmailViaGmail } from '../providers/email/gmail';
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

emailWorker.on('failed', (job, err) => {
  logger.error({ jobId: job?.id, err }, 'email job exhausted retries');
});

otpWorker.on('failed', (job, err) => {
  logger.error({ jobId: job?.id, phone: job?.data?.phone, err }, 'OTP job exhausted retries');
});

process.on('SIGTERM', async () => {
  await Promise.all([emailWorker.close(), otpWorker.close()]);
  process.exit(0);
});