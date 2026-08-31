import nodemailer, { Transporter } from 'nodemailer';
import { logger } from '../../lib/logger';
import {EmailJobPayload} from '../../queues/types'
import {env} from '../../config/env'

let transporter: Transporter | null = null;

function getTransporter(): Transporter {
  if (transporter) return transporter;
  
  transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
      user: env.GMAIL_USER,
      pass: env.GMAIL_APP_PASSWORD,
    },
  });

  return transporter;
}

export async function sendEmailViaGmail(payload: EmailJobPayload): Promise<void> {
  const transport = getTransporter();

  try {
    const info = await transport.sendMail({
      from: `"Applica" <${process.env.GMAIL_USER}>`,
      to: payload.to,
      subject: payload.subject,
      html: payload.html,
      text: payload.text,
    });

    logger.info({ messageId: info.messageId, to: payload.to }, 'email sent via gmail');
  } catch (err) {
    logger.error({ err, to: payload.to }, 'gmail send failed');
    throw err; // rethrow so BullMQ retry/backoff kicks in
  }
}