import { Router } from "express";
import internalRoutes from "./internal.routes";

const router = Router();

router.use("/internal", internalRoutes);

export default router;