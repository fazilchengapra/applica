import { Request, Response, NextFunction } from "express";
import { includes } from "zod";

export function requireInternalService(req: Request, res: Response, next: NextFunction) {
    const allowed_services = [
        "user-service",
        "ai-service",
    ]
    const source = req.header("X-Internal-Service");
    if (!source || !allowed_services.includes(source)) {    
        return res.status(403).json({ error: "Forbidden: missing internal service trust header" });
    }
    next();
}