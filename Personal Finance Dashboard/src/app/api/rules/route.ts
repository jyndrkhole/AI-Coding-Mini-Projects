import { NextResponse } from "next/server";
import { v4 as uuidv4 } from "uuid";
import { ensureSchema, getStore, listRules } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const { db } = await getStore();
    await ensureSchema(db);
    const rules = await listRules(db);
    return NextResponse.json({ rules });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Failed to load rules";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const whenText = String(body?.whenText || "").trim();
    const thenText = String(body?.thenText || "").trim();
    if (!whenText || !thenText) {
      return NextResponse.json(
        { error: "whenText and thenText are required" },
        { status: 400 }
      );
    }
    const { db } = await getStore();
    await ensureSchema(db);
    const id = uuidv4();
    const createdAt = new Date().toISOString();
    const enabled = body?.enabled === false ? 0 : 1;
    await db
      .prepare(
        `INSERT INTO rules (id, whenText, thenText, enabled, createdAt) VALUES (?, ?, ?, ?, ?)`
      )
      .bind(id, whenText, thenText, enabled, createdAt)
      .run();
    return NextResponse.json({
      rule: { id, whenText, thenText, enabled: !!enabled, createdAt },
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Failed to create rule";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function PATCH(req: Request) {
  try {
    const body = await req.json();
    const id = body?.id;
    if (!id) {
      return NextResponse.json({ error: "id required" }, { status: 400 });
    }
    const { db } = await getStore();
    await ensureSchema(db);
    const existing = await db
      .prepare(`SELECT * FROM rules WHERE id = ?`)
      .bind(id)
      .first();
    if (!existing) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    const whenText =
      typeof body.whenText === "string"
        ? body.whenText.trim()
        : String(existing.whenText);
    const thenText =
      typeof body.thenText === "string"
        ? body.thenText.trim()
        : String(existing.thenText);
    const enabled =
      body.enabled === undefined
        ? Number(existing.enabled)
        : body.enabled
          ? 1
          : 0;
    await db
      .prepare(
        `UPDATE rules SET whenText = ?, thenText = ?, enabled = ? WHERE id = ?`
      )
      .bind(whenText, thenText, enabled, id)
      .run();
    return NextResponse.json({
      rule: {
        id,
        whenText,
        thenText,
        enabled: !!enabled,
        createdAt: existing.createdAt,
      },
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Failed to update rule";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE(req: Request) {
  try {
    const url = new URL(req.url);
    const id = url.searchParams.get("id");
    if (!id) {
      return NextResponse.json({ error: "id required" }, { status: 400 });
    }
    const { db } = await getStore();
    await ensureSchema(db);
    await db.prepare(`DELETE FROM rules WHERE id = ?`).bind(id).run();
    return NextResponse.json({ ok: true });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Failed to delete rule";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
