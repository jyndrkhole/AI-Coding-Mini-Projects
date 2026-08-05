import { NextResponse } from "next/server";
import { v4 as uuidv4 } from "uuid";
import { ensureSchema, getStore } from "@/lib/db";
import { safeFilename } from "@/lib/fingerprint";
import { MAX_FILE_BYTES } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const form = await req.formData();
    const files = form.getAll("files").filter((f): f is File => f instanceof File);
    const single = form.get("file");
    if (single instanceof File) files.push(single);

    if (!files.length) {
      return NextResponse.json({ error: "No files provided" }, { status: 400 });
    }

    const { db, bucket } = await getStore();
    await ensureSchema(db);

    const saved: unknown[] = [];
    const errors: string[] = [];

    for (const file of files) {
      if (file.size > MAX_FILE_BYTES) {
        errors.push(`${file.name}: exceeds 20 MB limit`);
        continue;
      }
      const id = uuidv4();
      const objectKey = `uploads/${id}-${safeFilename(file.name)}`;
      const buf = await file.arrayBuffer();
      await bucket.put(objectKey, buf, {
        httpMetadata: { contentType: file.type || "application/octet-stream" },
      });

      const createdAt = new Date().toISOString();
      const status = "stored";
      await db
        .prepare(
          `INSERT INTO documents (id, filename, mimeType, size, objectKey, status, source, createdAt)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
        )
        .bind(
          id,
          file.name,
          file.type || "application/octet-stream",
          file.size,
          objectKey,
          status,
          "upload",
          createdAt
        )
        .run();

      saved.push({
        id,
        filename: file.name,
        mimeType: file.type || "application/octet-stream",
        size: file.size,
        status,
        source: "upload",
        createdAt,
      });
    }

    return NextResponse.json({
      documents: saved,
      errors,
      stored: saved.length,
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Upload failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE(req: Request) {
  try {
    const url = new URL(req.url);
    const id = url.searchParams.get("id");
    if (!id) {
      return NextResponse.json({ error: "id is required" }, { status: 400 });
    }
    const { db, bucket } = await getStore();
    await ensureSchema(db);
    const row = await db
      .prepare(`SELECT objectKey FROM documents WHERE id = ?`)
      .bind(id)
      .first<{ objectKey: string }>();
    if (!row) {
      return NextResponse.json({ error: "Not found" }, { status: 404 });
    }
    await bucket.delete(row.objectKey);
    await db.prepare(`DELETE FROM documents WHERE id = ?`).bind(id).run();
    return NextResponse.json({ ok: true });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Delete failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
