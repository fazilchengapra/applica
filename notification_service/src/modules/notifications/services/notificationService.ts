import { KNOWN_NOTIFICATION_TYPES } from '../../../constants/notificationType';
import { logger } from '../../../lib/logger';
import type { Prisma } from '../../../generated/prisma/client';
import type { NotificationRecord } from '../repositories/notificationRepository';
import * as repository from '../repositories/notificationRepository';
import { publishNotificationCreated } from '../../realtime/notificationEvent';
import type { NotificationListQuery } from '../schemas/notification.schema';

export class NotificationNotFoundError extends Error {
  constructor() {
    super('Notification not found.');
    this.name = 'NotificationNotFoundError';
  }
}

export class UnknownNotificationTypeError extends Error {
  constructor(type: string) {
    super(`Unknown notification type: ${type}`);
    this.name = 'UnknownNotificationTypeError';
  }
}

/** The wire shape, kept separate from the Prisma row so a column rename cannot change the API. */
export interface NotificationView {
  id: string;
  type: string;
  title: string;
  body: string;
  metadata: unknown;
  read_at: string | null;
  created_at: string;
  archived_at: string | null;
}

export interface PaginatedNotifications {
  count: number;
  next: string | null;
  previous: string | null;
  results: NotificationView[];
}

function toView(notification: NotificationRecord): NotificationView {
  return {
    id: notification.id,
    type: notification.type,
    title: notification.title,
    body: notification.body,
    metadata: notification.metadata,
    read_at: notification.readAt ? notification.readAt.toISOString() : null,
    created_at: notification.createdAt.toISOString(),
    archived_at: notification.archivedAt ? notification.archivedAt.toISOString() : null,
  };
}

/**
 * `next`/`previous` carry the same page size, not the current page number, so
 * following `next` walks the list instead of re-requesting it.
 */
function buildPageLink(
  baseUrl: string | undefined,
  query: NotificationListQuery,
  page: number,
): string {
  if (!baseUrl) {
    return '';
  }

  const url = new URL(baseUrl, 'http://placeholder');
  url.searchParams.set('page', String(page));
  url.searchParams.set('page_size', String(query.page_size));

  if (query.unread_only) {
    url.searchParams.set('unread_only', 'true');
  }

  if (query.type) {
    url.searchParams.set('type', query.type);
  }

  // An archive page has to keep saying so, or following `next` silently walks
  // back into the inbox.
  if (query.archived) {
    url.searchParams.set('archived', 'true');
  }

  return `${url.pathname}${url.search}`;
}

export async function listNotifications(
  userId: number,
  query: NotificationListQuery,
  baseUrl?: string,
): Promise<PaginatedNotifications> {
  const filter = {
    userId,
    unreadOnly: query.unread_only,
    archivedOnly: query.archived,
    typeFilter: query.type,
  };
  const count = await repository.countNotifications(filter);

  const rows = await repository.listNotifications({
    ...filter,
    skip: (query.page - 1) * query.page_size,
    take: query.page_size,
  });

  const totalPages = count === 0 ? 0 : Math.ceil(count / query.page_size);

  return {
    count,
    next: query.page < totalPages ? buildPageLink(baseUrl, query, query.page + 1) : null,
    // Clamped to the last real page: a client that overshoots to page 99 of a
    // 1-page list follows `previous` once to get back, instead of having to
    // walk back one page at a time.
    previous:
      query.page > 1
        ? buildPageLink(baseUrl, query, Math.min(query.page - 1, Math.max(totalPages, 1)))
        : null,
    results: rows.map(toView),
  };
}

export async function getUnreadCount(userId: number): Promise<{ unread: number }> {
  return { unread: await repository.countUnread(userId) };
}

export async function markRead(userId: number, id: string): Promise<NotificationView> {
  const existing = await repository.findOwnedNotification(userId, id);

  if (!existing) {
    throw new NotificationNotFoundError();
  }

  // Only write when it is still unread, so a retried request keeps the first
  // read_at instead of overwriting it.
  await repository.markReadIfUnread(userId, id, new Date());

  const updated = await repository.findOwnedNotification(userId, id);

  if (!updated) {
    // Deleted between the read and the re-read; nothing left to report.
    throw new NotificationNotFoundError();
  }

  return toView(updated);
}

