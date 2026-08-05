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
import { buildFingerprint, normalizeTags } from "@/lib/fingerprint";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type IncomingTx = {
  id?: string;
  date?: string;
  merchant?: string;
  category?: string;
  amount?: number;
  type?: string;
  account?: string;
  tags?: unknown;
  receipt?: boolean;
  source?: string;
};

function validateTx(input: IncomingTx): string | null {
  if (!input.merchant || !String(input.merchant).trim()) {
    return "Merchant/source is required";
  }
  if (!input.date || !/^\d{4}-\d{2}-\d{2}$/.test(input.date)) {
    return "Valid date (YYYY-MM-DD) is required";
  }
  const amount = Number(input.amount);
  if (!(amount > 0) || !Number.isFinite(amount)) {
    return "Amount must be a positive number";
  }
  if (input.type !== "expense" && input.type !== "income") {
    return "Type must be expense or income";
  }
  return null;
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const items: IncomingTx[] = Array.isArray(body)
      ? body
      : Array.isArray(body?.transactions)
        ? body.transactions
        : [body];

    const { db } = await getStore();
    await ensureSchema(db);
    const rules = await listRules(db);

    let inserted = 0;
    let duplicates = 0;
    const created: unknown[] = [];
    const errors: string[] = [];

    for (const raw of items) {
      const err = validateTx(raw);
      if (err) {
        errors.push(err);
        continue;
      }
      const merchant = String(raw.merchant).trim();
      const amount = Math.abs(Number(raw.amount));
      const account = (raw.account || "Imported account").trim() || "Imported account";
      const date = raw.date!;
      const fingerprint = buildFingerprint(date, merchant, amount, account);

      if (await getFingerprintExists(db, fingerprint)) {
        duplicates++;
        continue;
      }

      let tags = normalizeTags(raw.tags);
      let category = (raw.category || "Needs review").trim() || "Needs review";
      const applied = applyRulesToCategory(merchant, category, tags, rules);
      category = applied.category;
      tags = applied.tags;

      const id = raw.id || uuidv4();
      const createdAt = new Date().toISOString();
      const source = raw.source || "manual";
      const receipt = raw.receipt ? 1 : 0;

      try {
        await db
          .prepare(
            `INSERT INTO transactions
             (id, date, merchant, category, amount, type, account, tags, receipt, source, fingerprint, createdAt)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
          )
          .bind(
            id,
            date,
            merchant,
            category,
            amount,
            raw.type,
            account,
            JSON.stringify(tags),
            receipt,
            source,
            fingerprint,
            createdAt
          )
          .run();

        for (const t of tags) await upsertTag(db, t);

        inserted++;
        created.push({
          id,
          date,
          merchant,
          category,
          amount,
          type: raw.type,
          account,
          tags,
          receipt: !!receipt,
          source,
          fingerprint,
          createdAt,
        });
      } catch (e) {
        const msg = e instanceof Error ? e.message : "insert failed";
        if (/UNIQUE|unique/i.test(msg)) {
          duplicates++;
        } else {
          errors.push(msg);
        }
      }
    }

    return NextResponse.json({
      inserted,
      duplicates,
      errors,
      transactions: created,
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Failed to save transactions";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function PATCH(req: Request) {
  try {
    const body = await req.json();
    const id = body?.id;
    if (!id || typeof id !== "string") {
      return NextResponse.json({ error: "id is required" }, { status: 400 });
    }
    const { db } = await getStore();
    await ensureSchema(db);

    const existing = await db
      .prepare(`SELECT * FROM transactions WHERE id = ?`)
      .bind(id)
      .first();
    if (!existing) {
      return NextResponse.json({ error: "Transaction not found" }, { status: 404 });
    }

    let category = String(existing.category);
    let tags = JSON.parse(String(existing.tags || "[]")) as string[];

    if (typeof body.category === "string" && body.category.trim()) {
      category = body.category.trim();
    }
    if (body.tags !== undefined) {
      tags = normalizeTags(body.tags);
    }

    await db
      .prepare(`UPDATE transactions SET category = ?, tags = ? WHERE id = ?`)
      .bind(category, JSON.stringify(tags), id)
      .run();

    for (const t of tags) await upsertTag(db, t);

    const row = await db
      .prepare(`SELECT * FROM transactions WHERE id = ?`)
      .bind(id)
      .first();

    return NextResponse.json({
      id: row!.id,
      date: row!.date,
      merchant: row!.merchant,
      category: row!.category,
      amount: row!.amount,
      type: row!.type,
      account: row!.account,
      tags: JSON.parse(String(row!.tags || "[]")),
      receipt: Number(row!.receipt) === 1,
      source: row!.source,
      fingerprint: row!.fingerprint,
      createdAt: row!.createdAt,
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Update failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE(req: Request) {
  try {
    const url = new URL(req.url);
    let id = url.searchParams.get("id");
    if (!id) {
      const body = await req.json().catch(() => ({}));
      id = body?.id;
    }
    if (!id) {
      return NextResponse.json({ error: "id is required" }, { status: 400 });
    }
    const { db } = await getStore();
    await ensureSchema(db);
    const result = await db
      .prepare(`DELETE FROM transactions WHERE id = ?`)
      .bind(id)
      .run();
    if (!result.meta?.changes) {
      return NextResponse.json({ error: "Transaction not found" }, { status: 404 });
    }
    return NextResponse.json({ ok: true, id });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Delete failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
