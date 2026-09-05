import { z } from "zod";
import { BaseEventSchema } from "./envelope.schema";
import {NotificationEventType} from '../../../constants/eventTypes'

export const AccountRegistered = BaseEventSchema.extend({
  eventType: z.literal(NotificationEventType.USER_REGISTERED),
  payload: z.object({
    email: z.string().email(),
    registration_method: z.enum(["email", "google", "phone_otp"]),
  }),
});
    
export const AccountVerificationRequested = BaseEventSchema.  extend({
  eventType: z.enum([NotificationEventType.ACCOUNT_VERIFICATION_REQUESTED, NotificationEventType.EMAIL_CHANGE_REQUESTED]),
  payload: z.object({
    email: z.string().email(),
    verification_link: z.string().url(),
  }),
});

export const EmailChanged = BaseEventSchema.extend({
  eventType: z.literal(NotificationEventType.EMAIL_CHANGED),
  payload: z.object({
    email: z.string().email(),
    old_email: z.string()
  }),
});

export const PasswordChanged = BaseEventSchema.extend({
    eventType: z.literal(NotificationEventType.PASSWORD_CHANGED),
    payload: z.object({
      email: z.string().email(),
  }),
})

export const ForgotPasswordRequested = BaseEventSchema.extend({
    eventType: z.literal(NotificationEventType.FORGOT_PASSWORD_REQ),
    payload: z.object({
      email: z.string().email(),
      raw_token: z.string().url(),
  }),
})

export const AccountEvents = [AccountRegistered, AccountVerificationRequested, EmailChanged, PasswordChanged, ForgotPasswordRequested] as const;