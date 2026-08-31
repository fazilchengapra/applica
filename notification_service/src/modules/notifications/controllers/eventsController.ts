import { Request, Response } from "express";
import { z } from "zod";
import { NotificationEvent } from "../schemas";
import { dispatchEmail } from "../service";
import { logger } from "../../../lib/logger";

const log = logger.child({ module: "notificationController" });

export async function handleIncomingEvent(req: Request, res: Response): Promise<Response> {
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
        case "account.verification_requested": {
            const payload = {
            to: event.payload.email,
            subject: "Account Verification",
            html: "",
            text: `Your verification link is ${event.payload.verificationLink}`,
            };

            await dispatchEmail(payload);
            break;
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