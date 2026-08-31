import { Router } from "express";
import { requireInternalService } from "../.../../../../../middleware/internalAuth.middleware";
import { handleIncomingEvent } from "../../controllers/eventsController";

const router = Router();

router.post("/dispatch", requireInternalService, handleIncomingEvent);

export default router;