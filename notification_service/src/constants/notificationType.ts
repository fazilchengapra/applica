/**
 * Notification types, mirroring `user_service`'s `NotificationType` choices.
 *
 * The two lists have to agree: this service stores `type` as free text, so a
 * value user_service invents is silently accepted here and then unfilterable
 * and unrecognisable to a client. `assertKnownType` is what keeps them honest.
 *
 * Every type currently lives in the `account.` namespace, which is why the list
 * filter accepts a trailing `*` (`type=account.*`) to select a whole namespace
 * rather than enumerating its members.
 */
export const NotificationType = {
  EMAIL_CHANGE_REQ: 'account.email_change_requested',
  EMAIL_CHANGED: 'account.email_changed',
  EMAIL_VERIFIED: 'account.email_verified',

  PASSWORD_CHANGED: 'account.password_changed',
  FORGOT_PASSWORD_REQ: 'account.forgot_password_req',
  PASSWORD_RESET_COMPLETED: 'account.password_reset_completed',

  PHONE_CHANGED: 'account.phone_changed',
  PHONE_VERIFIED: 'account.phone_verified',

  SMS_LOGIN_OTP: 'account.sms_login_otp',
  PHONE_VERIFICATION_OTP_REQUEST: 'account.sms_verification_otp',
  CHANGE_PHONE_NUMBER_REQUEST: 'account.changed_phone_number_req',

  WELCOME: 'account.register',
  ACCOUNT_VERIFICATION_REQ: 'account.verification_requested',
  REGISTERED: 'account.user_registered',
} as const;

export type NotificationTypeValue = (typeof NotificationType)[keyof typeof NotificationType];

export const KNOWN_NOTIFICATION_TYPES: readonly string[] = Object.values(NotificationType);

/** The namespace every known type shares, used as the documented `account.*` filter. */
export const TYPE_NAMESPACE_PREFIX = 'account.';

/** Matches the `type` column width; a filter adds at most a trailing `*`. */
export const MAX_TYPE_FILTER_LENGTH = 64;
