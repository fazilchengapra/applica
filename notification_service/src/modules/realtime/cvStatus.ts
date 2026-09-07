import { Request, Response } from 'express';
import { z } from 'zod';
import {
  REALTIME_CV_STATUS_CHANNEL,
  createRealtimeEventClients,
} from '../../config/redis';
import { logger } from '../../lib/logger';

const cvStatusSchema = z.object({
  userId: z.string().min(1),
  cvId: z.string().min(1),
  status: z.enum(['pending', 'processing', 'completed', 'failed']),
});

const { publisher } = createRealtimeEventClients();

export async function publishCvStatus(req: Request, res: Response): Promise<Response> {
  const parsed = cvStatusSchema.safeParse(req.body);

  if (!parsed.success) {
    return res.status(400).json({ error: 'Invalid CV status payload' });
  }

  try {
    await publisher.publish(REALTIME_CV_STATUS_CHANNEL, JSON.stringify(parsed.data));
    return res.status(202).json({ status: 'accepted' });
  } catch (err) {
    logger.error({ err }, 'cv_status_publish_failed');
    return res.status(503).json({ error: 'Realtime status unavailable' });
  }
}