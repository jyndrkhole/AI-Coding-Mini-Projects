import { useEffect, useRef, useState } from "react";
import type { WebhookEvent } from "../types";

export function useWebhookStream(onEvent: (event: WebhookEvent) => void) {
  const [connected, setConnected] = useState(false);
  const handlerRef = useRef(onEvent);
  handlerRef.current = onEvent;

  useEffect(() => {
    const source = new EventSource("/api/stream");
    source.addEventListener("ready", () => setConnected(true));
    source.addEventListener("webhook", (message) => {
      try {
        handlerRef.current(JSON.parse((message as MessageEvent).data) as WebhookEvent);
      } catch {
        /* ignore malformed SSE payloads */
      }
    });
    source.onerror = () => setConnected(false);
    return () => {
      source.close();
      setConnected(false);
    };
  }, []);

  return connected;
}
