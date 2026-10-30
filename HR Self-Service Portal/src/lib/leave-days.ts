import { eachIsoDate, roundDay, weekday } from "./dates";

export type DayPortion = "FULL" | "AM" | "PM";

export type CountedDay = {
  iso: string;
  portion: number;
};

export type CountLeaveDaysInput = {
  startIso: string;
  endIso: string;
  startPortion: DayPortion;
  endPortion: DayPortion;
  weekendDays: number[];
  holidayIsos: string[];
  allowsHalfDay: boolean;
};

export type CountLeaveDaysResult =
  | { ok: true; days: CountedDay[]; requestedDays: number }
  | { ok: false; error: string };

function portionForDate(
  iso: string,
  startIso: string,
  endIso: string,
  startPortion: DayPortion,
  endPortion: DayPortion,
): DayPortion {
  if (iso === startIso) return startPortion;
  if (iso === endIso) return endPortion;
  return "FULL";
}

export function countLeaveDays(input: CountLeaveDaysInput): CountLeaveDaysResult {
  if (input.endIso < input.startIso) {
    return { ok: false, error: "The end date must be on or after the start date." };
  }

  const singleDay = input.startIso === input.endIso;
  const startPortion = input.startPortion;
  const endPortion = singleDay ? input.startPortion : input.endPortion;
  if ((startPortion !== "FULL" || endPortion !== "FULL") && !input.allowsHalfDay) {
    return { ok: false, error: "This leave type does not allow half-day leave." };
  }

  const holidays = new Set(input.holidayIsos);
  const weekends = new Set(input.weekendDays);
  const days: CountedDay[] = [];

  for (const iso of eachIsoDate(input.startIso, input.endIso)) {
    if (weekends.has(weekday(iso)) || holidays.has(iso)) continue;
    const portion = portionForDate(iso, input.startIso, input.endIso, startPortion, endPortion);
    days.push({ iso, portion: portion === "FULL" ? 1 : 0.5 });
  }

  if (days.length === 0) {
    return { ok: false, error: "The selected dates do not include a working day." };
  }

  return {
    ok: true,
    days,
    requestedDays: roundDay(days.reduce((sum, day) => sum + day.portion, 0)),
  };
}
