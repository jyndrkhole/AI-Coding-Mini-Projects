const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

export function isIsoDate(value: string): boolean {
  const match = ISO_DATE.exec(value);
  if (!match) return false;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

export function dateOnly(iso: string): Date {
  return new Date(`${iso}T00:00:00.000Z`);
}

export function isoFromDateOnly(value: Date): string {
  return value.toISOString().slice(0, 10);
}

export function todayIso(timeZone: string, now = new Date()): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}

export function weekday(iso: string): number {
  return dateOnly(iso).getUTCDay();
}

export function eachIsoDate(startIso: string, endIso: string): string[] {
  const days: string[] = [];
  let cursor = dateOnly(startIso).getTime();
  const last = dateOnly(endIso).getTime();
  while (cursor <= last) {
    days.push(new Date(cursor).toISOString().slice(0, 10));
    cursor += 86_400_000;
  }
  return days;
}

export function leaveYearStartIso(
  iso: string,
  startMonth: number,
  startDay: number,
): string {
  const [year, month, day] = iso.split("-").map(Number);
  const startsThisYear =
    month > startMonth || (month === startMonth && day >= startDay);
  const startYear = startsThisYear ? year : year - 1;
  return `${startYear}-${String(startMonth).padStart(2, "0")}-${String(startDay).padStart(2, "0")}`;
}

function timeZoneOffsetMs(instant: Date, timeZone: string): number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).formatToParts(instant);
  const value = (type: string) => parts.find((part) => part.type === type)?.value ?? "0";
  const hour = value("hour") === "24" ? "0" : value("hour");
  const zoned = Date.UTC(
    Number(value("year")),
    Number(value("month")) - 1,
    Number(value("day")),
    Number(hour),
    Number(value("minute")),
    Number(value("second")),
  );
  return zoned - instant.getTime();
}

/** Interpret a clock time in `timeZone` and return the UTC instant. */
export function zonedDateTimeToUtc(isoDateTime: string, timeZone: string): Date {
  const normalized = isoDateTime.includes("T") ? isoDateTime : `${isoDateTime}T00:00:00`;
  const [datePart, timePart] = normalized.split("T");
  const [year, month, day] = datePart.split("-").map(Number);
  const [hour = 0, minute = 0, second = 0] = timePart.split(":").map(Number);
  const utcGuess = Date.UTC(year, month - 1, day, hour, minute, second);
  const firstPass = utcGuess - timeZoneOffsetMs(new Date(utcGuess), timeZone);
  return new Date(utcGuess - timeZoneOffsetMs(new Date(firstPass), timeZone));
}

export function startOfZonedDay(isoDate: string, timeZone: string): Date {
  return zonedDateTimeToUtc(`${isoDate}T00:00:00`, timeZone);
}

export function addDaysIso(iso: string, days: number): string {
  return new Date(dateOnly(iso).getTime() + days * 86_400_000).toISOString().slice(0, 10);
}

export function formatLongDate(isoOrNow: string | Date, timeZone: string): string {
  const date = typeof isoOrNow === "string" ? dateOnly(isoOrNow) : isoOrNow;
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: typeof isoOrNow === "string" ? "UTC" : timeZone,
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

export function formatDisplayDate(iso: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(dateOnly(iso));
}

export function formatDateRange(startIso: string, endIso: string): string {
  if (startIso === endIso) return formatDisplayDate(startIso);
  return `${formatDisplayDate(startIso)} – ${formatDisplayDate(endIso)}`;
}

export function greetingFor(timeZone: string, now = new Date()): string {
  const hour = Number(
    new Intl.DateTimeFormat("en-GB", {
      timeZone,
      hour: "numeric",
      hourCycle: "h23",
    }).format(now),
  );
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export function roundDay(value: number): number {
  return Math.round(value * 10) / 10;
}

export function formatDays(value: number): string {
  const rounded = roundDay(value);
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}
