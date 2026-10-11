import { createApp } from "./app.ts";
import { env, loadedEnvFiles } from "./config/env.ts";
import { isPortalAuthEnabled } from "./config/portalSession.ts";
import { initDb } from "./database/db.ts";

initDb(env.databasePath);

const app = createApp();

app.listen(env.port, "0.0.0.0", () => {
  const base = env.publicBaseUrl.replace(/\/$/, "");
  console.log(`Push Notifications Test Portal listening on ${base}`);
  console.log(`Webhook:  POST ${base}/webhooks/iri`);
  console.log(`Health:   GET  ${base}/health`);
  console.log(`Swagger:  GET  ${base}/api-docs`);
  console.log(`Portal login: ${isPortalAuthEnabled() ? "enabled" : "disabled"}`);
  if (loadedEnvFiles.length > 0) {
    console.log(`Env file: ${loadedEnvFiles.join(", ")}`);
  } else {
    console.log("Env file: none found next to the app or in the process folder");
  }
});
