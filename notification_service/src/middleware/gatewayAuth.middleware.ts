import { timingSafeEqual } from 'node:crypto';

import type { NextFunction, Request, Response } from 'express';

import { env } from '../config/env';

/**
 * The notification inbox is user data, so these routes cannot be reached the way
 * the internal ones are. Kong verifies the JWT and then stamps two headers:
 * `X-Gateway-Secret` (from the header_injector config) and `X-User-Id` (from
 * the token's `sub`). This middleware is the service's half of that contract:
 *
 *   1. the gateway secret must match, which proves the request went through Kong
 *      and that X-User-Id was stamped by the gateway rather than the client;
 *   2. X-User-Id must be a positive integer, which is the user every query in
 *      these routes is scoped to.
 *
 * Nothing here re-reads or re-verifies the JWT — Kong is the only place tokens
 * are validated, which is also why the secret check is not optional: without it
 * a client that can reach the service directly would simply assert its own
 * X-User-Id and read someone else's inbox.
 */
export function requireGatewayUser(req: Request, res: Response, next: NextFunction) {
  const providedSecret = req.header('X-Gateway-Secret');
  const expectedSecret = env.GATEWAY_INTERNAL_SECRET;

  if (!providedSecret || !secretsMatch(providedSecret, expectedSecret)) {
    return res.status(403).json({ error: 'Forbidden: request did not come through the gateway' });
  }

  const rawUserId = req.header('X-User-Id');
  if (!rawUserId || !/^\d+$/.test(rawUserId)) {
    return res.status(401).json({ error: 'Unauthorized: missing or invalid user context' });
  }

  const userId = Number(rawUserId);
  if (!Number.isSafeInteger(userId) || userId < 1) {
    return res.status(401).json({ error: 'Unauthorized: missing or invalid user context' });
  }

  res.locals.userId = userId;
  next();
}

/**
 * Constant-time comparison so a mismatched secret cannot be discovered by
 * timing how far the strings agree. `timingSafeEqual` throws on a length
 * mismatch, which is why the lengths are compared up front — the length of a
 * shared secret is not itself a secret worth protecting.
 */
function secretsMatch(provided: string, expected: string): boolean {
  const providedBuffer = Buffer.from(provided);
  const expectedBuffer = Buffer.from(expected);

  if (providedBuffer.length !== expectedBuffer.length) {
    return false;
  }

  return timingSafeEqual(providedBuffer, expectedBuffer);
}
