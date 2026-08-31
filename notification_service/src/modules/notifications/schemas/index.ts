import { z } from "zod";
import { AccountEvents } from "./account.schema";

export const NotificationEvent = z.discriminatedUnion("eventType", [
  ...AccountEvents,
]);

export type NotificationEvent = z.infer<typeof NotificationEvent>;