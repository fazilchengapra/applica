import { Router } from 'express';

import { requireGatewayUser } from '../../../../middleware/gatewayAuth.middleware';
import * as notificationController from '../../controllers/notificationController';

const router = Router();

// Kong has already verified the JWT and stamped X-User-Id; this service only
// confirms the request came through Kong before acting on that id.
router.use(requireGatewayUser);

// The literal collection paths come first so they cannot be captured by the
// :id pattern below.
router.get('/', notificationController.listNotifications);
router.get('/unread-count', notificationController.getUnreadCount);
router.post('/read-all', notificationController.markAllRead);
router.post('/:id/read', notificationController.markRead);
router.delete('/:id', notificationController.remove);

export default router;
