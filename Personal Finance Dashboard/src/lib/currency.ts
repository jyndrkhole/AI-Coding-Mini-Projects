/** Default for India / Asia/Kolkata users. */
export const DEFAULT_CURRENCY = "INR";
export const DEFAULT_LOCALE = "en-IN";

export const CURRENCY_OPTIONS: {
  code: string;
  label: string;
  locale: string;
  regions?: string[];
  timezones?: string[];
}[] = [
  {
    code: "INR",
    label: "₹ Indian Rupee (INR)",
    locale: "en-IN",
    regions: ["IN"],
    timezones: ["Asia/Kolkata", "Asia/Calcutta"],
  },
  {
    code: "USD",
    label: "$ US Dollar (USD)",
    locale: "en-US",
    regions: ["US"],
    timezones: ["America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles"],
  },
  {
    code: "EUR",
    label: "€ Euro (EUR)",
    locale: "en-IE",
    regions: ["DE", "FR", "IE", "ES", "IT", "NL", "AT", "BE", "PT", "FI"],
  },
  {
    code: "GBP",
    label: "£ British Pound (GBP)",
    locale: "en-GB",
    regions: ["GB"],
    timezones: ["Europe/London"],
  },
  {
    code: "AED",
    label: "د.إ UAE Dirham (AED)",
    locale: "en-AE",
    regions: ["AE"],
    timezones: ["Asia/Dubai"],
  },
  {
    code: "SGD",
    label: "S$ Singapore Dollar (SGD)",
    locale: "en-SG",
    regions: ["SG"],
    timezones: ["Asia/Singapore"],
  },
  {
    code: "AUD",
    label: "A$ Australian Dollar (AUD)",
    locale: "en-AU",
    regions: ["AU"],
    timezones: ["Australia/Sydney", "Australia/Melbourne"],
  },
  {
    code: "CAD",
    label: "C$ Canadian Dollar (CAD)",
    locale: "en-CA",
    regions: ["CA"],
    timezones: ["America/Toronto", "America/Vancouver"],
  },
  {
    code: "JPY",
    label: "¥ Japanese Yen (JPY)",
    locale: "ja-JP",
    regions: ["JP"],
    timezones: ["Asia/Tokyo"],
  },
];

const LOCALE_BY_CURRENCY = Object.fromEntries(
  CURRENCY_OPTIONS.map((c) => [c.code, c.locale])
);

export function localeForCurrency(currency: string): string {
  return LOCALE_BY_CURRENCY[currency] || DEFAULT_LOCALE;
}

export function isSupportedCurrency(code: string): boolean {
  return CURRENCY_OPTIONS.some((c) => c.code === code);
}

/** Infer currency from timezone / browser locale; falls back to INR. */
export function detectCurrencyFromLocation(
  timeZone?: string,
  language?: string
): { currency: string; locale: string } {
  const tz =
    timeZone ||
    (typeof Intl !== "undefined"
      ? Intl.DateTimeFormat().resolvedOptions().timeZone
      : undefined);
  if (tz) {
    const byTz = CURRENCY_OPTIONS.find((c) => c.timezones?.includes(tz));
    if (byTz) return { currency: byTz.code, locale: byTz.locale };
  }

  const lang =
    language ||
    (typeof navigator !== "undefined" ? navigator.language : undefined) ||
    "";
  const region = lang.includes("-") ? lang.split("-")[1]?.toUpperCase() : "";
  if (region) {
    const byRegion = CURRENCY_OPTIONS.find((c) => c.regions?.includes(region));
    if (byRegion) return { currency: byRegion.code, locale: byRegion.locale };
  }

  return { currency: DEFAULT_CURRENCY, locale: DEFAULT_LOCALE };
}

let activeCurrency = DEFAULT_CURRENCY;
let activeLocale = DEFAULT_LOCALE;

export function configureMoney(currency?: string, locale?: string) {
  const code =
    currency && isSupportedCurrency(currency) ? currency : DEFAULT_CURRENCY;
  activeCurrency = code;
  activeLocale = locale || localeForCurrency(code);
}

export function getActiveCurrency() {
  return activeCurrency;
}

export function formatMoney(
  n: number,
  currency?: string,
  locale?: string
): string {
  const code =
    currency && isSupportedCurrency(currency)
      ? currency
      : currency || activeCurrency || DEFAULT_CURRENCY;
  const loc = locale || (currency ? localeForCurrency(code) : activeLocale);
  try {
    return new Intl.NumberFormat(loc, {
      style: "currency",
      currency: code,
      maximumFractionDigits: code === "JPY" ? 0 : 2,
    }).format(n);
  } catch {
    return new Intl.NumberFormat(DEFAULT_LOCALE, {
      style: "currency",
      currency: DEFAULT_CURRENCY,
    }).format(n);
  }
}
