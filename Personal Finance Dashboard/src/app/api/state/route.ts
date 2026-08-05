import { NextResponse } from "next/server";
import {
  ensureSchema,
  getStore,
  listDocuments,
  listRules,
  listTags,
  listTransactions,
  loadSettings,
  wipeAll,
} from "@/lib/db";
import { WIPE_CONFIRMATION } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const { db } = await getStore();
    await ensureSchema(db);
    const [transactions, tags, rules, settings, documents] = await Promise.all([
      listTransactions(db, 5000),
      listTags(db),
      listRules(db),
      loadSettings(db),
      listDocuments(db, 100),
    ]);
    // Never return object bytes — strip objectKey from client view? Spec says metadata ok but don't show raw keys to user in UI. API can include for internal use; we'll omit objectKey from public payload for safety and use id for actions.
    const docs = documents.map(({ objectKey: _k, ...rest }) => rest);
    return NextResponse.json({
      transactions,
      tags,
      rules,
      settings,
      documents: docs,
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Failed to load state";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    if (body?.confirmation !== WIPE_CONFIRMATION) {
      return NextResponse.json(
        { error: "Confirmation phrase required" },
        { status: 400 }
      );
    }
    const { db, bucket } = await getStore();
    await ensureSchema(db);
    await wipeAll(db, bucket);
    return NextResponse.json({
      ok: true,
      message: "All Ledgerly data erased",
      freshStart: true,
    });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Wipe failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
