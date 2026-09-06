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
      raw_token: z.string(),
      email: z.string().email(),
  }),
})

export const PASSWORD_REST_COMPETED = BaseEventSchema.extend({
    eventType: z.literal(NotificationEventType.PASSWORD_RESET_COMPETED),
    payload: z.object({
      email: z.string().email(),
  }),
})

export const LOGIN_OTP_REQUESTED = BaseEventSchema.extend({
    eventType: z.literal(NotificationEventType.LOGIN_OTP_REQUESTED),
    payload: z.object({
      phone_number: z.string().min(10).max(20),
      raw_otp: z.string().min(6).max(6),
  }),
})

export const PHONE_VERIFICATION_OTP_REQUESTED = BaseEventSchema.extend({
    eventType: z.literal(NotificationEventType.PHONE_VERIFICATION_OTP_REQUESTED),
    payload: z.object({
      phone_number: z.string().min(10).max(20),
      raw_otp: z.string().min(6).max(6),
  }),
})

export const AccountEvents = [
  AccountRegistered,
  AccountVerificationRequested, 
  EmailChanged, PasswordChanged, 
  ForgotPasswordRequested, 
  PASSWORD_REST_COMPETED, 
  LOGIN_OTP_REQUESTED,
  PHONE_VERIFICATION_OTP_REQUESTED
] as const;