export async function markAllRead(userId: number): Promise<{ updated: number }> {
  // One UPDATE whose row count is exactly the number that were still unread, so
  // a notification created mid-call is neither missed nor silently counted.
  // Archived rows are left alone: dismissed is not unread.
  return { updated: await repository.markAllRead(userId, new Date()) };
}

/**
 * Dismisses a notification out of the inbox without claiming it was read. Read and
 * dismissed are different facts, so this never touches `read_at` and archiving an
 * unread row does not silently mark it seen.
 */
export async function archive(userId: number, id: string): Promise<NotificationView> {
  const existing = await repository.findOwnedNotification(userId, id);

  if (!existing) {
    throw new NotificationNotFoundError();
  }

  // Conditional write, so a retried request keeps the first archived_at.
  await repository.archiveIfInInbox(userId, id, new Date());

  const updated = await repository.findOwnedNotification(userId, id);

  if (!updated) {
    // Deleted between the archive and the re-read; nothing left to report.
    throw new NotificationNotFoundError();
  }

  return toView(updated);
}

export async function remove(userId: number, id: string): Promise<void> {
  const deleted = await repository.deleteOwnedNotification(userId, id);

  if (deleted === 0) {
    throw new NotificationNotFoundError();
  }
}

/** Rows per statement in the two bulk deletes, so neither holds a huge lock set. */
const BULK_DELETE_BATCH_SIZE = 500;

/**
 * Drops every notification belonging to a user. Called when the account is
 * deleted: there is no foreign key to cascade from, because the users live in a
 * different database, so without this the deleted account's titles, bodies and
 * masked metadata would sit here indefinitely.
 */
export async function purgeForUser(userId: number): Promise<{ deleted: number }> {
  const deleted = await repository.deleteAllForUser(userId, BULK_DELETE_BATCH_SIZE);

  if (deleted > 0) {
    logger.info({ userId, deleted }, 'notifications_purged');
  }

  return { deleted };
}

export interface CreateNotificationCommand {
  userId: number;
  type: string;
  title: string;
  body: string;
  metadata: Prisma.InputJsonObject;
  dedupeKey?: string;
}

export interface CreateNotificationResult {
  notification: NotificationView;
  deduplicated: boolean;
}

/**
 * The only write path. Real-time delivery happens here rather than in the
 * caller so that a row and its push cannot disagree: the socket emit needs the
 * generated id and created_at, which only exist after the insert.
 *
 * A failed push is logged and swallowed. The notification is already durable,
 * and the client can always recover it by listing the inbox; failing the request
 * instead would make the caller believe nothing was created.
 */
export async function create(input: CreateNotificationCommand): Promise<CreateNotificationResult> {
  if (!KNOWN_NOTIFICATION_TYPES.includes(input.type)) {
    throw new UnknownNotificationTypeError(input.type);
  }

  const outcome = await repository.createNotification(input);
  const view = toView(outcome.notification);

  // Only a genuine insert is a "created" event. A deduplicated retry is the same
  // row the client has already been told about, so re-announcing it would replay a
  // notification the client already holds. A client that missed the original push
  // recovers by listing the inbox, which is the path it already relies on.
  if (!outcome.deduplicated) {
    try {
      // Announced over Redis rather than emitted directly: the socket registry is
      // per-process, so a direct emit would only reach users connected to *this*
      // instance. Every instance is subscribed, including this one.
      await publishNotificationCreated(String(input.userId), view);
    } catch (err) {
      // The row is already durable. Failing the request here would tell the
      // producer nothing was created, which is worse than a client that has to
      // discover the notification by listing the inbox.
      logger.error(
        { err, notificationId: view.id, userId: input.userId },
        'notification_publish_failed',
      );
    }
  }

  return { notification: view, deduplicated: outcome.deduplicated };
}
