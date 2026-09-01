import type { RequestHandler } from "express";
import { addSseClient } from "../../services/sseService.ts";

export const streamEvents: RequestHandler = (req, res) => {
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache, no-transform");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders?.();
  res.write("event: ready\ndata: {\"status\":\"connected\"}\n\n");
  addSseClient(res);

  const heartbeat = setInterval(() => {
    res.write(": heartbeat\n\n");
  }, 30_000);

  req.on("close", () => {
    clearInterval(heartbeat);
  });
};
