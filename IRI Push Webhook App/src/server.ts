import { createApp } from "./app.ts";
import { env } from "./config/env.ts";
import { initDb } from "./database/db.ts";

initDb(env.databasePath);

const app = createApp();

app.listen(env.port, "0.0.0.0", () => {
  const base = env.publicBaseUrl.replace(/\/$/, "");
  console.log(`IRI Push Notification Test Portal listening on ${base}`);
  console.log(`Webhook:  POST ${base}/webhooks/iri`);
  console.log(`Health:   GET  ${base}/health`);
  console.log(`Swagger:  GET  ${base}/api-docs`);
});
