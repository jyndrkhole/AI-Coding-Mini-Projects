import { NextResponse } from "next/server";
import { v4 as uuidv4 } from "uuid";
import {
  applyRulesToCategory,
  ensureSchema,
  getFingerprintExists,
  getStore,
  listRules,
  upsertTag,
} from "@/lib/db";
import { parseCsvText, type CsvColumnMap } from "@/lib/csv";
import { buildFingerprint, normalizeTags } from "@/lib/fingerprint";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const contentType = req.headers.get("content-type") || "";
    let text = "";
    let mapping: CsvColumnMap | undefined;
    let previewOnly = false;

    if (contentType.includes("multipart/form-data")) {
      const form = await req.formData();
      const file = form.get("file");
      if (!(file instanceof File)) {
        return NextResponse.json({ error: "CSV file required" }, { status: 400 });
      }
      text = await file.text();
      const mapRaw = form.get("mapping");
      if (typeof mapRaw === "string" && mapRaw) {
        mapping = JSON.parse(mapRaw) as CsvColumnMap;
      }
      previewOnly = form.get("preview") === "1" || form.get("preview") === "true";
    } else {
      const body = await req.json();
      text = String(body?.text || "");
      mapping = body?.mapping;
      previewOnly = Boolean(body?.previewOnly);
    }

    if (!text.trim()) {
      return NextResponse.json({ error: "Empty CSV" }, { status: 400 });
    }

    const parsed = parseCsvText(text, mapping);
    if (parsed.ambiguous) {
      return NextResponse.json({
        needsMapping: true,
        headers: parsed.headers,
        previewRows: parsed.previewRows,
        mapping: parsed.mapping,
      });
    }

    if (previewOnly) {
      return NextResponse.json({
        needsMapping: false,
        headers: parsed.headers,
        previewRows: parsed.previewRows,
        mapping: parsed.mapping,
        rowCount: parsed.rows.length,
        skipped: parsed.skipped,
        needsReview: parsed.needsReview,
      });
    }

    const { db } = await getStore();
    await ensureSchema(db);
    const rules = await listRules(db);

    let inserted = 0;
    let duplicates = 0;

    for (const row of parsed.rows) {
      const fingerprint = buildFingerprint(
        row.date,
        row.merchant,
        row.amount,
        row.account
      );
      if (await getFingerprintExists(db, fingerprint)) {
        duplicates++;
        continue;
      }
      let tags = normalizeTags([]);
      let category = row.category;
      const applied = applyRulesToCategory(row.merchant, category, tags, rules);
      category = applied.category;
      tags = applied.tags;
      const id = uuidv4();
      try {
        await db
          .prepare(
            `INSERT INTO transactions
             (id, date, merchant, category, amount, type, account, tags, receipt, source, fingerprint, createdAt)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
          )
          .bind(
            id,
            row.date,
            row.merchant,
            category,
            row.amount,
            row.type,
            row.account,
            JSON.stringify(tags),
            0,
            "csv",
            fingerprint,
            new Date().toISOString()
          )
          .run();
        for (const t of tags) await upsertTag(db, t);
        inserted++;
      } catch (e) {
        const msg = e instanceof Error ? e.message : "";
        if (/UNIQUE|unique/i.test(msg)) duplicates++;
      }
    }

    return NextResponse.json({
      inserted,
      duplicates,
      skipped: parsed.skipped,
      needsReview: parsed.needsReview,
      headers: parsed.headers,
      mapping: parsed.mapping,
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : "CSV import failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
