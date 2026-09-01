import type { Response } from "express";
import type { WebhookEvent } from "../types/index.ts";

const clients = new Set<Response>();

export function addSseClient(res: Response): void {
  clients.add(res);
  res.on("close", () => {
    clients.delete(res);
  });
}

export function broadcastWebhookEvent(event: WebhookEvent): void {
  const payload = `event: webhook\ndata: ${JSON.stringify(event)}\n\n`;
  for (const client of clients) {
    client.write(payload);
  }
}

export function sseClientCount(): number {
  return clients.size;
}
