import { Router } from 'express';

import { requireInternalService } from '../../../../middleware/internalAuth.middleware';
import { handleIncomingEvent } from '../../controllers/eventsController';
import * as notificationController from '../../controllers/notificationController';

const router = Router();

// The write side of the inbox, for other services rather than browsers. It sits
// behind the same trust check as /dispatch, because creating a row for an
// arbitrary user is the same class of capability as reading one.
router.post('/notifications', requireInternalService, notificationController.createNotification);

router.get('/users/:userId/unread-count', requireInternalService, notificationController.getUnreadCountForUser);

router.post('/dispatch', requireInternalService, handleIncomingEvent);

export default router;
