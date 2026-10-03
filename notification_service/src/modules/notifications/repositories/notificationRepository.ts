import type { Notification, Prisma } from '../../../generated/prisma/client';
import { prisma } from '../../../lib/prisma';

export type NotificationRecord = Notification;

type NotificationWhere = Prisma.NotificationWhereInput;

export interface ListNotificationsInput {
  userId: number;
  unreadOnly: boolean;
  typeFilter?: string;
  skip: number;
  take: number;
}

/**
 * `user_id` is a bigint column, so Prisma wants a bigint in the query while the
 * user id arrives from Kong's header as a plain number. Converting here keeps
 * the bigint out of the service and controller types — and therefore out of
 * anything that has to be JSON-serialised.
 */
function userKey(userId: number): bigint {
  return BigInt(userId);
}

/**
 * `account.*` selects a namespace, a bare value selects exactly one type, and a
 * bare `*` (or no filter at all) means "any type". Only the first two constrain
 * the column.
 */
function buildTypeFilter(typeFilter?: string): NotificationWhere {
  if (!typeFilter || typeFilter === '*') {
    return {};
  }

  if (typeFilter.endsWith('*')) {
    return { type: { startsWith: typeFilter.slice(0, -1) } };
  }

  return { type: typeFilter };
}

/**
 * The unread list and the unread count are the reason `idx_user_read_created`
 * exists. Both are `user_id = ? AND read_at IS NULL`, which is a seek on that
 * index rather than a scan of the table.
 */
function buildWhere({
  userId,
  unreadOnly,
  typeFilter,
}: Omit<ListNotificationsInput, 'skip' | 'take'>): NotificationWhere {
  return {
    userId: userKey(userId),
    ...(unreadOnly ? { readAt: null } : {}),
    ...buildTypeFilter(typeFilter),
  };
}

/**
 * `id` breaks ties on `created_at`. The column stores microseconds, so ties are
 * rare but not impossible, and an unstable order makes offset pagination skip or
 * repeat a row between two requests. The cost is a sort over one page-sized
 * slice of the user's own rows; the index still does the narrowing, and it
 * already carries created_at DESC for the primary ordering.
 */
export async function listNotifications(input: ListNotificationsInput): Promise<NotificationRecord[]> {
  return prisma.notification.findMany({
    where: buildWhere(input),
    orderBy: [{ createdAt: 'desc' }, { id: 'desc' }],
    skip: input.skip,
    take: input.take,
  });
}

export async function countNotifications(
  input: Pick<ListNotificationsInput, 'userId' | 'unreadOnly' | 'typeFilter'>,
): Promise<number> {
  return prisma.notification.count({ where: buildWhere(input) });
}

export async function countUnread(userId: number): Promise<number> {
  return prisma.notification.count({ where: { userId: userKey(userId), readAt: null } });
}

/**
 * Ownership is part of the lookup, not a check afterwards: a notification
 * belonging to another user is then indistinguishable from one that never
 * existed, and returning `null` for both is what stops the endpoint from
 * confirming that somebody else's notification id is real.
 */
export async function findOwnedNotification(
  userId: number,
  id: string,
): Promise<NotificationRecord | null> {
  return prisma.notification.findFirst({ where: { id, userId: userKey(userId) } });
}

/**
 * Marks one notification read, but only if it is currently unread. Encoding the
 * condition in the UPDATE is what makes a retry safe: the second attempt
 * matches no rows and leaves the original `read_at` alone, so re-reading cannot
 * claim the user looked at it twice.
 */
export async function markReadIfUnread(userId: number, id: string, readAt: Date): Promise<number> {
  const result = await prisma.notification.updateMany({
    where: { id, userId: userKey(userId), readAt: null },
    data: { readAt },
  });

  return result.count;
}

export async function markAllRead(userId: number, readAt: Date): Promise<number> {
  const result = await prisma.notification.updateMany({
    where: { userId: userKey(userId), readAt: null },
    data: { readAt },
  });

  return result.count;
}

export async function deleteOwnedNotification(userId: number, id: string): Promise<number> {
  const result = await prisma.notification.deleteMany({
    where: { id, userId: userKey(userId) },
  });

  return result.count;
}

export async function createNotification(data: {
  userId: number;
  type: string;
  title: string;
  body: string;
  metadata: Prisma.InputJsonValue;
}): Promise<NotificationRecord> {
  return prisma.notification.create({ data: { ...data, userId: userKey(data.userId) } });
}
