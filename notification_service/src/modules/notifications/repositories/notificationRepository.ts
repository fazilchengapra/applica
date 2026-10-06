import type { Notification, Prisma } from '../../../generated/prisma/client';
import { prisma } from '../../../lib/prisma';

export type NotificationRecord = Notification;

type NotificationWhere = Prisma.NotificationWhereInput;

export interface ListNotificationsInput {
  userId: number;
  unreadOnly: boolean;
  archivedOnly: boolean;
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
 * The unread list and the unread count are the reason
 * `idx_user_read_archived_created` exists. Both are `user_id = ? AND
 * read_at IS NULL AND archived_at IS NULL`, which is three equality seeks on that
 * index rather than a scan of the table.
 *
 * `archived_at` is always constrained, in one direction or the other, because the
 * default inbox and the archive are two different views of the same rows and a
 * query that left the column free could not use either index.
 */
function buildWhere({
  userId,
  unreadOnly,
  archivedOnly,
  typeFilter,
}: Omit<ListNotificationsInput, 'skip' | 'take'>): NotificationWhere {
  return {
    userId: userKey(userId),
    ...(unreadOnly ? { readAt: null } : {}),
    ...(archivedOnly ? { archivedAt: { not: null } } : { archivedAt: null }),
    ...buildTypeFilter(typeFilter),
  };
}

/**
 * `id` breaks ties on `created_at`. The column stores microseconds, so ties are
 * rare but not impossible, and an unstable order makes offset pagination skip or
 * repeat a row between two requests.
 *
 * The indexes carry created_at DESC and id DESC to match this ordering, but the
 * sort is not actually eliminated: Postgres treats `archived_at IS NULL` as a
 * filter rather than an equality scan key, so it narrows to the user's rows and
 * sorts that slice in memory. That is tens of microseconds over tens of rows.
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
  input: Pick<ListNotificationsInput, 'userId' | 'unreadOnly' | 'archivedOnly'>,
): Promise<number> {
  return prisma.notification.count({ where: buildWhere(input) });
}

/**
 * Dismissed rows are not unread, whatever their read_at says: a notification the
 * user archived without opening must not keep a badge lit.
 */
export async function countUnread(userId: number): Promise<number> {
  return prisma.notification.count({
    where: { userId: userKey(userId), readAt: null, archivedAt: null },
  });
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

/**
 * `archivedAt: null` is load-bearing, not an optimisation: read-all means "mark
 * everything still in the inbox as seen", and a dismissed notification is no
 * longer in the inbox. Including archived rows here would silently mark a
 * notification the user never opened as read, which is the one thing the
 * read/dismissed distinction exists to prevent.
 */
export async function markAllRead(userId: number, readAt: Date): Promise<number> {
  const result = await prisma.notification.updateMany({
    where: { userId: userKey(userId), readAt: null, archivedAt: null },
    data: { readAt },
  });

  return result.count;
}

/**
 * Archives only a row that is still in the inbox, for the same reason
 * `markReadIfUnread` is conditional: the second attempt matches nothing and
 * leaves the original `archived_at` alone, so a retried request cannot claim the
 * user dismissed it twice or slide the timestamp forward.
 */
export async function archiveIfInInbox(
  userId: number,
  id: string,
  archivedAt: Date,
): Promise<number> {
  const result = await prisma.notification.updateMany({
    where: { id, userId: userKey(userId), archivedAt: null },
    data: { archivedAt },
  });

  return result.count;
}

/**
 * Retention: notifications the user has already dealt with, older than the cutoff,
 * in bounded batches so the daily sweep never holds a long-running transaction or
 * a huge lock set.
 *
 * "Dealt with" is `read_at IS NOT NULL OR archived_at IS NOT NULL` — either
 * endpoint is enough. Keeping only read rows would mean a notification the user
 * dismissed without opening is never pruned, which is a slow unbounded leak for
 * exactly the users who dismiss most aggressively. Rows still unread and in the
 * inbox are kept however old they are: they are live content, not history.
 *
 * The two branches are served by `idx_read_created` and `idx_archived_created`,
 * each of which carries `created_at` for the cutoff range, so Postgres bitmap-ORs
 * two index scans rather than scanning the table.
 *
 * Global by design — the sweep prunes every user's rows, unlike
 * `deleteAllForUser`, which is scoped to one account being deleted.
 */
export async function pruneSettledBefore(cutoff: Date, batchSize: number): Promise<number> {
  const doomed = await prisma.notification.findMany({
    where: {
      createdAt: { lt: cutoff },
      OR: [{ readAt: { not: null } }, { archivedAt: { not: null } }],
    },
    select: { id: true },
    orderBy: { createdAt: 'asc' },
    take: batchSize,
  });

  if (doomed.length === 0) {
    return 0;
  }

  // Scoped to the ids just selected rather than repeating the predicate, so a row
  // that became unsettled between the select and the delete is not deleted by a
  // sweep that no longer has a reason to remove it.
  const result = await prisma.notification.deleteMany({
    where: { id: { in: doomed.map((row) => row.id) } },
  });

  return result.count;
}

/**
 * Account deletion. There is no foreign key to `user_service` — it is a separate
 * database — so nothing cascades and orphaned rows would otherwise keep a deleted
 * account's notification titles, bodies and masked metadata forever.
 *
 * Batched like `pruneSettledBefore`, for the same reason: `deleteMany` has no
 * `take`, so the ids are read a page at a time and then deleted by id. The delete
 * is scoped to those ids so a notification created for the id mid-loop —
 * impossible in practice, since the account is going away — is not silently
 * swallowed into a batch, and so the loop terminates.
 */
export async function deleteAllForUser(userId: number, batchSize: number): Promise<number> {
  let deleted = 0;

  for (;;) {
    const doomed = await prisma.notification.findMany({
      where: { userId: userKey(userId) },
      select: { id: true },
      take: batchSize,
    });

    if (doomed.length === 0) {
      return deleted;
    }

    const result = await prisma.notification.deleteMany({
      where: { id: { in: doomed.map((row) => row.id) } },
    });

    deleted += result.count;
  }
}

export async function deleteOwnedNotification(userId: number, id: string): Promise<number> {
  const result = await prisma.notification.deleteMany({
    where: { id, userId: userKey(userId) },
  });

  return result.count;
}

export interface CreateNotificationInput {
  userId: number;
  type: string;
  title: string;
  body: string;
  metadata: Prisma.InputJsonValue;
  dedupeKey?: string;
}

/**
 * Whether the row was inserted or was already there. The two cases are
 * indistinguishable in the returned record — a retry has to hand back the
 * original notification so the producer sees a stable id — but the caller
 * answers 201 for the first and 200 for the second.
 */
export type CreateNotificationOutcome =
  | { deduplicated: false; notification: NotificationRecord }
  | { deduplicated: true; notification: NotificationRecord };

/**
 * `skipDuplicates` compiles to `ON CONFLICT DO NOTHING`, and `createManyAndReturn`
 * hands back only the rows that were actually inserted. An empty result therefore
 * means the `(user_id, dedupe_key)` index already holds this event, which is what
 * makes a retried producer request converge on one row instead of two.
 *
 * Without a `dedupeKey` there is no unique constraint in play besides the primary
 * key, which this call generates fresh, so the insert cannot be skipped and the
 * read-back is never reached.
 */
export async function createNotification(
  input: CreateNotificationInput,
): Promise<CreateNotificationOutcome> {
  const userIdKey = userKey(input.userId);
  const row = { ...input, userId: userIdKey };

  // Two attempts rather than one: the conflicting row can be purged by the
  // retention job or an account deletion between the skipped insert and the
  // read-back, and retrying turns that race into a fresh insert rather than a 500.
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const inserted = await prisma.notification.createManyAndReturn({
      data: [row],
      skipDuplicates: true,
    });

    if (inserted.length > 0) {
      return { deduplicated: false, notification: inserted[0] };
    }

    const existing = await prisma.notification.findUnique({
      where: { userId_dedupeKey: { userId: userIdKey, dedupeKey: input.dedupeKey as string } },
    });

    if (existing) {
      return { deduplicated: true, notification: existing };
    }
  }

  throw new Error('Notification dedupe read-back found no row after a skipped insert');
}
