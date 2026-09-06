import { emailQueue, otpQueue } from '../../queues/definitions';
import {EmailJobPayload, SMSPayload} from '../../queues/types'

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