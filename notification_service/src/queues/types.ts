export interface EmailJobPayload {
  to: string;
  subject: string;
  html: string;
  text?: string;
}

export interface SMSPayload{
  to: string;
  body: string
}

/**
 * Housekeeping rather than a message to a user: which notifications are old
 * enough to prune. Carries no user data, and nothing here is ever rendered.
 */
export interface RetentionJobPayload {
  /** Read notifications older than this are deleted. Unread rows are kept. */
  cutoff: string;
}