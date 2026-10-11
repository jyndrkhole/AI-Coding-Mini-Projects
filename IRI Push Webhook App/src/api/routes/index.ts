import { Router } from "express";
import { receiveWebhook } from "../controllers/webhookController.ts";
import { getHealth } from "../controllers/healthController.ts";
import { clearEvents, exportEvents, getEvent, listEvents } from "../controllers/webhookEventsController.ts";
import { getCatalogEvent, listCatalog } from "../controllers/catalogController.ts";
import { getStats } from "../controllers/statsController.ts";
import { getConfig, putConfig } from "../controllers/configController.ts";
import { getPortalSession, portalLogin, portalLoginLimiter, portalLogout } from "../controllers/portalAuthController.ts";
import { streamEvents } from "../controllers/sseController.ts";
import { webhookAuth } from "../middleware/webhookAuth.ts";
import { requirePortalAuth } from "../middleware/portalAuth.ts";
import { webhookRateLimiter } from "../middleware/rateLimit.ts";

export const webhookRouter = Router();
webhookRouter.post("/iri", webhookRateLimiter, webhookAuth, receiveWebhook);

export const apiRouter = Router();
apiRouter.get("/portal/session", getPortalSession);
apiRouter.post("/portal/login", portalLoginLimiter, portalLogin);
apiRouter.post("/portal/logout", portalLogout);
apiRouter.use(requirePortalAuth);
apiRouter.get("/health", getHealth);
apiRouter.get("/webhook-events", listEvents);
apiRouter.get("/webhook-events/export", exportEvents);
apiRouter.get("/webhook-events/:id", getEvent);
apiRouter.delete("/webhook-events", clearEvents);
apiRouter.get("/stats", getStats);
apiRouter.get("/events", listCatalog);
apiRouter.get("/events/:eventType", getCatalogEvent);
apiRouter.get("/config", getConfig);
apiRouter.put("/config", putConfig);
apiRouter.get("/stream", streamEvents);

export const healthRouter = Router();
healthRouter.get("/", getHealth);
