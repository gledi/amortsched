export function fromDateValue(value: string): Date | undefined {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return undefined;

  const [, year, month, day] = match;
  const date = new Date(Number(year), Number(month) - 1, Number(day));

  if (date.getFullYear() !== Number(year) || date.getMonth() !== Number(month) - 1 || date.getDate() !== Number(day)) {
    return undefined;
  }

  return date;
}

export function toDateValue(date: Date | undefined): string {
  if (!date) return "";

  const year = String(date.getFullYear()).padStart(4, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}
