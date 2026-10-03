import { KNOWN_NOTIFICATION_TYPES } from '../../../constants/notificationType';
import { logger } from '../../../lib/logger';
import type { Prisma } from '../../../generated/prisma/client';
import type { NotificationRecord } from '../repositories/notificationRepository';
import * as repository from '../repositories/notificationRepository';
import { emitToUser } from '../../realtime/socket.emitter';
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
  };
}

/**
 * `next`/`previous` carry the same page size, not the current page number, so
 * following `next` walks the list instead of re-requesting it.
 */
function buildPageLink(baseUrl: string | undefined, query: NotificationListQuery, page: number): string {
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

  return `${url.pathname}${url.search}`;
}

export async function listNotifications(
  userId: number,
  query: NotificationListQuery,
  baseUrl?: string,
): Promise<PaginatedNotifications> {
  const filter = { userId, unreadOnly: query.unread_only, typeFilter: query.type };
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
  return { updated: await repository.markAllRead(userId, new Date()) };
}

export async function remove(userId: number, id: string): Promise<void> {
  const deleted = await repository.deleteOwnedNotification(userId, id);

  if (deleted === 0) {
    throw new NotificationNotFoundError();
  }
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
export async function create(input: {
  userId: number;
  type: string;
  title: string;
  body: string;
  metadata: Prisma.InputJsonObject;
}): Promise<NotificationView> {
  if (!KNOWN_NOTIFICATION_TYPES.includes(input.type)) {
    throw new UnknownNotificationTypeError(input.type);
  }

  const created = await repository.createNotification({
    userId: input.userId,
    type: input.type,
    title: input.title,
    body: input.body,
    metadata: input.metadata,
  });

  try {
    emitToUser(String(input.userId), 'notification.created', toView(created));
  } catch (err) {
    logger.error({ err, notificationId: created.id, userId: input.userId }, 'notification_push_failed');
  }

  return toView(created);
}
