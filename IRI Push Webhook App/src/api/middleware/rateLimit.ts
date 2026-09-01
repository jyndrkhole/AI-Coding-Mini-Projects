import rateLimit from "express-rate-limit";
import { env } from "../../config/env.ts";

export const webhookRateLimiter = rateLimit({
  windowMs: env.rateLimitWindowMs,
  max: env.rateLimitMax,
  standardHeaders: true,
  legacyHeaders: false,
  skip: () => env.nodeEnv === "test",
  validate: { xForwardedForHeader: false },
  message: {
    status: "error",
    message: "Too many webhook requests"
  }
});
