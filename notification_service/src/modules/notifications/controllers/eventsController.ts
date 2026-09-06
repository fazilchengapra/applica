import { Request, Response } from "express";
import { date, z } from "zod";
import { NotificationEvent } from "../schemas";
import { dispatchEmail, dispatchOtpSms } from "../service";
import { logger } from "../../../lib/logger";
import {NotificationEventType} from '../../../constants/eventTypes'

// templates (email)
import {createVerificationEmailPayload} from '../templates/email/verificationEmail'
import {createRegistrationCompletedEmailPayload} from '../templates/email/registeredEmail'
import {createChangeEmailPayload} from '../templates/email/changeEmail'
import {createEmailChangedConfirmedPayload} from '../templates/email/emailChangedConfirm'
import {createPasswordChangedEmailPayload} from '../templates/email/passwordChangedEamil'
import {createForgotPasswordEmailPayload} from '../templates/email/forgotPassword'
import {createPasswordResetCompletedEmailPayload} from '../templates/email/passwordResetCompeted'

// templates (phone)
import {createLoginOtpSms, createPhoneVerificationOtpSms} from '../templates/phone/phoneTemplates'

// helper
import {get_forgot_pass_url} from '../helpers/make_urls'
import { da } from "zod/v4/locales";

const log = logger.child({ module: "notificationController" });

export async function handleIncomingEvent(req: Request, res: Response): Promise<Response> {
  console.log(req.body);
  const parsed = NotificationEvent.safeParse(req.body);

  

  if (!parsed.success) {
    log.error({ errors: z.flattenError(parsed.error) }, "invalid notification event payload");
    return res.status(400).json({
      error: "Invalid event payload",
      details: z.flattenError(parsed.error),
    });
  }

  const event = parsed.data;
  log.info({ eventId: event.eventId, eventType: event.eventType }, "notification event received");

  try {
    switch (event.eventType) {
        case NotificationEventType.ACCOUNT_VERIFICATION_REQUESTED: {
          const data = event.payload
          const payload = createVerificationEmailPayload(data.email, data.verification_link)

          await dispatchEmail(payload);
          break;
        }

        case NotificationEventType.USER_REGISTERED:{
          const data = event.payload
          const payload = createRegistrationCompletedEmailPayload(data.email)

          await dispatchEmail(payload)
          break
        }

        case NotificationEventType.EMAIL_CHANGE_REQUESTED:{
          const data = event.payload
          const payload = createChangeEmailPayload(data.email, data.verification_link)

          await dispatchEmail(payload)
          break
        }

        case NotificationEventType.EMAIL_CHANGED:{
          const data = event.payload
          const payload = createEmailChangedConfirmedPayload(data.email, data.old_email)

          await dispatchEmail(payload)
          break
        }

        case NotificationEventType.PASSWORD_CHANGED:{
          const data = event.payload
          const payload = createPasswordChangedEmailPayload(data.email)

          await dispatchEmail(payload)
          break
        }

        case NotificationEventType.FORGOT_PASSWORD_REQ:{
          const data = event.payload
          const url = get_forgot_pass_url(data.raw_token)
          const payload = createForgotPasswordEmailPayload(data.email, url)

          await dispatchEmail(payload)
          break
        }

        case NotificationEventType.PASSWORD_RESET_COMPETED:{
          const data = event.payload
          const payload = createPasswordResetCompletedEmailPayload(data.email)

          await dispatchEmail(payload)
          break
        }

        case NotificationEventType.PHONE_VERIFICATION_OTP_REQUESTED:{
          const data = event.payload
          const payload = createPhoneVerificationOtpSms(data.raw_otp, data.phone_number)

          await dispatchOtpSms(payload)
          break
        }

        case NotificationEventType.LOGIN_OTP_REQUESTED:{
          const data = event.payload
          const payload = createLoginOtpSms(data.raw_otp, data.phone_number)

          await dispatchOtpSms(payload)
          break
        }
}
    return res.status(200).json({
      status: "accepted",
      eventId: event.eventId,
      eventType: event.eventType,
    });
  } catch (err) {
    log.error({ err, eventId: event.eventId, eventType: event.eventType }, "failed to process event");
    return res.status(500).json({
      error: "Failed to process event",
      eventId: event.eventId,
    });
  }
}