import pino from 'pino';

const isProduction = process.env.NODE_ENV === 'production';

export const logger = pino({
  level: process.env.LOG_LEVEL ?? (isProduction ? 'info' : 'debug'),

  // Pretty, colorized output locally; structured JSON in prod (for CloudWatch etc.)
  transport: isProduction
    ? undefined
    : {
        target: 'pino-pretty',
        options: {
          colorize: true,
          translateTime: 'HH:MM:ss',
          ignore: 'pid,hostname',
        },
      },

  base: {
    service: 'notification_service',
  },

  // Redact sensitive fields globally — important given OTPs / tokens pass through here
  redact: {
    paths: [
      'payload.otp',
      'payload.password',
      'payload.token',
      '*.password',
      '*.otp',
      'req.headers.authorization',
    ],
    censor: '[REDACTED]',
  },
});