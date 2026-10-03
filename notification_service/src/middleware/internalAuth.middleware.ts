import { timingSafeEqual } from 'node:crypto';

import type { NextFunction, Request, Response } from 'express';

import { env } from '../config/env';

/**
 * Gate for the service-to-service routes.
 *
 * The secret is the actual check. Kong's `internal-secret-auth` plugin already
 * verified it on the way in, but this service used to trust only the
 * `X-Internal-Service` header the plugin stamps — a header any client that can
 * reach the port directly could simply write, which would have let it dispatch
 * mail and create inbox rows for arbitrary users. Comparing the secret here as
 * well means bypassing the gateway buys an attacker nothing.
 *
 * `X-Internal-Service` is still required, but only as a claim about *which*
 * service is calling: it is recorded, not trusted for authorization.
 */
export function requireInternalService(req: Request, res: Response, next: NextFunction) {
  const providedSecret = req.header('X-Internal-Secret');

  if (!providedSecret || !secretsMatch(providedSecret, env.GATEWAY_INTERNAL_SECRET)) {
    return res.status(403).json({ error: 'Forbidden: missing internal service trust header' });
  }

  const source = req.header('X-Internal-Service');
  if (!source) {
    return res.status(403).json({ error: 'Forbidden: missing internal service trust header' });
  }

  res.locals.internalService = source;
  next();
}

function secretsMatch(provided: string, expected: string): boolean {
  const providedBuffer = Buffer.from(provided);
  const expectedBuffer = Buffer.from(expected);

  if (providedBuffer.length !== expectedBuffer.length) {
    return false;
  }

  return timingSafeEqual(providedBuffer, expectedBuffer);
}
