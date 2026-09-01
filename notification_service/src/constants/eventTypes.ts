export const NotificationEventType = {
  ACCOUNT_VERIFICATION_REQUESTED:
    "account.verification_requested",

  PASSWORD_RESET_REQUESTED:
    "account.password_reset_requested",

  USER_REGISTERED:
    "account.user_registered",

  EMAIL_CHANGE_REQUESTED: "account.email_change_requested"
} as const;