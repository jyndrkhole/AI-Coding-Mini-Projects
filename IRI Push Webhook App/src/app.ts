import path from "node:path";
import fs from "node:fs";
import express, { type Request, type Response, type NextFunction } from "express";
import cors from "cors";
import swaggerUi from "swagger-ui-express";
import { env, PROJECT_ROOT } from "./config/env.ts";
import { apiRouter, healthRouter, webhookRouter } from "./api/routes/index.ts";
import { errorHandler, notFoundHandler } from "./api/middleware/errorHandler.ts";
import { requirePortalAuth } from "./api/middleware/portalAuth.ts";
import { servePortalLoginPage } from "./api/middleware/portalLoginPage.ts";
import { openApiSpec } from "./openapi.ts";

const exposedHeaders = ["Content-Disposition", "X-Export-Count", "X-Export-Total", "X-Export-Truncated"];

function corsOptions(): cors.CorsOptions {
  if (env.corsOrigin === "*") {
    return { origin: true, exposedHeaders };
  }
  const origins = env.corsOrigin.split(",").map((item) => item.trim()).filter(Boolean);
  return { origin: origins, exposedHeaders };
}

function webhookBodyParser(req: Request, res: Response, next: NextFunction): void {
  express.raw({ type: "*/*", limit: env.bodyLimit })(req, res, (err) => {
    if (err) {
      next(err);
      return;
    }
    const buffer = req.body as Buffer | undefined;
    req.rawBody = buffer && Buffer.isBuffer(buffer) ? buffer.toString("utf8") : "";
    if (!req.rawBody) {
      req.body = {};
      next();
      return;
    }
    try {
      req.body = JSON.parse(req.rawBody);
    } catch {
      req.jsonParseError = true;
      req.body = undefined;
    }
    next();
  });
}

export function createApp() {
  const app = express();
  app.disable("x-powered-by");
  app.set("trust proxy", 1);
  app.use(cors(corsOptions()));
  app.use("/webhooks", webhookBodyParser);
  app.use((req, res, next) => {
    if (req.path.startsWith("/webhooks")) {
      next();
      return;
    }
    const contentType = req.headers["content-type"] ?? "";
    if (contentType.includes("application/x-www-form-urlencoded")) {
      express.urlencoded({ extended: false, limit: env.bodyLimit })(req, res, next);
      return;
    }
    express.json({ limit: env.bodyLimit })(req, res, next);
  });

  app.use("/health", healthRouter);
  app.use("/webhooks", webhookRouter);
  app.use("/api", apiRouter);

  const faviconSvg = path.join(PROJECT_ROOT, "frontend", "public", "favicon.svg");
  const sendFavicon: express.RequestHandler = (_req, res, next) => {
    if (!fs.existsSync(faviconSvg)) {
      next();
      return;
    }
    res.setHeader("Cache-Control", "public, max-age=86400");
    res.type("image/svg+xml").send(fs.readFileSync(faviconSvg, "utf8"));
  };
  app.get("/favicon.svg", sendFavicon);
  app.get("/favicon.ico", sendFavicon);
  app.use("/api-docs", requirePortalAuth, swaggerUi.serve, swaggerUi.setup(openApiSpec, {
    customSiteTitle: "Push Notifications Test Portal API"
  }));
  app.use("/api-docs.json", requirePortalAuth, (_req, res) => {
    res.json(openApiSpec);
  });

  app.use(servePortalLoginPage);

  const frontendDist = path.join(PROJECT_ROOT, "frontend", "dist");
  if (fs.existsSync(frontendDist)) {
    app.use(express.static(frontendDist));
    app.get("*", (req, res, next) => {
      if (
        req.path.startsWith("/api") ||
        req.path.startsWith("/webhooks") ||
        req.path.startsWith("/health") ||
        req.path.startsWith("/api-docs")
      ) {
        next();
        return;
      }
      res.sendFile(path.join(frontendDist, "index.html"));
    });
  }

  app.use(notFoundHandler);
  app.use(errorHandler);
  return app;
}
