import { NextResponse } from "next/server";
import { ensureSchema, getStore, patchSettings, upsertTag } from "@/lib/db";
import { normalizeTags } from "@/lib/fingerprint";
import { isValidPeriod } from "@/lib/periods";
import type { AppSettings } from "@/lib/types";
import { isSupportedCurrency, localeForCurrency } from "@/lib/currency";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function uniqNames(list: unknown): string[] {
  if (!Array.isArray(list)) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const item of list) {
    if (typeof item !== "string") continue;
    const t = item.trim();
    if (!t) continue;
    const key = t.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(t);
  }
  return out;
}

export async function PUT(req: Request) {
  try {
    const body = (await req.json()) as Partial<AppSettings> & {
      tags?: string[];
    };
    const { db } = await getStore();
    await ensureSchema(db);

    const patch: Partial<AppSettings> = {};

    if (body.categories !== undefined) {
      patch.categories = uniqNames(body.categories);
    }
    if (body.accounts !== undefined) {
      patch.accounts = uniqNames(body.accounts);
    }
    if (body.goals !== undefined && Array.isArray(body.goals)) {
      patch.goals = body.goals;
    }
    if (body.budgets !== undefined && Array.isArray(body.budgets)) {
      patch.budgets = body.budgets;
    }
    if (body.subscriptions !== undefined && Array.isArray(body.subscriptions)) {
      patch.subscriptions = body.subscriptions;
    }
    if (body.recurring !== undefined && Array.isArray(body.recurring)) {
      patch.recurring = body.recurring;
    }
    if (body.dismissedPatterns !== undefined) {
      patch.dismissedPatterns = uniqNames(body.dismissedPatterns);
    }
    if (body.assetsTotal !== undefined) {
      const n = Number(body.assetsTotal);
      if (!Number.isFinite(n) || n < 0) {
        return NextResponse.json({ error: "Invalid assetsTotal" }, { status: 400 });
      }
      patch.assetsTotal = n;
    }
    if (body.liabilitiesTotal !== undefined) {
      const n = Number(body.liabilitiesTotal);
      if (!Number.isFinite(n) || n < 0) {
        return NextResponse.json(
          { error: "Invalid liabilitiesTotal" },
          { status: 400 }
        );
      }
      patch.liabilitiesTotal = n;
    }
    if (body.netWorthConfigured !== undefined) {
      patch.netWorthConfigured = Boolean(body.netWorthConfigured);
    }
    if (body.selectedPeriod !== undefined) {
      if (!isValidPeriod(body.selectedPeriod)) {
        return NextResponse.json({ error: "Invalid selectedPeriod" }, { status: 400 });
      }
      patch.selectedPeriod = body.selectedPeriod;
    }
    if (body.currency !== undefined) {
      const code = String(body.currency).trim().toUpperCase();
      if (!isSupportedCurrency(code)) {
        return NextResponse.json({ error: "Unsupported currency" }, { status: 400 });
      }
      patch.currency = code;
      patch.locale =
        typeof body.locale === "string" && body.locale.trim()
          ? body.locale.trim()
          : localeForCurrency(code);
    } else if (body.locale !== undefined) {
      patch.locale = String(body.locale);
    }
    if (body.driveFolder !== undefined) {
      patch.driveFolder = body.driveFolder;
    }
    if (body.driveSync !== undefined) {
      patch.driveSync = body.driveSync as AppSettings["driveSync"];
    }
    if (body.processedFileIds !== undefined && Array.isArray(body.processedFileIds)) {
      patch.processedFileIds = body.processedFileIds.map(String).slice(-5000);
    }
    if (body.driveResetAt !== undefined) {
      patch.driveResetAt = body.driveResetAt;
    }
    if (body.freshStart !== undefined) {
      patch.freshStart = Boolean(body.freshStart);
    }

    // Optional global tags list via preferences
    if (Array.isArray(body.tags)) {
      for (const t of normalizeTags(body.tags)) {
        await upsertTag(db, t);
      }
    }

    const settings = await patchSettings(db, patch);
    return NextResponse.json({ settings });
  } catch (e) {
    const message = e instanceof Error ? e.message : "Failed to save preferences";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
