export const CURRENCIES: ReadonlyArray<{ code: string; name: string }> = [
  { code: "USD", name: "US dollar" },
  { code: "EUR", name: "Euro" },
  { code: "GBP", name: "British pound" },
  { code: "CHF", name: "Swiss franc" },
  { code: "CAD", name: "Canadian dollar" },
  { code: "AUD", name: "Australian dollar" },
  { code: "NZD", name: "New Zealand dollar" },
  { code: "JPY", name: "Japanese yen" },
  { code: "CNY", name: "Chinese yuan" },
  { code: "HKD", name: "Hong Kong dollar" },
  { code: "SGD", name: "Singapore dollar" },
  { code: "INR", name: "Indian rupee" },
  { code: "KRW", name: "South Korean won" },
  { code: "AED", name: "UAE dirham" },
  { code: "SEK", name: "Swedish krona" },
  { code: "NOK", name: "Norwegian krone" },
  { code: "DKK", name: "Danish krone" },
  { code: "PLN", name: "Polish złoty" },
  { code: "CZK", name: "Czech koruna" },
  { code: "HUF", name: "Hungarian forint" },
  { code: "RON", name: "Romanian leu" },
  { code: "BGN", name: "Bulgarian lev" },
  { code: "ALL", name: "Albanian lek" },
  { code: "MKD", name: "Macedonian denar" },
  { code: "RSD", name: "Serbian dinar" },
  { code: "TRY", name: "Turkish lira" },
  { code: "BRL", name: "Brazilian real" },
  { code: "MXN", name: "Mexican peso" },
  { code: "ZAR", name: "South African rand" },
];

export const LOCALES: ReadonlyArray<{ code: string; name: string }> = [
  { code: "en-US", name: "English (United States)" },
  { code: "en-GB", name: "English (United Kingdom)" },
  { code: "de-DE", name: "Deutsch (Deutschland)" },
  { code: "fr-FR", name: "Français (France)" },
  { code: "it-IT", name: "Italiano (Italia)" },
  { code: "es-ES", name: "Español (España)" },
  { code: "sq-AL", name: "Shqip (Shqipëri)" },
];

export const DEFAULT_CURRENCY = "USD";
export const DEFAULT_LOCALE = "en-US";

let displayLocale = DEFAULT_LOCALE;

export function setDisplayLocale(locale: string | null | undefined): void {
  displayLocale = locale || DEFAULT_LOCALE;
}

export function getDisplayLocale(): string {
  return displayLocale;
}
