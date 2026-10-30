import { existsSync } from "node:fs";
import EmbeddedPostgres from "embedded-postgres";

const databaseDir = ".data/postgres";
const pg = new EmbeddedPostgres({
  databaseDir,
  user: "peoplehub",
  password: "peoplehub",
  port: 5432,
  persistent: true,
});

if (!existsSync(`${databaseDir}/PG_VERSION`)) {
  await pg.initialise();
}

await pg.start();

try {
  await pg.createDatabase("peoplehub");
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  if (!/already exists/i.test(message)) throw error;
}

console.log("PostgreSQL is ready at localhost:5432, database peoplehub.");

const shutdown = async () => {
  await pg.stop();
  process.exit(0);
};

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

await new Promise(() => {});
