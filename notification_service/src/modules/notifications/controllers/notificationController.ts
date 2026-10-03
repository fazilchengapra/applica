import type { Request, Response } from 'express';
import { z } from 'zod';

import { logger } from '../../../lib/logger';
import {
  createNotificationBodySchema,
  internalUserIdParamsSchema,
  notificationListQuerySchema,
  notificationParamsSchema,
} from '../schemas/notification.schema';
import * as notificationService from '../services/notificationService';

const log = logger.child({ module: 'notificationController' });

/**
 * Validation failures answer 400 with the field errors rather than DRF's flat
 * `{"detail": "..."}`; a client that sends `page_size=0` needs to know *which*
 * parameter was wrong.
 */
function badRequest(res: Response, error: z.ZodError): Response {
  return res.status(400).json({
    error: 'Invalid request',
    details: z.flattenError(error),
  });
}

export async function listNotifications(req: Request, res: Response): Promise<Response> {
  const parsed = notificationListQuerySchema.safeParse(req.query);

  if (!parsed.success) {
    return badRequest(res, parsed.error);
  }

  const page = await notificationService.listNotifications(
    res.locals.userId,
    parsed.data,
    req.originalUrl,
  );

  return res.status(200).json(page);
}

export async function getUnreadCount(_req: Request, res: Response): Promise<Response> {
  return res.status(200).json(await notificationService.getUnreadCount(res.locals.userId));
}

export async function markRead(req: Request, res: Response): Promise<Response> {
  const params = notificationParamsSchema.safeParse(req.params);

  if (!params.success) {
    return badRequest(res, params.error);
  }

  try {
    return res.status(200).json(await notificationService.markRead(res.locals.userId, params.data.id));
  } catch (err) {
    if (err instanceof notificationService.NotificationNotFoundError) {
      return res.status(404).json({ detail: err.message });
    }
    throw err;
  }
}

export async function markAllRead(_req: Request, res: Response): Promise<Response> {
  return res.status(200).json(await notificationService.markAllRead(res.locals.userId));
}

export async function remove(req: Request, res: Response): Promise<Response> {
  const params = notificationParamsSchema.safeParse(req.params);

  if (!params.success) {
    return badRequest(res, params.error);
  }

  try {
    await notificationService.remove(res.locals.userId, params.data.id);
  } catch (err) {
    if (err instanceof notificationService.NotificationNotFoundError) {
      return res.status(404).json({ detail: err.message });
    }
    throw err;
  }

  return res.status(204).send();
}

/** Service-to-service create. Not reachable from a browser: see internal.routes.ts. */
export async function createNotification(req: Request, res: Response): Promise<Response> {
  const parsed = createNotificationBodySchema.safeParse(req.body);

  if (!parsed.success) {
    return badRequest(res, parsed.error);
  }

  try {
    const created = await notificationService.create(parsed.data);
    return res.status(201).json(created);
  } catch (err) {
    if (err instanceof notificationService.UnknownNotificationTypeError) {
      log.warn({ type: parsed.data.type }, 'unknown_notification_type');
      return res.status(400).json({ detail: err.message });
    }
    throw err;
  }
}

/**
 * Unread count for an arbitrary user, for the ai_service home BFF.
 *
 * Separate from the browser route because the caller there is a service acting
 * on someone else's behalf: there is no browser JWT to present, and the BFF
 * already proved who it is with the shared internal secret. Trusting an
 * `X-User-Id` here would let any service holding that one shared secret read
 * any user's count, so the user id is a path parameter and the route sits
 * behind the internal-secret check.
 */
export async function getUnreadCountForUser(req: Request, res: Response): Promise<Response> {
  const params = internalUserIdParamsSchema.safeParse(req.params);

  if (!params.success) {
    return badRequest(res, params.error);
  }

  return res.status(200).json(await notificationService.getUnreadCount(params.data.userId));
}
