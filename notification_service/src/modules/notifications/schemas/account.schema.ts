import { z } from "zod";
import { BaseEventSchema } from "./envelope.schema";

export const AccountRegistered = BaseEventSchema.extend({
  eventType: z.literal("account.registered"),
  payload: z.object({
    email: z.string().email(),
    displayName: z.string(),
    registrationMethod: z.enum(["email", "google", "phone_otp"]),
  }),
});
    
export const AccountVerificationRequested = BaseEventSchema.extend({
  eventType: z.literal("account.verification_requested"),
  payload: z.object({
    email: z.string().email(),
    verification_link: z.string().url(),
  }),
});

export const AccountEvents = [AccountRegistered, AccountVerificationRequested] as const;