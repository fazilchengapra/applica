import { Queue } from 'bullmq';
import { bullmqConnection } from '../config/redis';

export const emailQueue = new Queue('email-dispatch', { connection: bullmqConnection });
export const otpQueue = new Queue('otp-dispatch', { connection: bullmqConnection });
export const pushQueue = new Queue('push-dispatch', { connection: bullmqConnection });

/**
 * Housekeeping jobs (currently just the retention sweep). Separate from the
 * message queues so a slow or failing sweep cannot occupy a slot that an OTP
 * delivery needs.
 */
export const maintenanceQueue = new Queue('maintenance-dispatch', { connection: bullmqConnection });