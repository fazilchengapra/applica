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