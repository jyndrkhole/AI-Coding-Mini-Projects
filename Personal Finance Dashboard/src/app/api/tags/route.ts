import { NextResponse } from "next/server";
import { ensureSchema, getStore, listTags, upsertTag } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const { db } = await getStore();
    await ensureSchema(db);
    const tags = await listTags(db);
    return NextResponse.json({ tags });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Failed to load tags";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const name = String(body?.name || "").trim();
    if (!name) {
      return NextResponse.json({ error: "name required" }, { status: 400 });
    }
    const { db } = await getStore();
    await ensureSchema(db);
    await upsertTag(db, name);
    const tags = await listTags(db);
    return NextResponse.json({ tags });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Failed to create tag";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE(req: Request) {
  try {
    const url = new URL(req.url);
    const name = url.searchParams.get("name");
    const strip = url.searchParams.get("strip") === "1";
    if (!name) {
      return NextResponse.json({ error: "name required" }, { status: 400 });
    }
    const { db } = await getStore();
    await ensureSchema(db);
    await db.prepare(`DELETE FROM tags WHERE name = ?`).bind(name).run();
    if (strip) {
      const txs = await db
        .prepare(`SELECT id, tags FROM transactions`)
        .all<{ id: string; tags: string }>();
      for (const row of txs.results) {
        const tags = JSON.parse(row.tags || "[]") as string[];
        const next = tags.filter(
          (t) => t.toLowerCase() !== name.toLowerCase()
        );
        if (next.length !== tags.length) {
          await db
            .prepare(`UPDATE transactions SET tags = ? WHERE id = ?`)
            .bind(JSON.stringify(next), row.id)
            .run();
        }
      }
    }
    return NextResponse.json({ ok: true });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Failed to delete tag";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
