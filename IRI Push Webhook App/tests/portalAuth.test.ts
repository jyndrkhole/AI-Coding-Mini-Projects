import { afterEach, describe, expect, it } from "vitest";
import request from "supertest";
import { createTestApp } from "./helpers.ts";
import {
  portalSessionTtlMs,
  signPortalSession,
  verifyPortalSession
} from "../src/config/portalSession.ts";

describe("portal UI login", () => {
  afterEach(() => {
    delete process.env.PORTAL_AUTH_ENABLED;
    delete process.env.PORTAL_USERNAME;
    delete process.env.PORTAL_PASSWORD;
    delete process.env.PORTAL_SESSION_TTL_HOURS;
    delete process.env.PORTAL_SESSION_TTL_MINUTES;
  });

  it("leaves UI APIs open when portal auth is disabled", async () => {
    const app = createTestApp();
    await request(app).get("/api/config").expect(200);
  });

  it("blocks UI APIs without a session and still accepts webhooks", async () => {
    process.env.PORTAL_AUTH_ENABLED = "true";
    process.env.PORTAL_USERNAME = "admin";
    process.env.PORTAL_PASSWORD = "portal-secret";
    const app = createTestApp();

    const denied = await request(app).get("/api/config").expect(401);
    expect(denied.body.message).toBe("Portal login required");

    await request(app)
      .post("/webhooks/iri")
      .send({ eventType: "applicationStatus.v1.applicationReceived", policyNumber: "P-OPEN" })
      .expect(200);

    await request(app).get("/health").expect(200);
  });

  it("allows UI APIs after a valid login", async () => {
    process.env.PORTAL_AUTH_ENABLED = "true";
    process.env.PORTAL_USERNAME = "admin";
    process.env.PORTAL_PASSWORD = "portal-secret";
    const app = createTestApp();
    const agent = request.agent(app);

    await agent.post("/api/portal/login").send({ username: "admin", password: "wrong" }).expect(401);

    const login = await agent
      .post("/api/portal/login")
      .send({ username: "admin", password: "portal-secret" })
      .expect(200);
    expect(login.body.authenticated).toBe(true);
    const rawCookie = login.headers["set-cookie"];
    const setCookie = Array.isArray(rawCookie) ? rawCookie.join(";") : rawCookie ?? "";
    expect(setCookie).toContain("portal_session_3000=");
    expect(setCookie).toContain("portal_session=;");
    expect(setCookie).toMatch(/Max-Age=3600/);

    const config = await agent.get("/api/config").expect(200);
    expect(config.body.portalAuthEnabled).toBe(true);

    await agent.post("/api/portal/logout").expect(200);
    await agent.get("/api/config").expect(401);
  });

  it("rejects expired portal sessions after the TTL", () => {
    process.env.PORTAL_PASSWORD = "portal-secret";
    expect(portalSessionTtlMs()).toBe(60 * 60 * 1000);

    const fresh = signPortalSession("admin");
    expect(verifyPortalSession(fresh)).toBe("admin");

    const expired = signPortalSession("admin", Date.now() - portalSessionTtlMs() - 1000);
    expect(verifyPortalSession(expired)).toBeNull();
  });

  it("honors PORTAL_SESSION_TTL_MINUTES for short local tests", () => {
    process.env.PORTAL_PASSWORD = "portal-secret";
    process.env.PORTAL_SESSION_TTL_MINUTES = "1";
    expect(portalSessionTtlMs()).toBe(60_000);
  });

  it("serves a login HTML page for GET / instead of the app shell", async () => {
    process.env.PORTAL_AUTH_ENABLED = "true";
    process.env.PORTAL_USERNAME = "admin";
    process.env.PORTAL_PASSWORD = "portal-secret";
    const app = createTestApp();

    const page = await request(app).get("/").expect(200);
    expect(page.text).toContain("Sign in");
    expect(page.text).toContain("theme-toggle");
    expect(page.text).toContain("action=\"/api/portal/login\"");
    expect(page.text).toContain("/favicon.svg");

    const icon = await request(app).get("/favicon.svg").expect(200);
    expect(icon.headers["content-type"]).toMatch(/svg/);
    const svg = Buffer.isBuffer(icon.body) ? icon.body.toString("utf8") : String(icon.text ?? icon.body);
    expect(svg).toContain("#16324f");
    expect(svg).toContain("#14b8a6");

    const agent = request.agent(app);
    await agent
      .post("/api/portal/login")
      .type("form")
      .send({ username: "admin", password: "portal-secret" })
      .expect(303);
    const home = await agent.get("/").expect(200);
    expect(home.text).not.toContain("action=\"/api/portal/login\"");
  });
});
