import path from "node:path";
import fs from "node:fs";
import express, { type Request, type Response, type NextFunction } from "express";
import cors from "cors";
import swaggerUi from "swagger-ui-express";
import { env, PROJECT_ROOT } from "./config/env.ts";
import { apiRouter, healthRouter, webhookRouter } from "./api/routes/index.ts";
import { errorHandler, notFoundHandler } from "./api/middleware/errorHandler.ts";
import { openApiSpec } from "./openapi.ts";

function corsOptions(): cors.CorsOptions {
  if (env.corsOrigin === "*") {
    return { origin: true };
  }
  const origins = env.corsOrigin.split(",").map((item) => item.trim()).filter(Boolean);
  return { origin: origins };
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
    express.json({ limit: env.bodyLimit })(req, res, next);
  });

  app.use("/health", healthRouter);
  app.use("/webhooks", webhookRouter);
  app.use("/api", apiRouter);
  app.use("/api-docs", swaggerUi.serve, swaggerUi.setup(openApiSpec, {
    customSiteTitle: "IRI Push Notification Test Portal API"
  }));
  app.get("/api-docs.json", (_req, res) => {
    res.json(openApiSpec);
  });

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
