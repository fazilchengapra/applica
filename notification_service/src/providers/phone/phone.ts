import twilio from 'twilio';
import {env} from '../../config/env'
import {SMSPayload} from '../../queues/types'

const client = twilio(env.TWILIO_ACCOUNT_SID, env.TWILIO_AUTH_TOKEN);

export async function sendSms(data: SMSPayload) {
  return client.messages.create({
    to: data.to,
    from: env.TWILIO_FROM_NUMBER,
    body: data.body,
  });
}