import { z } from 'zod';

import { MAX_TYPE_FILTER_LENGTH } from '../../../constants/notificationType';

export const DEFAULT_PAGE_SIZE = 20;
export const MAX_PAGE_SIZE = 100;

const uuidSchema = z.string().uuid('Must be a valid notification id.');

/**
 * A `*` is only meaningful as a trailing wildcard. Anywhere else it would be a
 * literal character that can never match, so it is rejected rather than quietly
 * returning an empty page: a client that meant `account.*` and typed
 * `acc*unt` has a bug, and an empty 200 would hide it.
 *
 * The prefix itself is unconstrained, so a new namespace (`job.*`) filters the
 * moment it exists without this having to be taught about it.
 */
const typeFilterSchema = z
  .string()
  .trim()
  .max(MAX_TYPE_FILTER_LENGTH + 1)
  .refine((value) => {
    const wildcardIndex = value.indexOf('*');
    return wildcardIndex === -1 || wildcardIndex === value.length - 1;
  }, 'A "*" is only supported as a trailing wildcard, e.g. "account.*".');

/**
 * `page` is bounded from below but not above: a page past the end is an empty
 * page with a working `previous` link rather than a 404, because a client
 * rendering an inbox should degrade to "nothing more to load" instead of an
 * error. Only a *malformed* page (non-integer, zero, negative) is a 400.
 */
export const notificationListQuerySchema = z.object({
  unread_only: z
    .enum(['true', 'false'])
    .optional()
    .transform((value) => value === 'true'),
  type: typeFilterSchema.optional(),
  page: z.coerce.number().int().min(1).optional().default(1),
  page_size: z.coerce.number().int().min(1).max(MAX_PAGE_SIZE).optional().default(DEFAULT_PAGE_SIZE),
});

export type NotificationListQuery = z.infer<typeof notificationListQuerySchema>;

export const notificationParamsSchema = z.object({ id: uuidSchema });

export type NotificationParams = z.infer<typeof notificationParamsSchema>;

/** A user id arriving as a path parameter, e.g. from the home BFF. */
export const internalUserIdParamsSchema = z.object({
  userId: z.coerce.number().int().positive().max(Number.MAX_SAFE_INTEGER),
});

export type InternalUserIdParams = z.infer<typeof internalUserIdParamsSchema>;

/**
 * The write side, used by the service-to-service create endpoint. Kept separate
 * from the read schemas because it is the one place a caller supplies `type`, and
 * it is the boundary where an unknown type should be refused.
 */
export const createNotificationBodySchema = z.object({
  userId: z.coerce.number().int().min(1),
  type: z.string().trim().min(1).max(MAX_TYPE_FILTER_LENGTH),
  title: z.string().trim().min(1).max(255),
  body: z.string().max(10_000).default(''),
  // z.json() rather than z.unknown(): the column is jsonb, so a value that
  // cannot be serialised (undefined, a function, a cycle) has to be rejected at
  // the edge instead of failing the insert deep inside Prisma.
  metadata: z.record(z.string(), z.json()).default({}),
});

export type CreateNotificationBody = z.infer<typeof createNotificationBodySchema>;
