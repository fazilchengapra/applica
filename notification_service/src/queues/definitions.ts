import { Queue } from 'bullmq';
import { bullmqConnection } from '../config/redis';

export const emailQueue = new Queue('email-dispatch', { connection: bullmqConnection });
export const otpQueue = new Queue('otp-dispatch', { connection: bullmqConnection });
export const pushQueue = new Queue('push-dispatch', { connection: bullmqConnection });