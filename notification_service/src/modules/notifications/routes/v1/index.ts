import { Router } from "express";
import internalRoutes from "./internal.routes";
import { publishCvStatus } from "../../../realtime/cvStatus";
import { requireInternalService } from "../../../../middleware/internalAuth.middleware";

const router = Router();

router.use("/internal", internalRoutes);
router.post("/realtime/cv-status", requireInternalService, publishCvStatus);

export default router;