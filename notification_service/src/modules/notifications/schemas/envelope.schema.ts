import { z } from "zod";

export const BaseEventSchema = z.object({
  eventId: z.string().uuid(),
  eventType: z.string(),
  userId: z.string().uuid(),
  occurredAt: z.string().datetime(),
  source: z.string(),
});