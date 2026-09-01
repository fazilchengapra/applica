import { z } from "zod";

export const BaseEventSchema = z.object({
  eventId: z.string().uuid(),
  eventType: z.string(),
  userId: z.string(),
  occurredAt: z.string().datetime({offset:true}),
  source: z.string(),
});