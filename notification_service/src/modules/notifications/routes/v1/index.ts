import { Router } from "express";
import internalRoutes from "./internal.routes";
import { publishCvStatus } from "../../../realtime/cvStatus";

const router = Router();

router.use("/internal", internalRoutes);
router.post("/realtime/cv-status", publishCvStatus);

export default router;