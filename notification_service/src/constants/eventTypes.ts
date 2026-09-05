export const NotificationEventType = {
  ACCOUNT_VERIFICATION_REQUESTED:
    "account.verification_requested",

  PASSWORD_RESET_REQUESTED:
    "account.password_reset_requested",

  USER_REGISTERED:
    "account.user_registered",

  EMAIL_CHANGE_REQUESTED: "account.email_change_requested",
  EMAIL_CHANGED: "account.email_changed",

  PASSWORD_CHANGED: 'account.password_changed',
  FORGOT_PASSWORD_REQ: 'account.forgot_password_req'
} as const;