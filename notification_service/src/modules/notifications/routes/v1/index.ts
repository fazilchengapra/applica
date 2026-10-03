import { Router } from 'express';

import { requireInternalService } from '../../../../middleware/internalAuth.middleware';
import internalRoutes from './internal.routes';
import { publishCvStatus } from '../../../realtime/cvStatus';

const router = Router();

router.use('/internal', internalRoutes);

router.post('/realtime/cv-status', requireInternalService, publishCvStatus);

export default router;
